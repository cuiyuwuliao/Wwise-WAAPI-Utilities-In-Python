import os
import re
import sys
from pydub import AudioSegment
from pydub import effects
import stat
import waapi
import xml.etree.ElementTree as ET
from P4 import P4, P4Exception

reconcile_folders = []
needReconcile = True

def extractFromString(input_string):
    substrings = input_string.split(' "')
    if substrings[0].startswith('"'):
        substrings[0] = substrings[0][1:]
    cleaned_substrings = []
    for substring in substrings:
        cleaned_substrings.append(substring.split('"')[0])
    return cleaned_substrings

def remove_read_only_attribute(filename):
    file_stat = os.stat(filename)
    os.chmod(filename, file_stat.st_mode | stat.S_IWUSR)


def getWwiseList():
    client = waapi.WaapiClient()
    wwiseList = []
    project_info = client.call("ak.wwise.core.getProjectInfo")
    xml_input_paths = []
    
    # Construct XML input paths
    xml_input_paths.append(os.path.join(project_info['directories']['root'], 'Actor-Mixer Hierarchy'))
    xml_input_paths.append(os.path.join(project_info['directories']['root'], 'Interactive Music Hierarchy'))
    
    # Construct WAV folder path
    wav_folder_path = os.path.join(project_info['directories']['originals'], 'SFX')
    reconcile_folders.append(wav_folder_path)
    # Get selected objects
    selection = client.call("ak.wwise.ui.getSelectedObjects")
    id_list = [obj['id'] for obj in selection['objects']]
    
    for directory_path in xml_input_paths:
        for filename in os.listdir(directory_path):
            if filename.endswith(".wwu"):
                file_path = os.path.join(directory_path, filename)
                tree = ET.parse(file_path)
                root = tree.getroot()
                
                for sound in root.findall(".//Sound"):
                    sound_name = sound.get('Name')
                    sound_id = sound.get("ID")
                    if sound_id not in id_list:
                        continue
                    for audio_file_source in sound.findall(".//AudioFileSource"):
                        audio_file = audio_file_source.find("AudioFile")
                        audio_file = audio_file.text
                        
                        # Construct the full file path
                        full_audio_file_path = os.path.join(wav_folder_path, audio_file)
                        full_audio_file_path = full_audio_file_path.replace('\\', '/')  # Convert to single slash format
                        
                        if full_audio_file_path not in wwiseList:
                            wwiseList.append(full_audio_file_path)
                for audio_file_source in root.findall(".//AudioFileSource"):
                    audio_file_source_id = audio_file_source.get("ID")
                    if audio_file_source_id not in id_list:
                        continue
                    audio_file = audio_file_source.find("AudioFile")
                    audio_file = audio_file.text
                    # Construct the full file path
                    full_audio_file_path = os.path.join(wav_folder_path, audio_file)
                    full_audio_file_path = full_audio_file_path.replace('\\', '/')  # Convert to single slash format
                    if full_audio_file_path not in wwiseList:
                        wwiseList.append(full_audio_file_path)
    return wwiseList

def reconcile_offline_work(folders, reconcile):
    current_dir = ""
    if getattr(sys, 'frozen', False):
        current_dir = os.path.dirname(sys.executable)
    else:
        current_dir = os.path.dirname(os.path.abspath(__file__))
    workspace = ""
    try:
        parent_dir = os.path.dirname(current_dir)
        workspacefile = os.path.join(parent_dir, ".config.txt")
        print("使用公用config")
    except:
        print("使用独立config")
        workspacefile = os.path.join(current_dir, ".config.txt")
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

def handleFileList(fileList, amount, forceGain, normalize):
    change = False
    if isinstance(fileList, str):
        fileList = extractFromString(fileList)
    if len(fileList) == 0:
        print("没有可编辑的wav文件")
    for file in fileList:
        file.strip('"')
        file.strip('\'')
        remove_read_only_attribute(file)
        if(adjust(file, amount, forceGain, normalize)):
            change = True
    return change

# filename = input("wav file: ")
def convert_to_float(value):
    try:
        return float(value)
    except ValueError:
        print(f"您输入的不是数字, 您在搞笑吗\n")
        return None  
def adjust(filename, amount, forceGain, normalize):
    sound = AudioSegment.from_file(filename, format="wav")
    originalVolume = sound.dBFS
    processedSound = sound + amount
    if(processedSound.max_dBFS > -0.5):
        if(forceGain):
            processedSound.export(filename, format="wav")
            print(f"{filename}从{round(originalVolume, 2)}改到了{round(processedSound.dBFS,2)}")
            return True
        elif(normalize):
            normalizedSound = effects.normalize(sound, 0.1)
            normalizedSound.export(filename, format="wav")
            print(f"{filename}从{round(originalVolume, 2)}正常化到了{round(normalizedSound.dBFS,2)}")
            return True
        print(f"这个音频再加音量就爆了: {filename} , 所以没有做修改")
        return False
    print(f"{filename}从{round(originalVolume, 2)}改到了{round(processedSound.dBFS,2)}")
    processedSound.export(filename, format="wav")
    return True
    
amount = None
forceGain = False
normalize = False
while amount == None:
    inputstring = input("\n说明: 输入一个音量数字然后回车, 负号代表减, 数字后面加f表示允许爆音, 在数字后面加n爆音时自动normalize, 在数字前加w可指定wwise外音频\n\n请输入一个数字: ")
    if inputstring.endswith('f'):
        inputstring = inputstring[:-1]
        forceGain = True
    if inputstring.endswith('n'):
        inputstring = inputstring[:-1]
        normalize = True
    if inputstring.startswith('w'):
        inputstring = inputstring[1:]
        amount = convert_to_float(inputstring)
        fileList = input("拖入一个需要调整的wav文件,然后回车(纯外用, wwise内音频不会被修改): ")
        handleFileList(fileList, amount, forceGain, normalize)
        needReconcile = False
    else:
        fileList = getWwiseList()
        amount = convert_to_float(inputstring)
        change = handleFileList(fileList, amount, forceGain, normalize)
        if needReconcile and change:
            reconcile_offline_work(reconcile_folders, True)
    



print("音量调整成功, 任意键退出")
input()
sys.exit()