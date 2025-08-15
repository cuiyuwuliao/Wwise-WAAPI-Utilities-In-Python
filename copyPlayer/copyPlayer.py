import threading
import pyperclip
import waapi
import queue
import asyncio
import re
import time
import keyboard

# Set this to True for standard mode, False for tray mode
STANDARD_MODE = True
FLUSH_MODE = True

# Queue for communication between threads
request_queue = queue.Queue()
response_queue = queue.Queue()
stop_event = threading.Event()  # Initialize the stop event

refreshRate = 60
lastRefreshTime = 0
NZDictionary = {}
WwiseDictionary = []  # Global variable for WwiseDictionary
firstBuild = True  # Flag for first build
copyStrike = {"count": 0, "lastStrikeTime":0}

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
    return (s.startswith('{') and s.endswith('}')) or bool(s) and all(c.isalnum() or c == '_' or c == ' ' for c in s)

def buildWwiseDictionary():
    global WwiseDictionary  # Declare as global
    firstBuild = False
    if WwiseDictionary == []:
        firstBuild = True
    WwiseDictionary.clear() 
    try:
        with waapi.WaapiClient() as client:
            args = {
                "waql": f"$ from type sound, Event, actorMixer, folder, randomSequenceContainer, switchContainer, blendContainer, bus, WorkUnit, MusicSegment, MusicPlaylistContainer, MusicSwitchContainer",
                "options": {"return": ["name", "shortID", "id", "type", "notes"]}
            }
            search_result = client.call("ak.wwise.core.object.get", args)["return"]
            for objects in search_result:
                WwiseDictionary.append({
                    "name": objects["name"],
                    "shortID": objects.get("shortID", None),
                    "id": objects["id"],
                    "type": objects["type"],
                    "NZID": extract_sound_id(objects["notes"])[1]  # Get only the sound ID
                })
    except Exception as e:
        custom_print(e)
        custom_print("读取wwise信息失败")
        WwiseDictionary = []
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
                            "command": "FindInProjectExplorerSelectionChannel1",
                            "objects": [event]
                        }
                        result = client.call("ak.wwise.ui.commands.execute", arg)
                    elif event.startswith("stop:"):
                        client.call("ak.soundengine.stopAll", {"gameObject": 1122334})
                    else:
                        client.call("ak.soundengine.registerGameObj", {"gameObject": 2233445, "name": "QuickListener"})
                        client.call("ak.soundengine.setDefaultListeners", {"listeners": [2233445]})
                        client.call("ak.soundengine.registerGameObj", {"gameObject": 1122334, "name": "QuickPlay"})
                        result = client.call("ak.soundengine.postEvent", {"event": event, "gameObject": 1122334})
            except Exception as e:
                custom_print(f"!WAAPI error: {e}")
        except queue.Empty:
            continue



def start_task():
    stop_event.clear()
    threading.Thread(target=waapi_event_loop, daemon=True).start()
    keyboard.add_hotkey('ctrl+c', onCopy)
    keyboard.add_hotkey('ctrl+v', onPaste)
    keyboard.wait()

def stop_task():
    stop_event.set()
    with waapi.WaapiClient() as client:
        try:
            client.call("ak.soundengine.stopAll", {"gameObject": 1122334})
        except Exception:
            custom_print("无法终止对象的声音")


def findInWwiseDictionary(string):
    match = None
    for item in WwiseDictionary:
        if (item["id"] == string or
            item["name"] == string or
            item["shortID"] == string or
            item["NZID"] == string): 
            if item["type"] == "Event":
                request_queue.put(item["name"]) 
                match = item
            else:
                # 检索结果非唯一时, 优先使用event
                if match is None or match["type"] != "Event":
                    match = item
            continue
    return match


def onPaste():
    request_queue.put("stop:") 

def onCopy():
    global lastRefreshTime, copyStrike
    time.sleep(0.01)#等开Windows复制好内容
    current_text = pyperclip.paste()
    if not is_valid_string(current_text):
        return
    
    #连续复制四次在wwise打开
    openInWwise = False
    lastStrikeTime = copyStrike["lastStrikeTime"]
    currentTime = time.time()
    copyStrike["lastStrikeTime"] = currentTime
    if currentTime - lastStrikeTime < 0.5:
        copyStrike["count"] += 1
        if copyStrike["count"] > 2:
            openInWwise = True
    else:
        copyStrike["count"] = 0

    if(currentTime - lastRefreshTime > 1800): #每半个小时强制刷新一次
        lastRefreshTime = currentTime
        request_queue.put("$refreshWwiseDictionary") 
        response_queue.get()


    match = findInWwiseDictionary(current_text)
    if match is not None:
        custom_print(f"!_$ name: {match['name']}\n$ type:{match['type']}\n$ GUID:{match['id']}\n$ shortID:{match['shortID']}\n$ NZID:{match['NZID']}\n!_")
        if openInWwise:
            request_queue.put(f"select:{match['id']}") 
    else:
        # 如果字典不是最新的, 刷新后再试一下
        if (currentTime - lastRefreshTime > refreshRate) or WwiseDictionary == []:
            lastRefreshTime = currentTime
            request_queue.put("$refreshWwiseDictionary") 
            response_queue.get()
            match = findInWwiseDictionary(current_text)
            if match is not None:
                custom_print(f"!_$ name: {match['name']}\n$ type:{match['type']}\n$ GUID:{match['id']}\n$ shortID:{match['shortID']}\n$ NZID:{match['NZID']}\n!_")
                if openInWwise:
                    request_queue.put(f"select:{match['id']}") 

if STANDARD_MODE:
    buildWwiseDictionary()  # Build the dictionary initially
    if not WwiseDictionary:
        custom_print("!_读取Wwise信息失败, 请确保Wwise已打开!_")
    start_task()
    while not stop_event.is_set():
        time.sleep(1)  # Keep the main thread alive


        
