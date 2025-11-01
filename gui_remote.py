#!/usr/bin/env python3

import tkinter as tk
from tkinter import ttk
from tkinter import messagebox
import samsungctl
import json
import os

class SamsungRemoteGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Samsung TV Remote")
        self.config = self.load_config()

        # Open persistent connection
        try:
            self.remote = samsungctl.Remote(self.config).__enter__()
        except Exception as e:
            messagebox.showerror("Connection Error", f"Failed to connect to TV: {str(e)}")
            self.root.quit()
            return

        # Bind close event
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

        # Create notebook for tabs
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(expand=True, fill="both")

        # IP input at top
        self.create_ip_frame()

        # Create tabs
        self.create_basic_tab()
        self.create_navigation_tab()
        self.create_menu_tab()
        self.create_input_tab()
        self.create_numbers_tab()
        self.create_colors_tab()
        self.create_media_tab()
        self.create_aspect_tab()
        self.create_other_tab()

    def on_close(self):
        if hasattr(self, 'remote'):
            self.remote.__exit__(None, None, None)
        self.root.destroy()

    def load_config(self):
        config_path = os.path.join(os.getenv("HOME"), ".config", "samsungctl.conf")
        if os.path.exists(config_path):
            with open(config_path, 'r') as f:
                return json.load(f)
        else:
            messagebox.showerror("Config Error", "Config file not found. Please run samsungctl command line first to set up.")
            self.root.quit()
            return None

    def create_ip_frame(self):
        ip_frame = ttk.Frame(self.root)
        ip_frame.pack(side=tk.TOP, fill=tk.X, padx=5, pady=5)

        ip_label = tk.Label(ip_frame, text="TV IP:")
        ip_label.pack(side=tk.LEFT, padx=5)
        self.ip_entry = tk.Entry(ip_frame, width=15)
        self.ip_entry.insert(0, self.config.get("host", ""))
        self.ip_entry.pack(side=tk.LEFT, padx=5)
        update_btn = tk.Button(ip_frame, text="Update IP", command=self.update_ip)
        update_btn.pack(side=tk.LEFT, padx=5)

    def update_ip(self):
        new_ip = self.ip_entry.get()
        if new_ip:
            self.config["host"] = new_ip
            self.save_config()
            messagebox.showinfo("Updated", f"TV IP updated to {new_ip}")
        else:
            messagebox.showerror("Error", "Please enter a valid IP address")

    def save_config(self):
        config_path = os.path.join(os.getenv("HOME"), ".config", "samsungctl.conf")
        os.makedirs(os.path.dirname(config_path), exist_ok=True)
        with open(config_path, 'w') as f:
            json.dump(self.config, f, indent=4)

    def send_key(self, key):
        try:
            self.remote.control(key)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to send {key}: {str(e)}")

    def create_basic_tab(self):
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="Basic")

        buttons = [
            ("Power", "KEY_POWER"),
            ("Vol +", "KEY_VOLUP"),
            ("Vol -", "KEY_VOLDOWN"),
            ("Mute", "KEY_MUTE"),
            ("Ch +", "KEY_CHUP"),
            ("Ch -", "KEY_CHDOWN"),
        ]

        for i, (text, key) in enumerate(buttons):
            btn = tk.Button(tab, text=text, command=lambda k=key: self.send_key(k), width=10, height=2)
            btn.grid(row=i//2, column=i%2, padx=5, pady=5)

    def create_navigation_tab(self):
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="Navigation")

        buttons = [
            ("Up", "KEY_UP"),
            ("Down", "KEY_DOWN"),
            ("Left", "KEY_LEFT"),
            ("Right", "KEY_RIGHT"),
            ("Enter", "KEY_ENTER"),
            ("Return", "KEY_RETURN"),
            ("Exit", "KEY_EXIT"),
        ]

        for i, (text, key) in enumerate(buttons):
            btn = tk.Button(tab, text=text, command=lambda k=key: self.send_key(k), width=10, height=2)
            btn.grid(row=i//3, column=i%3, padx=5, pady=5)

    def create_menu_tab(self):
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="Menu")

        buttons = [
            ("Menu", "KEY_MENU"),
            ("Home", "KEY_HOME"),
            ("Guide", "KEY_GUIDE"),
            ("Info", "KEY_INFO"),
            ("Tools", "KEY_TOOLS"),
            ("Help", "KEY_HELP"),
            ("Top Menu", "KEY_TOPMENU"),
            ("Contents", "KEY_CONTENTS"),
        ]

        for i, (text, key) in enumerate(buttons):
            btn = tk.Button(tab, text=text, command=lambda k=key: self.send_key(k), width=10, height=2)
            btn.grid(row=i//4, column=i%4, padx=5, pady=5)

    def create_input_tab(self):
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="Input")

        buttons = [
            ("Source", "KEY_SOURCE"),
            ("HDMI", "KEY_HDMI"),
            ("HDMI1", "KEY_HDMI1"),
            ("HDMI2", "KEY_HDMI2"),
            ("HDMI3", "KEY_HDMI3"),
            ("HDMI4", "KEY_HDMI4"),
            ("TV", "KEY_TV"),
            ("Component1", "KEY_COMPONENT1"),
            ("AV1", "KEY_AV1"),
            ("DVI", "KEY_DVI"),
            ("PC", "KEY_PCMODE"),
        ]

        for i, (text, key) in enumerate(buttons):
            btn = tk.Button(tab, text=text, command=lambda k=key: self.send_key(k), width=10, height=2)
            btn.grid(row=i//4, column=i%4, padx=5, pady=5)

    def create_numbers_tab(self):
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="Numbers")

        buttons = [
            ("0", "KEY_0"),
            ("1", "KEY_1"),
            ("2", "KEY_2"),
            ("3", "KEY_3"),
            ("4", "KEY_4"),
            ("5", "KEY_5"),
            ("6", "KEY_6"),
            ("7", "KEY_7"),
            ("8", "KEY_8"),
            ("9", "KEY_9"),
            ("11", "KEY_11"),
            ("12", "KEY_12"),
            ("Plus100", "KEY_PLUS100"),
        ]

        for i, (text, key) in enumerate(buttons):
            btn = tk.Button(tab, text=text, command=lambda k=key: self.send_key(k), width=5, height=2)
            btn.grid(row=i//5, column=i%5, padx=5, pady=5)

    def create_colors_tab(self):
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="Colors")

        buttons = [
            ("Red", "KEY_RED"),
            ("Green", "KEY_GREEN"),
            ("Yellow", "KEY_YELLOW"),
            ("Blue", "KEY_BLUE"),
            ("Cyan", "KEY_CYAN"),
        ]

        for i, (text, key) in enumerate(buttons):
            btn = tk.Button(tab, text=text, command=lambda k=key: self.send_key(k), width=10, height=2)
            btn.grid(row=0, column=i, padx=5, pady=5)

    def create_media_tab(self):
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="Media")

        buttons = [
            ("Play", "KEY_PLAY"),
            ("Pause", "KEY_PAUSE"),
            ("Stop", "KEY_STOP"),
            ("Rewind", "KEY_REWIND"),
            ("FF", "KEY_FF"),
            ("Rec", "KEY_REC"),
            ("Live", "KEY_LIVE"),
            ("Quick Replay", "KEY_QUICK_REPLAY"),
            ("Still Picture", "KEY_STILL_PICTURE"),
            ("Instant Replay", "KEY_INSTANT_REPLAY"),
        ]

        for i, (text, key) in enumerate(buttons):
            btn = tk.Button(tab, text=text, command=lambda k=key: self.send_key(k), width=12, height=2)
            btn.grid(row=i//5, column=i%5, padx=5, pady=5)

    def create_aspect_tab(self):
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="Aspect")

        buttons = [
            ("Aspect", "KEY_ASPECT"),
            ("Picture Size", "KEY_PICTURE_SIZE"),
            ("4:3", "KEY_4_3"),
            ("16:9", "KEY_16_9"),
            ("3:4", "KEY_EXT14"),
            ("16:9 Alt", "KEY_EXT15"),
        ]

        for i, (text, key) in enumerate(buttons):
            btn = tk.Button(tab, text=text, command=lambda k=key: self.send_key(k), width=10, height=2)
            btn.grid(row=i//3, column=i%3, padx=5, pady=5)

    def create_other_tab(self):
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="Other")

        buttons = [
            ("Sleep", "KEY_SLEEP"),
            ("Energy Saving", "KEY_ESAVING"),
            ("PIP On/Off", "KEY_PIP_ONOFF"),
            ("Caption", "KEY_CAPTION"),
            ("Clock", "KEY_CLOCK_DISPLAY"),
            ("Zoom In", "KEY_ZOOM_IN"),
            ("Zoom Out", "KEY_ZOOM_OUT"),
            ("Bookmark", "KEY_BOOKMARK"),
            ("Clear", "KEY_CLEAR"),
            ("Magic Bright", "KEY_MAGIC_BRIGHT"),
        ]

        for i, (text, key) in enumerate(buttons):
            btn = tk.Button(tab, text=text, command=lambda k=key: self.send_key(k), width=12, height=2)
            btn.grid(row=i//5, column=i%5, padx=5, pady=5)

if __name__ == "__main__":
    root = tk.Tk()
    app = SamsungRemoteGUI(root)
    root.mainloop()