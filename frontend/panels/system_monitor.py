"""
System Monitor Panel

This panel provides a real-time, at-a-glance overview of key system metrics.
It is designed to be compact, resilient, and informative, using a series of 
fixed-width cards to display information for the CPU, GPU, RAM, Disk I/O, and Network.

Key Features:
- Resilient data fetching: Gracefully handles missing sensors or libraries (e.g., GPUtil).
- Clean shutdown: Prevents errors when the application closes.
- Centralized logging: Integrates with the global logger for better diagnostics.
- Dynamic progress bar coloring: Colors change from green to orange to red based on load.
- Automatic theme detection: Adapts label backgrounds to the current theme.
"""

import tkinter as tk
from tkinter import ttk
import psutil
import time
import subprocess
import shutil

# --- Optional Dependencies ---
try:
    # GPUtil is a common library for NVIDIA GPU statistics.
    import GPUtil
except ImportError:
    GPUtil = None # If not installed, we will fall back to using nvidia-smi.

# --- Constants ---
PANEL_TITLE = "System Monitor"
UPDATE_INTERVAL_MS = 1000  # Refresh every 1 second.

# --- Logging ---
def log(launcher, message, level="info"):
    """Centralized logging helper for the System Monitor panel."""
    log_message = f"[{PANEL_TITLE}] {message}"
    print(log_message) # For direct console feedback.
    if launcher and hasattr(launcher, 'log_to_global'):
        launcher.log_to_global(PANEL_TITLE, message)

# --- Main Panel Class ---

