import waapi
import os
import re
import sys


allowDupes = False
clearSwitch = False
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
    children = []
    selection = get_selected_objects()
    selectionIds = []
    itemInfoList = []
    switchGroupList = []
    for item in selection:
        itemId = item['id']
        query = f"$ from object \"{itemId}\" select children"
        type = get_info(item["id"], ["type"])[0]['type']
        if(type != "SwitchContainer"):
            print("check")
            continue
        children += (get_info(query, None))
    selectionIds = []
    itemInfoList = []
    switchGroupList = []


    for item in children:
        itemId = item['id']
        selectionIds.append(itemId)
        itemInfo = get_info(f"\"{itemId}\"", ["id","name","parent"])
        itemParentDic = itemInfo[0]['parent']
        itemParentType = get_info(itemParentDic["id"], ["type"])[0]['type']
        if(itemParentType != "SwitchContainer"):
            continue
        switchGroupDic = get_info(itemParentDic["id"], ["SwitchGroupOrStateGroup"])[0]['SwitchGroupOrStateGroup']
        query = f"$ from object \"{switchGroupDic["id"]}\" select children"
        try:
            switches = get_info(query, None)
        except:
            print(f"{item['name']} switch容器没有指定switch group, 请指定后重试")
            client.disconnect()
            sys.exit()
            break
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
        switches = list[0]["switches"]
        for switch in switches:
            bestMatch = ""
            bestScore = 0.0
            for item in list:
                for scores in item["scores"]:
                    if scores["id"] == switch["id"]:
                        if scores["score"] > bestScore:
                            bestScore = scores["score"]
                            bestMatch = item["id"]
                        break
            if bestMatch != "":
                args = {
                    "child" : bestMatch,
                    "stateOrSwitch" : switch["id"]
                }
                client.call("ak.wwise.core.switchContainer.addAssignment", args)


                


client.disconnect()


