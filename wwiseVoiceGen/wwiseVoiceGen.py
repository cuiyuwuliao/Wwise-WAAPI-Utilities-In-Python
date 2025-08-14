import waapi
import time
import random
import secrets
import string
import os

try:
    with waapi.WaapiClient() as client:
        client.call("ak.soundengine.registerGameObj", {"gameObject": 2233445, "name": "QuickListener"})
        client.call("ak.soundengine.setDefaultListeners", {"listeners": [2233445]})
except Exception as e:
    print(f"WAAPI error: {e}")




def playEvent(eventName):
    try:
        with waapi.WaapiClient() as client:
            randomObject = int(f"{random.randint(1, 9_999_999):07d}")
            client.call("ak.soundengine.registerGameObj", {"gameObject": randomObject, "name": "QuickPlay"})

            randomPitch = random.randint(0,300)
            client.call("ak.soundengine.setRTPCValue", {"rtpc": "pitch", "value": randomPitch, "gameObject": randomObject})

            randomVolume = random.randint(-3,0)
            client.call("ak.soundengine.setRTPCValue", {"rtpc": "volume", "value": randomVolume, "gameObject": randomObject})
            
            result = client.call("ak.soundengine.postEvent", {"event": eventName, "gameObject": randomObject})
            playingID = result['return']
            return playingID
    except Exception as e:
        print(f"WAAPI error: {e}")

def stopPlayingID(playingID):
    try:
        with waapi.WaapiClient() as client:
            client.call("ak.soundengine.stopPlayingID", {"playingId": playingID, "transitionDuration": 200, "fadeCurve": 4})
    except Exception as e:
        print(f"WAAPI error: {e}")

while True:
    duration = random.uniform(0.2, 0.4)
    playingID = playEvent("randomVoice2")
    symbols = "!@#$%^&*"
    secure_random = ''.join(secrets.choice(symbols) for _ in range(12))
    os.system('cls')
    print(f"怪物说: {secure_random}")  # Example: "^%$#@&*!@#$"
    time.sleep(duration)
    stopPlayingID(playingID)
