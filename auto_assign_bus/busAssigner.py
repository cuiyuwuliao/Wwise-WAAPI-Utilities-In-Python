import waapi
import os
import re
import sys

client = waapi.WaapiClient()
busList = []
allowList = ["RandomSequenceContainer", "SwitchContainer","Sound","ActorMixer","BlendContainer"]

def get_selected_objects():
    global client
    result = client.call("ak.wwise.ui.getSelectedObjects")
    return result.get("objects", {})

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

def jaccard_similarity(str1, str2):
    # Split strings into sets of words, handling both spaces and underscores
    set1 = set(re.split(r'[\s_]+', str1.lower()))
    set2 = set(re.split(r'[\s_]+', str2.lower()))
    # Calculate intersection and union
    intersection = len(set1.intersection(set2))
    union = len(set1.union(set2))
    # Return Jaccard similarity
    return intersection / union if union != 0 else 0.0

import re

def contains_all_substrings(string_a, string_b):
    # Convert both strings to lowercase
    string_a = string_a.lower()
    string_b = string_b.lower()
    
    # Split the strings into lists of substrings
    substrings_a = string_a.split('_')
    substrings_b = string_b.split('_')
    
    # Create a set for substrings in A
    set_a = set()
    
    nameHasSpecifier = False
    nameSpecifier = ""
    for sub in substrings_a:
        # Check if the substring ends with a 4-digit integer
        match = re.search(r'(\d{4})$', sub)
        if match:
            # Store the first digit of the 4-digit integer
            set_a.add(sub[:-4]+match.group(0)[0])
            nameHasSpecifier = True
            nameSpecifier = sub
        else:
            # Otherwise, store the entire substring
            set_a.add(sub)

    busHasSpecifier = False
    # Check if all substrings in B are in A
    for sub in substrings_b:
        match = re.search(r'(\d{4})$', sub)
        if match:
            # Check if the first digit of the 4-digit integer is in set_a
            busHasSpecifier = True
            if sub[:-4]+match.group(0)[0] not in set_a:
                return False
            if not sub.endswith("000") and sub != nameSpecifier:
                return False
        elif sub not in set_a:
            return False
    if busHasSpecifier == nameHasSpecifier:
        return True
    
    return False


def setBus(item):
    global busList, allowList
    itemId = item['id']
    itemName = item['name']
    bestMatch = ""
    bestScore = 0.0
    for item in busList:
        busName = item['name']
        if busName.startswith(("Bus_", "bus_")):
            busName = busName[4:]  # Remove the first 4 characters
        busPath = item['path']
        if contains_all_substrings(itemName, busName):
            if bestMatch == "":
                bestMatch = busPath
            score = jaccard_similarity(busName, itemName)
            if score > bestScore:
                bestScore = score
                bestMatch = busPath
    if bestMatch == "":
        print(f"{itemName}没有匹配的bus")
        return
    arg = {
        "objects": [
            {
                "object": itemId, 
                "@OutputBus": bestMatch,
                "@OverrideOutput": "True"
            }
        ]
    }
    client.call("ak.wwise.core.object.set", arg)
    print(f"将{itemName}发送到了{bestMatch}")


busList = get_info("$ from type bus", ["path", "name"])
selection = get_selected_objects()
selectionIds = []
for item in selection:
    itemType = get_info(item["id"], ["type"])[0]['type']
    if itemType not in allowList:
        print(f"选中的{itemType}不是可以设置发送的类型：{','.join(allowList)}")
        continue
    setBus(item)
    selectionIds.append(item)

client.disconnect()