class SystemMonitor(ttk.Frame):
    """The main UI and logic for the system monitor panel."""
    def __init__(self, parent, launcher=None):
        super().__init__(parent, padding="2")
        self.launcher = launcher
        self._is_running = True # Flag to control the main update loop.

        # --- State Variables for Rate Calculation ---
        self.last_time = time.time()
        self.last_net_io = psutil.net_io_counters()
        try:
            # disk_io_counters can fail on some systems (e.g., certain containers or permissions)
            self.last_disk_io = psutil.disk_io_counters()
        except (PermissionError, RuntimeError) as e:
            self.last_disk_io = None
            log(self.launcher, f"Could not initialize disk I/O stats: {e}", "error")

        # --- Configuration for UI and Thresholds ---
        self.card_width = 150
        self.card_height = 140
        self.MAX_TEMP = 99.0 # For progress bar scaling.
        self.MAX_DISK_MB_S = 7000.0 # Heuristic for disk I/O bar scaling.
        self.MAX_NET_MB_S = 2000.0 # Heuristic for network bar scaling.

        self._configure_styles()
        self.create_widgets()
        self.update_stats() # Start the update loop.

    def _configure_styles(self):
        """Define custom styles for progress bars."""
        style = ttk.Style()
        style.theme_use('default')
        colors = {
            "Green": "#4caf50",
            "Orange": "#ff9800",
            "Red": "#f44336",
            "Blue": "#2196f3",
            "Purple": "#9c27b0"
        }
        for name, color in colors.items():
            style.configure(f"{name}.Horizontal.TProgressbar", background=color, troughcolor="#e0e0e0")

    def create_card(self, col_index, title):
        """Creates a standardized, fixed-size frame for a category (e.g., CPU)."""
        frame = ttk.LabelFrame(self, text=title, width=self.card_width, height=self.card_height)
        frame.grid(row=0, column=col_index, padx=2, pady=2, sticky="ns")
        frame.grid_propagate(False) # Prevent the frame from resizing to fit content.
        frame.columnconfigure(0, weight=1)
        return frame

    def create_metric_row(self, parent, label_text, color_style, row_offset):
        """Creates a standard row within a card, containing a label, a value, and a progress bar."""
        bg_color = self.winfo_toplevel().cget('bg') # Auto-detect theme background.

        frame_text = ttk.Frame(parent)
        frame_text.grid(row=row_offset, column=0, sticky="ew", padx=4, pady=(2,0))
        
        lbl_title = tk.Label(frame_text, text=label_text, font=("Consolas", 7, "bold"), fg="#555", bg=bg_color)
        lbl_title.pack(side=tk.LEFT)
        
        lbl_val = tk.Label(frame_text, text="--", font=("Consolas", 7, "bold"), fg="#333", bg=bg_color)
        lbl_val.pack(side=tk.RIGHT)

        bar = ttk.Progressbar(parent, length=100, mode='determinate', style=color_style)
        bar.grid(row=row_offset + 1, column=0, sticky="ew", padx=4, pady=(0, 2))
        
        return lbl_val, bar

    def create_widgets(self):
        """Create all the cards and their metric rows."""
        # CPU Card
        cpu_frame = self.create_card(0, "CPU")
        self.lbl_cpu, self.bar_cpu = self.create_metric_row(cpu_frame, "Usage", "Green.Horizontal.TProgressbar", 0)
        self.lbl_cpu_temp, self.bar_cpu_temp = self.create_metric_row(cpu_frame, "Temp", "Orange.Horizontal.TProgressbar", 2)

        # GPU Card
        gpu_frame = self.create_card(1, "GPU")
        self.lbl_gpu, self.bar_gpu = self.create_metric_row(gpu_frame, "Core", "Green.Horizontal.TProgressbar", 0)
        self.lbl_gpu_mem, self.bar_gpu_mem = self.create_metric_row(gpu_frame, "VRAM", "Blue.Horizontal.TProgressbar", 2)
        self.lbl_gpu_temp, self.bar_gpu_temp = self.create_metric_row(gpu_frame, "Temp", "Orange.Horizontal.TProgressbar", 4)

        # RAM Card
        ram_frame = self.create_card(2, "RAM")
        self.lbl_ram, self.bar_ram = self.create_metric_row(ram_frame, "Usage", "Green.Horizontal.TProgressbar", 0)
        self.lbl_swap, self.bar_swap = self.create_metric_row(ram_frame, "Swap", "Orange.Horizontal.TProgressbar", 2)

        # Disk I/O Card
        disk_frame = self.create_card(3, "Disk I/O")
        self.lbl_disk_r, self.bar_disk_r = self.create_metric_row(disk_frame, "Read", "Blue.Horizontal.TProgressbar", 0)
        self.lbl_disk_w, self.bar_disk_w = self.create_metric_row(disk_frame, "Write", "Orange.Horizontal.TProgressbar", 2)
        self.lbl_disk_t, self.bar_disk_t = self.create_metric_row(disk_frame, "Temp", "Red.Horizontal.TProgressbar", 4)

        # Network Card
        net_frame = self.create_card(4, "Network")
        self.lbl_net_d, self.bar_net_d = self.create_metric_row(net_frame, "Down", "Green.Horizontal.TProgressbar", 0)
        self.lbl_net_u, self.bar_net_u = self.create_metric_row(net_frame, "Up", "Purple.Horizontal.TProgressbar", 2)

    def get_bar_style(self, percent):
        """Determines progress bar color based on percentage."""
        if percent < 60: return "Green.Horizontal.TProgressbar"
        if percent < 85: return "Orange.Horizontal.TProgressbar"
        return "Red.Horizontal.TProgressbar"

    def format_speed(self, bytes_per_sec):
        """Formats a byte rate into a human-readable string (KB/s or MB/s)."""
        if bytes_per_sec is None: return "N/A"
        mb = bytes_per_sec / (1024 * 1024)
        return f"{mb:.1f} MB/s" if mb >= 1.0 else f"{bytes_per_sec / 1024:.0f} KB/s"

    def get_gpu_data(self):
        """Fetches GPU data using GPUtil or nvidia-smi as a fallback."""
        # Method 1: GPUtil (preferred)
        if GPUtil:
            try:
                gpu = GPUtil.getGPUs()[0]
                return gpu.load * 100, gpu.memoryUsed, gpu.memoryTotal, gpu.temperature
            except Exception as e:
                # Log the first time, then silently fail to avoid log spam.
                if not hasattr(self, '_gputil_failed'):
                    log(self.launcher, f"GPUtil failed: {e}. Falling back to nvidia-smi.", "warn")
                    self._gputil_failed = True

        # Method 2: nvidia-smi (fallback)
        if shutil.which("nvidia-smi"):
            try:
                cmd = ["nvidia-smi", "--query-gpu=utilization.gpu,memory.used,memory.total,temperature.gpu", "--format=csv,noheader,nounits"]
                output = subprocess.check_output(cmd, stderr=subprocess.DEVNULL).decode('utf-8').strip()
                parts = [float(p) for p in output.split(',')]
                if len(parts) == 4:
                    return parts[0], parts[1], parts[2], parts[3]
            except (subprocess.CalledProcessError, FileNotFoundError, ValueError) as e:
                if not hasattr(self, '_smi_failed'):
                    log(self.launcher, f"nvidia-smi failed: {e}. GPU monitoring disabled.", "error")
                    self._smi_failed = True # Prevent repeated log spam.
        
        return 0, 0, 1, 0 # Return safe default values.

    def get_sensor_temp(self, sensor_names):
        """Safely retrieves a temperature from psutil.sensors_temperatures()."""
        try:
            temps = psutil.sensors_temperatures()
            if not temps: return 0.0
            for name in sensor_names:
                if name in temps:
                    # Return the first valid sensor reading found.
                    return temps[name][0].current
        except (KeyError, IndexError) as e:
            log(self.launcher, f"Could not read sensor from {sensor_names}: {e}", "warn")
        return 0.0
    
    def update_stats(self):
        """The main update loop. Fetches all data and updates the UI widgets."""
        if not self._is_running or not self.winfo_exists():
            return
        try:
            # --- Update UI (wrapped in a single try/except for robustness) ---
            self._update_cpu_stats()
            self._update_ram_stats()
            self._update_gpu_stats()
            self._update_io_stats()
        except Exception as e:
            log(self.launcher, f"Unhandled error in update_stats: {e}", "error")
        finally:
            # Schedule the next run, ensuring the loop continues even if one cycle fails.
            self.after(UPDATE_INTERVAL_MS, self.update_stats)

    def _update_cpu_stats(self):
        cpu_usage = psutil.cpu_percent(interval=None)
        cpu_temp = self.get_sensor_temp(['coretemp', 'k10temp', 'cpu_thermal'])
        self.lbl_cpu.config(text=f"{cpu_usage:.1f}%")
        self.bar_cpu['value'] = cpu_usage
        self.bar_cpu.config(style=self.get_bar_style(cpu_usage))
        self.lbl_cpu_temp.config(text=f"{cpu_temp:.0f}°C")
        self.bar_cpu_temp['value'] = (cpu_temp / self.MAX_TEMP) * 100

    def _update_ram_stats(self):
        ram = psutil.virtual_memory()
        swap = psutil.swap_memory()
        self.lbl_ram.config(text=f"{ram.percent:.1f}%")
        self.bar_ram['value'] = ram.percent
        self.bar_ram.config(style=self.get_bar_style(ram.percent))
        self.lbl_swap.config(text=f"{swap.percent:.1f}%")
        self.bar_swap['value'] = swap.percent
    
    def _update_gpu_stats(self):
        g_load, g_mem, g_total, g_temp = self.get_gpu_data()
        mem_pct = (g_mem / g_total) * 100 if g_total > 0 else 0
        self.lbl_gpu.config(text=f"{g_load:.0f}%")
        self.bar_gpu['value'] = g_load
        self.bar_gpu.config(style=self.get_bar_style(g_load))
        self.lbl_gpu_mem.config(text=f"{g_mem:.0f} MB")
        self.bar_gpu_mem['value'] = mem_pct
        self.lbl_gpu_temp.config(text=f"{g_temp:.0f}°C")
        self.bar_gpu_temp['value'] = (g_temp / self.MAX_TEMP) * 100

    def _update_io_stats(self):
        curr_time = time.time()
        delta = curr_time - self.last_time
        if delta < 0.5: return # Update I/O rates less frequently.

        # Network I/O
        net = psutil.net_io_counters()
        down_rate = (net.bytes_recv - self.last_net_io.bytes_recv) / delta
        up_rate = (net.bytes_sent - self.last_net_io.bytes_sent) / delta
        self.lbl_net_d.config(text=self.format_speed(down_rate))
        self.bar_net_d['value'] = min((down_rate / (1024*1024) / self.MAX_NET_MB_S) * 100, 100)
        self.lbl_net_u.config(text=self.format_speed(up_rate))
        self.bar_net_u['value'] = min((up_rate / (1024*1024) / self.MAX_NET_MB_S) * 100, 100)
        self.last_net_io = net

        # Disk I/O & Temp
        disk_temp = self.get_sensor_temp(['nvme', 'drivetemp'])
        self.lbl_disk_t.config(text=f"{disk_temp:.0f}°C" if disk_temp > 0 else "N/A")
        self.bar_disk_t['value'] = (disk_temp / self.MAX_TEMP) * 100

        if self.last_disk_io:
            try:
                disk = psutil.disk_io_counters()
                read_rate = (disk.read_bytes - self.last_disk_io.read_bytes) / delta
                write_rate = (disk.write_bytes - self.last_disk_io.write_bytes) / delta
                self.lbl_disk_r.config(text=self.format_speed(read_rate))
                self.bar_disk_r['value'] = min((read_rate / (1024*1024) / self.MAX_DISK_MB_S) * 100, 100)
                self.lbl_disk_w.config(text=self.format_speed(write_rate))
                self.bar_disk_w['value'] = min((write_rate / (1024*1024) / self.MAX_DISK_MB_S) * 100, 100)
                self.last_disk_io = disk
            except (PermissionError, RuntimeError) as e:
                # Disable disk I/O monitoring if it fails.
                self.last_disk_io = None 
                log(self.launcher, f"Disabling disk I/O monitoring: {e}", "error")

        self.last_time = curr_time

    def stop(self):
        """Cleanly stops the panel's update loop."""
        log(self.launcher, "Stopping system monitor update loop.")
        self._is_running = False

# --- Factory Function ---
def create_panel(parent, launcher):
    """Creates the SystemMonitor panel."""
    panel = SystemMonitor(parent, launcher=launcher)
    return panel
