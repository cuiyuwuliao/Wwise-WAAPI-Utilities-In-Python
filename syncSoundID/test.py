import json
import os
import re
from waapi import WaapiClient
# file_path = 'C:\\Users\\Administrator\\Desktop\\tools\\syncSoundID\\SoundID.json'
file_path = 'D:\\.tjp\\v1\\UsNpnYkd\\P4NZ\\UnrealProject\\Nezha\\Saved\\CloudDoc\\Json\\BattleAudioEffect.json'

client = WaapiClient()
result = client.call("ak.wwise.core.getProjectInfo")
sound_bank_output_root = result['directories']['soundBankOutputRoot']
# Define the path for the sample text file
sample_file_path = os.path.join(sound_bank_output_root, 'sample.txt')
# Create and write to the sample text file
with open(sample_file_path, 'w') as file:
    file.write("This is a sample text file created in the sound bank output root.")
    
print(sound_bank_output_root)
client.disconnect()