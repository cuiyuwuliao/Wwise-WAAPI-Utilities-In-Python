import os
import sys
from PyQt5.QtWidgets import (QApplication, QMainWindow, QTableWidget, QTableWidgetItem, 
                             QVBoxLayout, QWidget, QPushButton, QScrollArea, 
                             QMessageBox, QHBoxLayout, QHeaderView)
from PyQt5.QtCore import Qt
import xml.etree.ElementTree as ET
import shutil
import stat
import waapi
import time
import signal
from P4 import P4, P4Exception
import re

class SortRulesEditor(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Sort Rules Editor")
        self.setGeometry(100, 100, 800, 600)
        current_dir = ""
        if getattr(sys, 'frozen', False):
            current_dir = os.path.dirname(sys.executable)
        else:
            current_dir = os.path.dirname(os.path.abspath(__file__))
        script_dir = current_dir

        self.rules_file = os.path.join(script_dir, "sortRules.txt")
        self.rules_dict = {}
        
        self.init_ui()
        self.load_rules()
        
    def init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        layout = QVBoxLayout()
        central_widget.setLayout(layout)
        
        # Create scroll area for the table
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        layout.addWidget(scroll)
        
        # Create table widget
        self.table = QTableWidget()
        self.table.setColumnCount(3)  # 2 data columns + 1 button column
        self.table.setHorizontalHeaderLabels(["特征字符(格式:@workunit@^前缀^特征字)", "Original/SFX下的路径", "操作"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        scroll.setWidget(self.table)
        
        # Add save button
        save_btn = QPushButton("保存规则")
        save_btn.clicked.connect(self.save_rules)
        layout.addWidget(save_btn)
        
        # Add sync button
        sync_btn = QPushButton("同步到Wwise")
        sync_btn.clicked.connect(self.sync_to_wwise)
        layout.addWidget(sync_btn)
        
    def load_rules(self):
        # Check if file exists, if not create with header
        if not os.path.exists(self.rules_file):
            with open(self.rules_file, 'w', encoding='utf-8') as f:
                f.write("特征字符\t路径\n")
            return
        
        # Read existing rules
        with open(self.rules_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        # Process data (skip header)
        for line in lines[1:]:
            line = line.strip()
            if line:
                parts = line.split('\t')
                if len(parts) >= 2:
                    key = parts[0]
                    value = parts[1]
                    if key:  # Only add if key is not empty
                        self.rules_dict[key] = value
        
        self.populate_table()
    
    def populate_table(self):
        # Clear the table first
        self.table.setRowCount(0)
        
        # Add data rows
        for i, (key, value) in enumerate(self.rules_dict.items()):
            self.add_row(i, key, value)
    
    def add_row(self, row_pos, key="", value=""):
        self.table.insertRow(row_pos)
        
        # Set items
        key_item = QTableWidgetItem(key)
        value_item = QTableWidgetItem(value)
        self.table.setItem(row_pos, 0, key_item)
        self.table.setItem(row_pos, 1, value_item)
        
        # Add buttons
        self.add_buttons(row_pos)
    
    def add_buttons(self, row_pos):
        btn_widget = QWidget()
        btn_layout = QHBoxLayout()
        btn_widget.setLayout(btn_layout)
        btn_layout.setContentsMargins(2, 2, 2, 2)
        btn_layout.setSpacing(2)
        
        # Add button
        add_btn = QPushButton("+")
        add_btn.setFixedWidth(30)
        add_btn.clicked.connect(lambda _, r=row_pos: self.handle_add_row(r))
        btn_layout.addWidget(add_btn)
        
        # Delete button
        del_btn = QPushButton("-")
        del_btn.setFixedWidth(30)
        del_btn.clicked.connect(lambda _, r=row_pos: self.handle_delete_row(r))
        btn_layout.addWidget(del_btn)
        
        self.table.setCellWidget(row_pos, 2, btn_widget)
    
    def handle_add_row(self, current_row):
        new_row = current_row + 1
        self.add_row(new_row)
        self.update_button_connections()
        self.table.setCurrentCell(new_row, 0)
            
    def handle_delete_row(self, row_to_delete):
        reply = QMessageBox.Yes
        if reply == QMessageBox.Yes:
            self.table.removeRow(row_to_delete)
            self.update_button_connections()
    
    def update_button_connections(self):
        for row in range(self.table.rowCount()):
            if self.table.cellWidget(row, 2):
                self.table.removeCellWidget(row, 2)
                self.add_buttons(row)
    
    def save_rules(self):
        new_rules = {}
        empty_rows = []
        keys_seen = []
        dupes = []
        errors = []
        for row in range(self.table.rowCount()):
            key_item = self.table.item(row, 0)
            value_item = self.table.item(row, 1)
            key = key_item.text().strip() if key_item else ""
            value = value_item.text().strip() if value_item else ""
            valid, text = validate_key(key)
            if not valid:
                errors.append(f"{key}不合规: {text}")
            if key == "":
                empty_rows.append(str(row + 1))
                continue

            if key in keys_seen:
                dupes.append(key)
            else:
                keys_seen.append(key)

            if value == "":
                value = "$root$"
            new_rules[key] = value
        
        if errors:
            QMessageBox.warning(self, "规则写法不合规", 
                              f"{'\n'.join(errors)}\n请修正后再试")
            return False

        if dupes:
            QMessageBox.warning(self, "重复条目", 
                              f"{', '.join(dupes)}\n请解决这些重复值")
            return False

        if empty_rows:
            QMessageBox.warning(self, "空条目", 
                              f"以下行有空条目: {', '.join(empty_rows)}\n请填写完整或删除这些行。")
            return False

        remove_read_only(self.rules_file)
        with open(self.rules_file, 'w', encoding='utf-8') as f:
            f.write("特征字符\t路径\n")
            for key, value in new_rules.items():
                f.write(f"{key}\t{value}\n")
        
        QMessageBox.information(self, "成功", "规则保存成功!")
        self.rules_dict = new_rules
        return True
    
    def sync_to_wwise(self):
        if not self.save_rules():
            return
        # Call the external method here
        msg_box = QMessageBox(self)
        msg_box.setIcon(QMessageBox.Information)
        msg_box.setText("console显示整理完就可以关了")
        msg_box.setWindowTitle("整理中, 不要关闭")
        msg_box.setModal(False)  # Make it non-blocking
        msg_box.show()
        wwise_method(self.rules_dict)  # Replace this with your actual method call
        

    def check_uniqueness(self, keys):
        key_list = list(keys)
        non_unique = set()
        for i in range(len(key_list)):
            for j in range(len(key_list)):
                if i != j and key_list[i] in key_list[j]:
                    non_unique.add(key_list[i])
                    non_unique.add(key_list[j])
        return list(non_unique)
    



client = waapi.WaapiClient()
project_info = client.call("ak.wwise.core.getProjectInfo")
client.call("ak.wwise.core.project.save")
print("正在保存工程\n")
time.sleep(1.5)
# Get directories from the Wwise
xml_input_paths = []
xml_input_paths.append(os.path.join(project_info['directories']['root'], 'Actor-Mixer Hierarchy'))
xml_input_paths.append(os.path.join(project_info['directories']['root'], 'Interactive Music Hierarchy'))
wav_folder_path = os.path.join(project_info['directories']['originals'], 'SFX')

all_paths = [os.path.join(project_info['directories']['root'], 'Actor-Mixer Hierarchy'), 
             os.path.join(project_info['directories']['root'], 'Interactive Music Hierarchy'),
             os.path.join(project_info['directories']['originals'], 'SFX'),
             os.path.join(project_info['directories']['root'], 'Tools')
             ]

current_dir = ""
if getattr(sys, 'frozen', False):
    current_dir = os.path.dirname(sys.executable)
else:
    current_dir = os.path.dirname(os.path.abspath(__file__))
workspace = ""

workspacefile = os.path.join(current_dir, ".config.txt")
try:
    parent_dir = os.path.dirname(current_dir)
    workspacefile = os.path.join(parent_dir, ".config.txt")
    print("使用公用config")
except:
    print("使用独立config")
    


try:
    with open(workspacefile, 'r') as file:
        workspace = file.readline().strip()
        print("当前workspace:", workspace)
except FileNotFoundError:
    print("没有找到workspace.")
except Exception as e:
    print(f"没有找到workspace: {e}")

p4 = P4()
p4.client = workspace

try:
    p4.connect()
    p4.client = workspace
except P4Exception as e:
    for error in e.errors:
        print(f"无法连接到您的workspace, 请您确定workspace配置正确, 如果不连接workspace, 记得手动在p4里reconcile一下: {error}")


def parseKey(key: str):
    workunitname = ''
    prefix = ''
    text = ''
    # Extract workunitname (between @...@)
    if '@' in key:
        parts = key.split('@')
        # Iterate through parts to find a pair of @ delimiters
        for i in range(len(parts) - 1):
            if parts[i] == '' and parts[i+1] != '':
                workunitname = parts[i+1]
                key = key.replace(f'@{workunitname}@', '', 1)  # Remove extracted part
                break
    # Extract prefix (between ^...^)
    if '^' in key:
        parts = key.split('^')
        # Iterate through parts to find a pair of ^ delimiters
        for i in range(len(parts) - 1):
            if parts[i] == '' and parts[i+1] != '':
                prefix = parts[i+1]
                key = key.replace(f'^{prefix}^', '', 1)  # Remove extracted part
                break

    # The remaining part is treated as text
    text = key.strip()
    return {
        'workunitname': workunitname,
        'prefix': prefix,
        'text': text
    }

def validate_key(s):
    # Check 1: If string has @, it must have exactly 2 @
    at_count = s.count('@')
    if at_count > 0 and at_count != 2:
        return False, "Must have exactly 2 @ signs if any present"
    # Check 2: If string has ^, it must have exactly 2 ^
    caret_count = s.count('^')
    if caret_count > 0 and caret_count != 2:
        return False, "Must have exactly 2 ^ signs if any present"
    # Check 3: If string has both @ and ^, the first ^ must be right after the second @
    if at_count == 2 and caret_count == 2:
        second_at_pos = s.find('@', s.find('@') + 1)
        first_caret_pos = s.find('^')
        if first_caret_pos != second_at_pos + 1:
            return False, "First ^ must be right after second @ when both are present"
    # Check 4: If string has @ or ^, it must begin with @ or ^
    if (at_count > 0 or caret_count > 0) and not (s.startswith('@') or s.startswith('^')):
        return False, "String must begin with @ or ^ if they are present"
    # Check 5: String should not end with @ or ^
    if s.endswith('@') or s.endswith('^'):
        return False, "String should not end with @ or ^"
    return True, "String is valid"

name_list = []
# Function to modify the XML file and rename WAV files
def modify_audio_file_in_xml(xml_file_path, wav_folder_path, rules):
    global client
    tree = ET.parse(xml_file_path)
    workunit_name = os.path.splitext(os.path.basename(xml_file_path))[0]
    root = tree.getroot()

    changes_count = 0
    changes = []
    

    # Iterate through AudioFileSource elements
    for sound in root.findall(".//Sound"):
        sound_name = sound.get('Name')
        sound_name_lower = sound_name
        new_path = None
        best_match = ""
        matchWorkunit = False
        for key in rules.keys():
            parseResult = parseKey(key)
            workunit = parseResult["workunitname"]
            prefix = parseResult["prefix"]
            text = parseResult["text"]

            if text != "" and text in sound_name_lower: #text machted
                if prefix != "" and not sound_name_lower.startswith(prefix): #prefix mismatch, skip
                    continue
                if workunit != "" and workunit != workunit_name:
                    continue
                elif not matchWorkunit: #found workunit rule, prioritize maching workunit
                    matchWorkunit = True
                    best_match = text
                    new_path = rules[key]

                if len(text) >= len(best_match): #found better match for text
                    if not matchWorkunit: # no workunit rule, update match
                        best_match = text
                        new_path = rules[key]
                    elif workunit_name == workunit: # has workunit rule and has matching workunit, update match
                            best_match = text
                            new_path = rules[key]
                    else: # has workunit rule but no matching workunit, skip
                        continue
        if new_path == None:
            continue 

        for audio_file_source in sound.findall(".//AudioFileSource"):
            change = False
            audio_file = audio_file_source.find("AudioFile")
            audio_file_name_old = audio_file.text
            language = audio_file_source.find("Language")
            if language.text != "SFX":
                print(audio_file.text + " original命名不统一, 因为分类不为音效所以没有更名")
                continue

            if audio_file is not None:
                old_value = audio_file.text
                # Only change the path, keeping the name
                path, name = os.path.split(old_value)  # Split the path and file name
                
                if new_path != "$root$":
                    new_value = f"{new_path}\\{name}" 
                else:
                    new_value = name
                
                # Change the audio file path in the XML
                if audio_file.text != new_value:
                    common_reference = False
                    for name in name_list:
                        if audio_file.text == name["oldfile"]:
                            audio_file.text = name["newfile"]
                            common_reference = True
                            continue
                    if common_reference:
                        continue
                    audio_file.text = new_value
                    change = True
                    changes.append(f"Changed '{old_value}' to '{audio_file.text}' in '{xml_file_path}'")


                name_list.append(dict(oldfile=audio_file_name_old, newfile=new_value))

                # Rename the actual WAV file if it exists
                old_wav_path = os.path.join(wav_folder_path, old_value)
                new_wav_path = os.path.join(wav_folder_path, new_value)

                if old_wav_path != new_wav_path:
                    if os.path.isfile(old_wav_path):
                        remove_read_only(old_wav_path)  # Remove read-only attribute before renaming
                        try:
                            directory = os.path.dirname(new_wav_path)
                            if not os.path.exists(directory):
                                os.makedirs(directory)
                            shutil.move(old_wav_path, new_wav_path)
                            old_akd = os.path.splitext(old_wav_path)[0] + '.akd'
                            new_akd = os.path.splitext(new_wav_path)[0] + '.akd'
                            try:
                                shutil.move(old_akd, new_akd)
                            except:
                                print("akd命名失败")
                            changes.append(f"Renamed WAV file '{old_wav_path}' to '{new_wav_path}'")
                        except Exception as e:
                            changes.append(f"Failed to rename WAV file '{old_wav_path}': {e}")
                            change = False
                            print(f"移动{old_wav_path}的wav文件到{new_wav_path}时失败:{e}")
                    else:
                        changes.append(f"没有找到对应的wav文件: '{old_wav_path}',所以只更改了wwu引用,跳过original命名")
                if change:
                    changes_count += 1
                else:
                    continue
    for sound in root.findall(".//Sound"):
        sound_name = sound.get('Name')
        for audio_file_source in sound.findall(".//AudioFileSource"):
            audio_file = audio_file_source.find("AudioFile")
            audio_file_name_old = audio_file.text
            for name in name_list:
                if audio_file.text == name["oldfile"] and audio_file.text != name["newfile"]:
                    audio_file.text = name["newfile"]
                    print(f"{sound_name}存在相同original引用，original一并修改成了{name["newfile"]}")
                    changes_count += 1
                    continue

    # Write the modified XML back to the file if changes were made
    if changes_count > 0:
        client.call("ak.wwise.core.project.save")
        remove_read_only(xml_file_path)
        tree.write(xml_file_path, encoding='utf-8', xml_declaration=True)
        print(f"Modified XML file saved as: {xml_file_path}")
    return changes_count, changes

# Function to remove read-only attribute
def remove_read_only(file_path):
    """Remove the read-only attribute from a file."""
    try:
        checkout_file(file_path)
        os.chmod(file_path, stat.S_IWRITE)  # Change the file's mode to writable
    except Exception as e:
        print(f"Failed to change permissions for {file_path}: {e}")

def checkout_file(file_path):
    try:
        p4.run('edit', file_path)
        print(f"checkOut:{file_path}")
    except P4Exception as e:
        for error in e.errors:
            print(f"无法checkout文件, 先帮您改了, 命名记得在p4里reconcile一下: {error}")

def process_directory(directory_paths, wav_folder_path, rules):
    total_changes = 0
    all_changes = []
    for directory_path in directory_paths:
        for filename in os.listdir(directory_path):
            if filename.endswith(".wwu"):
                file_path = os.path.join(directory_path, filename)
                changes_count, changes = modify_audio_file_in_xml(file_path, wav_folder_path, rules)
                total_changes += changes_count
                all_changes.extend(changes)

    return total_changes, all_changes



def reconcile_offline_work(folders, reconcile):
    global p4
    print("正在和p4同步离线文件, 请不要退出, 如果不慎退出, 记得手动reconcile")
    try:
        for folder in folders:
            if reconcile:
                print(f"Reconciling offline work in folder: {folder}")
                try:
                    # Attempt to reconcile, targeting all files in the folder
                    reconcile_results = p4.run_reconcile(f"{folder}/...")
                    # Check if there are any results
                    if not reconcile_results:  # No files to reconcile
                        continue  # Skip to the next folder
                except P4Exception as e:
                    if "no file(s) to reconcile" in str(e):
                        continue  # Skip to next folder
                    else:
                        print(f"An error occurred during reconciliation: {e}")
            else:
                print(f"Skipping reconciliation for folder: {folder}")

    except P4Exception as e:
        print(f"An error occurred: {e}")
        print("本地文件reconcile同步出现异常, 请在p4手动reconcile")
    finally:
        if reconcile:
            p4.disconnect()
            print("Disconnected from Perforce.")

def wwise_method(rules):
    total_changes, all_changes = process_directory(xml_input_paths, wav_folder_path, rules)

    if total_changes > 0:
        for change in all_changes:
            print(change)
        print(f"\n总共修改: {total_changes}")
        reconcile_offline_work(all_paths, True)
        print("整理完毕,您可以关闭了")
    else:
        print("不需要整理")


def signal_handler(sig, frame):
    print("Exiting...")
    QApplication.quit()  # Cleanly quit the QApplication
    sys.exit(0)  # Exit the script

if __name__ == "__main__":
    signal.signal(signal.SIGINT, signal_handler)
    app = QApplication([])
    window = SortRulesEditor()
    window.show()
    app.exec_()


