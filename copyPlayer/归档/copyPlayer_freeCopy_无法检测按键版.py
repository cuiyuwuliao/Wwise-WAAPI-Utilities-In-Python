import threading
import pyperclip
import waapi
import queue
import asyncio
import re
import time


# Set this to True for standard mode, False for tray mode
STANDARD_MODE = True
FLUSH_MODE = True

# Queue for communication between threads
request_queue = queue.Queue()
response_queue = queue.Queue()
refresh_time = 90
# Event to signal clipboard check
clipboard_event = threading.Event()
NZDictionary = {}
WwiseDictionary = []  # Global variable for WwiseDictionary
stop_event = threading.Event()  # Initialize the stop event
firstBuild = True  # Flag for first build

def custom_print(*args, **kwargs):
    """Custom print function that flushes output based on FLUSH_MODE."""
    flush = FLUSH_MODE
    print(*args, flush=flush, **kwargs)

def extract_sound_id(input_string):
    pattern = r'\$NZID:([^\s]+)'
    match = re.search(pattern, input_string)
    if match:
        sound_id = match.group(1)
        return True, sound_id
    else:
        return False, ''

def is_valid_string(s):
    return (s.startswith('{') and s.endswith('}')) or bool(s) and all(c.isalnum() or c == '_' for c in s)

def buildWwiseDictionary():
    global WwiseDictionary  # Declare as global
    firstBuild = False
    if WwiseDictionary == []:
        firstBuild = True
    WwiseDictionary.clear() 
    try:
        with waapi.WaapiClient() as client:
            args = {
                "waql": f"$ from type sound, Event, actorMixer, folder, randomSequenceContainer, switchContainer, blendContainer, bus, rtpc",
                "options": {"return": ["name", "shortID", "id", "type", "notes"]}
            }
            search_result = client.call("ak.wwise.core.object.get", args)["return"]
            for objects in search_result:
                WwiseDictionary.append({
                    "name": objects["name"],
                    "shortID": objects["shortID"],
                    "id": objects["id"],
                    "type": objects["type"],
                    "NZID": extract_sound_id(objects["notes"])[1]  # Get only the sound ID
                })
    except Exception as e:
        custom_print(e)
        custom_print("读取wwise信息失败")
        return []
    custom_print("已同步wwise信息")
    if firstBuild:
        custom_print("!_已同步wwise信息!_")
        firstBuild = False
    return WwiseDictionary

def waapi_event_loop():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    while not stop_event.is_set():
        try:
            event = request_queue.get(timeout=0.1)
            result = 0
            if event == "$refreshWwiseDictionary":
                result = buildWwiseDictionary()  # Update global WwiseDictionary
                response_queue.put((result, True))
                continue
            try:
                with waapi.WaapiClient() as client:
                    if event.startswith("select:"):
                        event = event.replace("select:", "")
                        result = client.call("ak.wwise.ui.bringToForeground")
                        arg = {
                            "command": "FindInProjectExplorerSyncGroup1",
                            "objects": [event]
                        }
                        result = client.call("ak.wwise.ui.commands.execute", arg)
                    else:
                        client.call("ak.soundengine.registerGameObj", {"gameObject": 2233445, "name": "QuickListener"})
                        client.call("ak.soundengine.setDefaultListeners", {"listeners": [2233445]})
                        client.call("ak.soundengine.registerGameObj", {"gameObject": 1122334, "name": "QuickPlay"})
                        client.call("ak.soundengine.stopAll", {"gameObject": 1122334})
                        result = client.call("ak.soundengine.postEvent", {"event": event, "gameObject": 1122334})
            except Exception as e:
                custom_print(f"!WAAPI error: {e}")
        except queue.Empty:
            continue

def background_task():
    current_time = time.time()
    lastTickTime = time.time()
    while not stop_event.is_set():
        try:
            last_text = ""
            valid = True
            num_repeat_copy = 0
            while not stop_event.is_set():
                clipboard_event.wait()  # Wait for the signal to check clipboard
                clipboard_event.clear()  # Clear the event for future checks
                current_text = pyperclip.paste()

                current_time = time.time()
                elapsed_time = current_time - lastTickTime
                if elapsed_time > refresh_time:  # 每60秒刷新一次字典
                    request_queue.put("$refreshWwiseDictionary") 
                    lastTickTime = current_time

                if current_text.endswith(" ") or not is_valid_string(current_text):
                    continue
                if last_text != current_text:
                    valid = True
                if valid:
                    match = None
                    for item in WwiseDictionary:
                        if (str(item["id"]) == current_text or
                            item["name"] == current_text or
                            item["shortID"] == current_text or
                            item["NZID"] == current_text): 
                            if item["type"] == "Event":
                                request_queue.put(item["name"]) 
                                match = item
                            else:
                                if match is None or match["type"] != "Event":
                                    match = item
                            continue
                    if match is None:
                        valid = False
                    else:
                        if current_text == last_text.replace(" ", ""):
                            num_repeat_copy += 1
                            if num_repeat_copy > 2:
                                request_queue.put(f"select:{match['id']}") 
                                num_repeat_copy = 0
                        custom_print(f"!_$ name: {match['name']}\n$ type:{match['type']}\n$ GUID:{match['id']}\n$ shortID:{match['shortID']}\n$ NZID:{match['NZID']}\n!_")
                        pyperclip.copy(f"{current_text} ")
                        last_text = current_text
                time.sleep(0.1)
        except Exception as e:
            time.sleep(10)

def start_task():
    stop_event.clear()
    threading.Thread(target=background_task, daemon=True).start()
    threading.Thread(target=waapi_event_loop, daemon=True).start()
    threading.Thread(target=clipboard_monitor, daemon=True).start()

def clipboard_monitor():
    while not stop_event.is_set():
        clipboard_event.set()  # Signal to check the clipboard
        time.sleep(0.4)

def stop_task():
    stop_event.set()
    with waapi.WaapiClient() as client:
        try:
            client.call("ak.soundengine.stopAll", {"gameObject": 1122334})
        except Exception:
            custom_print("无法终止对象的声音")

if STANDARD_MODE:
    buildWwiseDictionary()  # Build the dictionary initially
    if not WwiseDictionary:
        custom_print("!_读取Wwise信息失败, 请确保Wwise已打开!_")
    start_task()
    while not stop_event.is_set():
        time.sleep(1)  # Keep the main thread alive
