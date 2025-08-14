import xml.etree.ElementTree as ET
import os
import shutil
import stat
import waapi
import sys
import time
from P4 import P4, P4Exception
client = waapi.WaapiClient()
client.call("ak.wwise.core.project.save")


print("正在保存工程\n")
time.sleep(1.5)


current_dir = ""
if getattr(sys, 'frozen', False):
    current_dir = os.path.dirname(sys.executable)
else:
    current_dir = os.path.dirname(os.path.abspath(__file__))
workspace = ""

workspacefile = os.path.join(current_dir, ".config.txt")
try:
    parent_dir = os.path.dirname(current_dir)
    workspacefile = os.path.join(parent_dir, ".config.txt")
    print("使用公用config")
except:
    print("使用独立config")




try:
    with open(workspacefile, 'r') as file:
        workspace = file.readline().strip()
        print("当前workspace:", workspace)
except FileNotFoundError:
    print("没有找到workspace.")
except Exception as e:
    print(f"没有找到workspace: {e}")

p4 = P4()
p4.client = workspace

try:
    p4.connect()
    p4.client = workspace
except P4Exception as e:
    for error in e.errors:
        print(f"无法连接到您的workspace, 请您确定workspace配置正确, 命名先帮您改了, 记得在p4里reconcile一下: {error}")


def checkout_file(file_path):
    global p4
    try:
        p4.run('edit', file_path)
    except P4Exception as e:
        for error in e.errors:
            print(f"无法checkout文件, 先帮您改了, 命名记得在p4里reconcile一下: {error}")

def reconcile_offline_work(folders, reconcile):
    global p4
    print("正在和p4同步离线文件, 请不要退出, 如果不慎退出, 记得手动reconcile")
    try:
        for folder in folders:
            if reconcile:
                print(f"Reconciling offline work in folder: {folder}")
                try:
                    # Attempt to reconcile, targeting all files in the folder
                    reconcile_results = p4.run_reconcile(f"{folder}/...")
                    # Check if there are any results
                    if not reconcile_results:  # No files to reconcile
                        continue  # Skip to the next folder
                except P4Exception as e:
                    if "no file(s) to reconcile" in str(e):
                        continue  # Skip to next folder
                    else:
                        print(f"An error occurred during reconciliation: {e}")
            else:
                print(f"Skipping reconciliation for folder: {folder}")

    except P4Exception as e:
        print(f"An error occurred: {e}")
        print("本地文件reconcile同步出现异常, 请在p4手动reconcile")
    finally:
        if reconcile:
            p4.disconnect()
            print("Disconnected from Perforce.")

# Function to remove read-only attribute
def remove_read_only(file_path):
    """Remove the read-only attribute from a file."""
    try:
        checkout_file(file_path)
        os.chmod(file_path, stat.S_IWRITE)  # Change the file's mode to writable
    except Exception as e:
        print(f"Failed to change permissions for {file_path}: {e}")

