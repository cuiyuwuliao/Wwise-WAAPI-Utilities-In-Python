import waapi
import sys

client = waapi.WaapiClient()
client.call("ak.wwise.core.project.save")


def get_selected_objects():
    global client
    result = client.call("ak.wwise.ui.getSelectedObjects")
    return result.get("objects", {})

# 查询，注意语法，
# waql: 使用id时候必须包含引号和{}, 使用waql语句时必须以包含引号然后以$开头
# info必须为一个string list
def get_info(waql, info):
    global client
    args = {
        "waql": waql,
        "options" : {"return": info}
        }
    result = client.call("ak.wwise.core.object.get", args)
    return result["return"]

def SetProperty(object, property, value):
    arg = {
        "object": object,
        "property": property,
        "value": value
    }
    client.call("ak.wwise.core.object.setProperty", arg)

try:
    selectionReturn = get_selected_objects()
    selectionIds = []
    for item in selectionReturn:
        selectionIds.append(item["id"])
except Exception as e:
    input("无效的选择, 请在wwise中点击选中一个actor mixer作为起始点")
    client.disconnect()
    sys.exit()

mainTable = {}
for Id in selectionIds:
    info = get_info("\"" + Id +"\"", ["makeUpGain", "Volume", "path"])[0]
    if "makeUpGain" in info and "Volume" in info:
        mainTable[Id] = info

for Id in mainTable.keys():
    info = mainTable[Id]
    volume = info["Volume"]
    makeUpGain = info["makeUpGain"]
    path = info["path"]
    if volume != None and makeUpGain != None:
        if(volume != 0):
            newGain = makeUpGain+volume 
            if newGain > 96 or newGain < -96:
                print(f"注意!!!!!!!{path}的makeUpGain要被加爆了!!!所以没有更改!!!")
                continue
            SetProperty(Id, "Volume", 0)
            SetProperty(Id, "MakeUpGain", newGain)
            print(f"{path}: 音量{volume}已归零")

