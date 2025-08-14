import waapi
import os
import re
import sys
import time


log_data = []
client = waapi.WaapiClient()


def read_log_file(file_path):
    log_data = []
    try:
        with open(file_path, 'r') as file:
            # Read all lines from the file
            for line in file:
                # Replace actual tabs with the string '\t'
                formatted_line = line.replace('\t', '\\t').strip()
                log_data.append(formatted_line)
    except FileNotFoundError:
        print(f"Error: The file '{file_path}' was not found.")
    except Exception as e:
        print(f"An error occurred: {e}")
    
    return log_data

def parse_log_entry(entry):
    parts = entry.split('\\t')
    
    while len(parts) < 8:
        parts.append('added')  # Append empty strings to ensure there are 8 fields
    return {
        "Timestamp": parts[0],
        "Type": parts[1],
        "Description": parts[2],
        "Object Name": parts[3],
        "Game Object Name": parts[4],
        "Object ID": parts[5],
        "Game Object ID": parts[6],
        "Scope": parts[7]
    }

def recall_api_calls(log_data):
    # Skip the header
    parsed_entries = [parse_log_entry(entry) for entry in log_data[1:]]
    # Sort entries by timestamp
    sorted_entries = sorted(parsed_entries, key=lambda x: x["Timestamp"])

    # Execute API calls with delays based on timestamps
    last_time = 0
    for entry in sorted_entries:
        timestamp = entry["Timestamp"]
        # Convert timestamp to seconds
        time_parts = list(map(float, timestamp.split(':')))
        current_time = time_parts[0] * 3600 + time_parts[1] * 60 + time_parts[2]
        # Wait for the appropriate amount of time
        if current_time > last_time:
            time.sleep(current_time - last_time)  # Delay until the next call
        execute_api_from_log(entry)
        last_time = current_time

def execute_api_from_log(entry):
    """Execute API calls based on the parsed log entry."""
    api_call = entry["Description"]
    gameObject_id = int(entry["Game Object ID"]) if entry["Game Object ID"] else 0
    object_name = entry["Object Name"]
    object_id = entry["Object ID"]
    listeners = [gameObject_id]
    name = entry["Game Object Name"] or "UnnamedObject"
    position_data = extract_position_data(api_call)
    scaling_factor = extract_scaling_factor(api_call)
    rtpc = extract_rtpc_value(api_call)
    switch = extract_switch(api_call)

    if "RegisterGameObj" in api_call:
        client.call("ak.soundengine.registerGameObj", {"gameObject": gameObject_id, "name": name})
    elif "SetPosition" in api_call:
        client.call("ak.soundengine.setPosition", {"gameObject": gameObject_id, "position": position_data})
    elif "SetDefaultListeners" in api_call:
        client.call("ak.soundengine.setDefaultListeners", {"listeners": listeners})
    elif "PostEvent" in api_call:
        client.call("ak.soundengine.postEvent", {"event": object_name, "gameObject": gameObject_id})
    elif "SetAttenuationScalingFactor" in api_call:
        client.call("ak.soundengine.setScalingFactor", {"gameObject": gameObject_id, "attenuationScalingFactor": scaling_factor})
    elif "SetSwitch" in api_call:
        client.call("ak.soundengine.setSwitch", {"switchGroup": object_name, "switchState": switch, "gameObject": gameObject_id})
    elif "SetState" in api_call:
        client.call("ak.soundengine.setState", {"stateGroup": object_name, "state": switch})
    elif "SetRTPCValue" in api_call:
        client.call("ak.soundengine.setRTPCValue", {"rtpc": object_name, "value": rtpc, "gameObject": gameObject_id})
    elif "UnregisterGameObj" in api_call:
        client.call("ak.soundengine.unregisterGameObj", {"gameObject": gameObject_id})
    elif "StopAll" in api_call:
        client.call("ak.soundengine.stopAll", {"gameObject": gameObject_id})
    elif "StopPlayingID" in api_call:
        client.call("ak.soundengine.stopPlayingID", {"playingId": object_id,"transitionDuration": 100,"fadeCurve": 4})
    elif "SetGameObjectAuxSendValues" in api_call:
        print("待做功能: AuxSend")
    else:
        print(f"Unknown API call: {api_call}")

def extract_scaling_factor(description):
    """Extract the attenuation scaling factor from the description string."""
    match = re.search(r"Scale factor:\s*(\w+)", description)
    if match:
        return float(match.group(1))
    return None

def extract_switch(description):
    """Extract the switch name from the SetSwitch description string."""
    if ("Switch" in description):
        match = re.search(r"SetSwitch:\s*To\s*(\w+)", description)
    else:
        match = re.search(r"SetState:\s*To\s*(\w+)", description)
    if match:
        return match.group(1)
    return None

