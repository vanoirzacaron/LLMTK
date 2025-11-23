"""
Shared Utilities
Common functions used across all tabs
Thread-Safe Version to prevent Segmentation Faults
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
            cpu = self.process.cpu_percent(interval=None) # Interval None prevents blocking
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
    """
    Thread-safe logging function.
    Can be safely called from background threads.
    """
    def _update():
        try:
            if not widget.winfo_exists(): return
            widget.configure(state=tk.NORMAL)
            timestamp = datetime.now().strftime("%H:%M:%S")
            widget.insert(tk.END, f"[{timestamp}] {message}\n")
            widget.see(tk.END)
            widget.configure(state=tk.DISABLED)
        except:
            pass

    # If in main thread, run immediately. If in background, schedule it.
    if threading.current_thread() is threading.main_thread():
        _update()
    else:
        widget.after(0, _update)

def clear_log(widget):
    """Thread-safe clear log"""
    def _clear():
        try:
            if not widget.winfo_exists(): return
            widget.configure(state=tk.NORMAL)
            widget.delete(1.0, tk.END)
            widget.configure(state=tk.DISABLED)
        except:
            pass

    if threading.current_thread() is threading.main_thread():
        _clear()
    else:
        widget.after(0, _clear)

def update_monitor_display(launcher, name, stats_labels):
    """
    Update process monitoring display.
    Calculates in thread, updates GUI via .after()
    """
    # Initialize CPU percent for the first interval
    if name in launcher.processes:
        try:
            p = psutil.Process(launcher.processes[name].pid)
            p.cpu_percent(interval=None)
        except: pass

    while launcher.monitoring_active.get(name, False):
        s_text, c_text, m_text = "Status: Not Started", "CPU: N/A", "Memory: N/A"
        
        try:
            if name in launcher.processes:
                process = launcher.processes[name]
                if process.poll() is None:  # Process running
                    pid = process.pid
                    if name not in launcher.monitors or launcher.monitors[name].pid != pid:
                        launcher.monitors[name] = ProcessMonitor(pid)
                    
                    stats = launcher.monitors[name].get_stats()
                    if stats:
                        s_text = f"Status: Running (PID: {pid})"
                        c_text = f"CPU: {stats['cpu']:.1f}%"
                        m_text = f"Memory: {stats['memory_mb']:.1f} MB"
                    else:
                        s_text = "Status: Stopped"
                else:
                    s_text = "Status: Stopped"
        except Exception:
            pass 
        
        # Define the GUI update function
        def _update_gui(s, c, m):
            try:
                if not stats_labels['status'].winfo_exists(): return
                stats_labels['status'].config(text=s)
                stats_labels['cpu'].config(text=c)
                stats_labels['memory'].config(text=m)
            except: pass

        # Schedule the GUI update on the main thread
        try:
            # We use one of the labels to trigger .after()
            stats_labels['status'].after(0, _update_gui, s_text, c_text, m_text)
        except:
            break

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
                    if line:
                        # log_to_widget now handles thread safety internally
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
            def reset_buttons():
                try:
                    start_btn.configure(state=tk.NORMAL)
                    stop_btn.configure(state=tk.DISABLED)
                    kill_btn.configure(state=tk.DISABLED)
                except:
                    pass
            
            # Schedule button reset on main thread
            if start_btn.winfo_exists():
                start_btn.after(0, reset_buttons)
    
    # Run in isolated daemon thread
    thread = threading.Thread(target=run, daemon=True)
    thread.start()