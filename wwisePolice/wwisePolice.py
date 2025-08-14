import waapi
import re
import os
import time
from datetime import datetime

FLUSH_MODE = True


def custom_print(*args, **kwargs):
    """Custom print function that flushes output based on FLUSH_MODE."""
    flush = FLUSH_MODE
    print(*args, flush=flush, **kwargs)



NZDictionary = []
lastNZDictionary = []

    
def checkWwiseMedia():
    try:
        with waapi.WaapiClient() as client:
            # scopeExample = "$ from type sound, Event, actorMixer, folder ,randomSequenceContainer,switchContainer,blendContainer,bus, rtpc"
            args = {
                "waql": "$ from type event select children select target select this, descendants where type = \"sound\"",
                "options": {"return": ["name", "id", "originalFilePath"]}
            }
            search_result = client.call("ak.wwise.core.object.get", args)["return"]

            outputString = ""
            lostFileList = []
            for objects in search_result:
                args = {
                    "waql": f"$ from object \"{objects["id"]}\" select activeSource",
                    "options": {"return": ["originalFilePath", "type"]}
                }

                activeSourceResult = client.call("ak.wwise.core.object.get", args)["return"]
                soundName = objects["name"]
                activeSourceType = ""
                activeSourcePath = ""
                try:
                    activeSourceType =  activeSourceResult[0]["type"]
                except:
                    activeSourceType = ""
                try:
                    activeSourcePath =  activeSourceResult[0]["originalFilePath"]
                except:
                    activeSourcePath = ""

                if activeSourceType == "":
                    outputString += f"$ source为空: {soundName}\n"
                    continue

                if activeSourceType == 'AudioFileSource':
                    if not (os.path.isfile(activeSourcePath)) and soundName not in lostFileList:
                        outputString += f"$ source丢失: {soundName}\n"
                        lostFileList.append(soundName)
            if outputString != "":
                outputString = f"!!_警告: 以下Wwise文件丢失, 请立即解决\n{outputString}!_"
            custom_print(f"无资源丢失")
            custom_print(outputString)
    except Exception as e:
        custom_print(e)
        custom_print("验证音频信息失败")
        return False
    return True

def extract_sound_id(input_string):
    pattern = r'\$NZID:([^\s]+)'
    match = re.search(pattern, input_string)
    if match:
        sound_id = match.group(1)
        return True, sound_id
    else:
        return False, ''

def getAllEventNotes():
    newNZDictionary = []
    try:
        with waapi.WaapiClient() as client:
            args = {
                "waql": f"$ from type Event",
                "options": {"return": ["name", "notes"]}
            }
            search_result = client.call("ak.wwise.core.object.get", args)["return"]
            for objects in search_result:
                rt, NzId = extract_sound_id(objects["notes"])
                if not rt:
                    continue
                newNZDictionary.append({
                    "name" : objects["name"],
                    "NZID" : NzId
                })
            return newNZDictionary
    except Exception as e:
        custom_print(e)
        custom_print("获取事件信息失败")
        return []



while True:
    custom_print(f"new loop({datetime.now()})")
    NZDictionary = getAllEventNotes()
    custom_print(f"事件个数:{len(NZDictionary)}")
    if lastNZDictionary == []:
        lastNZDictionary = NZDictionary
    if NZDictionary != []:
        lastNameList = {item['name'] for item in lastNZDictionary}
        NameList = {item['name'] for item in NZDictionary}
        removedNames = [item for item in lastNameList if item not in NameList]
        if len(removedNames) > 0:
            custom_print(f"!!_警告:\n发现编辑器引用事件已从Wwise删除, 如果是您删的, 请确保无误删\n{removedNames}!_")
            lastNZDictionary = NZDictionary  # Update lastNZDictionary
    checkWwiseMedia()
    time.sleep(120) 

