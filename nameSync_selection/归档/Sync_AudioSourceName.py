import xml.etree.ElementTree as ET
import os
import shutil
import stat
import waapi
import sys
from P4 import P4, P4Exception

client = waapi.WaapiClient()

current_dir = ""
if getattr(sys, 'frozen', False):
    current_dir = os.path.dirname(sys.executable)
else:
    current_dir = os.path.dirname(os.path.abspath(__file__))
workspacefile = os.path.join(current_dir, "config.txt")
workspace = ""
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


# Function to remove read-only attribute
def remove_read_only(file_path):
    """Remove the read-only attribute from a file."""
    try:
        checkout_file(file_path)
        os.chmod(file_path, stat.S_IWRITE)  # Change the file's mode to writable
    except Exception as e:
        print(f"Failed to change permissions for {file_path}: {e}")

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

# Function to modify the XML file and rename WAV files
def modify_audio_file_in_xml(xml_file_path, wav_folder_path, id_list):
    # Remove read-only attribute from the XML file
   

    tree = ET.parse(xml_file_path)
    root = tree.getroot()

    changes_count = 0
    changes = []

    # Iterate through AudioFileSource elements
    for sound in root.findall(".//Sound"):
        sound_name = sound.get('Name')
        sound_id = sound.get('ID')
        if(sound_id not in id_list):
            continue
        print(sound_name)
        for audio_file_source in sound.findall(".//AudioFileSource"):
            audio_file_source_name = audio_file_source.get('Name')
            audio_file_source_id = audio_file_source.get('ID')
            audio_file = audio_file_source.find("AudioFile")
            language = audio_file_source.find("Language")
            
            # Check if the audio_file_source_id is in the provided list
            if audio_file_source_id not in id_list:
                continue  # Skip if ID does not match

            if language.text != "SFX":
                print(audio_file.text + " original命名不统一, 因为分类不为音效所以没有更名")
                continue
            if audio_file is not None:
                old_value = audio_file.text
                # Only change the file name, keeping the path
                path, _ = os.path.split(old_value)  # Split the path and file name
                new_value = f"{path}/{audio_file_source_name}.WAV" if path else f"{audio_file_source_name}.WAV"
                
                # Change the audio file path in the XML
                if audio_file.text != new_value:
                    audio_file.text = new_value
                    changes_count += 1
                    changes.append(f"Changed '{old_value}' to '{audio_file.text}' in '{xml_file_path}'")

                # Rename the actual WAV file if it exists
                old_wav_path = os.path.join(wav_folder_path, old_value)
                new_wav_path = os.path.join(wav_folder_path, new_value)
                if old_wav_path != new_wav_path:
                    if os.path.isfile(old_wav_path):
                        remove_read_only(old_wav_path)  # Remove read-only attribute before renaming
                        try:
                            shutil.move(old_wav_path, new_wav_path)
                            changes.append(f"Renamed WAV file '{old_wav_path}' to '{new_wav_path}'")
                        except Exception as e:
                            changes.append(f"Failed to rename WAV file '{old_wav_path}': {e}")
                    else:
                        changes.append(f"没有找到对应的wav文件: '{old_wav_path}'，所以只更改了wwu引用，跳过original命名")

    # Write the modified XML back to the file if changes were made
    if changes_count > 0:
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

selection = client.call("ak.wwise.ui.getSelectedObjects")
id_list = [obj['id'] for obj in selection['objects']]

all_paths = [os.path.join(project_info['directories']['root'], 'Actor-Mixer Hierarchy'), 
             os.path.join(project_info['directories']['root'], 'Interactive Music Hierarchy'),
             os.path.join(project_info['directories']['originals'], 'SFX')
             ]


# Initialize total changes
total_changes = 0
all_changes = []
# Check if the XML input is a file or a directory
if os.path.isfile(xml_input_paths[0]) and xml_input_paths[0].endswith(".wwu"):
    changes_count, changes = modify_audio_file_in_xml(xml_input_paths[0], wav_folder_path, id_list)
    total_changes += changes_count
    all_changes.extend(changes)
elif os.path.isdir(xml_input_paths[0]):
    total_changes, all_changes = process_directory(xml_input_paths, wav_folder_path, id_list)
else:
    print("未能成功读取到wwu")

# Print the results
if total_changes > 0:
    for change in all_changes:
        print(change)
    print(f"\n总共修改: {total_changes}")
else:
    print("没有重新命名的original文件")

reconcile_offline_work(all_paths, True)
print("original重命名完毕, 您可以关闭了")