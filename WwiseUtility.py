import waapi
import re
import os
import random
import string


def randomString(length=3):
    characters = string.ascii_letters + string.digits  # Includes both letters and digits
    random_string = ''.join(random.choice(characters) for _ in range(length))
    return random_string

#Get all wwise objects of certain types
def getWwiseObjectList(customTypeList = None):
    typeList = ["sound", "Event", "actorMixer", "randomSequenceContainer", "switchContainer", "blendContainer", "bus", "audioFileSource","MusicSegment", "WorkUnit"]
    if customTypeList is not None:
        typeList = customTypeList
    with waapi.WaapiClient() as client:
        args = {
            "waql": f"$ from type {','.join(typeList)}",
            "options": {"return": ["name", "shortID", "id", "type", "notes", "path", "originalFilePath","activeSource"]}
        }
        search_result = client.call("ak.wwise.core.object.get", args)["return"]
    return search_result


#Return the dicts in the list that have matching value
def getItemsFromDicList(wwiseObjectList, searchString, singleItem = False):
    filteredList = [
        obj for obj in wwiseObjectList
        if any(searchString in str(value) for value in obj.values())
    ]
    if singleItem:
        return filteredList[0]
    return filteredList



#select an wwise object and open Wwise GUI windows
def selectInWwise(object, OpenWwise=False):
    with waapi.WaapiClient() as client:
        if OpenWwise:
            client.call("ak.wwise.ui.bringToForeground")
        client.call("ak.wwise.ui.commands.execute", {
            "command": "FindInProjectExplorerSyncGroup1",
            "objects": [object]
        })


def getSelectedObjects(singleItem = False):
    with waapi.WaapiClient() as client:
        returnContent = {"options": {"return": ["name", "shortID", "id", "type", "notes","parent"]}}
        result = client.call("ak.wwise.ui.getSelectedObjects",returnContent)["objects"]
        if singleItem:
            return result[0]
        return result

#return the descendants info of an wwise object
#includeSelf: if True, include the the object itself
def getDescendantsFromID(id, includeSelf = False):
    if isinstance(id, dict):
        id = id["id"]
    thisArg = ""
    if includeSelf:
        thisArg = ", this"
    with waapi.WaapiClient() as client:
        args = {
            "waql": f"$ from object \"{id}\" select descendants{thisArg}",
            "options": {"return": ["name", "shortID", "id", "type", "notes", "path", "originalFilePath","activeSource","parent"]}
        }
        search_result = client.call("ak.wwise.core.object.get", args)["return"]
        return search_result


def playWwiseEvent(eventName):
    with waapi.WaapiClient() as client:
        client.call("ak.soundengine.registerGameObj", {"gameObject": 2233445, "name": "QuickListener"})
        client.call("ak.soundengine.setDefaultListeners", {"listeners": [2233445]})
        client.call("ak.soundengine.registerGameObj", {"gameObject": 1122334, "name": "QuickPlay"})
        client.call("ak.soundengine.stopAll", {"gameObject": 1122334})
        client.call("ak.soundengine.postEvent", {"event": eventName, "gameObject": 1122334})

# Add a tag to a Wwise object path, for example: <Sound SFX> -> "\\Actor-Mixer Hierarchy\\Default Work Unit\\<Sound SFX>MySound"
def addWwisePathTag(input_string, tag):
    parts = input_string.split('\\')
    if parts:
        parts[-1] = f"{tag}{parts[-1]}"
    return '\\'.join(parts)

# For checking mathcing names without "_1P" suffix
def checkStringEquals_ignoreP(string1, string2):
    if string1.lower().endswith("_1p"):
        string1 = string1[:-3]
    if string2.lower().endswith("_1p"): 
        string2 = string2[:-3]
    return string1.lower() == string2.lower()
        
    

