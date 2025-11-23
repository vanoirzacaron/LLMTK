"""
Shared Utilities
Common functions used across all tabs
"""

import tkinter as tk
from tkinter import ttk, scrolledtext
import subprocess
import threading
import os
import signal
import psutil
from datetime import datetime

class ProcessMonitor:
    """Monitor process resource usage"""
    def __init__(self, pid):
        self.pid = pid
        try:
            self.process = psutil.Process(pid)
        except psutil.NoSuchProcess:
            self.process = None
    
    def get_stats(self):
        """Get current process statistics"""
        if not self.process or not self.process.is_running():
            return None
        
        try:
            cpu = self.process.cpu_percent(interval=0.1)
            mem = self.process.memory_info()
            mem_mb = mem.rss / 1024 / 1024
            return {
                'cpu': cpu,
                'memory_mb': mem_mb,
                'status': self.process.status()
            }
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            return None

def create_log_widget(parent):
    """Create a log widget with consistent styling"""
    log = scrolledtext.ScrolledText(
        parent,
        wrap=tk.WORD,
        state=tk.DISABLED,
        bg='#1e1e1e',
        fg='#00ff00',
        font=('Courier', 9)
    )
    return log

def log_to_widget(widget, message):
    """Add message to specific log widget"""
    try:
        widget.configure(state=tk.NORMAL)
        timestamp = datetime.now().strftime("%H:%M:%S")
        widget.insert(tk.END, f"[{timestamp}] {message}\n")
        widget.see(tk.END)
        widget.configure(state=tk.DISABLED)
    except:
        pass  # Widget might be destroyed

def clear_log(widget):
    """Clear specific log widget"""
    widget.configure(state=tk.NORMAL)
    widget.delete(1.0, tk.END)
    widget.configure(state=tk.DISABLED)

def update_monitor_display(launcher, name, stats_labels):
    """Update process monitoring display"""
    while launcher.monitoring_active.get(name, False):
        try:
            if name in launcher.processes:
                process = launcher.processes[name]
                if process.poll() is None:  # Process running
                    pid = process.pid
                    if name not in launcher.monitors or launcher.monitors[name].pid != pid:
                        launcher.monitors[name] = ProcessMonitor(pid)
                    
                    stats = launcher.monitors[name].get_stats()
                    if stats:
                        stats_labels['status'].config(text=f"Status: Running (PID: {pid})")
                        stats_labels['cpu'].config(text=f"CPU: {stats['cpu']:.1f}%")
                        stats_labels['memory'].config(text=f"Memory: {stats['memory_mb']:.1f} MB")
                    else:
                        stats_labels['status'].config(text="Status: Stopped")
                        stats_labels['cpu'].config(text="CPU: N/A")
                        stats_labels['memory'].config(text="Memory: N/A")
                else:
                    stats_labels['status'].config(text="Status: Stopped")
                    stats_labels['cpu'].config(text="CPU: N/A")
                    stats_labels['memory'].config(text="Memory: N/A")
            else:
                stats_labels['status'].config(text="Status: Not Started")
                stats_labels['cpu'].config(text="CPU: N/A")
                stats_labels['memory'].config(text="Memory: N/A")
        except Exception as e:
            pass  # Suppress monitoring errors
        
        threading.Event().wait(1.0)  # Update every second

def create_monitor_frame(parent, name, launcher):
    """Create a monitoring frame for a service"""
    monitor_frame = ttk.LabelFrame(parent, text="Process Monitor", padding="10")
    
    stats_labels = {}
    
    stats_labels['status'] = ttk.Label(monitor_frame, text="Status: Not Started", font=('Arial', 10))
    stats_labels['status'].pack(anchor=tk.W, pady=2)
    
    stats_labels['cpu'] = ttk.Label(monitor_frame, text="CPU: N/A", font=('Arial', 10))
    stats_labels['cpu'].pack(anchor=tk.W, pady=2)
    
    stats_labels['memory'] = ttk.Label(monitor_frame, text="Memory: N/A", font=('Arial', 10))
    stats_labels['memory'].pack(anchor=tk.W, pady=2)
    
    # Start monitoring thread
    launcher.monitoring_active[name] = True
    monitor_thread = threading.Thread(
        target=update_monitor_display,
        args=(launcher, name, stats_labels),
        daemon=True
    )
    monitor_thread.start()
    launcher.monitor_threads[name] = monitor_thread
    
    return monitor_frame

def run_command(launcher, name, command, log_widget, start_btn, stop_btn, kill_btn, cwd=None):
    """Run command in separate isolated thread"""
    def run():
        process = None
        try:
            log_to_widget(log_widget, "=" * 60)
            log_to_widget(log_widget, f"STARTING {name}")
            log_to_widget(log_widget, "=" * 60)
            log_to_widget(log_widget, f"Working directory: {cwd or 'current'}")
            log_to_widget(log_widget, f"Command: {command}")
            log_to_widget(log_widget, "")
            
            # Use bash explicitly with process group for proper cleanup
            process = subprocess.Popen(
                ["/bin/bash", "-c", command],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                cwd=cwd,
                bufsize=1,
                env=os.environ.copy(),
                preexec_fn=os.setsid  # Create new process group
            )
            
            launcher.processes[name] = process
            
            # Read output line by line
            try:
                for line in process.stdout:
                    if line.strip():
                        log_to_widget(log_widget, line.rstrip())
            except Exception as e:
                log_to_widget(log_widget, f"Stream reading error: {e}")
            
            process.wait()
            
            log_to_widget(log_widget, "")
            log_to_widget(log_widget, "=" * 60)
            if process.returncode == 0:
                log_to_widget(log_widget, f"{name} STOPPED CLEANLY")
            elif process.returncode == -signal.SIGTERM:
                log_to_widget(log_widget, f"{name} TERMINATED")
            elif process.returncode == -signal.SIGKILL:
                log_to_widget(log_widget, f"{name} FORCE KILLED")
            else:
                log_to_widget(log_widget, f"{name} EXITED WITH CODE: {process.returncode}")
            log_to_widget(log_widget, "=" * 60)
            
        except Exception as e:
            log_to_widget(log_widget, f"EXCEPTION: {str(e)}")
            import traceback
            log_to_widget(log_widget, traceback.format_exc())
        
        finally:
            # Cleanup
            if name in launcher.processes:
                del launcher.processes[name]
            if name in launcher.monitors:
                del launcher.monitors[name]
            
            # Re-enable buttons safely
            try:
                start_btn.configure(state=tk.NORMAL)
                stop_btn.configure(state=tk.DISABLED)
                kill_btn.configure(state=tk.DISABLED)
            except:
                pass
    
    # Run in isolated daemon thread
    thread = threading.Thread(target=run, daemon=True)
    thread.start()