name_list = []
# Function to modify the XML file and rename WAV files
def modify_audio_file_in_xml(xml_file_path, wav_folder_path, id_list):
    global client
    tree = ET.parse(xml_file_path)
    root = tree.getroot()

    changes_count = 0
    changes = []
    

    # Iterate through AudioFileSource elements
    for sound in root.findall(".//Sound"):
        sound_name = sound.get('Name')
        sound_name_lower = sound_name.lower()
        if sound_name_lower.endswith('_1p') or sound_name_lower.endswith('_3p'):
            sound_name = sound_name[:-3]
        sound_id = sound.get('ID')
        if(sound_id not in id_list):
            continue
        
        version = 0
        for audio_file_source in sound.findall(".//AudioFileSource"):
            change = False
            audio_file = audio_file_source.find("AudioFile")
            audio_file_name_old = audio_file.text
            language = audio_file_source.find("Language")
            if language.text != "SFX":
                print(audio_file.text + " original命名不统一, 因为分类不为音效所以没有更名")
                continue

            version += 1
            if(version == 1):
                new_name = f"{sound_name}"
            else:
                new_name = f"{sound_name}_Ver{version}"
            audio_file_source.set('Name', new_name)
            if audio_file_source.get("Name") != sound_name:
                change = True


            if audio_file is not None:
                old_value = audio_file.text
                # Only change the file name, keeping the path
                path, _ = os.path.split(old_value)  # Split the path and file name
                new_value = f"{path}\\{new_name}.wav" if path else f"{new_name}.wav"
                
                
                # Change the audio file path in the XML
                if audio_file.text != new_value:
                    common_reference = False
                    for name in name_list:
                        if audio_file.text == name["oldfile"]:
                            audio_file.text = name["newfile"]
                            common_reference = True
                            continue
                    if common_reference:
                        continue
                    audio_file.text = new_value
                    change = True
                    changes.append(f"Changed '{old_value}' to '{audio_file.text}' in '{xml_file_path}'")
                
                name_list.append(dict(oldfile=audio_file_name_old, newfile=new_value))
                # Rename the actual WAV file if it exists
                old_wav_path = os.path.join(wav_folder_path, old_value)
                new_wav_path = os.path.join(wav_folder_path, new_value)
                if old_wav_path != new_wav_path:
                    if os.path.isfile(old_wav_path):
                        remove_read_only(old_wav_path)  # Remove read-only attribute before renaming
                        try:
                            directory = os.path.dirname(new_wav_path)
                            if not os.path.exists(directory):
                                os.makedirs(directory)
                            shutil.move(old_wav_path, new_wav_path)
                            old_akd = os.path.splitext(old_wav_path)[0] + '.akd'
                            new_akd = os.path.splitext(new_wav_path)[0] + '.akd'
                            try:
                                shutil.move(old_akd, new_akd)
                            except:
                                print("akd命名失败")
                            changes.append(f"Renamed WAV file '{old_wav_path}' to '{new_wav_path}'")
                        except Exception as e:
                            change = False
                            print(f"移动{old_wav_path}的wav文件到{new_wav_path}时失败:{e}")
                            changes.append(f"Failed to rename WAV file '{old_wav_path}': {e}")
                    else:
                        changes.append(f"没有找到对应的wav文件: '{old_wav_path}',所以只更改了wwu引用,跳过original命名")

                if change:
                    changes_count += 1
                else:
                    continue
    for sound in root.findall(".//Sound"):
        sound_name = sound.get('Name')
        for audio_file_source in sound.findall(".//AudioFileSource"):
            audio_file = audio_file_source.find("AudioFile")
            audio_file_name_old = audio_file.text
            for name in name_list:
                if audio_file.text == name["oldfile"] and audio_file.text != name["newfile"]:
                    audio_file.text = name["newfile"]
                    print(f"{sound_name}存在相同original引用，original一并修改成了{name["newfile"]}")
                    changes_count += 1
                    continue


    # Write the modified XML back to the file if changes were made
    if changes_count > 0:
        client.call("ak.wwise.core.project.save")
        remove_read_only(xml_file_path)
        tree.write(xml_file_path, encoding='utf-8', xml_declaration=True)
        print(f"Modified XML file saved as: {xml_file_path}")
    
    return changes_count, changes

# Function to process files in a directory
def process_directory(directory_paths, wav_folder_path, id_list):
    total_changes = 0
    all_changes = []
    for directory_path in directory_paths:
        for filename in os.listdir(directory_path):
            if filename.endswith(".wwu"):
                file_path = os.path.join(directory_path, filename)
                changes_count, changes = modify_audio_file_in_xml(file_path, wav_folder_path, id_list)
                total_changes += changes_count
                all_changes.extend(changes)

    return total_changes, all_changes

project_info = client.call("ak.wwise.core.getProjectInfo")
# Get directories from the Wwise
xml_input_paths = []
xml_input_paths.append(os.path.join(project_info['directories']['root'], 'Actor-Mixer Hierarchy'))
xml_input_paths.append(os.path.join(project_info['directories']['root'], 'Interactive Music Hierarchy'))
wav_folder_path = os.path.join(project_info['directories']['originals'], 'SFX')

all_paths = [os.path.join(project_info['directories']['root'], 'Actor-Mixer Hierarchy'), 
             os.path.join(project_info['directories']['root'], 'Interactive Music Hierarchy'),
             os.path.join(project_info['directories']['originals'], 'SFX')
             ]


selection = client.call("ak.wwise.ui.getSelectedObjects")
id_list = [obj['id'] for obj in selection['objects']]


# Initialize total changes
total_changes = 0
all_changes = []


total_changes, all_changes = process_directory(xml_input_paths, wav_folder_path, id_list)


# Print the results
if total_changes > 0:
    for change in all_changes:
        print(change)
    print(f"\n总共修改: {total_changes}")
    reconcile_offline_work(all_paths, True)
    print("original重命名完毕,您可以关闭了")
else:
    print("没有重新命名的original文件")