#target: 导入的目的地, 可以是sound也可以是父级, 为父级时自动匹配父级下所有命名相同的声音，使用id或者wwise返回的包含id的字典
#newSource: True则覆盖active source, False则创建新的Source
#newSound: True则添加新Sound(命名重复时自动加后缀), False则只导入命名匹配的Sound
#noImport：模拟运行,但不导入
#会返回一个dict list, 包含要导入的文件和在wwise里匹配到的导入目的地
def batchImportToTarget(filePaths, target, newSource=False, newSound=False, noImport=False):
    if isinstance(filePaths, str):
        filePaths = [filePaths]
    if isinstance(target, str):
        target = {"id" : target}
    targetDescendants= getDescendantsFromID(target, includeSelf=True)
    tempRenames = []
    with waapi.WaapiClient() as client:
        importItems = []
        importBrief = []
        for descendant in targetDescendants:
            name = descendant["name"]
            objectPath = descendant["path"]
            if not newSound and descendant["type"] == "Sound":#情况1 为子级Sound对象导入声音
                for filePath in filePaths:
                    fileName, extension = os.path.splitext(os.path.basename(filePath))#从path中获取没有extension的filename
                    oldFilePath = filePath
                    directory = os.path.dirname(filePath)
                    # if name == fileName:
                    if checkStringEquals_ignoreP(name, fileName):
                        originalFilePath = ""
                        subPath = ""
                        try:#从activeSource获取subPath, 获取失败时不用subPath，通常是因为sound没有任何source
                            originalFilePath = descendant["originalFilePath"]
                            subPath = re.match(r".*\\SFX\\(.+\\)", originalFilePath).group(1)
                        except:
                            subPath = ""
                        if newSource:#情况1.1 新增source
                            randomTag = randomString() #防止覆盖以前的source, 给新的音频文件加一个tag
                            newFileName = f"{fileName}_{randomTag}{extension}"
                            newFilePath = os.path.join(directory, newFileName)
                            tempRenames.append({"oldPath":filePath, "newPath":newFilePath})
                            filePath = newFilePath
                        elif subPath != "":#情况1.2 覆盖source
                            newFileName = os.path.basename(originalFilePath)
                            newFilePath = os.path.join(directory, newFileName)
                            tempRenames.append({"oldPath":filePath, "newPath":newFilePath})
                            filePath = newFilePath
                        if subPath not in ["", None]:
                            importItems.append({"audioFile": filePath,"objectPath": addWwisePathTag(objectPath,"<Sound SFX>"), "originalsSubFolder":subPath})
                        else:
                            importItems.append({"audioFile": filePath,"objectPath": addWwisePathTag(objectPath,"<Sound SFX>")})
                        importBrief.append({"audioFile": oldFilePath, "objectPath":addWwisePathTag(objectPath,"<Sound SFX>")})
            elif newSound and descendant["id"] == target["id"]: #情况2 在一个父级单位下创建新的声音
                for filePath in filePaths:
                    importBrief[filePath] = "" #加入brief
                    fileName = os.path.splitext(os.path.basename(filePath))[0]#从path中获取没有extension的filename
                    importItems.append({"audioFile": filePath,"objectPath": objectPath+f"\\<Sound SFX>{fileName}"})
                    importBrief.append({"audioFile": oldFilePath, "objectPath":objectPath+f"\\<Sound SFX>{fileName}"})
        arg = {
                "importOperation": "useExisting" if not newSound else "createNew",
                "default": {
                    "importLanguage": "SFX"
                },
                "imports": importItems
            }
        if not noImport:
            for path in tempRenames:
                os.rename(path["oldPath"], path["newPath"])
            client.call("ak.wwise.core.audio.import", arg)
            for path in tempRenames:
                os.rename(path["newPath"], path["oldPath"])
        return importBrief
    
def getSelectionInput(restriction):
    selectionType = ""
    selectionName = ""
    selection = None
    while selectionType not in restriction:
        input(f"请在wwise中选择一个有效的对象({", ".join(restriction)}), 然后回车")
        selection = getSelectedObjects(singleItem=True)
        try:
            selectionType = selection["type"]
            selectionName = selection["name"]
        except:
            print("wwise中没有选择任何对象")
            continue
        print(f"选择了: <{selectionType}>{selectionName}")
    return selection
        


def addRtpc(controlInput, propertyName, curve, target):
    with waapi.WaapiClient() as client:
        args = {
            "objects": [
                {
                    "object": target,
                    "@RTPC": [
                        {
                            "type": "RTPC",
                            "name": "",
                            "@Curve": curve,
                            "notes": "copied",
                            "@PropertyName": propertyName,
                            "@ControlInput": controlInput,
                        }
                    ],
                }
            ],
            "options": {"return": ["id", "name", "type", "@Curve"]},
        }
        result = client.call("ak.wwise.core.object.set", args)
    return result


# copy the RTPC from one object to another
def copyRtpc(id, ids, overwrite):
    global client
    if(overwrite):
        for i in range(0, len(ids), 1):
            deleteRTPC(ids[i])

    sourceRtpcs = {}
    # args = {
    #     "waql": f"\"{id}\"",
    #     "options": {"return": ["@RTPC"]},
    # }
    try:
        sourceRtpcs = getInfo(id, "@RTPC")
    except KeyError:
        if(not overwrite):
            print("Source object has no RTPC!")
            
    for i in range(0, len(sourceRtpcs), 1):
        rtpcId = sourceRtpcs[i]["id"]
        args = {
            "waql": f"\"{rtpcId}\"",
            "options": {"return": ["@PropertyName", "@ControlInput", "@Curve"]},
        }
        rtpcValues = client.call("ak.wwise.core.object.get", args)["return"][0]
        try:
            curve = rtpcValues["@Curve"]
            curve.pop("id")
            curve.pop("@Flags")
            curve["type"] = "Curve"
            controlInput = rtpcValues["@ControlInput"]["id"]
            propertyName = rtpcValues["@PropertyName"]
            for i in range(0, len(ids), 1):
                addRtpc(controlInput, propertyName, curve, ids[i])
        except KeyError:
            print("Source object has incomplete RTPC")



# 删除一个对象下所有RTPC
def deleteRTPC(id):
    with waapi.WaapiClient() as client:
        rtpc = getInfo(id, "@RTPC")
        for i in range(0, len(rtpc), 1):
            rtpcId = rtpc[i]["id"]
            args = {"object": rtpcId, "property" : "RTPC" ,"value": None}
            client.call("ak.wwise.core.object.setReference", args)


#返回一个wwise对象的指定信息
def getInfo(id, info):
    with waapi.WaapiClient() as client:
        args = {
            "waql": f"\"{id}\"",
            "options": {"return": [info]},
        }
        result = client.call("ak.wwise.core.object.get", args)

        return result["return"][0][info]