def extract_rtpc_value(description):
    """Extract the RTPC value from the SetRTPCValue description string."""
    match = re.search(r"Value: Value: \s*(\w+)", description)
    if match:
        return float(match.group(1))
    return None

def extract_position_data(description):
    """Extract position data from the SetPosition description."""
    # Example format: SetPosition: Position:(X:107198,Y:363383,Z:4040.4), Front:(X:1,Y:0,Z:0), Top:(X:0,Y:0,Z:1)
    match = re.search(r"Position:\(X:(.*?),Y:(.*?),Z:(.*?)\), Front:\(X:(.*?),Y:(.*?),Z:(.*?)\), Top:\(X:(.*?),Y:(.*?),Z:(.*?)\)", description)
    if match:
        return {
            "position": {
                "x": float(match.group(1)),
                "y": float(match.group(2)),
                "z": float(match.group(3))
            },
            "orientationFront": {
                "x": float(match.group(4)),
                "y": float(match.group(5)),
                "z": float(match.group(6))
            },
            "orientationTop": {
                "x": float(match.group(7)),
                "y": float(match.group(8)),
                "z": float(match.group(9))
            }
        }
    return {}
file_path = input("拖入你的prof.txt文件")
log_data = read_log_file(file_path)
recall_api_calls(log_data)

client.disconnect()




# log_data = [
#     "Timestamp\tType\tDescription\tObject Name\tGame Object Name\tObject ID\tGame Object ID\tScope",
#     "0:0:0.498\tAPI Call\tRegisterGameObj: BP_Projectile_Ability_3001293.TsAkComponent (ID:775714816)\t\tBP_Projectile_Ability_3001293.TsAkComponent\t\t112233\tGame Object",
#     "0:0:0.498\tAPI Call\tSetPosition: Position:(X:107198,Y:363383,Z:4040.4), Front:(X:1,Y:0,Z:0), Top:(X:0,Y:0,Z:1)\t\tBP_Projectile_Ability_3001293.TsAkComponent\t\t112233\tGame Object",
#     "0:0:0.565\tAPI Call\tSetDefaultListeners: PlayerCameraManager0.AkComponent_0\t\t\t\t112233\tGame Object",
#     "0:0:0.498\tAPI Call\tPostEvent\tha\tBP_Projectile_Ability_300103a0.TsAkComponent\t1423728865\t112233\tGame Object",
#     "0:0:1.498\tAPI Call\tPostEvent\tha\tBP_Projectile_Ability_300103a0.TsAkComponent\t1423728865\t112233\tGame Object",
#     "0:0:1.440\tAPI Call\tSetSwitch: To Bone_Hollow_Large_Drag\tItem_Switch_BeHit\tTransport/Soundcaster\t2628773320\t18446744073709551614\tGame Object",
#     "0:0:1\tAPI Call\tSetSwitch: To Bone_Hollow_Large_Drag\tItem_Switch_BeHit\tTransport/Soundcaster\t2628773320\t18446744073709551614\tGame Object",
#     "0:0:1\tAPI Call\tSetState: To State Rainy\tState_Global_Weather\t\t279122783\t\t\t",
#     "0:0:1\tAPI Call\tSetRTPCValue: Value: 4\t\tBP_NzPlayerController0.AkComponent_0\t\t8748092410880\tGame Object",
#     "0:0:1\tAPI Call\tUnregisterGameObj\t\tGlobal_Event\t\t8747337129792\tGame Object",
#     "0:0:1\tAPI Call\tSetAttenuationScalingFactor: Scale factor: 1\t\tBP_Sapphire_PT_030.TsAkComponent\t\t8743953438720\tGame Object"
# ]


# soundcaster的gameobject id
# client.call("ak.soundengine.postEvent", {"event": "ha_01","gameObject": 18446744073709551614})

# client.call("ak.soundengine.registerGameObj", {"gameObject": 1122334, "name": "listener"})
# client.call("ak.soundengine.registerGameObj", {"gameObject": 4332211, "name": "MyGameObjectName"})
# client.call("ak.soundengine.setDefaultListeners", {"listeners": [1122334]})
# arg_pos = {"gameObject": 4332211,"position": {
# "orientationFront": {
# "x": 1,
# "y": 0,
# "z": 0
# },
# "orientationTop": {
# "x": 0,
# "y": 0,
# "z": 1
# },
# "position": {
# "x": 5,
# "y": 10,
# "z": 100
# }
# }
# }
# client.call("ak.soundengine.setPosition", arg_pos)
# client.call("ak.soundengine.postEvent", {"event": "ha_01","gameObject": 4332211})