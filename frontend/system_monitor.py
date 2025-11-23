"""
System Monitor Widget (Improved UI)
Displays system stats with fixed-width cards, color coding, and progress bars.
Requires: pip install psutil GPUtil
"""

import tkinter as tk
from tkinter import ttk
import psutil
import time

# Try importing GPUtil for NVIDIA support
try:
    import GPUtil
except ImportError:
    GPUtil = None

class SystemMonitor(ttk.Frame):
    def __init__(self, parent, interval=1000):
        super().__init__(parent, padding="2")
        self.interval = interval
        self.last_time = time.time()
        self.last_net_io = psutil.net_io_counters()
        try:
            self.last_disk_io = psutil.disk_io_counters()
        except:
            self.last_disk_io = None

        # Configuration
        self.card_width = 180
        self.card_height = 85
        
        # Define styles for progress bars
        self.style = ttk.Style()
        self.style.theme_use('default') # 'default' or 'clam' usually allows color changes best
        self.style.configure("Green.Horizontal.TProgressbar", background="#4caf50")
        self.style.configure("Orange.Horizontal.TProgressbar", background="#ff9800")
        self.style.configure("Red.Horizontal.TProgressbar", background="#f44336")

        self.create_widgets()
        self.update_stats()

    def create_card(self, col_index, title):
        """Creates a fixed-size container for a stat category"""
        frame = ttk.LabelFrame(self, text=title, width=self.card_width, height=self.card_height)
        frame.grid(row=0, column=col_index, padx=5, pady=2)
        frame.grid_propagate(False) # Forces the frame to respect width/height
        
        # Configure internal grid to center content
        frame.columnconfigure(0, weight=1)
        return frame

    def create_widgets(self):
        # 1. CPU CARD
        cpu_frame = self.create_card(0, "CPU")
        self.lbl_cpu_val = tk.Label(cpu_frame, text="0%", font=("Arial", 14, "bold"), fg="#333")
        self.lbl_cpu_val.grid(row=0, column=0, sticky="w", padx=5)
        
        self.pb_cpu = ttk.Progressbar(cpu_frame, length=140, mode='determinate', style="Green.Horizontal.TProgressbar")
        self.pb_cpu.grid(row=1, column=0, padx=5, pady=2, sticky="ew")
        
        self.lbl_cpu_detail = tk.Label(cpu_frame, text="Temp: --°C", font=("Consolas", 8), fg="#666")
        self.lbl_cpu_detail.grid(row=2, column=0, sticky="w", padx=5)

        # 2. GPU CARD
        gpu_frame = self.create_card(1, "GPU")
        self.lbl_gpu_val = tk.Label(gpu_frame, text="0%", font=("Arial", 14, "bold"), fg="#333")
        self.lbl_gpu_val.grid(row=0, column=0, sticky="w", padx=5)
        
        self.pb_gpu = ttk.Progressbar(gpu_frame, length=140, mode='determinate', style="Green.Horizontal.TProgressbar")
        self.pb_gpu.grid(row=1, column=0, padx=5, pady=2, sticky="ew")
        
        self.lbl_gpu_detail = tk.Label(gpu_frame, text="VRAM: -- | --°C", font=("Consolas", 8), fg="#666")
        self.lbl_gpu_detail.grid(row=2, column=0, sticky="w", padx=5)

        # 3. RAM CARD
        ram_frame = self.create_card(2, "RAM")
        self.lbl_ram_val = tk.Label(ram_frame, text="0%", font=("Arial", 14, "bold"), fg="#333")
        self.lbl_ram_val.grid(row=0, column=0, sticky="w", padx=5)
        
        self.pb_ram = ttk.Progressbar(ram_frame, length=140, mode='determinate', style="Green.Horizontal.TProgressbar")
        self.pb_ram.grid(row=1, column=0, padx=5, pady=2, sticky="ew")
        
        self.lbl_ram_detail = tk.Label(ram_frame, text="Used: -- GB", font=("Consolas", 8), fg="#666")
        self.lbl_ram_detail.grid(row=2, column=0, sticky="w", padx=5)

        # 4. DISK I/O CARD
        disk_frame = self.create_card(3, "Disk I/O")
        # No progress bar for disk, just big numbers
        self.lbl_disk_r = tk.Label(disk_frame, text="R: 0 MB/s", font=("Consolas", 10, "bold"), fg="#2196f3")
        self.lbl_disk_r.grid(row=0, column=0, sticky="w", padx=5, pady=(5,0))
        
        self.lbl_disk_w = tk.Label(disk_frame, text="W: 0 MB/s", font=("Consolas", 10, "bold"), fg="#ff9800")
        self.lbl_disk_w.grid(row=1, column=0, sticky="w", padx=5)

        # 5. NETWORK CARD
        net_frame = self.create_card(4, "Network")
        self.lbl_net_down = tk.Label(net_frame, text="↓ 0 KB/s", font=("Consolas", 10, "bold"), fg="#4caf50")
        self.lbl_net_down.grid(row=0, column=0, sticky="w", padx=5, pady=(5,0))
        
        self.lbl_net_up = tk.Label(net_frame, text="↑ 0 KB/s", font=("Consolas", 10, "bold"), fg="#9c27b0")
        self.lbl_net_up.grid(row=1, column=0, sticky="w", padx=5)

    def get_color_style(self, percent):
        """Returns the appropriate progress bar style based on percentage"""
        if percent < 60: return "Green.Horizontal.TProgressbar"
        if percent < 85: return "Orange.Horizontal.TProgressbar"
        return "Red.Horizontal.TProgressbar"

    def get_text_color(self, percent):
        """Returns hex color for text"""
        if percent < 60: return "#2e7d32" # Dark Green
        if percent < 85: return "#ef6c00" # Dark Orange
        return "#c62828" # Dark Red

    def format_bytes(self, size):
        power = 2**10
        n = 0
        power_labels = {0 : '', 1: 'K', 2: 'M', 3: 'G', 4: 'T'}
        while size > power:
            size /= power
            n += 1
        return f"{size:.1f}{power_labels[n]}B"

    def get_cpu_temp(self):
        try:
            temps = psutil.sensors_temperatures()
            if temps:
                for name in ['coretemp', 'k10temp', 'cpu_thermal', 'asus']:
                    if name in temps:
                        return f"{temps[name][0].current:.0f}°C"
        except:
            pass
        return "N/A"

    def update_stats(self):
        if not self.winfo_exists(): return

        # --- CPU ---
        cpu_pct = psutil.cpu_percent(interval=None)
        self.lbl_cpu_val.config(text=f"{cpu_pct}%", fg=self.get_text_color(cpu_pct))
        self.pb_cpu['value'] = cpu_pct
        self.pb_cpu.config(style=self.get_color_style(cpu_pct))
        self.lbl_cpu_detail.config(text=f"Temp: {self.get_cpu_temp()}")

        # --- RAM ---
        ram = psutil.virtual_memory()
        self.lbl_ram_val.config(text=f"{ram.percent}%", fg=self.get_text_color(ram.percent))
        self.pb_ram['value'] = ram.percent
        self.pb_ram.config(style=self.get_color_style(ram.percent))
        self.lbl_ram_detail.config(text=f"Used: {self.format_bytes(ram.used)}")

        # --- GPU ---
        if GPUtil:
            try:
                gpus = GPUtil.getGPUs()
                if gpus:
                    gpu = gpus[0]
                    load = gpu.load * 100
                    self.lbl_gpu_val.config(text=f"{load:.0f}%", fg=self.get_text_color(load))
                    self.pb_gpu['value'] = load
                    self.pb_gpu.config(style=self.get_color_style(load))
                    self.lbl_gpu_detail.config(text=f"VRAM: {gpu.memoryUsed}MB | {gpu.temperature}°C")
            except:
                self.lbl_gpu_val.config(text="ERR")
        else:
            self.lbl_gpu_val.config(text="N/A")

        # --- DISK & NET ---
        curr_time = time.time()
        delta = curr_time - self.last_time
        if delta >= 0.5:
            # Network
            net = psutil.net_io_counters()
            down = (net.bytes_recv - self.last_net_io.bytes_recv) / delta
            up = (net.bytes_sent - self.last_net_io.bytes_sent) / delta
            self.lbl_net_down.config(text=f"↓ {self.format_bytes(down)}/s")
            self.lbl_net_up.config(text=f"↑ {self.format_bytes(up)}/s")
            self.last_net_io = net

            # Disk
            try:
                disk = psutil.disk_io_counters()
                if self.last_disk_io and disk:
                    r = (disk.read_bytes - self.last_disk_io.read_bytes) / delta
                    w = (disk.write_bytes - self.last_disk_io.write_bytes) / delta
                    self.lbl_disk_r.config(text=f"R: {self.format_bytes(r)}/s")
                    self.lbl_disk_w.config(text=f"W: {self.format_bytes(w)}/s")
                self.last_disk_io = disk
            except:
                pass
            self.last_time = curr_time

        self.after(self.interval, self.update_stats)