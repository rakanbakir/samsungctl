#!/usr/bin/env python3

import socket
import ipaddress
import threading
import queue
import struct
import time
import tkinter as tk
from tkinter import ttk
from tkinter import messagebox
import samsungctl
import json
import os
import logging
import time
from datetime import datetime

# Configure logging
def setup_logging():
    """Setup logging to file and console"""
    # Create logs directory if it doesn't exist
    log_dir = os.path.join(os.path.dirname(__file__), "logs")
    os.makedirs(log_dir, exist_ok=True)
    
    # Create log filename with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = os.path.join(log_dir, f"samsung_remote_{timestamp}.log")
    
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file, encoding='utf-8'),
            logging.StreamHandler()  # Also log to console
        ]
    )
    
    logging.info(f"Logging initialized. Log file: {log_file}")
    return log_file

# Initialize logging
log_file = setup_logging()

class ModernSamsungRemote:
    def __init__(self, root):
        logging.info("Initializing Samsung TV Remote GUI")
        self.root = root
        self.root.title("Samsung TV Remote")
        self.root.geometry("480x750")
        self.root.configure(bg='#1a1a1a')
        self.root.resizable(True, True)

        # Load configuration
        self.config = self.load_config()
        if self.config is None:
            # Config loading failed, but continue with default config
            self.config = {
                "name": "samsungctl",
                "host": "",
                "method": "websocket",
                "port": 8001,
                "timeout": 5
            }
            logging.warning("Config loading failed, using default configuration")

        # Initialize connection status
        self.connection_status = "Disconnected"
        
        # Initialize remote connection
        self.remote = None

        # Load logo
        try:
            self.logo_image = tk.PhotoImage(file="samsung_icon.png")
            logging.info("Logo image loaded successfully")
        except Exception as e:
            logging.warning(f"Could not load logo: {e}")
            self.logo_image = None

        # Setup modern styling
        self.setup_styles()

        # Create scrollable canvas
        self.create_scrollable_canvas()

        # Initialize command history
        self.command_history = []
        self.max_history = 10

        # Load app sequences from config
        self.app_sequences = self.config.get('app_sequences', {}) if self.config else {}

        # Load discovery subnets from config
        self.discovery_subnets = self.config.get('discovery_subnets', []) if self.config else []

        # Create main layout inside scrollable frame
        self.create_header()
        self.create_main_remote()
        self.create_footer()

        # Update initial connection status display
        self.update_connection_status()

        # Setup keyboard navigation
        self.setup_keyboard_navigation()

        # Configure scrolling
        self.configure_scrolling()

        # Auto-connect if IP is configured
        if self.config and self.config.get("host"):
            logging.info("IP address configured, attempting automatic connection...")
            self.connect_to_tv()

        # Bind close event
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
        
        logging.info("Samsung TV Remote GUI initialization completed")

    def setup_styles(self):
        """Setup modern styling for buttons and widgets"""
        style = ttk.Style()

                # Configure colors
        self.bg_color = '#1a1a1a'
        self.button_bg = '#2d2d2d'
        self.button_hover = '#404040'
        self.accent_color = '#0078d4'
        self.text_color = '#ffffff'
        self.secondary_text = '#cccccc'

        # Button styles
        style.configure('Modern.TButton',
                       background=self.button_bg,
                       foreground=self.text_color,
                       borderwidth=0,
                       focuscolor=self.accent_color,
                       font=('Segoe UI', 10, 'bold'),
                       padding=8)

        style.map('Modern.TButton',
                 background=[('active', self.button_hover),
                           ('pressed', self.accent_color)])

        # Frame styles
        style.configure('Card.TFrame', background=self.bg_color)
        style.configure('Header.TFrame', background='#0078d4')

    def create_scrollable_canvas(self):
        """Create a scrollable canvas for the main content"""
        # Create main container
        self.main_container = ttk.Frame(self.root, style='Card.TFrame')
        self.main_container.pack(fill=tk.BOTH, expand=True)

        # Create canvas and scrollbars
        self.canvas = tk.Canvas(self.main_container, bg=self.bg_color, highlightthickness=0)
        self.v_scrollbar = ttk.Scrollbar(self.main_container, orient=tk.VERTICAL, command=self.canvas.yview)
        self.h_scrollbar = ttk.Scrollbar(self.main_container, orient=tk.HORIZONTAL, command=self.canvas.xview)

        # Pack the canvas and scrollbars
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.v_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.h_scrollbar.pack(side=tk.BOTTOM, fill=tk.X)

        # Configure canvas
        self.canvas.configure(yscrollcommand=self.v_scrollbar.set, xscrollcommand=self.h_scrollbar.set)

        # Create scroll position indicator
        self.scroll_indicator = tk.Label(self.main_container, text="▲", font=('Segoe UI', 12),
                                       bg=self.accent_color, fg='white', width=2, height=1)
        self.scroll_indicator.place(relx=0.95, rely=0.05, anchor='center')
        self.scroll_indicator.bind("<Button-1>", lambda e: self.scroll_to_top())
        self.scroll_indicator.config(cursor="hand2")
        
        # Initially hide the indicator
        self.scroll_indicator.place_forget()

        # Create frame inside canvas for content
        self.scrollable_frame = ttk.Frame(self.canvas, style='Card.TFrame')
        self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor='nw')

    def configure_scrolling(self):
        """Configure the scrolling behavior"""
        def on_frame_configure(event):
            # Update scroll region to encompass the inner frame
            self.canvas.configure(scrollregion=self.canvas.bbox("all"))
            self.update_scroll_indicator()

        def on_canvas_configure(event):
            # Resize the inner frame to match canvas width
            if self.canvas.winfo_exists():
                self.canvas.itemconfig(self.canvas.find_withtag("all")[0], width=event.width)

        # Bind events
        self.scrollable_frame.bind("<Configure>", on_frame_configure)
        self.canvas.bind("<Configure>", on_canvas_configure)
        
        # Bind scroll events to update indicator
        self.v_scrollbar.config(command=lambda *args: [self.canvas.yview(*args), self.update_scroll_indicator()])

        # Mouse wheel scrolling - bind to root window for maximum coverage
        def on_mousewheel(event):
            try:
                delta = -1 * (event.delta // 120)  # -1 for down, 1 for up
                self.canvas.yview_scroll(delta, "units")
                self.update_scroll_indicator()
                logging.debug(f"Mouse wheel scroll: delta={event.delta}, direction={delta}")
                return "break"  # Consume the event
            except Exception as e:
                logging.error(f"Mouse wheel error: {e}")
                return "break"

        def on_shift_mousewheel(event):
            try:
                delta = -1 * (event.delta // 120)
                self.canvas.xview_scroll(delta, "units")
                logging.debug(f"Shift mouse wheel scroll: delta={event.delta}, direction={delta}")
                return "break"
            except Exception as e:
                logging.error(f"Shift mouse wheel error: {e}")
                return "break"

        # Bind to root window - this catches mouse wheel events anywhere in the window
        self.root.bind("<MouseWheel>", on_mousewheel)
        self.root.bind("<Shift-MouseWheel>", on_shift_mousewheel)

        # Keyboard scrolling (use different keys to avoid conflicts)
        self.root.bind("<Prior>", lambda e: self.canvas.yview_scroll(-1, "pages"))  # Page Up
        self.root.bind("<Next>", lambda e: self.canvas.yview_scroll(1, "pages"))    # Page Down
        self.root.bind("<Shift-Up>", lambda e: self.canvas.yview_scroll(-1, "units"))
        self.root.bind("<Shift-Down>", lambda e: self.canvas.yview_scroll(1, "units"))
        self.root.bind("<Shift-Left>", lambda e: self.canvas.xview_scroll(-1, "units"))
        self.root.bind("<Shift-Right>", lambda e: self.canvas.xview_scroll(1, "units"))

    def send_key(self, key):
        """Send a key command to the TV"""
        if self.remote:
            try:
                logging.info(f"Sending control command: {key}")
                self.remote.control(key)
                logging.info(f"Sent key command: {key}")
                
                # Add to command history
                from datetime import datetime
                self.command_history.insert(0, {
                    'command': key,
                    'timestamp': datetime.now().strftime("%H:%M:%S"),
                    'success': True
                })
                # Keep only last N commands
                if len(self.command_history) > self.max_history:
                    self.command_history.pop()
                    
            except Exception as e:
                error_msg = str(e)
                logging.error(f"Failed to send command {key}: {error_msg}")
                
                # Add failed command to history
                from datetime import datetime
                self.command_history.insert(0, {
                    'command': key,
                    'timestamp': datetime.now().strftime("%H:%M:%S"),
                    'success': False,
                    'error': error_msg
                })
                if len(self.command_history) > self.max_history:
                    self.command_history.pop()
                
                # Check for common connection errors and attempt reconnection
                if "Broken pipe" in error_msg or "Connection" in error_msg or "[Errno 32]" in error_msg:
                    logging.warning("Connection lost, attempting to reconnect...")
                    self.connection_status = "Reconnecting"
                    self.connect_to_tv()
                    
                    # If reconnection successful, retry the command
                    if self.connection_status == "Connected":
                        try:
                            logging.info(f"Retrying command after reconnection: {key}")
                            self.remote.control(key)
                            logging.info(f"Successfully sent command after reconnection: {key}")
                            # Update history to show successful retry
                            self.command_history[0]['success'] = True
                            self.command_history[0]['retried'] = True
                            return
                        except Exception as retry_error:
                            logging.error(f"Failed to send command even after reconnection: {retry_error}")
                
                messagebox.showerror("Error", f"Failed to send command: {error_msg}")
        else:
            logging.warning(f"Attempted to send key {key} but no TV connection available")
            try:
                if self.root and self.root.winfo_exists():
                    messagebox.showwarning("Not Connected", "Please connect to TV first")
            except Exception as dialog_error:
                logging.error(f"Failed to show connection warning dialog: {dialog_error}")

    def update_connection_status(self):
        """Update the connection status display in the header"""
        try:
            if hasattr(self, 'status_label') and self.status_label.winfo_exists():
                status_text = "Disconnected - No Config" if not self.config.get("host") else ("Connected" if self.connection_status == "Connected" else f"{self.connection_status}")
                status_color = '#ff4444' if self.connection_status != "Connected" else '#00ff00'
                self.status_label.config(text=f"● {status_text}", fg=status_color)
                logging.info(f"Connection status updated to: {status_text}")
        except Exception as e:
            logging.error(f"Failed to update connection status display: {e}")

    def connect_to_tv(self):
        """Establish connection to TV"""
        logging.info(f"Attempting to connect to TV at {self.config.get('host', 'unknown')} using {self.config.get('method', 'unknown')} method")
        try:
            self.remote = samsungctl.Remote(self.config).__enter__()
            self.connection_status = "Connected"
            logging.info("Successfully connected to Samsung TV")
            # Update the UI status
            self.update_connection_status()
            # Start connection monitoring
            self.start_connection_monitor()
        except Exception as e:
            self.connection_status = "Disconnected"
            logging.error(f"Failed to connect to TV: {str(e)}")
            # Update the UI status
            self.update_connection_status()
            # Only show error dialog if the application is still alive
            try:
                if self.root and self.root.winfo_exists():
                    messagebox.showerror("Connection Error", f"Failed to connect to TV: {str(e)}")
            except Exception as dialog_error:
                logging.error(f"Failed to show connection error dialog: {dialog_error}")
                # Application might be shutting down, just log the error

    def start_connection_monitor(self):
        """Start monitoring connection health"""
        def check_connection():
            if self.remote and self.connection_status == "Connected":
                try:
                    # Check if remote connection is still valid by attempting to access its attributes
                    # This is less intrusive than sending commands
                    if hasattr(self.remote, 'control') and callable(getattr(self.remote, 'control')):
                        logging.debug("Connection health check passed - remote object is valid")
                    else:
                        raise Exception("Remote object is invalid")
                except Exception as e:
                    logging.warning(f"Connection health check failed: {str(e)}")
                    self.connection_status = "Disconnected"
                    # Update the UI status
                    self.update_connection_status()
                    
            # Schedule next check in 60 seconds (increased from 30 to be less intrusive)
            if self.connection_status == "Connected":
                self.root.after(60000, check_connection)
        
        # Start monitoring after 60 seconds
        self.root.after(60000, check_connection)
        logging.info("Connection monitoring started")

    def create_header(self):
        """Create header with logo and title"""
        header_frame = ttk.Frame(self.scrollable_frame, style='Header.TFrame', height=80)
        header_frame.pack(fill=tk.X, padx=0, pady=0)
        header_frame.pack_propagate(False)

        # Logo
        if self.logo_image:
            logo_label = tk.Label(header_frame, image=self.logo_image, bg='#0078d4')
            logo_label.pack(side=tk.LEFT, padx=15, pady=10)

        # Title and status
        title_frame = ttk.Frame(header_frame, style='Header.TFrame')
        title_frame.pack(side=tk.LEFT, fill=tk.Y, expand=True, padx=10)

        title_label = tk.Label(title_frame, text="SAMSUNG",
                              font=('Segoe UI', 18, 'bold'), fg='white', bg='#0078d4')
        title_label.pack(anchor=tk.W)

        subtitle_label = tk.Label(title_frame, text="TV REMOTE CONTROL",
                                 font=('Segoe UI', 10), fg='#e6f3ff', bg='#0078d4')
        subtitle_label.pack(anchor=tk.W)

        # Connection status
        self.status_label = tk.Label(header_frame, text="● Disconnected",
                                   font=('Segoe UI', 8), fg='#ff4444', bg='#0078d4')
        self.status_label.pack(side=tk.RIGHT, padx=15, anchor=tk.S)

    def create_main_remote(self):
        """Create the main remote control interface"""
        main_frame = ttk.Frame(self.scrollable_frame, style='Card.TFrame')
        main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)

        # Power button (top center)
        power_frame = ttk.Frame(main_frame, style='Card.TFrame')
        power_frame.pack(pady=(20, 10))

        power_btn = tk.Button(power_frame, text="⏻", command=lambda: self.send_key("KEY_POWER"),
                             font=('Segoe UI', 16, 'bold'), bg='#ff4444', fg='white',
                             width=4, height=2, relief='raised', bd=3, takefocus=1)
        power_btn.pack()
        self.add_button_hover(power_btn, '#ff6666', '#ff4444')

        # Volume and channel controls
        vol_ch_frame = ttk.Frame(main_frame, style='Card.TFrame')
        vol_ch_frame.pack(pady=10)

        # Volume controls (left)
        vol_frame = ttk.Frame(vol_ch_frame, style='Card.TFrame')
        vol_frame.pack(side=tk.LEFT, padx=(0, 30))

        vol_up = self.create_round_button(vol_frame, "🔊", "KEY_VOLUP", 12)
        vol_up.pack(pady=2)

        vol_label = tk.Label(vol_frame, text="VOL", font=('Segoe UI', 8), fg=self.secondary_text, bg=self.bg_color)
        vol_label.pack(pady=2)

        vol_down = self.create_round_button(vol_frame, "🔉", "KEY_VOLDOWN", 12)
        vol_down.pack(pady=2)

        # Channel controls (right)
        ch_frame = ttk.Frame(vol_ch_frame, style='Card.TFrame')
        ch_frame.pack(side=tk.RIGHT, padx=(30, 0))

        ch_up = self.create_round_button(ch_frame, "📺+", "KEY_CHUP", 12)
        ch_up.pack(pady=2)

        ch_label = tk.Label(ch_frame, text="CH", font=('Segoe UI', 8), fg=self.secondary_text, bg=self.bg_color)
        ch_label.pack(pady=2)

        ch_down = self.create_round_button(ch_frame, "📺-", "KEY_CHDOWN", 12)
        ch_down.pack(pady=2)

        # Navigation pad
        nav_frame = ttk.Frame(main_frame, style='Card.TFrame')
        nav_frame.pack(pady=20)

        # Up button
        up_btn = self.create_round_button(nav_frame, "▲", "KEY_UP", 14)
        up_btn.grid(row=0, column=1, pady=5)

        # Left, OK, Right buttons
        left_btn = self.create_round_button(nav_frame, "◀", "KEY_LEFT", 14)
        left_btn.grid(row=1, column=0, padx=5)

        ok_btn = tk.Button(nav_frame, text="OK", command=lambda: self.send_key("KEY_ENTER"),
                          font=('Segoe UI', 12, 'bold'), bg=self.accent_color, fg='white',
                          width=6, height=2, relief='raised', bd=2, takefocus=1)
        ok_btn.grid(row=1, column=1, padx=5)
        self.add_button_hover(ok_btn, '#0099ff', self.accent_color)

        right_btn = self.create_round_button(nav_frame, "▶", "KEY_RIGHT", 14)
        right_btn.grid(row=1, column=2, padx=5)

        # Down button
        down_btn = self.create_round_button(nav_frame, "▼", "KEY_DOWN", 14)
        down_btn.grid(row=2, column=1, pady=5)

        # Media controls
        media_frame = ttk.Frame(main_frame, style='Card.TFrame')
        media_frame.pack(pady=10)

        media_controls = [
            ("▶", "KEY_PLAY"),
            ("⏸", "KEY_PAUSE"),
            ("⏹", "KEY_STOP")
        ]

        for i, (symbol, key) in enumerate(media_controls):
            def make_media_command(k):
                return lambda: self.send_key(k)
            media_btn = tk.Button(media_frame, text=symbol, command=make_media_command(key),
                                 font=('Segoe UI', 12, 'bold'), bg=self.button_bg, fg=self.text_color,
                                 width=4, height=2, relief='raised', bd=2, takefocus=1)
            media_btn.grid(row=0, column=i, padx=5)
            self.add_button_hover(media_btn, self.button_hover, self.button_bg)

        # Number pad
        num_frame = ttk.Frame(main_frame, style='Card.TFrame')
        num_frame.pack(pady=10)

        # Create a proper 3x4 grid for numbers 1-9, then 0 centered
        numbers = [
            ['1', '2', '3'],
            ['4', '5', '6'],
            ['7', '8', '9'],
            ['', '0', '']
        ]

        for i, row in enumerate(numbers):
            for j, num in enumerate(row):
                if num:  # Only create button if there's a number
                    def make_num_command(n):
                        return lambda: self.send_key(f"KEY_{n}")
                    num_btn = tk.Button(num_frame, text=num, command=make_num_command(num),
                                       font=('Segoe UI', 12, 'bold'), bg=self.button_bg, fg=self.text_color,
                                       width=4, height=2, relief='raised', bd=1, takefocus=1)
                    num_btn.grid(row=i, column=j, padx=3, pady=3, sticky='nsew')
                    self.add_button_hover(num_btn, self.button_hover, self.button_bg)
                else:
                    # Create empty label to maintain grid structure
                    empty_label = tk.Label(num_frame, text="", bg=self.bg_color)
                    empty_label.grid(row=i, column=j, padx=3, pady=3)

        # Make sure the grid columns have equal weight
        for i in range(3):
            num_frame.grid_columnconfigure(i, weight=1)

        # Color buttons
        color_frame = ttk.Frame(main_frame, style='Card.TFrame')
        color_frame.pack(pady=10)

        colors = [
            ('A', '#ff4444', 'KEY_RED'),
            ('B', '#44ff44', 'KEY_GREEN'),
            ('C', '#ffff44', 'KEY_YELLOW'),
            ('D', '#4444ff', 'KEY_BLUE'),
            ('E', '#00ffff', 'KEY_CYAN'),
            ('F', '#ff00ff', 'KEY_MAGENTA')
        ]

        for color_name, color_code, key in colors:
            def make_color_command(k):
                return lambda: self.send_key(k)
            color_btn = tk.Button(color_frame, text=color_name, command=make_color_command(key),
                                 font=('Segoe UI', 10, 'bold'), bg=color_code, fg='white',
                                 width=6, height=2, relief='raised', bd=2, takefocus=1)
            color_btn.pack(side=tk.LEFT, padx=5)
            self.add_button_hover(color_btn, self.adjust_color(color_code, 30), color_code)

        # Smart Apps section
        smart_apps_frame = ttk.Frame(main_frame, style='Card.TFrame')
        smart_apps_frame.pack(pady=10)

        smart_apps_label = tk.Label(smart_apps_frame, text="Smart Apps", font=('Segoe UI', 10, 'bold'),
                                   fg=self.text_color, bg=self.bg_color)
        smart_apps_label.pack(anchor=tk.W, pady=(0, 5))

        # Smart app buttons
        smart_apps = [
            ("Netflix", "KEY_NETFLIX", "#E50914"),
            ("YouTube", "KEY_YOUTUBE", "#FF0000"),
            ("Amazon", "KEY_AMAZON", "#00A8E1"),
            ("Hulu", "KEY_HULU", "#1CE783"),
            ("Disney+", "KEY_DISNEY", "#0063E5")
        ]

        for app_name, key, app_color in smart_apps:
            def make_app_command(k):
                return lambda: self.send_key(k)
            app_btn = tk.Button(smart_apps_frame, text=app_name, command=make_app_command(key),
                               font=('Segoe UI', 8), bg=app_color, fg='white',
                               width=8, height=1, relief='raised', bd=1, takefocus=1)
            app_btn.pack(side=tk.LEFT, padx=1)
            self.add_button_hover(app_btn, self.adjust_color(app_color, 30), app_color)

        # Gaming section
        gaming_frame = ttk.Frame(main_frame, style='Card.TFrame')
        gaming_frame.pack(pady=10)

        gaming_label = tk.Label(gaming_frame, text="Gaming", font=('Segoe UI', 10, 'bold'),
                               fg=self.text_color, bg=self.bg_color)
        gaming_label.pack(anchor=tk.W, pady=(0, 5))

        # Gaming buttons
        gaming_apps = [
            ("Game", "KEY_GAME", "#9C27B0"),
            ("Game Mode", "KEY_GAME_MODE", "#673AB7")
        ]

        for game_name, key, game_color in gaming_apps:
            def make_game_command(k):
                return lambda: self.send_key(k)
            game_btn = tk.Button(gaming_frame, text=game_name, command=make_game_command(key),
                                font=('Segoe UI', 8), bg=game_color, fg='white',
                                width=10, height=1, relief='raised', bd=1, takefocus=1)
            game_btn.pack(side=tk.LEFT, padx=1)
            self.add_button_hover(game_btn, self.adjust_color(game_color, 30), game_color)

        # Advanced Controls section
        advanced_frame = ttk.Frame(main_frame, style='Card.TFrame')
        advanced_frame.pack(pady=10)

        advanced_label = tk.Label(advanced_frame, text="Advanced Controls", font=('Segoe UI', 10, 'bold'),
                                 fg=self.text_color, bg=self.bg_color)
        advanced_label.pack(anchor=tk.W, pady=(0, 5))

        # Advanced control buttons - arranged in rows
        advanced_controls_row1 = [
            ("3D", "KEY_3D", "#FF5722"),
            ("Subtitle", "KEY_SUBTITLE", "#795548"),
            ("AD", "KEY_AD", "#607D8B"),
            ("Repeat", "KEY_REPEAT", "#9E9E9E"),
            ("Shuffle", "KEY_SHUFFLE", "#BDBDBD"),
            ("TTX Mix", "KEY_TTX_MIX", "#FF9800"),
            ("TTX Subface", "KEY_TTX_SUBFACE", "#FF5722")
        ]

        advanced_controls_row2 = [
            ("PIP On/Off", "KEY_PIP_ONOFF", "#2196F3"),
            ("PIP Swap", "KEY_PIP_SWAP", "#03A9F4"),
            ("PIP CH+", "KEY_PIP_CHUP", "#00BCD4"),
            ("PIP CH-", "KEY_PIP_CHDOWN", "#009688")
        ]

        # First row
        for ctrl_name, key, ctrl_color in advanced_controls_row1:
            def make_ctrl_command(k):
                return lambda: self.send_key(k)
            ctrl_btn = tk.Button(advanced_frame, text=ctrl_name, command=make_ctrl_command(key),
                                font=('Segoe UI', 7), bg=ctrl_color, fg='white',
                                width=8, height=1, relief='raised', bd=1, takefocus=1)
            ctrl_btn.pack(side=tk.LEFT, padx=1)
            self.add_button_hover(ctrl_btn, self.adjust_color(ctrl_color, 30), ctrl_color)

        # Second row - create a new frame for the second row
        advanced_row2_frame = ttk.Frame(main_frame, style='Card.TFrame')
        advanced_row2_frame.pack(pady=(0, 10))

        for ctrl_name, key, ctrl_color in advanced_controls_row2:
            def make_ctrl_command(k):
                return lambda: self.send_key(k)
            ctrl_btn = tk.Button(advanced_row2_frame, text=ctrl_name, command=make_ctrl_command(key),
                                font=('Segoe UI', 7), bg=ctrl_color, fg='white',
                                width=8, height=1, relief='raised', bd=1, takefocus=1)
            ctrl_btn.pack(side=tk.LEFT, padx=1)
            self.add_button_hover(ctrl_btn, self.adjust_color(ctrl_color, 30), ctrl_color)

        # Additional Sources section
        additional_sources_frame = ttk.Frame(main_frame, style='Card.TFrame')
        additional_sources_frame.pack(pady=10)

        additional_sources_label = tk.Label(additional_sources_frame, text="Additional Sources", font=('Segoe UI', 10, 'bold'),
                                          fg=self.text_color, bg=self.bg_color)
        additional_sources_label.pack(anchor=tk.W, pady=(0, 5))

        # Additional input sources
        additional_inputs = [
            ("Component1", "KEY_COMPONENT1"),
            ("Component2", "KEY_COMPONENT2"),
            ("AV1", "KEY_AV1"),
            ("AV2", "KEY_AV2"),
            ("AV3", "KEY_AV3"),
            ("S-Video1", "KEY_SVIDEO1"),
            ("S-Video2", "KEY_SVIDEO2"),
            ("PC", "KEY_PC"),
            ("DVI", "KEY_DVI"),
            ("RGB", "KEY_RGB")
        ]

        for input_name, key in additional_inputs:
            def make_input_command(k, name):
                return lambda: self.switch_input(k, name)
            input_btn = tk.Button(additional_sources_frame, text=input_name, command=make_input_command(key, input_name),
                                font=('Segoe UI', 6), bg=self.button_bg, fg=self.text_color,
                                width=9, height=1, relief='raised', bd=1, takefocus=1)
            input_btn.pack(side=tk.LEFT, padx=1)
            self.add_button_hover(input_btn, self.button_hover, self.button_bg)

        # Special Functions section
        special_frame = ttk.Frame(main_frame, style='Card.TFrame')
        special_frame.pack(pady=10)

        special_label = tk.Label(special_frame, text="Special Functions", font=('Segoe UI', 10, 'bold'),
                                fg=self.text_color, bg=self.bg_color)
        special_label.pack(anchor=tk.W, pady=(0, 5))

        # Special function buttons - arranged in rows
        special_controls_row1 = [
            ("Magic Channel", "KEY_MAGIC_CHANNEL", "#E91E63"),
            ("Magic Info", "KEY_MAGIC_INFO", "#F44336"),
            ("Magic Picture", "KEY_MAGIC_PICTURE", "#9C27B0"),
            ("Magic Sound", "KEY_MAGIC_SOUND", "#673AB7"),
            ("DVR", "KEY_DVR", "#3F51B5")
        ]

        special_controls_row2 = [
            ("DVR Menu", "KEY_DVR_MENU", "#2196F3"),
            ("Antenna", "KEY_ANTENA", "#03A9F4"),
            ("Clock Display", "KEY_CLOCK_DISPLAY", "#00BCD4"),
            ("Setup Clock", "KEY_SETUP_CLOCK_TIMER", "#009688"),
            ("Factory", "KEY_FACTORY", "#4CAF50")
        ]

        # First row
        for func_name, key, func_color in special_controls_row1:
            def make_func_command(k):
                return lambda: self.send_key(k)
            func_btn = tk.Button(special_frame, text=func_name, command=make_func_command(key),
                                font=('Segoe UI', 6), bg=func_color, fg='white',
                                width=10, height=1, relief='raised', bd=1, takefocus=1)
            func_btn.pack(side=tk.LEFT, padx=1)
            self.add_button_hover(func_btn, self.adjust_color(func_color, 30), func_color)

        # Second row - create a new frame for the second row
        special_row2_frame = ttk.Frame(main_frame, style='Card.TFrame')
        special_row2_frame.pack(pady=(0, 10))

        for func_name, key, func_color in special_controls_row2:
            def make_func_command(k):
                return lambda: self.send_key(k)
            func_btn = tk.Button(special_row2_frame, text=func_name, command=make_func_command(key),
                                font=('Segoe UI', 6), bg=func_color, fg='white',
                                width=10, height=1, relief='raised', bd=1, takefocus=1)
            func_btn.pack(side=tk.LEFT, padx=1)
            self.add_button_hover(func_btn, self.adjust_color(func_color, 30), func_color)

        # Additional function buttons
        func_frame = ttk.Frame(main_frame, style='Card.TFrame')
        func_frame.pack(pady=10)

        functions = [
            ('Menu', 'KEY_MENU'),
            ('Home', 'KEY_HOME'),
            ('Guide', 'KEY_GUIDE'),
            ('Info', 'KEY_INFO'),
            ('Back', 'KEY_RETURN'),
            ('Mute', 'KEY_MUTE'),
            ('Scan API', None),  # Special button for TV API scanning
            ('History', None)  # Special button for command history
        ]

        # Arrange in 2 rows of 4 buttons each (added Scan API and History buttons)
        for i, (func_name, key) in enumerate(functions):
            row = i // 4
            col = i % 4
            if func_name == 'History':
                # Special history button
                history_btn = tk.Button(func_frame, text=func_name, command=self.show_command_history,
                                       font=('Segoe UI', 9), bg=self.accent_color, fg='white',
                                       width=8, height=2, relief='raised', bd=1, takefocus=1)
                history_btn.grid(row=row, column=col, padx=3, pady=3, sticky='nsew')
                self.add_button_hover(history_btn, '#0099ff', self.accent_color)
            elif func_name == 'Scan API':
                # Special scan API button
                scan_btn = tk.Button(func_frame, text=func_name, command=self.scan_tv_api,
                                    font=('Segoe UI', 9), bg='#ff8800', fg='white',
                                    width=8, height=2, relief='raised', bd=1, takefocus=1)
                scan_btn.grid(row=row, column=col, padx=3, pady=3, sticky='nsew')
                self.add_button_hover(scan_btn, '#ffaa33', '#ff8800')
            else:
                def make_func_command(k):
                    return lambda: self.send_key(k)
                func_btn = tk.Button(func_frame, text=func_name, command=make_func_command(key),
                                    font=('Segoe UI', 9), bg=self.button_bg, fg=self.text_color,
                                    width=8, height=2, relief='raised', bd=1, takefocus=1)
                func_btn.grid(row=row, column=col, padx=3, pady=3, sticky='nsew')
                self.add_button_hover(func_btn, self.button_hover, self.button_bg)

        self.add_button_hover(func_btn, self.button_hover, self.button_bg)

        # Picture/Sound settings section
        settings_frame = ttk.Frame(main_frame, style='Card.TFrame')
        settings_frame.pack(pady=10)

        settings_label = tk.Label(settings_frame, text="Picture/Sound Settings", font=('Segoe UI', 10, 'bold'),
                                 fg=self.text_color, bg=self.bg_color)
        settings_label.pack(anchor=tk.W, pady=(0, 5))

        # Picture mode buttons
        picture_modes = [
            ("Standard", "Standard"),
            ("Movie", "Movie"),
            ("Dynamic", "Dynamic"),
            ("Game", "Game")
        ]

        for i, (mode_name, mode_key) in enumerate(picture_modes):
            def make_picture_command(name):
                return lambda: self.set_picture_mode(name)
            pic_btn = tk.Button(settings_frame, text=mode_name, command=make_picture_command(mode_key),
                               font=('Segoe UI', 8), bg=self.button_bg, fg=self.text_color,
                               width=10, height=1, relief='raised', bd=1, takefocus=1)
            pic_btn.pack(side=tk.LEFT, padx=1)
            self.add_button_hover(pic_btn, self.button_hover, self.button_bg)

        # Sound mode buttons
        sound_modes = [
            ("Mono", "KEY_MONO"),
            ("Stereo", "KEY_STEREO"),
            ("Dual", "KEY_DUAL"),
            ("Surround", "KEY_SURROUND")
        ]

        # Create a new frame for sound modes
        sound_frame = ttk.Frame(main_frame, style='Card.TFrame')
        sound_frame.pack(pady=(0, 10))

        sound_label = tk.Label(sound_frame, text="Sound Modes", font=('Segoe UI', 10, 'bold'),
                              fg=self.text_color, bg=self.bg_color)
        sound_label.pack(anchor=tk.W, pady=(0, 5))

        for sound_name, key in sound_modes:
            def make_sound_command(k):
                return lambda: self.send_key(k)
            sound_btn = tk.Button(sound_frame, text=sound_name, command=make_sound_command(key),
                                font=('Segoe UI', 8), bg=self.button_bg, fg=self.text_color,
                                width=10, height=1, relief='raised', bd=1, takefocus=1)
            sound_btn.pack(side=tk.LEFT, padx=1)
            self.add_button_hover(sound_btn, self.button_hover, self.button_bg)

        # Input source selector
        input_frame = ttk.Frame(main_frame, style='Card.TFrame')
        input_frame.pack(pady=10)

        input_label = tk.Label(input_frame, text="Input Sources", font=('Segoe UI', 10, 'bold'),
                              fg=self.text_color, bg=self.bg_color)
        input_label.pack(anchor=tk.W, pady=(0, 5))

        # Common input sources
        inputs = [("TV", "KEY_TV"), ("HDMI1", "KEY_HDMI1"), ("HDMI2", "KEY_HDMI2"), ("HDMI3", "KEY_HDMI3")]
        for i, (input_name, key) in enumerate(inputs):
            def make_input_command(k, name):
                return lambda: self.switch_input(k, name)
            input_btn = tk.Button(input_frame, text=input_name, command=make_input_command(key, input_name),
                                font=('Segoe UI', 7), bg=self.button_bg, fg=self.text_color,
                                width=6, height=1, relief='raised', bd=1, takefocus=1)
            input_btn.pack(side=tk.LEFT, padx=1)
            self.add_button_hover(input_btn, self.button_hover, self.button_bg)

    def create_footer(self):
        """Create footer with IP configuration"""
        footer_frame = ttk.Frame(self.scrollable_frame, style='Card.TFrame')
        footer_frame.pack(fill=tk.X, padx=20, pady=(0, 20))

        # IP configuration
        ip_label = tk.Label(footer_frame, text="TV IP:", font=('Segoe UI', 9),
                           fg=self.secondary_text, bg=self.bg_color)
        ip_label.pack(side=tk.LEFT, padx=(0, 5))

        self.ip_entry = tk.Entry(footer_frame, width=15, font=('Segoe UI', 9),
                                bg=self.button_bg, fg=self.text_color, insertbackground=self.text_color)
        self.ip_entry.insert(0, self.config.get("host", ""))
        self.ip_entry.pack(side=tk.LEFT, padx=(0, 5))

        update_btn = tk.Button(footer_frame, text="Update", command=self.update_ip,
                              font=('Segoe UI', 9), bg=self.accent_color, fg='white',
                              relief='raised', bd=1, padx=10)
        update_btn.pack(side=tk.LEFT, padx=(0, 10))
        self.add_button_hover(update_btn, '#0099ff', self.accent_color)

        # Network discovery button
        discover_btn = tk.Button(footer_frame, text="🔍 Discover TVs", command=self.discover_tvs,
                                font=('Segoe UI', 9), bg='#28a745', fg='white',
                                relief='raised', bd=1, padx=10)
        discover_btn.pack(side=tk.LEFT)
        self.add_button_hover(discover_btn, '#218838', '#28a745')

    def create_round_button(self, parent, text, key, size=12):
        """Create a round button with hover effects"""
        btn = tk.Button(parent, text=text, command=lambda: self.send_key(key),
                       font=('Segoe UI', size, 'bold'), bg=self.button_bg, fg=self.text_color,
                       width=3, height=1, relief='raised', bd=2, takefocus=1)
        self.add_button_hover(btn, self.button_hover, self.button_bg)
        return btn

    def add_button_hover(self, button, hover_color, normal_color):
        """Add hover effect to button"""
        def on_enter(e):
            button.config(bg=hover_color)

        def on_leave(e):
            button.config(bg=normal_color)

        button.bind('<Enter>', on_enter)
        button.bind('<Leave>', on_leave)

    def adjust_color(self, color, amount):
        """Adjust color brightness"""
        # Simple color adjustment for hover effects
        if color.startswith('#'):
            r = min(255, int(color[1:3], 16) + amount)
            g = min(255, int(color[3:5], 16) + amount)
            b = min(255, int(color[5:7], 16) + amount)
            return f'#{r:02x}{g:02x}{b:02x}'
        return color

    def setup_keyboard_navigation(self):
        """Setup keyboard shortcuts for better accessibility"""
        logging.info("Setting up keyboard navigation shortcuts")
        
        # Number keys for direct access
        for i in range(10):
            self.root.bind(str(i), lambda e, num=i: self.send_key(f"KEY_{num}"))

        # Arrow keys for TV navigation (not scrolling)
        self.root.bind('<KeyPress-Up>', lambda e: self.send_key("KEY_UP"))
        self.root.bind('<KeyPress-Down>', lambda e: self.send_key("KEY_DOWN"))
        self.root.bind('<KeyPress-Left>', lambda e: self.send_key("KEY_LEFT"))
        self.root.bind('<KeyPress-Right>', lambda e: self.send_key("KEY_RIGHT"))
        self.root.bind('<Return>', lambda e: self.send_key("KEY_ENTER"))
        self.root.bind('<Escape>', lambda e: self.send_key("KEY_RETURN"))

        # Common shortcuts
        self.root.bind('<space>', lambda e: self.send_key("KEY_PLAY"))  # Space for play/pause
        self.root.bind('p', lambda e: self.send_key("KEY_POWER"))
        self.root.bind('m', lambda e: self.send_key("KEY_MUTE"))
        self.root.bind('=', lambda e: self.send_key("KEY_VOLUP"))  # = key for volume up
        self.root.bind('-', lambda e: self.send_key("KEY_VOLDOWN"))  # - key for volume down
        self.root.bind('c', lambda e: self.send_key("KEY_CHUP"))
        self.root.bind('v', lambda e: self.send_key("KEY_CHDOWN"))

        # Focus management - ensure buttons can receive focus
        self.root.focus_set()
        
        logging.info("Keyboard navigation shortcuts configured")

    def load_config(self):
        config_path = os.path.join(os.getenv("HOME"), ".config", "samsungctl.conf")
        logging.info(f"Attempting to load config from: {config_path}")
        if os.path.exists(config_path):
            try:
                with open(config_path, 'r') as f:
                    config = json.load(f)
                logging.info("Configuration loaded successfully")
                return config
            except Exception as e:
                logging.error(f"Error loading config: {e}")
                return None
        else:
            logging.warning("Config file not found. Using default settings.")
            return None

    def update_ip(self):
        new_ip = self.ip_entry.get()
        if new_ip:
            self.config["host"] = new_ip
            self.save_config()
            logging.info(f"TV IP updated to: {new_ip}")
            try:
                if self.root and self.root.winfo_exists():
                    messagebox.showinfo("Updated", f"TV IP updated to {new_ip}")
            except Exception as dialog_error:
                logging.error(f"Failed to show IP update dialog: {dialog_error}")
            # Reconnect with new IP
            self.connect_to_tv()
        else:
            logging.warning("Attempted to update IP with empty value")
            try:
                if self.root and self.root.winfo_exists():
                    messagebox.showerror("Error", "Please enter a valid IP address")
            except Exception as dialog_error:
                logging.error(f"Failed to show IP error dialog: {dialog_error}")

    def discover_tvs(self):
        """Discover Samsung TVs on the local network"""
        logging.info("Starting TV discovery process")
        
        # Create discovery dialog
        discover_window = tk.Toplevel(self.root)
        discover_window.title("Discover Samsung TVs")
        discover_window.geometry("600x550")
        discover_window.configure(bg=self.bg_color)
        discover_window.resizable(True, True)
        
        # Title
        title_label = tk.Label(discover_window, text="Samsung TV Discovery",
                              font=('Segoe UI', 16, 'bold'), fg=self.text_color, bg=self.bg_color)
        title_label.pack(pady=10)
        
        # Subnet configuration section
        subnet_frame = ttk.Frame(discover_window, style='Card.TFrame')
        subnet_frame.pack(fill=tk.X, padx=20, pady=(0, 10))
        
        subnet_title = tk.Label(subnet_frame, text="Network Subnets to Scan:",
                               font=('Segoe UI', 11, 'bold'), fg=self.text_color, bg=self.bg_color)
        subnet_title.pack(anchor=tk.W, padx=10, pady=(10, 5))
        
        subnet_note = tk.Label(subnet_frame, text="Note: UPnP only works on local subnet. Port scanning checks all subnets.",
                              font=('Segoe UI', 8), fg=self.secondary_text, bg=self.bg_color)
        subnet_note.pack(anchor=tk.W, padx=10, pady=(0, 5))
        
        # Get local subnet automatically
        local_ip = self._get_local_ip()
        local_subnet = self._get_subnet(local_ip) if local_ip else "192.168.1.0/24"
        
        # Subnet entry with local subnet pre-filled
        subnet_entry = tk.Entry(subnet_frame, width=30, font=('Segoe UI', 9),
                               bg=self.button_bg, fg=self.text_color, insertbackground=self.text_color)
        subnet_entry.insert(0, local_subnet)
        subnet_entry.pack(side=tk.LEFT, padx=(10, 5), pady=5)
        
        # Add subnet button
        subnet_listbox = tk.Listbox(subnet_frame, height=3, width=35, font=('Segoe UI', 8),
                                   bg=self.button_bg, fg=self.text_color, selectbackground=self.accent_color)
        subnet_listbox.pack(side=tk.LEFT, padx=(0, 10), pady=5)
        
        # Pre-populate with saved subnets or local subnet
        saved_subnets = self.discovery_subnets if self.discovery_subnets else [local_subnet]
        for subnet in saved_subnets:
            subnet_listbox.insert(tk.END, subnet)
        
        def add_subnet():
            subnet = subnet_entry.get().strip()
            if subnet and subnet not in subnet_listbox.get(0, tk.END):
                try:
                    # Validate subnet format
                    ipaddress.ip_network(subnet, strict=False)
                    subnet_listbox.insert(tk.END, subnet)
                    subnet_entry.delete(0, tk.END)
                    logging.info(f"Added subnet to scan: {subnet}")
                    # Save updated subnets
                    self._save_discovery_subnets(list(subnet_listbox.get(0, tk.END)))
                except ValueError:
                    try:
                        if self.root and self.root.winfo_exists():
                            messagebox.showerror("Invalid Subnet", "Please enter a valid subnet (e.g., 192.168.1.0/24)")
                    except Exception as dialog_error:
                        logging.error(f"Failed to show subnet error dialog: {dialog_error}")
        
        def remove_subnet():
            selection = subnet_listbox.curselection()
            if selection:
                subnet_listbox.delete(selection[0])
                # Save updated subnets
                self._save_discovery_subnets(list(subnet_listbox.get(0, tk.END)))
        
        add_btn = tk.Button(subnet_frame, text="Add", command=add_subnet,
                           font=('Segoe UI', 8), bg=self.accent_color, fg='white',
                           relief='raised', bd=1, padx=8)
        add_btn.pack(side=tk.TOP, pady=(5, 2))
        self.add_button_hover(add_btn, '#0099ff', self.accent_color)
        
        remove_btn = tk.Button(subnet_frame, text="Remove", command=remove_subnet,
                              font=('Segoe UI', 8), bg='#dc3545', fg='white',
                              relief='raised', bd=1, padx=8)
        remove_btn.pack(side=tk.TOP, pady=(2, 5))
        self.add_button_hover(remove_btn, '#c82333', '#dc3545')
        
        # Bind Enter key to add subnet
        subnet_entry.bind('<Return>', lambda e: add_subnet())
        
        # Status label
        status_label = tk.Label(discover_window, text="Discovery Methods:\n• UPnP: Fast, local subnet only\n• Port Scan: Slower, scans all configured subnets",
                               font=('Segoe UI', 9), fg=self.secondary_text, bg=self.bg_color,
                               justify=tk.LEFT)
        status_label.pack(pady=5)
        
        # Progress bar
        progress_var = tk.DoubleVar()
        progress_bar = ttk.Progressbar(discover_window, variable=progress_var, maximum=100)
        progress_bar.pack(fill=tk.X, padx=20, pady=10)
        
        # Results frame with scrollbar
        results_frame = ttk.Frame(discover_window, style='Card.TFrame')
        results_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=(0, 20))
        
        # Create scrollable results area
        canvas = tk.Canvas(results_frame, bg=self.bg_color, highlightthickness=0)
        scrollbar = tk.Scrollbar(results_frame, orient=tk.VERTICAL, command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas, style='Card.TFrame')
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Results container
        self.discovery_results = []
        results_container = ttk.Frame(scrollable_frame, style='Card.TFrame')
        results_container.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Start discovery in background thread
        def start_discovery():
            try:
                # Get subnets to scan from listbox
                subnets_to_scan = list(subnet_listbox.get(0, tk.END))
                if not subnets_to_scan:
                    status_label.config(text="No subnets configured for scanning", fg='#ff4444')
                    return
                    
                self._perform_tv_discovery(discover_window, status_label, progress_var, results_container, subnets_to_scan)
            except Exception as e:
                logging.error(f"TV discovery failed: {e}")
                status_label.config(text=f"Discovery failed: {str(e)}", fg='#ff4444')
        
        # Start discovery button
        start_btn = tk.Button(discover_window, text="🔍 Start Discovery", command=lambda: threading.Thread(target=start_discovery, daemon=True).start(),
                             font=('Segoe UI', 10), bg='#28a745', fg='white',
                             relief='raised', bd=1, padx=15)
        start_btn.pack(pady=(0, 10))
        self.add_button_hover(start_btn, '#218838', '#28a745')
        
        # Close button
        close_btn = tk.Button(discover_window, text="Close", command=discover_window.destroy,
                             font=('Segoe UI', 10), bg=self.button_bg, fg=self.text_color,
                             relief='raised', bd=1, padx=20)
        close_btn.pack(pady=(0, 10))
        self.add_button_hover(close_btn, self.button_hover, self.button_bg)
        
        # Bind mousewheel to canvas
        def on_mousewheel(event):
            canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        canvas.bind("<MouseWheel>", on_mousewheel)

    def _perform_tv_discovery(self, window, status_label, progress_var, results_container, subnets_to_scan):
        """Perform the actual TV discovery process"""
        discovered_tvs = []

        try:
            logging.info(f"Scanning {len(subnets_to_scan)} subnet(s): {subnets_to_scan}")

            # First try UPnP discovery (only works on local subnet)
            status_label.config(text="Searching for TVs using UPnP (local subnet only)...")
            window.update()
            upnp_tvs = self._discover_upnp_tvs()
            discovered_tvs.extend(upnp_tvs)
            logging.info(f"UPnP discovery found {len(upnp_tvs)} TVs on local subnet")

            # Then do port scanning for each configured subnet
            total_subnets = len(subnets_to_scan)

            for subnet_idx, subnet in enumerate(subnets_to_scan):
                status_label.config(text=f"Port scanning subnet {subnet_idx + 1}/{total_subnets}: {subnet}...")
                window.update()
                logging.info(f"Port scanning subnet: {subnet}")

                # Common Samsung TV ports
                tv_ports = [8001, 55000]  # websocket and legacy ports

                # Generate IP range to scan (first 50 IPs in subnet)
                ip_range = []
                try:
                    network = ipaddress.ip_network(subnet, strict=False)
                    for ip in network.hosts():
                        ip_range.append(str(ip))
                        if len(ip_range) >= 50:  # Limit scan to first 50 IPs per subnet
                            break
                except ValueError as e:
                    logging.error(f"Invalid subnet format {subnet}: {e}")
                    continue

                if not ip_range:
                    logging.warning(f"No IP addresses found in subnet {subnet}")
                    continue

                total_ips = len(ip_range)
                status_label.config(text=f"Scanning {total_ips} IPs in {subnet}...")

                # Scan IPs in background
                port_scan_tvs = self._scan_ip_range(ip_range, tv_ports, status_label, progress_var, window)

                # Merge results, avoiding duplicates
                existing_ips = {tv['ip'] for tv in discovered_tvs}
                for tv in port_scan_tvs:
                    if tv['ip'] not in existing_ips:
                        discovered_tvs.append(tv)
                        logging.info(f"Port scan found TV: {tv}")

            # Update results display
            self._display_discovery_results(results_container, discovered_tvs, window)

            # Log detailed results by subnet
            subnet_results = {}
            for tv in discovered_tvs:
                ip_parts = tv['ip'].split('.')
                subnet = f"{ip_parts[0]}.{ip_parts[1]}.{ip_parts[2]}.0/24"
                if subnet not in subnet_results:
                    subnet_results[subnet] = []
                subnet_results[subnet].append(tv)

            logging.info("Discovery results by subnet:")
            for subnet, tvs in subnet_results.items():
                logging.info(f"  {subnet}: {len(tvs)} TV(s) found")

            if discovered_tvs:
                status_label.config(text=f"Found {len(discovered_tvs)} Samsung TV(s)!", fg='#28a745')
                logging.info(f"TV discovery completed. Found {len(discovered_tvs)} TVs across {len(subnets_to_scan)} subnets")
            else:
                status_label.config(text="No Samsung TVs found on configured subnets", fg='#ff8800')
                logging.info("TV discovery completed. No TVs found")
        except Exception as e:
            logging.error(f"Error during TV discovery: {e}")
            status_label.config(text=f"Discovery error: {str(e)}", fg='#ff4444')

    def _get_local_ip(self):
        """Get the local IP address"""
        try:
            # Create a socket to get local IP
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))  # Connect to Google DNS
            local_ip = s.getsockname()[0]
            s.close()
            return local_ip
        except Exception as e:
            logging.error(f"Could not get local IP: {e}")
            return None

    def _get_subnet(self, ip):
        """Get subnet from IP address (assumes /24 subnet)"""
        try:
            ip_parts = ip.split('.')
            return f"{ip_parts[0]}.{ip_parts[1]}.{ip_parts[2]}.0/24"
        except Exception as e:
            logging.error(f"Could not determine subnet: {e}")
            return "192.168.1.0/24"  # Default fallback

    def _scan_ip_range(self, ip_range, ports, status_label, progress_var, window):
        """Scan IP range for Samsung TVs"""
        discovered_tvs = []
        total_ips = len(ip_range)
        
        for i, ip in enumerate(ip_range):
            if not window.winfo_exists():  # Check if window still exists
                break
                
            # Update progress
            progress = (i / total_ips) * 100
            progress_var.set(progress)
            status_label.config(text=f"Scanning {ip}... ({i+1}/{total_ips})")
            window.update()
            
            # Check each port
            for port in ports:
                try:
                    # Quick connection test
                    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    sock.settimeout(0.5)  # 500ms timeout
                    
                    result = sock.connect_ex((ip, port))
                    if result == 0:
                        # Port is open, try to identify as Samsung TV
                        tv_info = self._identify_tv(ip, port)
                        if tv_info:
                            discovered_tvs.append(tv_info)
                            logging.info(f"Found Samsung TV: {tv_info}")
                            break  # Found TV on this IP, no need to check other ports
                    
                    sock.close()
                    
                except Exception as e:
                    logging.debug(f"Error checking {ip}:{port} - {e}")
                    continue
            
            # Small delay to avoid overwhelming network
            time.sleep(0.01)
        
        return discovered_tvs

    def _discover_upnp_tvs(self):
        """Discover Samsung TVs using UPnP/SSDP protocol"""
        discovered_tvs = []
        
        try:
            # SSDP M-SEARCH request for UPnP devices
            ssdp_request = (
                'M-SEARCH * HTTP/1.1\r\n'
                'HOST: 239.255.255.250:1900\r\n'
                'MAN: "ssdp:discover"\r\n'
                'MX: 3\r\n'
                'ST: upnp:rootdevice\r\n'
                'USER-AGENT: SamsungRemote/1.0\r\n'
                '\r\n'
            )
            
            # Create UDP socket for SSDP
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
            sock.settimeout(5)
            
            # Set up multicast
            sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 2)
            
            # Bind to a random port
            sock.bind(('', 0))
            
            # Send M-SEARCH request to SSDP multicast address
            sock.sendto(ssdp_request.encode(), ('239.255.255.250', 1900))
            
            logging.info("Sent UPnP M-SEARCH request")
            
            # Listen for responses
            responses = []
            start_time = time.time()
            
            while time.time() - start_time < 4:  # Listen for 4 seconds
                try:
                    data, addr = sock.recvfrom(4096)
                    response = data.decode('utf-8', errors='ignore')
                    responses.append((response, addr[0]))
                except socket.timeout:
                    break
                except Exception as e:
                    logging.debug(f"Error receiving SSDP response: {e}")
                    break
            
            sock.close()
            
            logging.info(f"Received {len(responses)} UPnP responses")
            
            # Parse responses to find Samsung TVs
            for response, ip in responses:
                tv_info = self._parse_upnp_response(response, ip)
                if tv_info:
                    discovered_tvs.append(tv_info)
                    logging.info(f"Found Samsung TV via UPnP: {tv_info}")
            
        except Exception as e:
            logging.error(f"UPnP discovery failed: {e}")
        
        return discovered_tvs

    def _parse_upnp_response(self, response, ip):
        """Parse UPnP response to identify Samsung TVs"""
        try:
            lines = response.split('\n')
            headers = {}
            
            for line in lines:
                if ':' in line:
                    key, value = line.split(':', 1)
                    headers[key.strip().upper()] = value.strip()
            
            # Check if this is a Samsung TV
            server = headers.get('SERVER', '').upper()
            location = headers.get('LOCATION', '')
            
            # Look for Samsung-specific identifiers
            is_samsung_tv = False
            model_name = "Unknown"
            
            if 'SAMSUNG' in server or 'SEC_HHP' in server:
                is_samsung_tv = True
                model_name = "Samsung TV (UPnP)"
            
            # Check location URL for Samsung-specific patterns
            if not is_samsung_tv and location:
                if 'Samsung' in location or 'SEC_HHP' in location:
                    is_samsung_tv = True
                    model_name = "Samsung TV (UPnP)"
            
            if is_samsung_tv:
                # Determine connection method and port
                method = 'websocket'  # Default to websocket for modern TVs
                port = 8001
                
                # Try to get more specific information
                if location:
                    try:
                        # Parse the location URL to get more details
                        if '8001' in location:
                            method = 'websocket'
                            port = 8001
                        elif '55000' in location:
                            method = 'legacy'
                            port = 55000
                    except:
                        pass
                
                return {
                    'ip': ip,
                    'port': port,
                    'method': method,
                    'name': f"Samsung TV ({ip})",
                    'model': model_name,
                    'discovery_method': 'UPnP'
                }
            
        except Exception as e:
            logging.debug(f"Error parsing UPnP response from {ip}: {e}")
        
        return None

    def _check_ip_conflict(self, target_ip):
        """Check if an IP address is already in use by sending ARP requests"""
        try:
            # Use ARP to check if IP is in use
            import subprocess
            
            # Run ARP command to check if IP is in ARP table
            result = subprocess.run(['arp', '-n', target_ip], 
                                  capture_output=True, text=True, timeout=5)
            
            # Check if IP appears in ARP table (indicates it's in use)
            if target_ip in result.stdout and result.returncode == 0:
                lines = result.stdout.strip().split('\n')
                for line in lines:
                    if target_ip in line and ('ether' in line or 'hwaddr' in line):
                        logging.warning(f"IP conflict detected: {target_ip} is already in ARP table")
                        return True
            
            # Also try a quick ping to see if host responds
            ping_result = subprocess.run(['ping', '-c', '1', '-W', '1', target_ip],
                                       capture_output=True, timeout=3)
            
            if ping_result.returncode == 0:
                logging.warning(f"IP conflict detected: {target_ip} responds to ping")
                return True
            
            logging.info(f"No IP conflict detected for {target_ip}")
            return False
            
        except Exception as e:
            logging.debug(f"Could not check IP conflict for {target_ip}: {e}")
            # If we can't check, assume no conflict to avoid blocking connections
            return False

    def _resolve_ip_conflict(self, conflicting_ip):
        """Attempt to resolve IP conflicts by suggesting alternatives"""
        try:
            local_ip = self._get_local_ip()
            if not local_ip:
                return None
            
            # Get network information
            network = ipaddress.ip_network(self._get_subnet(local_ip), strict=False)
            
            # Find a free IP in the same subnet
            used_ips = set()
            
            # Check ARP table for used IPs
            try:
                import subprocess
                arp_result = subprocess.run(['arp', '-n'], capture_output=True, text=True)
                for line in arp_result.stdout.split('\n'):
                    if '(' in line and ')' in line:
                        ip = line.split('(')[1].split(')')[0]
                        used_ips.add(ip)
            except:
                pass
            
            # Find next available IP
            base_ip = ipaddress.ip_address(local_ip)
            for i in range(1, 20):  # Check next 20 IPs
                candidate = str(base_ip + i)
                if candidate not in used_ips and ipaddress.ip_address(candidate) in network:
                    # Quick ping check
                    try:
                        ping_result = subprocess.run(['ping', '-c', '1', '-W', '1', candidate],
                                                   capture_output=True, timeout=2)
                        if ping_result.returncode != 0:  # No response means IP is free
                            return candidate
                    except:
                        return candidate
            
            return None
            
        except Exception as e:
            logging.error(f"Error resolving IP conflict: {e}")
            return None
        """Try to identify if IP:port belongs to a Samsung TV"""
        try:
            # Try websocket connection first (modern TVs)
            if port == 8001:
                try:
                    # Quick websocket test
                    import websocket
                    ws_url = f"ws://{ip}:{port}/api/v2/channels/samsung.remote.control"
                    ws = websocket.create_connection(ws_url, timeout=2)
                    ws.close()
                    
                    # If we get here, it's likely a Samsung TV
                    return {
                        'ip': ip,
                        'port': port,
                        'method': 'websocket',
                        'name': f"Samsung TV ({ip})",
                        'model': 'Unknown (WebSocket)'
                    }
                except:
                    pass
            
            # Try legacy connection
            elif port == 55000:
                try:
                    # Send a simple legacy command to test
                    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    sock.settimeout(2)
                    sock.connect((ip, port))
                    
                    # Send a minimal command to test
                    test_cmd = b"\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"
                    sock.send(test_cmd)
                    
                    # If no immediate error, might be a TV
                    response = sock.recv(1024)
                    sock.close()
                    
                    if response:
                        return {
                            'ip': ip,
                            'port': port,
                            'method': 'legacy',
                            'name': f"Samsung TV ({ip})",
                            'model': 'Unknown (Legacy)'
                        }
                except:
                    pass
            
            # Additional identification methods could be added here
            # UPnP discovery, service detection, etc.
            
        except Exception as e:
            logging.debug(f"Error identifying TV at {ip}:{port} - {e}")
        
        return None

    def _display_discovery_results(self, container, discovered_tvs, window):
        """Display discovered TVs in the results container"""
        # Clear existing results
        for widget in container.winfo_children():
            widget.destroy()
        
        if not discovered_tvs:
            subnet_info = ", ".join(subnets_to_scan)
            no_results_label = tk.Label(container, text=f"No Samsung TVs found on configured subnets: {subnet_info}\n\nPossible reasons:\n• TVs are on different subnets that aren't routable\n• TVs have network discovery disabled\n• TVs are powered off or not connected to Wi-Fi\n• Firewall blocking discovery traffic\n• Try manual IP entry if you know your TV's address",
                                       font=('Segoe UI', 9), fg=self.secondary_text, bg=self.bg_color,
                                       justify=tk.LEFT, wraplength=500)
            no_results_label.pack(pady=20)
            return
        
        # Display found TVs
        results_label = tk.Label(container, text=f"Found {len(discovered_tvs)} Samsung TV(s):",
                                font=('Segoe UI', 12, 'bold'), fg=self.text_color, bg=self.bg_color)
        results_label.pack(anchor=tk.W, pady=(0, 10))
        
        for i, tv in enumerate(discovered_tvs):
            # TV info frame
            tv_frame = ttk.Frame(container, style='Card.TFrame')
            tv_frame.pack(fill=tk.X, pady=5)
            
            # TV details
            tv_info = f"📺 {tv['name']}\nIP: {tv['ip']} | Port: {tv['port']} | Method: {tv['method']}"
            if tv.get('discovery_method'):
                tv_info += f" | Found via: {tv['discovery_method']}"
            tv_label = tk.Label(tv_frame, text=tv_info, font=('Segoe UI', 9),
                               fg=self.text_color, bg=self.bg_color, justify=tk.LEFT)
            tv_label.pack(side=tk.LEFT, padx=10, pady=5)
            
            # Connect button
            connect_btn = tk.Button(tv_frame, text="Connect", 
                                   command=lambda ip=tv['ip'], port=tv['port'], method=tv['method']: self._connect_to_discovered_tv(ip, port, method, window),
                                   font=('Segoe UI', 9), bg=self.accent_color, fg='white',
                                   relief='raised', bd=1, padx=15)
            connect_btn.pack(side=tk.RIGHT, padx=10, pady=5)
            self.add_button_hover(connect_btn, '#0099ff', self.accent_color)

    def _connect_to_discovered_tv(self, ip, port, method, discovery_window):
        """Connect to a discovered TV and update configuration"""
        try:
            # Check for IP conflicts before connecting
            conflict_detected = self._check_ip_conflict(ip)
            if conflict_detected:
                response = messagebox.askyesno(
                    "IP Conflict Detected",
                    f"Warning: IP address {ip} may be in use by another device.\n"
                    "This could cause connection issues.\n\n"
                    "Do you want to continue anyway?",
                    icon='warning'
                )
                if not response:
                    logging.warning(f"User cancelled connection to {ip} due to IP conflict")
                    return
            
            # Update IP entry
            self.ip_entry.delete(0, tk.END)
            self.ip_entry.insert(0, ip)
            
            # Update config
            self.config["host"] = ip
            self.config["port"] = port
            self.config["method"] = method
            
            # Save config
            self.save_config()
            
            # Try to connect
            self.connect_to_tv()
            
            # Close discovery window
            discovery_window.destroy()
            
            # Show success message
            try:
                if self.root and self.root.winfo_exists():
                    messagebox.showinfo("Connected", f"Successfully connected to Samsung TV at {ip}")
            except Exception as dialog_error:
                logging.error(f"Failed to show connection success dialog: {dialog_error}")
                
            logging.info(f"Connected to discovered TV: {ip}:{port} ({method})")
            
        except Exception as e:
            logging.error(f"Failed to connect to discovered TV: {e}")
            try:
                if self.root and self.root.winfo_exists():
                    messagebox.showerror("Connection Failed", f"Could not connect to TV at {ip}: {str(e)}")
            except Exception as dialog_error:
                logging.error(f"Failed to show connection error dialog: {dialog_error}")

    def switch_input(self, key, input_name):
        """Switch to a specific input source"""
        logging.info(f"Switching to input: {input_name}")
        try:
            self.send_key("KEY_SOURCE")  # Open input selector
            # Navigate to desired input (this may need adjustment based on TV menu layout)
            self.root.after(500, lambda: self.send_key(key))
            logging.info(f"Input switch command sent for: {input_name}")
        except Exception as e:
            logging.error(f"Failed to switch to input {input_name}: {e}")
            try:
                if self.root and self.root.winfo_exists():
                    messagebox.showerror("Input Error", f"Could not switch to {input_name}")
            except Exception as dialog_error:
                logging.error(f"Failed to show input error dialog: {dialog_error}")

    def set_picture_mode(self, mode_name):
        """Set picture mode (Standard, Movie, Dynamic, Game)"""
        logging.info(f"Setting picture mode to: {mode_name}")
        try:
            # Navigate to settings menu - this sequence may need adjustment
            self.send_key("KEY_MENU")  # Open menu
            time.sleep(0.5)
            self.send_key("KEY_DOWN")  # Navigate to Picture
            time.sleep(0.5)
            self.send_key("KEY_ENTER")  # Enter Picture menu
            time.sleep(0.5)
            # Navigate to Picture Mode (this varies by TV model)
            self.send_key("KEY_DOWN")
            time.sleep(0.5)
            self.send_key("KEY_ENTER")  # Enter Picture Mode submenu
            time.sleep(0.5)
            # Select the desired mode
            mode_nav = {
                "Standard": ["KEY_ENTER"],  # Usually first option
                "Movie": ["KEY_DOWN", "KEY_ENTER"],
                "Dynamic": ["KEY_DOWN", "KEY_DOWN", "KEY_ENTER"],
                "Game": ["KEY_DOWN", "KEY_DOWN", "KEY_DOWN", "KEY_ENTER"]
            }
            if mode_name in mode_nav:
                for key in mode_nav[mode_name]:
                    self.send_key(key)
                    time.sleep(0.5)
            logging.info(f"Picture mode set to: {mode_name}")
        except Exception as e:
            logging.error(f"Failed to set picture mode to {mode_name}: {e}")
            try:
                if self.root and self.root.winfo_exists():
                    messagebox.showerror("Picture Mode Error", f"Could not set picture mode to {mode_name}")
            except Exception as dialog_error:
                logging.error(f"Failed to show picture mode error dialog: {dialog_error}")

    def scan_tv_api(self):
        """Scan and discover available TV commands/keys"""
        if not self.remote:
            try:
                if self.root and self.root.winfo_exists():
                    messagebox.showerror("Not Connected", "Please connect to TV first")
            except Exception as dialog_error:
                logging.error(f"Failed to show scan connection error dialog: {dialog_error}")
            return
            
        # Create scanning window
        scan_window = tk.Toplevel(self.root)
        scan_window.title("TV API Scanner")
        scan_window.geometry("700x600")
        
        # Create scrollable frame
        canvas = tk.Canvas(scan_window, bg=self.bg_color)
        scrollbar = tk.Scrollbar(scan_window, orient=tk.VERTICAL, command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas, style='Card.TFrame')
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Title
        title_label = tk.Label(scrollable_frame, text="Samsung TV API Scanner",
                              font=('Segoe UI', 16, 'bold'), fg=self.text_color, bg=self.bg_color)
        title_label.pack(pady=10)
        
        # Status label
        status_label = tk.Label(scrollable_frame, text="Scanning TV commands... Please wait.",
                               font=('Segoe UI', 10), fg=self.accent_color, bg=self.bg_color)
        status_label.pack(pady=5)
        
        # Progress bar
        progress_var = tk.DoubleVar()
        progress_bar = ttk.Progressbar(scrollable_frame, variable=progress_var, maximum=100)
        progress_bar.pack(fill=tk.X, padx=20, pady=10)
        
        # Results text area
        results_text = tk.Text(scrollable_frame, wrap=tk.WORD, height=20, padx=10, pady=10)
        results_scrollbar = tk.Scrollbar(scrollable_frame, command=results_text.yview)
        results_text.config(yscrollcommand=results_scrollbar.set)
        
        results_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(20, 0), pady=10)
        results_scrollbar.pack(side=tk.RIGHT, fill=tk.Y, pady=10, padx=(0, 20))
        
        # Start scanning in a separate thread to avoid blocking UI
        def scan_commands():
            try:
                # Common Samsung TV keys to test
                test_keys = [
                    # Basic controls
                    "KEY_POWER", "KEY_POWEROFF", "KEY_POWERON",
                    # Volume
                    "KEY_VOLUP", "KEY_VOLDOWN", "KEY_MUTE",
                    # Channel
                    "KEY_CHUP", "KEY_CHDOWN", "KEY_CH_LIST",
                    # Navigation
                    "KEY_UP", "KEY_DOWN", "KEY_LEFT", "KEY_RIGHT", "KEY_ENTER", "KEY_RETURN",
                    # Media controls
                    "KEY_PLAY", "KEY_PAUSE", "KEY_STOP", "KEY_REWIND", "KEY_FF", "KEY_REC",
                    # Menu and home
                    "KEY_MENU", "KEY_HOME", "KEY_GUIDE", "KEY_INFO", "KEY_EXIT",
                    # Source/Input
                    "KEY_SOURCE", "KEY_TV", "KEY_HDMI", "KEY_HDMI1", "KEY_HDMI2", "KEY_HDMI3", "KEY_HDMI4",
                    # Color buttons
                    "KEY_RED", "KEY_GREEN", "KEY_YELLOW", "KEY_BLUE", "KEY_CYAN", "KEY_MAGENTA",
                    # Number keys
                    "KEY_0", "KEY_1", "KEY_2", "KEY_3", "KEY_4", "KEY_5", "KEY_6", "KEY_7", "KEY_8", "KEY_9",
                    # Additional controls
                    "KEY_SLEEP", "KEY_WAKEUP", "KEY_ASPECT", "KEY_PICTURE_MODE", "KEY_SOUND_MODE",
                    "KEY_TOOLS", "KEY_MORE", "KEY_APPS", "KEY_WIDGETS", "KEY_SEARCH", "KEY_VOICE",
                    # Smart features
                    "KEY_NETFLIX", "KEY_YOUTUBE", "KEY_AMAZON", "KEY_HULU", "KEY_DISNEY",
                    # Gaming
                    "KEY_GAME", "KEY_GAME_MODE",
                    # Additional media
                    "KEY_3D", "KEY_SUBTITLE", "KEY_AD", "KEY_REPEAT", "KEY_SHUFFLE",
                    # Teletext
                    "KEY_TTX_MIX", "KEY_TTX_SUBFACE",
                    # PIP (Picture in Picture)
                    "KEY_PIP_ONOFF", "KEY_PIP_SWAP", "KEY_PIP_CHUP", "KEY_PIP_CHDOWN",
                    # Additional sources
                    "KEY_COMPONENT1", "KEY_COMPONENT2", "KEY_AV1", "KEY_AV2", "KEY_AV3",
                    "KEY_SVIDEO1", "KEY_SVIDEO2", "KEY_PC", "KEY_DVI", "KEY_RGB",
                    # Sound controls
                    "KEY_SOUNDMODE", "KEY_MONO", "KEY_STEREO", "KEY_DUAL", "KEY_SURROUND",
                    # Picture controls
                    "KEY_PMODE", "KEY_PSIZE", "KEY_POSITION", "KEY_PIP_SIZE", "KEY_PIP_POSITION",
                    # Additional functions
                    "KEY_MAGIC_CHANNEL", "KEY_MAGIC_INFO", "KEY_MAGIC_PICTURE", "KEY_MAGIC_SOUND",
                    "KEY_DVR", "KEY_DVR_MENU", "KEY_ANTENA", "KEY_CLOCK_DISPLAY",
                    "KEY_SETUP_CLOCK_TIMER", "KEY_FACTORY", "KEY_11", "KEY_12"
                ]
                
                working_keys = []
                failed_keys = []
                total_keys = len(test_keys)
                
                results_text.insert(tk.END, f"Scanning {total_keys} TV commands...\n")
                results_text.insert(tk.END, "=" * 60 + "\n\n")
                results_text.update()
                
                for i, key in enumerate(test_keys):
                    try:
                        # Update progress
                        progress_var.set((i / total_keys) * 100)
                        status_label.config(text=f"Testing: {key} ({i+1}/{total_keys})")
                        scan_window.update()
                        
                        # Try to send the key
                        self.remote.control(key)
                        
                        # If we get here without exception, key is supported
                        working_keys.append(key)
                        results_text.insert(tk.END, f"✓ {key}\n")
                        results_text.see(tk.END)
                        results_text.update()
                        
                        # Small delay to avoid overwhelming the TV
                        time.sleep(0.1)
                        
                    except Exception as e:
                        failed_keys.append((key, str(e)))
                        results_text.insert(tk.END, f"✗ {key} - {str(e)}\n")
                        results_text.see(tk.END)
                        results_text.update()
                
                # Final results
                progress_var.set(100)
                status_label.config(text=f"Scan complete! Found {len(working_keys)} working commands.")
                
                results_text.insert(tk.END, "\n" + "=" * 60 + "\n")
                results_text.insert(tk.END, f"SCAN RESULTS SUMMARY:\n")
                results_text.insert(tk.END, f"Working commands: {len(working_keys)}\n")
                results_text.insert(tk.END, f"Failed commands: {len(failed_keys)}\n")
                results_text.insert(tk.END, f"Success rate: {(len(working_keys)/total_keys)*100:.1f}%\n\n")
                
                if working_keys:
                    results_text.insert(tk.END, "WORKING COMMANDS:\n")
                    for key in working_keys:
                        results_text.insert(tk.END, f"  {key}\n")
                
                results_text.see(tk.END)
                results_text.config(state=tk.DISABLED)
                
                # Save results to file
                self.save_scan_results(working_keys, failed_keys)
                
            except Exception as e:
                status_label.config(text=f"Scan failed: {str(e)}", fg='#ff4444')
                results_text.insert(tk.END, f"\nScan failed: {str(e)}")
                logging.error(f"TV API scan failed: {e}")
        
        # Start scanning in background thread
        import threading
        scan_thread = threading.Thread(target=scan_commands, daemon=True)
        scan_thread.start()
        
        # Bind mousewheel to canvas
        def on_mousewheel(event):
            canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        canvas.bind("<MouseWheel>", on_mousewheel)

    def save_scan_results(self, working_keys, failed_keys):
        """Save scan results to a file"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"tv_api_scan_{timestamp}.txt"
            
            with open(filename, 'w') as f:
                f.write("Samsung TV API Scan Results\n")
                f.write("=" * 50 + "\n")
                f.write(f"Scan Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"TV IP: {self.config.get('host', 'Unknown')}\n\n")
                
                f.write(f"WORKING COMMANDS ({len(working_keys)}):\n")
                f.write("-" * 30 + "\n")
                for key in working_keys:
                    f.write(f"{key}\n")
                
                f.write(f"\nFAILED COMMANDS ({len(failed_keys)}):\n")
                f.write("-" * 30 + "\n")
                for key, error in failed_keys:
                    f.write(f"{key} - {error}\n")
            
            logging.info(f"Scan results saved to: {filename}")
            
        except Exception as e:
            logging.error(f"Failed to save scan results: {e}")

    def show_command_history(self):
        """Display command history in a new window"""
        history_window = tk.Toplevel(self.root)
        history_window.title("Command History")
        history_window.geometry("500x400")
        
        # Create text widget for history
        history_text = tk.Text(history_window, wrap=tk.WORD, padx=10, pady=10)
        scrollbar = tk.Scrollbar(history_window, command=history_text.yview)
        history_text.config(yscrollcommand=scrollbar.set)
        
        # Pack widgets
        history_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Add history entries
        history_text.insert(tk.END, "Command History (Most Recent First):\n")
        history_text.insert(tk.END, "=" * 50 + "\n\n")
        
        for i, entry in enumerate(self.command_history, 1):
            status = "✓" if entry['success'] else "✗"
            retried = " (Retried)" if entry.get('retried') else ""
            error_info = f" - Error: {entry['error']}" if not entry['success'] and 'error' in entry else ""
            
            history_text.insert(tk.END, f"{i}. [{entry['timestamp']}] {entry['command']} {status}{retried}{error_info}\n")
        
        if not self.command_history:
            history_text.insert(tk.END, "No commands sent yet.\n")
        
        history_text.config(state=tk.DISABLED)  # Make read-only
        
        # Add clear history button
        clear_button = tk.Button(history_window, text="Clear History", 
                                command=lambda: self.clear_command_history(history_window, history_text))
        clear_button.pack(pady=5)

    def clear_command_history(self, window, text_widget):
        """Clear the command history"""
        self.command_history.clear()
        text_widget.config(state=tk.NORMAL)
        text_widget.delete(1.0, tk.END)
        text_widget.insert(tk.END, "Command History (Most Recent First):\n")
        text_widget.insert(tk.END, "=" * 50 + "\n\n")
        text_widget.insert(tk.END, "History cleared.\n")
        text_widget.config(state=tk.DISABLED)
        logging.info("Command history cleared by user")

    def _save_discovery_subnets(self, subnets):
        """Save discovery subnets to configuration"""
        self.discovery_subnets = subnets
        self.config['discovery_subnets'] = subnets
        self.save_config()
        logging.info(f"Saved {len(subnets)} discovery subnets to configuration")

    def save_config(self):
        config_path = os.path.join(os.getenv("HOME"), ".config", "samsungctl.conf")
        try:
            os.makedirs(os.path.dirname(config_path), exist_ok=True)
            with open(config_path, 'w') as f:
                json.dump(self.config, f, indent=4)
            logging.info(f"Configuration saved to: {config_path}")
        except Exception as e:
            logging.error(f"Failed to save configuration: {e}")

    def update_scroll_indicator(self):
        """Update the scroll position indicator"""
        if not self.canvas.winfo_exists():
            return
            
        try:
            # Get scroll position (0.0 to 1.0)
            scroll_pos = self.canvas.yview()[0]
            
            if scroll_pos > 0.1:  # Show indicator when scrolled down
                self.scroll_indicator.place(relx=0.95, rely=0.05, anchor='center')
            else:
                self.scroll_indicator.place_forget()
        except Exception as e:
            logging.error(f"Error updating scroll indicator: {e}")

    def scroll_to_top(self):
        """Scroll to the top of the interface"""
        logging.debug("Scroll to top requested")
        if self.canvas.winfo_exists():
            try:
                self.canvas.yview_moveto(0.0)
                self.update_scroll_indicator()
                logging.debug("Scrolled to top successfully")
            except Exception as e:
                logging.error(f"Error scrolling to top: {e}")

    def on_close(self):
        logging.info("Application shutdown initiated")
        if self.remote:
            try:
                self.remote.__exit__(None, None, None)
                logging.info("TV connection closed successfully")
            except:
                logging.warning("Error occurred while closing TV connection")
        logging.info("Application shutdown completed")
        self.root.destroy()

if __name__ == "__main__":
    logging.info("Starting Samsung TV Remote GUI application")
    try:
        root = tk.Tk()
        app = ModernSamsungRemote(root)
        logging.info("Entering main event loop")
        root.mainloop()
        logging.info("Main event loop exited")
    except Exception as e:
        logging.critical(f"Critical error in main application: {e}")
        raise