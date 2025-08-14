import waapi
import os
import re
import sys
import time
import tkinter as tk
import threading
import time
from tkinter import messagebox
from warnings import filterwarnings
from datetime import datetime
from pyscreenrec import (
    ScreenRecorder,
    ScreenRecordingInProgress,
    NoScreenRecordingInProgress,
)

client = waapi.WaapiClient()
# to catch the warnings as error

foldername = "Prof_Sessions"

# Get the current time and format it
current_time = datetime.now()
formatted_time = current_time.strftime("%Y%m%d_%H%M")
file_name = f"{formatted_time}.mp4"

if getattr(sys, 'frozen', False):
    # If the application is frozen (running as an executable)
    current_folder = os.path.dirname(sys.executable)
else:
    # If the script is running in a normal Python environment
    current_folder = os.path.dirname(os.path.abspath(__file__))

# Create the export location
exportLocation = os.path.join(current_folder, foldername)

# Check if the folder exists, if not, create it
if not os.path.exists(exportLocation):
    os.makedirs(exportLocation)

# Combine the folder path with the file name
exportLocation = os.path.join(exportLocation, file_name)


COORDINATES = None
class RegionSelector(tk.Toplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title("Select Recording Region")
        self.geometry("800x600")
        self.attributes("-alpha", 0.5)
        self.attributes("-fullscreen", False)
        self.configure(background="grey")

        self.start_x = None
        self.start_y = None
        self.end_x = None
        self.end_y = None
        label = tk.Label(self, text="改变弹窗大小控制录制范围\n\n点我隐藏窗口", font=("Arial", 20))
        label.pack(pady=2)
        self.canvas = tk.Canvas(self, highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)
        self.bind("<Button-1>", self.lower_window)
        # Start the coordinate update loop
        self.update_coordinates()

    def kill(self):
        self.destroy()

    def update_coordinates(self):
        global COORDINATES
        x = self.winfo_x()
        y = self.winfo_y()
        width = self.winfo_width()
        height = self.winfo_height()
        COORDINATES = {
            "top": y,
            "left": x,
            "height": height,
            "width": width,
        }

        # Schedule this method to run again after 500 milliseconds
        self.after(100, self.update_coordinates)

    def get_window_info(self):
        return COORDINATES
    def lower_window(self, event):
        self.lower()
class GUIScreenRecorder(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Screen Recorder")
        self.geometry("500x400")
        self.recorder = ScreenRecorder()
        self.region_selector = None  # Attribute to hold the RegionSelector instance

        self.label = tk.Label(self, text="*直接开始录制会录制全屏*", font=("Arial", 18))
        self.label.pack(pady=10)
        self.start_button = tk.Button(
            self, text="开始录制", command=self.start_recording
        )
        self.start_button.pack(pady=10)

        self.select_region_button = tk.Button(
            self, text="选择录制范围", command=self.select_recording_region
        )
        self.select_region_button.pack(pady=10)

        self.stop_button = tk.Button(
            self, text="停止录制", command=self.stop_recording
        )
        self.stop_button.pack(pady=10)
        label2 = tk.Label(self, text="导出路径(以.mp4结尾):", font=("Arial", 10))
        label2.pack(pady=5)
        self.filename_entry = tk.Entry(self, width=40)
        self.filename_entry.pack(pady=10)
        self.filename_entry.insert(0, exportLocation)
        label3 = tk.Label(self, text="帧数:", font=("Arial", 10))
        label3.pack(pady=5)
        self.fps_entry = tk.Entry(self, width=10)
        self.fps_entry.pack(pady=10)
        self.fps_entry.insert(0, "30")
        label4 = tk.Label(self, text="结束后记得手动导出profiler文件为txt文件", font=("Arial", 10))
        label4.pack(pady=5)

    def select_recording_region(self):
        if self.region_selector is None or not self.region_selector.winfo_exists():
            self.region_selector = RegionSelector(self)
            self.region_selector.mainloop()
        else:
            messagebox.showinfo("Info", "选择区域窗口已打开")

    def start_recording(self):
        wwise_startCapture()
        global COORDINATES
        if COORDINATES is None:
            COORDINATES = {
                "top": 0,
                "left": 0,
                "height": self.winfo_screenheight(),
                "width": self.winfo_screenwidth(),
            }
        try:
            filename = self.filename_entry.get()
            fps = int(self.fps_entry.get())
            self.recorder.start_recording(filename, fps, COORDINATES)
            self.label.config(text="正在录制...")
        except (ValueError, SyntaxError):
            messagebox.showerror("帧数或路径不合法")
        except ScreenRecordingInProgress:
            messagebox.showerror("已经在录了, 请先结束上一次录制")

    def stop_recording(self):
        wwise_stopCapture()
        self.label.config(text="录制已结束, 文件已导出")
        try:
            self.recorder.stop_recording()
            messagebox.showinfo("Recording Stopped", "录制已停止, mp4文件输出到了指定路径")
        except NoScreenRecordingInProgress:
            messagebox.showerror("No Recording", "现在并没有在录制")
        

def wwise_startCapture():
    client.call("ak.wwise.core.profiler.enableProfilerData", {
        "dataTypes": [
            {
                "dataType": "apiCalls",
                "enable": True
            }
        ]
    })
    client.call("ak.wwise.core.remote.connect",{"host": "127.0.0.1"})
    client.call("ak.wwise.core.profiler.stopCapture")
    client.call("ak.wwise.core.profiler.startCapture")


def wwise_stopCapture():
    client.call("ak.wwise.core.profiler.stopCapture")


if __name__ == "__main__":
    app = GUIScreenRecorder()
    app.mainloop()


client.disconnect()




