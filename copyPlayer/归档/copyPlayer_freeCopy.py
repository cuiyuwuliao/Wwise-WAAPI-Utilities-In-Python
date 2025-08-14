import sys
import time
import threading
from PIL import Image, ImageDraw
import pystray
from pystray import MenuItem, Icon
import pyperclip
import waapi
import queue
import asyncio
import re
from reapy import reascript_api as RPR

# Queue for communication between threads
request_queue = queue.Queue()
response_queue = queue.Queue()

# Event to signal clipboard check
clipboard_event = threading.Event()
NZDictionary = {}

def extract_sound_id(input_string):
    # Define the regex pattern to match "$NZID:sound_id"
    pattern = r'\$NZID:([^\s]+)'

    # Search for the pattern in the input string
    match = re.search(pattern, input_string)

    if match:
        sound_id = match.group(1)
        return True, sound_id  # Return True and the extracted sound_id
    else:
        return False, ''  # Return False and an empty string
    
def buildNZDictionary():
    global NZDictionary
    try:
        with waapi.WaapiClient() as client:
            args = {
                "waql": f"$ from type Event",
                "options": {"return": ["name", "notes"]}
            }
            search_result = client.call("ak.wwise.core.object.get", args)["return"]
            for event in search_result:
                rt, NzId = extract_sound_id(event["notes"])
                NzId = NzId.strip()
                if(rt):
                    NZDictionary[NzId] = event["name"]
    except Exception as e:
        print(e)
        print("批量读取NZID信息失败")
        return
    print("已关联NZID信息")


def is_valid_string(s):
    return (s.startswith('{') and s.endswith('}')) or bool(s) and all(c.isalnum() or c == '_' for c in s)

# Function to create an icon image
def create_image(width, height):
    image = Image.new('RGB', (width, height), (255, 255, 255))
    dc = ImageDraw.Draw(image)
    dc.ellipse((0, 0, width, height), fill=(255, 0, 0))
    return image


    
# Function to run the WAAPI event loop in a dedicated thread
def waapi_event_loop():
    global NZDictionary
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    while not stop_event.is_set():
        try:
            event = request_queue.get(timeout=0.1)
            result = 0
            try:
                with waapi.WaapiClient() as client:
                    if event in NZDictionary:
                        event = NZDictionary[event]
                    args = {
                        "waql": f"$ from object \"Event:{event}\"",
                        "options": {"return": ["name", "id", "shortId", "notes"]}
                    }
                    if(event.startswith('{') and event.endswith('}')):
                        args["waql"] = f"$ from object \"{event}\""
                    search_result = client.call("ak.wwise.core.object.get", args)
                    if(search_result is None):
                        response_queue.put(("not an event", False))
                        print(f"未搜索到事件名或ID:{event}")
                        continue
                    search_result = search_result["return"]
                    if len(search_result) != 1:
                        response_queue.put(("not an event", False))
                        print(f"未搜索到事件名或ID:{event}")
                        continue
                    eventName = search_result[0]['name']
                    eventGUID = search_result[0]['id']
                    eventSortID = search_result[0]['shortId']
                    eventNotes = search_result[0]['notes']
                    re, NZId = extract_sound_id(eventNotes)
                    print(f"$ name: {eventName}\n$ GUID:{eventGUID}\n$ shortID:{eventSortID}\n$ NZID:{NZId}\n")
                    client.call("ak.soundengine.registerGameObj", {"gameObject": 2233445, "name": "QuickListener"})
                    client.call("ak.soundengine.setDefaultListeners", {"listeners": [2233445]})
                    client.call("ak.soundengine.registerGameObj", {"gameObject": 1122334, "name": "QuickPlay"})
                    result = client.call("ak.soundengine.postEvent", {"event": eventName, "gameObject": 1122334})
                response_queue.put((result, True))
            except Exception as e:
                print(f"WAAPI error: {e}")
                response_queue.put((result, False))
        except queue.Empty:
            continue

# Function to run your background tasks
def background_task():
    while not stop_event.is_set():
        try:
            last_text = ""
            valid = True
            while not stop_event.is_set():
                clipboard_event.wait()  # Wait for the signal to check clipboard
                clipboard_event.clear()  # Clear the event for future checks
                current_text = pyperclip.paste()
                if current_text.endswith(" ") or not is_valid_string(current_text):
                    continue
                if last_text != current_text:
                    valid = True
                if valid:
                    request_queue.put(current_text)
                    try:
                        response_text, success = response_queue.get(timeout=1.0)
                        if success:
                            pyperclip.copy(f"{current_text} ")
                        else:
                            valid = False
                    except queue.Empty:
                        valid = False
                last_text = current_text
                time.sleep(0.1)
        except Exception as e:
            print(f"Background task error: {e}")
            time.sleep(1)  # Optional: add a delay before restarting

# Function to start the background thread
def start_task(icon, item):
    stop_event.clear()
    threading.Thread(target=background_task, daemon=True).start()
    threading.Thread(target=waapi_event_loop, daemon=True).start()
    update_menu(icon, "停止监控")
    # Start the clipboard monitoring
    threading.Thread(target=clipboard_monitor, daemon=True).start()

# Function to monitor the clipboard
def clipboard_monitor():
    while not stop_event.is_set():
        clipboard_event.set()  # Signal to check the clipboard
        time.sleep(0.3)  # Adjust as needed for clipboard checking frequency

# Function to stop the background thread
def stop_task(icon, item):
    stop_event.set()
    update_menu(icon, "启动监控")
    with waapi.WaapiClient() as client:
        try:
            client.call("ak.soundengine.stopAll", {"gameObject": 1122334})
        except Exception:
            print(f"无法终止对象的声音")

# Function to exit the application
def exit_action(icon, item):
    stop_event.set()
    icon.stop()

# Function to update the menu item text
def update_menu(icon, item_text):
    icon.menu = pystray.Menu(
        MenuItem(item_text, stop_task if item_text == "停止监控" else start_task),
        MenuItem("退出", exit_action)
    )

buildNZDictionary()

# Initialize the stop event
stop_event = threading.Event()

# Create the system tray icon
icon = Icon("test_icon", create_image(64, 64), "moonPlayer", menu=pystray.Menu(
    MenuItem("停止监控", stop_task),
    MenuItem("退出", exit_action)
))

# Automatically start the task
start_task(icon, None)

# Run the icon
icon.run()