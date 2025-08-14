import waapi
import os
import re
import sys


allowDupes = False
clearSwitch = True
client = waapi.WaapiClient()

def remove_duplicates(dict_list, key):
    seen = set()
    unique_list = []
    for d in dict_list:
        if d[key] not in seen:
            seen.add(d[key])
            unique_list.append(d)
    return unique_list

def remove_dicts_by_key(item_list, key, value):
    return [item for item in item_list if item.get(key) != value]

def group_items_by_parent_id(item_info_list):
    grouped_items = {}
    
    # Group items by parentId
    for item in item_info_list:
        parent_id = item["parentId"]
        if parent_id not in grouped_items:
            grouped_items[parent_id] = []  # Initialize a new list for this parentId
        grouped_items[parent_id].append(item)  # Append the item to the corresponding list

    # Convert the dictionary values to a list of lists
    return list(grouped_items.values())

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

def jaccard_similarity(str1, str2):
    # Split strings into sets of words, handling both spaces and underscores
    set1 = set(re.split(r'[\s_]+', str1.lower()))
    set2 = set(re.split(r'[\s_]+', str2.lower()))
    # Calculate intersection and union
    intersection = len(set1.intersection(set2))
    union = len(set1.union(set2))
    # Return Jaccard similarity
    return intersection / union if union != 0 else 0.0

def get_selected_objects():
    global client
    result = client.call("ak.wwise.ui.getSelectedObjects")
    return result.get("objects", {})


def clear_assigned_objects():
    selection = get_selected_objects()
    for item in selection:
        id = item["id"]
        type = get_info(id, ["type"])[0]['type']
        if(type != "SwitchContainer"):
            continue
        Assignments = client.call("ak.wwise.core.switchContainer.getAssignments", {"id" : id})["return"]
        if len(Assignments) >0:
            for item in Assignments:
                client.call("ak.wwise.core.switchContainer.removeAssignment", item)
if clearSwitch:
    clear_assigned_objects()
else:
    selection = get_selected_objects()
    selectionIds = []
    itemInfoList = []
    switchGroupList = []
    for item in selection:
        itemId = item['id']
        selectionIds.append(itemId)
        itemInfo = get_info(f"\"{itemId}\"", ["id","name","parent"])
        itemParentDic = itemInfo[0]['parent']
        itemParentType = get_info(itemParentDic["id"], ["type"])[0]['type']
        if(itemParentType != "SwitchContainer"):
            continue
        switchGroupDic = get_info(itemParentDic["id"], ["SwitchGroupOrStateGroup"])[0]['SwitchGroupOrStateGroup']
        query = f"$ from object \"{switchGroupDic["id"]}\" select children"
        switches = get_info(query, None)
        switchGroupList.append({"name":switchGroupDic["name"],"id": switchGroupDic["id"], "switches": switches})

        itemInfoList.append({"name": itemInfo[0]["name"],
                            "id": itemId,
                            "parentName":itemParentDic["name"],
                            "parentId":itemParentDic["id"],
                            "switchGroupName": switchGroupDic["name"],
                            "switchGroupId": switchGroupDic["id"],
                            "switches": switches
                            })
    switchGroupList = remove_duplicates(switchGroupList, "id")

    for item in itemInfoList:
        switches = item["switches"]
        similarityBoard = []
        bestMatch = ""
        bestScore = 0.0
        for switch in switches:
            score = jaccard_similarity(switch["name"], item["name"])
            if score > bestScore:
                bestScore = score
                bestMatch = switch["id"]
            similarityBoard.append({"id":switch["id"],
                                    "score":score})
        similarityBoard.sort(key=lambda x: x["score"], reverse=True)
        item["scores"] = similarityBoard
        item["bestScore"] = bestScore
        if bestScore == 0:    
            continue
        
    dividedList = group_items_by_parent_id(itemInfoList)
    for list in dividedList:
        list.sort(key=lambda x: x["bestScore"], reverse=True)
        areadyMatched = []
        for item in list:
            bestMatch = ""
            for scores in item["scores"]:
                if scores["id"] in areadyMatched and not allowDupes:
                    continue
                bestMatch = scores["id"]
                areadyMatched.append(bestMatch)
                break
            if bestMatch != "":
                args = {
                    "child" : item["id"],
                    "stateOrSwitch" : bestMatch
                }
                client.call("ak.wwise.core.switchContainer.addAssignment", args)
client.disconnect()



# {
#     "child": "{7A12D08F-B0D9-4403-9EFA-2E6338C197C1}",
#     "stateOrSwitch": "{A076AA65-B71A-45BB-8841-5A20C52CE727}"
# }
# print(info)
# print(info[0]["parent"])

# switch_id = "\"" +'{05393FD2-56D4-4A82-92C1-2D21E648CC15}' + "\"" 

# result = get_info(switch_id, ["SwitchGroupOrStateGroup"])

# switchGroupID = result[0]["SwitchGroupOrStateGroup"]["id"]
# switchGroupID = "\"" + switchGroupID + "\"" 
# print(f"! Switch Group: {result}")

# query = f"$ from object {switchGroupID} select children"
# swiches = get_info(query, None)



# busList = get_info("$ from type bus", ["path", "name"])

# try:
#     selectionId = get_selected_objects()[0]["id"]
# except Exception as e:
#     input("无效的选择, 请在wwise中点击选中一个switch作为起始点")
#     client.disconnect()
