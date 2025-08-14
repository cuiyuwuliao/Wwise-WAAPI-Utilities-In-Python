import xml.etree.ElementTree as ET
import os
import stat
import waapi

client = waapi.WaapiClient()

# Function to collect referenced WAV base file names from XML
def collect_referenced_wav_files(xml_file_path):
    try:
        tree = ET.parse(xml_file_path)
        root = tree.getroot()
        referenced_files = set()

        # Iterate through AudioFileSource elements to collect referenced WAV file names
        for audio_file_source in root.findall(".//AudioFileSource"):
            audio_file = audio_file_source.find("AudioFile")
            if audio_file is not None:
                old_value = audio_file.text
                if old_value:
                    referenced_files.add(os.path.splitext(os.path.basename(old_value))[0].upper())

        return referenced_files
    except Exception as e:
        print(f"Error processing file {xml_file_path}: {e}")
        return set()  # Return an empty set on error

# Function to remove read-only attribute
def remove_read_only(file_path):
    """Remove the read-only attribute from a file."""
    try:
        os.chmod(file_path, stat.S_IWRITE)  # Change the file's mode to writable
    except Exception as e:
        print(f"Failed to change permissions for {file_path}: {e}")

# Function to process files in a directory and delete unreferenced WAV files
def process_directory(directory_paths, wav_folder_path):
    total_deleted = 0
    all_deleted_files = []
    referenced_files_set = set()

    # Collect referenced WAV files from all XML files
    for directory_path in directory_paths:
        for filename in os.listdir(directory_path):
            if filename.endswith(".wwu"):
                file_path = os.path.join(directory_path, filename)
                referenced_files_set.update(collect_referenced_wav_files(file_path))

    # Check and delete unreferenced WAV files in the wav_folder_path recursively
    for root, _, files in os.walk(wav_folder_path):
        for wav_file in files:
            file_to_delete = os.path.join(root, wav_file)
            base_name, _ = os.path.splitext(wav_file)  # Get the base name and ignore the extension
            base_name = base_name.upper()  # Convert to uppercase for comparison
            if base_name not in referenced_files_set:  # Compare base names
                if os.path.isfile(file_to_delete):  # Check if it is a file
                    remove_read_only(file_to_delete)  # Remove read-only attribute
                    try:
                        os.remove(file_to_delete)
                        all_deleted_files.append(wav_file)
                        total_deleted += 1
                    except PermissionError as e:
                        print(f"PermissionError: {e} while deleting {file_to_delete}")
                    except Exception as e:
                        print(f"An unexpected error occurred: {e} while deleting {file_to_delete}")

    return total_deleted, all_deleted_files

result = client.call("ak.wwise.core.getProjectInfo")
# Get directories from Wwise
xml_input_paths = []
xml_input_paths.append(os.path.join(result['directories']['root'], 'Actor-Mixer Hierarchy'))
xml_input_paths.append(os.path.join(result['directories']['root'], 'Interactive Music Hierarchy'))
wav_folder_path = os.path.join(result['directories']['originals'], 'SFX')

# Initialize total deleted files
total_deleted = 0
all_deleted_files = []

# Process directories and delete unreferenced WAV files
total_deleted, all_deleted_files = process_directory(xml_input_paths, wav_folder_path)

# Print the results
if total_deleted > 0:
    for deleted_file in all_deleted_files:
        print(f"删除了多余的音频样本: '{deleted_file}'")
    print(f"\n总共删除文件数量(包含akd文件): {total_deleted}")
else:
    print("没有找到多余的音频样本.")