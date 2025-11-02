#!/usr/bin/env python3

import tkinter as tk
from tkinter import ttk
from tkinter import messagebox
import samsungctl
import json
import os

class ModernSamsungRemote:
    def __init__(self, root):
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

        # Load logo
        try:
            self.logo_image = tk.PhotoImage(file="samsung_icon.png")
        except Exception as e:
            print(f"Could not load logo: {e}")
            self.logo_image = None

        # Setup modern styling
        self.setup_styles()

        # Create scrollable canvas
        self.create_scrollable_canvas()

        # Initialize connection
        self.remote = None
        self.connect_to_tv()

        # Create main layout inside scrollable frame
        self.create_header()
        self.create_main_remote()
        self.create_footer()

        # Setup keyboard navigation
        self.setup_keyboard_navigation()

        # Configure scrolling
        self.configure_scrolling()

        # Bind close event
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

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

        # Mouse wheel scrolling - improved implementation
        def on_mousewheel(event):
            if self.canvas.winfo_exists() and self.canvas.winfo_viewable():
                # Smoother scrolling - scroll by 3 units instead of 1
                delta = int(-1*(event.delta/120)) * 3
                self.canvas.yview_scroll(delta, "units")
                return "break"  # Prevent event propagation

        def on_shift_mousewheel(event):
            if self.canvas.winfo_exists() and self.canvas.winfo_viewable():
                # Horizontal scrolling with Shift+wheel
                delta = int(-1*(event.delta/120)) * 3
                self.canvas.xview_scroll(delta, "units")
                return "break"  # Prevent event propagation

        # Bind mouse wheel to canvas with better event handling
        self.canvas.bind_all("<MouseWheel>", on_mousewheel, add="+")
        self.canvas.bind_all("<Shift-MouseWheel>", on_shift_mousewheel, add="+")

        # Also bind to the main window for better coverage
        self.root.bind_all("<MouseWheel>", on_mousewheel, add="+")
        self.root.bind_all("<Shift-MouseWheel>", on_shift_mousewheel, add="+")

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
                self.remote.control(key)
            except Exception as e:
                messagebox.showerror("Error", f"Failed to send command: {str(e)}")
        else:
            messagebox.showwarning("Not Connected", "Please connect to TV first")

    def connect_to_tv(self):
        """Establish connection to TV"""
        try:
            self.remote = samsungctl.Remote(self.config).__enter__()
            self.connection_status = "Connected"
        except Exception as e:
            self.connection_status = "Disconnected"
            messagebox.showerror("Connection Error", f"Failed to connect to TV: {str(e)}")

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
        status_text = "Disconnected - No Config" if not self.config.get("host") else ("Connected" if self.connection_status == "Connected" else "Disconnected")
        status_color = '#ff4444' if not self.config.get("host") else ('#00ff00' if self.connection_status == "Connected" else '#ff4444')
        status_label = tk.Label(header_frame, text=f"● {status_text}",
                               font=('Segoe UI', 8), fg=status_color, bg='#0078d4')
        status_label.pack(side=tk.RIGHT, padx=15, anchor=tk.S)

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
            ('D', '#4444ff', 'KEY_BLUE')
        ]

        for color_name, color_code, key in colors:
            def make_color_command(k):
                return lambda: self.send_key(k)
            color_btn = tk.Button(color_frame, text=color_name, command=make_color_command(key),
                                 font=('Segoe UI', 10, 'bold'), bg=color_code, fg='white',
                                 width=6, height=2, relief='raised', bd=2, takefocus=1)
            color_btn.pack(side=tk.LEFT, padx=5)
            self.add_button_hover(color_btn, self.adjust_color(color_code, 30), color_code)

        # Additional function buttons
        func_frame = ttk.Frame(main_frame, style='Card.TFrame')
        func_frame.pack(pady=10)

        functions = [
            ('Menu', 'KEY_MENU'),
            ('Home', 'KEY_HOME'),
            ('Guide', 'KEY_GUIDE'),
            ('Info', 'KEY_INFO'),
            ('Back', 'KEY_RETURN'),
            ('Mute', 'KEY_MUTE')
        ]

        # Arrange in 2 rows of 3 buttons each
        for i, (func_name, key) in enumerate(functions):
            row = i // 3
            col = i % 3
            def make_func_command(k):
                return lambda: self.send_key(k)
            func_btn = tk.Button(func_frame, text=func_name, command=make_func_command(key),
                                font=('Segoe UI', 9), bg=self.button_bg, fg=self.text_color,
                                width=8, height=2, relief='raised', bd=1, takefocus=1)
            func_btn.grid(row=row, column=col, padx=3, pady=3, sticky='nsew')
            self.add_button_hover(func_btn, self.button_hover, self.button_bg)

        # Make sure the grid columns have equal weight
        for i in range(3):
            func_frame.grid_columnconfigure(i, weight=1)

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
        update_btn.pack(side=tk.LEFT)
        self.add_button_hover(update_btn, '#0099ff', self.accent_color)

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

    def load_config(self):
        config_path = os.path.join(os.getenv("HOME"), ".config", "samsungctl.conf")
        if os.path.exists(config_path):
            try:
                with open(config_path, 'r') as f:
                    return json.load(f)
            except Exception as e:
                print(f"Error loading config: {e}")
                return None
        else:
            print("Config file not found. Using default settings.")
            return None

    def update_ip(self):
        new_ip = self.ip_entry.get()
        if new_ip:
            self.config["host"] = new_ip
            self.save_config()
            messagebox.showinfo("Updated", f"TV IP updated to {new_ip}")
            # Reconnect with new IP
            self.connect_to_tv()
        else:
            messagebox.showerror("Error", "Please enter a valid IP address")

    def save_config(self):
        config_path = os.path.join(os.getenv("HOME"), ".config", "samsungctl.conf")
        os.makedirs(os.path.dirname(config_path), exist_ok=True)
        with open(config_path, 'w') as f:
            json.dump(self.config, f, indent=4)

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
        except:
            pass

    def scroll_to_top(self):
        """Scroll to the top of the interface"""
        if self.canvas.winfo_exists():
            self.canvas.yview_moveto(0.0)
            self.update_scroll_indicator()

    def on_close(self):
        if self.remote:
            try:
                self.remote.__exit__(None, None, None)
            except:
                pass
        self.root.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    app = ModernSamsungRemote(root)
    root.mainloop()