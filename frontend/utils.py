'''
Shared Utilities
Common functions used across all tabs
'''

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
            cpu = self.process.cpu_percent(interval=None)
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
    log.tag_config("error", foreground="red")
    return log

def log_to_widget(widget, message, is_realtime=False):
    '''
    Thread-safe logging function with error highlighting.
    '''
    def _update():
        try:
            if not widget.winfo_exists(): return
            widget.configure(state=tk.NORMAL)
            
            # Determine the full message and if it contains an error
            full_message = f"[{datetime.now().strftime('%H:%M:%S')}] {message}\n" if not is_realtime else message
            is_error = 'error' in message.lower()
            
            # Insert the message
            widget.insert(tk.END, full_message)
            
            # If it's an error, apply the tag
            if is_error:
                start_index = widget.index(f"end - {len(full_message) + 1}c")
                end_index = widget.index("end - 1c")
                # Search for the word 'error' and tag it
                start = start_index
                while True:
                    pos = widget.search('error', start, stopindex=end_index, nocase=True)
                    if not pos:
                        break
                    widget.tag_add("error", pos, f"{pos} + 5c")
                    start = f"{pos} + 1c"
            
            widget.see(tk.END)
            widget.configure(state=tk.DISABLED)
        except tk.TclError:
            pass # Widget might be destroyed

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
    '''
    Update process monitoring display.
    '''
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
                if process.poll() is None:
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
        
        def _update_gui(s, c, m):
            try:
                if not stats_labels['status'].winfo_exists(): return
                stats_labels['status'].config(text=s)
                stats_labels['cpu'].config(text=c)
                stats_labels['memory'].config(text=m)
            except: pass

        try:
            stats_labels['status'].after(0, _update_gui, s_text, c_text, m_text)
        except:
            break

        threading.Event().wait(1.0)

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
    
    launcher.monitoring_active[name] = True
    monitor_thread = threading.Thread(
        target=update_monitor_display,
        args=(launcher, name, stats_labels),
        daemon=True
    )
    monitor_thread.start()
    launcher.monitor_threads[name] = monitor_thread
    
    return monitor_frame

def run_command(launcher, name, command, log_fn, widget, start_btn=None, stop_btn=None, kill_btn=None, cwd=None, on_success=None, on_error=None, capture_output=False):
    """Run command in a separate thread with optional real-time output or output capture."""
    def run():
        process = None
        try:
            log_fn(f'STARTING {name}: {command}')
            
            process = subprocess.Popen(
                ["/bin/bash", "-c", command],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE, 
                text=True,
                bufsize=1,
                cwd=cwd,
                preexec_fn=os.setsid
            )
            
            launcher.processes[name] = process
            output = []

            # Handle stdout
            if process.stdout:
                if capture_output:
                    output.extend(process.stdout.readlines())
                else:
                    for line in iter(process.stdout.readline, ''):
                        log_fn(line, is_realtime=True)
                process.stdout.close()
            
            # Handle stderr
            stderr_output = []
            if process.stderr:
                stderr_output.extend(process.stderr.readlines())
                process.stderr.close()

            process.wait()
            full_output = "".join(output)
            full_error = "".join(stderr_output)

            if process.returncode == 0:
                log_fn(f'{name} completed successfully.')
                if on_success:
                    widget.after(0, on_success, full_output)
            else:
                error_message = f"{name} exited with code {process.returncode}: {full_error.strip()}"
                log_fn(f"ERROR: {error_message}")
                if on_error:
                    widget.after(0, on_error, error_message)

        except Exception as e:
            log_fn(f"EXCEPTION in {name}: {e}")
            if on_error:
                widget.after(0, on_error, str(e))
        
        finally:
            if name in launcher.processes:
                del launcher.processes[name]
            
            if start_btn:
                def reset_buttons():
                    try:
                        if start_btn.winfo_exists():
                            start_btn.configure(state=tk.NORMAL)
                        if stop_btn and stop_btn.winfo_exists():
                            stop_btn.configure(state=tk.DISABLED)
                        if kill_btn and kill_btn.winfo_exists():
                            kill_btn.configure(state=tk.DISABLED)
                    except tk.TclError:
                        pass
                
                if widget and widget.winfo_exists():
                    widget.after(0, reset_buttons)

    thread = threading.Thread(target=run, daemon=True)
    thread.start()