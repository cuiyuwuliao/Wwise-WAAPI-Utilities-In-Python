import json
import re
import os
from waapi import WaapiClient
# file_path = 'C:\\Users\\Administrator\\Desktop\\tools\\syncSoundID\\SoundID.json'
file_path = 'D:\\.tjp\\v1\\UsNpnYkd\\P4NZ\\UnrealProject\\Nezha\\Saved\\CloudDoc\\Json\\BattleAudioEffect.json'#占位路径


client = WaapiClient()
prjectInfo = client.call("ak.wwise.core.getProjectInfo")
file_path = prjectInfo['directories']['soundBankOutputRoot']
path_components = file_path.split(os.sep)

#从wwise内设置好的bnk输出路径内提取到UE工程的绝对路径，然后再和音频总表的相对路径组合，实现在任意电脑上运行
try:
    unreal_project_index = path_components.index("UnrealProject")
    unreal_project_folder = os.path.join(*path_components[:unreal_project_index + 1])
    relative_path = 'Nezha\\Saved\\CloudDoc\\Json\\BattleAudioEffect.json'#音频总表的相对路径
    file_path = os.path.join(unreal_project_folder, relative_path)
    file_path = file_path.replace(':', ':\\').replace('\\', '\\') #矫正一下路径格式
except ValueError:
    print("The folder 'UnrealProject' was not found in the path.")


try:
    with open(file_path, 'r', encoding='utf-8') as file:
        data = json.load(file)
except Exception as e:
    print(e)
    print()
    file_path = input("File not found. Please enter a valid path: ").strip("'\"")
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            data = json.load(file)
    except Exception as e:
        print(f"Error opening file: {e}")


NZList = []
for element in data:
    event_name = element[1]
    sound_id = element[0]
    NZList.append([event_name, sound_id])
# Connect to Wwise via WAAPI


# 查询，注意语法，
# waql: 使用id时候必须包含引号和{}, 使用waql语句时必须以包含引号然后以$开头
# info必须为一个string list
def get_info(waql, info):
    global client
    if waql.startswith('{') and waql.endswith('}'):
        waql = f'"{waql}"'
    args = {"waql": waql,"options" : {"return": info}}
    if info == None:
        args = {"waql": waql} 
    result = client.call("ak.wwise.core.object.get", args)
    return result["return"]

eventList = get_info("$ from type event", ["path", "name", "id"])


def extract_sound_id(input_string):
    # Define the regex pattern to match "$NZID:sound_id"
    pattern = r'\$NZID:([^ ]+)'

    # Search for the pattern in the input string
    match = re.search(pattern, input_string)

    if match:
        sound_id = match.group(1)
        return True, sound_id  # Return True and the extracted sound_id
    else:
        return False, ''  # Return False and an empty string

def modify_string_with_sound_id(input_string, sound_id):
    # Define the regex pattern to match "$NZID:sound_id"
    pattern = r'\$NZID:([^ ]+)'

    # Search for the pattern in the input string
    match = re.search(pattern, input_string)

    if match:
        # If a match is found, replace it with the new sound_id followed by a newline
        modified_string = re.sub(pattern, f'$NZID:{sound_id}\n', input_string)
    else:
        # If no match is found, create a new "$NZID:sound_id" at the beginning followed by a newline
        modified_string = f'$NZID:{sound_id}\n' + input_string

    return modified_string


def checkInSubLists(target, list):
    for subList in list:
        if target in subList:
            return True
    return False

def getNZIdByName(name):
    global NZList
    for subList in NZList:
        if name == subList[0]:
            return subList[1]
    return -1

modified_events = []
unmodified_events = []

for event in eventList:
    eventId = event["id"]
    eventNotes = get_info(event["id"], ["notes"])[0]["notes"]
    eventName = event["name"]
    rt, value = extract_sound_id(eventName)
    newNotes = ""
    NZId = getNZIdByName(eventName)

    if NZId != -1:  # notes中存在soundID，刷新soundID
        newNotes = modify_string_with_sound_id(eventNotes, NZId)
    elif rt:  # 事件名存在于NZ表中，刷新soundID
        newNotes = modify_string_with_sound_id(eventNotes, NZId)

    if newNotes != eventNotes:
        args = {
            "objects": [
                {
                    "object": eventId,
                    "notes": newNotes
                }
            ]
        }
        result = client.call("ak.wwise.core.object.set", args)
        modified_events.append(eventName)  # Add to modified list
    else:
        unmodified_events.append(eventName)  # Add to unmodified list


print("Modified Events:", modified_events)
print()
print("Unmodified Events:", unmodified_events)
input("\n结束, 任意键退出")

client.disconnect()