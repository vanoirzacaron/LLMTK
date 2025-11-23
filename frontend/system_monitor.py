"""
System Monitor Widget (Compact & Tall)
Features:
- Fixed-width cards (150px width, 140px height)
- Dedicated rows for GPU Temp and Disk Temp
- Progress bars for every metric
- Auto-detects background color to fix styling issues
"""

import tkinter as tk
from tkinter import ttk
import psutil
import time
import subprocess
import shutil

# Try importing GPUtil
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

        # --- Configuration ---
        self.card_width = 150   # 50px narrower than before
        self.card_height = 140  # Taller to fit 3 metrics
        
        self.MAX_TEMP = 99.0
        self.MAX_DISK_MB = 7000.0
        self.MAX_NET_MB = 2000.0

        # Style Definitions
        self.style = ttk.Style()
        self.style.theme_use('default')
        self.style.configure("Green.Horizontal.TProgressbar", background="#4caf50", troughcolor="#e0e0e0")
        self.style.configure("Orange.Horizontal.TProgressbar", background="#ff9800", troughcolor="#e0e0e0")
        self.style.configure("Red.Horizontal.TProgressbar", background="#f44336", troughcolor="#e0e0e0")
        self.style.configure("Blue.Horizontal.TProgressbar", background="#2196f3", troughcolor="#e0e0e0")
        self.style.configure("Purple.Horizontal.TProgressbar", background="#9c27b0", troughcolor="#e0e0e0")

        self.create_widgets()
        self.update_stats()

    def create_card(self, col_index, title):
        """Creates a fixed-size container"""
        frame = ttk.LabelFrame(self, text=title, width=self.card_width, height=self.card_height)
        frame.grid(row=0, column=col_index, padx=2, pady=2)
        frame.grid_propagate(False)
        frame.columnconfigure(0, weight=1)
        return frame

    def create_metric_row(self, parent, label_text, color_style="Green.Horizontal.TProgressbar", row_offset=0):
        """Helper to create a Label+Value row and a Bar row"""
        # Get theme background color safely
        bg_color = self.style.lookup('TFrame', 'background')
        if not bg_color: bg_color = "#f0f0f0"

        # Text Row (Use ttk.Frame for container)
        frame_text = ttk.Frame(parent)
        frame_text.grid(row=row_offset, column=0, sticky="ew", padx=4, pady=(2,0))
        
        # Labels (Compact font for narrower width)
        lbl_title = tk.Label(frame_text, text=label_text, font=("Consolas", 7, "bold"), 
                             fg="#555", bg=bg_color)
        lbl_title.pack(side=tk.LEFT)
        
        lbl_val = tk.Label(frame_text, text="--", font=("Consolas", 7, "bold"), 
                           fg="#333", bg=bg_color)
        lbl_val.pack(side=tk.RIGHT)

        # Bar Row
        bar = ttk.Progressbar(parent, length=100, mode='determinate', style=color_style)
        bar.grid(row=row_offset+1, column=0, sticky="ew", padx=4, pady=(0, 2))
        
        return lbl_val, bar

    def create_widgets(self):
        # 1. CPU
        cpu_frame = self.create_card(0, "CPU")
        self.lbl_cpu, self.bar_cpu = self.create_metric_row(cpu_frame, "Usage", "Green.Horizontal.TProgressbar", 0)
        self.lbl_cpu_temp, self.bar_cpu_temp = self.create_metric_row(cpu_frame, "Temp", "Orange.Horizontal.TProgressbar", 2)

        # 2. GPU (3 Rows)
        gpu_frame = self.create_card(1, "GPU")
        self.lbl_gpu, self.bar_gpu = self.create_metric_row(gpu_frame, "Core", "Green.Horizontal.TProgressbar", 0)
        self.lbl_gpu_mem, self.bar_gpu_mem = self.create_metric_row(gpu_frame, "VRAM", "Blue.Horizontal.TProgressbar", 2)
        self.lbl_gpu_temp, self.bar_gpu_temp = self.create_metric_row(gpu_frame, "Temp", "Orange.Horizontal.TProgressbar", 4)

        # 3. RAM (2 Rows - Spacer to align?)
        ram_frame = self.create_card(2, "RAM")
        self.lbl_ram, self.bar_ram = self.create_metric_row(ram_frame, "Usage", "Green.Horizontal.TProgressbar", 0)
        self.lbl_swap, self.bar_swap = self.create_metric_row(ram_frame, "Swap", "Orange.Horizontal.TProgressbar", 2)

        # 4. DISK (3 Rows)
        disk_frame = self.create_card(3, "Disk I/O")
        self.lbl_disk_r, self.bar_disk_r = self.create_metric_row(disk_frame, "Read", "Blue.Horizontal.TProgressbar", 0)
        self.lbl_disk_w, self.bar_disk_w = self.create_metric_row(disk_frame, "Write", "Orange.Horizontal.TProgressbar", 2)
        self.lbl_disk_t, self.bar_disk_t = self.create_metric_row(disk_frame, "Temp", "Red.Horizontal.TProgressbar", 4)

        # 5. NET (2 Rows)
        net_frame = self.create_card(4, "Network")
        self.lbl_net_d, self.bar_net_d = self.create_metric_row(net_frame, "Down", "Green.Horizontal.TProgressbar", 0)
        self.lbl_net_u, self.bar_net_u = self.create_metric_row(net_frame, "Up", "Purple.Horizontal.TProgressbar", 2)

    def get_bar_style(self, percent):
        if percent < 60: return "Green.Horizontal.TProgressbar"
        if percent < 85: return "Orange.Horizontal.TProgressbar"
        return "Red.Horizontal.TProgressbar"

    def format_speed(self, bytes_per_sec):
        mb = bytes_per_sec / (1024 * 1024)
        if mb >= 1.0:
            return f"{mb:.1f} MB/s"
        kb = bytes_per_sec / 1024
        return f"{kb:.0f} KB/s"

    def get_gpu_data(self):
        load, mem_used, mem_total, temp = 0, 0, 1, 0
        
        # Method 1: GPUtil
        if GPUtil:
            try:
                gpus = GPUtil.getGPUs()
                if gpus:
                    gpu = gpus[0]
                    return gpu.load * 100, gpu.memoryUsed, gpu.memoryTotal, gpu.temperature
            except:
                pass
        
        # Method 2: nvidia-smi
        if shutil.which("nvidia-smi"):
            try:
                cmd = ["nvidia-smi", "--query-gpu=utilization.gpu,memory.used,memory.total,temperature.gpu", "--format=csv,noheader,nounits"]
                output = subprocess.check_output(cmd).decode('utf-8').strip()
                parts = output.split(',')
                if len(parts) == 4:
                    load = float(parts[0])
                    mem_used = float(parts[1])
                    mem_total = float(parts[2])
                    temp = float(parts[3])
                    return load, mem_used, mem_total, temp
            except:
                pass
        return 0, 0, 1, 0

    def get_temp_by_names(self, sensor_names):
        """Helper to find temp from psutil sensors"""
        try:
            temps = psutil.sensors_temperatures()
            if not temps: return 0
            for name in sensor_names:
                if name in temps:
                    return temps[name][0].current
        except:
            pass
        return 0

    def update_stats(self):
        if not self.winfo_exists(): return

        # --- CPU ---
        cpu_usage = psutil.cpu_percent(interval=None)
        # Scan common CPU sensor names
        cpu_temp = self.get_temp_by_names(['coretemp', 'k10temp', 'cpu_thermal', 'asus', 'fam15h_power'])
        
        self.lbl_cpu.config(text=f"{cpu_usage}%")
        self.bar_cpu['value'] = cpu_usage
        self.bar_cpu.config(style=self.get_bar_style(cpu_usage))
        
        self.lbl_cpu_temp.config(text=f"{cpu_temp:.0f}°C")
        self.bar_cpu_temp['value'] = (cpu_temp / self.MAX_TEMP) * 100

        # --- RAM ---
        ram = psutil.virtual_memory()
        swap = psutil.swap_memory()
        
        self.lbl_ram.config(text=f"{ram.percent}%")
        self.bar_ram['value'] = ram.percent
        self.bar_ram.config(style=self.get_bar_style(ram.percent))
        
        self.lbl_swap.config(text=f"{swap.percent}%")
        self.bar_swap['value'] = swap.percent

        # --- GPU ---
        g_load, g_mem, g_total, g_temp = self.get_gpu_data()
        mem_pct = (g_mem / g_total) * 100 if g_total > 0 else 0
        
        self.lbl_gpu.config(text=f"{g_load:.0f}%")
        self.bar_gpu['value'] = g_load
        self.bar_gpu.config(style=self.get_bar_style(g_load))
        
        self.lbl_gpu_mem.config(text=f"{g_mem:.0f} MB")
        self.bar_gpu_mem['value'] = mem_pct
        
        # GPU Temp Row
        self.lbl_gpu_temp.config(text=f"{g_temp:.0f}°C")
        self.bar_gpu_temp['value'] = (g_temp / self.MAX_TEMP) * 100
        self.bar_gpu_temp.config(style=self.get_bar_style(g_temp/self.MAX_TEMP * 100))

        # --- Disk ---
        curr_time = time.time()
        delta = curr_time - self.last_time
        
        # Disk Temp (Try nvme, disk, etc)
        disk_temp = self.get_temp_by_names(['nvme', 'drivetemp', 'disk'])
        self.lbl_disk_t.config(text=f"{disk_temp:.0f}°C" if disk_temp > 0 else "N/A")
        self.bar_disk_t['value'] = (disk_temp / self.MAX_TEMP) * 100
        
        if delta >= 0.5:
            # Net
            net = psutil.net_io_counters()
            down_b = (net.bytes_recv - self.last_net_io.bytes_recv) / delta
            up_b = (net.bytes_sent - self.last_net_io.bytes_sent) / delta
            down_mb = down_b / (1024*1024)
            up_mb = up_b / (1024*1024)
            
            self.lbl_net_d.config(text=self.format_speed(down_b))
            self.bar_net_d['value'] = min((down_mb / self.MAX_NET_MB) * 100, 100)
            
            self.lbl_net_u.config(text=self.format_speed(up_b))
            self.bar_net_u['value'] = min((up_mb / self.MAX_NET_MB) * 100, 100)
            
            self.last_net_io = net

            # Disk IO
            try:
                disk = psutil.disk_io_counters()
                if self.last_disk_io and disk:
                    r_b = (disk.read_bytes - self.last_disk_io.read_bytes) / delta
                    w_b = (disk.write_bytes - self.last_disk_io.write_bytes) / delta
                    r_mb = r_b / (1024*1024)
                    w_mb = w_b / (1024*1024)
                    
                    self.lbl_disk_r.config(text=self.format_speed(r_b))
                    self.bar_disk_r['value'] = min((r_mb / self.MAX_DISK_MB) * 100, 100)
                    
                    self.lbl_disk_w.config(text=self.format_speed(w_b))
                    self.bar_disk_w['value'] = min((w_mb / self.MAX_DISK_MB) * 100, 100)
                    
                self.last_disk_io = disk
            except:
                pass
            
            self.last_time = curr_time

        self.after(self.interval, self.update_stats)