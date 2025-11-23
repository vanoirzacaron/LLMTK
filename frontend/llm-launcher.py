#!/usr/bin/env python3
"""
LLM Services Launcher - Enhanced with Process Monitoring
A robust GUI to start, monitor, and manage OpenHands and vLLM services
"""

import tkinter as tk
from tkinter import ttk, scrolledtext
import subprocess
import threading
import os
import signal
import psutil
from pathlib import Path
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

class LLMLauncher:
    def __init__(self, root):
        self.root = root
        self.root.title("LLM Services Launcher")
        self.root.geometry("900x700")
        self.root.resizable(True, True)
        
        # Store process references and monitors
        self.processes = {}
        self.monitors = {}
        self.monitor_threads = {}
        self.monitoring_active = {}
        
        # Main frame
        main_frame = ttk.Frame(root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Configure grid weights
        root.columnconfigure(0, weight=1)
        root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(1, weight=1)
        
        # Title
        title = ttk.Label(main_frame, text="🚀 LLM Services Launcher", font=('Arial', 16, 'bold'))
        title.grid(row=0, column=0, pady=(0, 10))
        
        # Create notebook (tabbed interface)
        self.notebook = ttk.Notebook(main_frame)
        self.notebook.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Create tabs
        self.create_vllm_tab()
        self.create_openhands_tab()
        self.create_testing_tab()
        
        # Handle window close
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        
    def on_closing(self):
        """Clean shutdown of all processes"""
        # Stop monitoring
        for name in list(self.monitoring_active.keys()):
            self.monitoring_active[name] = False
        
        # Terminate all processes
        for name, process in list(self.processes.items()):
            try:
                if process.poll() is None:  # Process still running
                    process.terminate()
                    process.wait(timeout=5)
            except:
                pass
        
        self.root.destroy()
    
    def create_log_widget(self, parent):
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
    
    def log_to_widget(self, widget, message):
        """Add message to specific log widget"""
        try:
            widget.configure(state=tk.NORMAL)
            timestamp = datetime.now().strftime("%H:%M:%S")
            widget.insert(tk.END, f"[{timestamp}] {message}\n")
            widget.see(tk.END)
            widget.configure(state=tk.DISABLED)
        except:
            pass  # Widget might be destroyed
    
    def clear_log(self, widget):
        """Clear specific log widget"""
        widget.configure(state=tk.NORMAL)
        widget.delete(1.0, tk.END)
        widget.configure(state=tk.DISABLED)
    
    def update_monitor_display(self, name, stats_labels):
        """Update process monitoring display"""
        while self.monitoring_active.get(name, False):
            try:
                if name in self.processes:
                    process = self.processes[name]
                    if process.poll() is None:  # Process running
                        pid = process.pid
                        if name not in self.monitors or self.monitors[name].pid != pid:
                            self.monitors[name] = ProcessMonitor(pid)
                        
                        stats = self.monitors[name].get_stats()
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
    
    def create_monitor_frame(self, parent, name):
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
        self.monitoring_active[name] = True
        monitor_thread = threading.Thread(
            target=self.update_monitor_display,
            args=(name, stats_labels),
            daemon=True
        )
        monitor_thread.start()
        self.monitor_threads[name] = monitor_thread
        
        return monitor_frame
    
    def create_vllm_tab(self):
        """Create vLLM tab"""
        vllm_tab = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(vllm_tab, text="vLLM Server")
        
        vllm_tab.columnconfigure(0, weight=1)
        vllm_tab.columnconfigure(1, weight=0)
        vllm_tab.rowconfigure(2, weight=1)
        
        # Left side - Info and logs
        left_frame = ttk.Frame(vllm_tab)
        left_frame.grid(row=0, column=0, rowspan=3, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(0, 10))
        left_frame.columnconfigure(0, weight=1)
        left_frame.rowconfigure(2, weight=1)
        
        # Info section
        info_frame = ttk.LabelFrame(left_frame, text="Server Information", padding="10")
        info_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        
        ttk.Label(info_frame, text="Model: DeepSeek-R1-Distill-Qwen-7B-AWQ").pack(anchor=tk.W)
        ttk.Label(info_frame, text="Host: 0.0.0.0:8000").pack(anchor=tk.W)
        ttk.Label(info_frame, text="API Key: sk-vllm-local-abc123xyz789-qwen-coder").pack(anchor=tk.W)
        
        # Control buttons
        button_frame = ttk.Frame(left_frame)
        button_frame.grid(row=1, column=0, pady=(0, 10))
        
        self.vllm_start_btn = ttk.Button(
            button_frame,
            text="▶ Start Server",
            command=self.start_vllm,
            width=15
        )
        self.vllm_start_btn.pack(side=tk.LEFT, padx=5)
        
        self.vllm_stop_btn = ttk.Button(
            button_frame,
            text="⏹ Stop Server",
            command=self.stop_vllm,
            state=tk.DISABLED,
            width=15
        )
        self.vllm_stop_btn.pack(side=tk.LEFT, padx=5)
        
        self.vllm_kill_btn = ttk.Button(
            button_frame,
            text="⚠️ Force Kill",
            command=self.kill_vllm,
            state=tk.DISABLED,
            width=15
        )
        self.vllm_kill_btn.pack(side=tk.LEFT, padx=5)
        
        ttk.Button(
            button_frame,
            text="🗑️ Clear Log",
            command=lambda: self.clear_log(self.vllm_log),
            width=12
        ).pack(side=tk.LEFT, padx=5)
        
        # Log section
        log_frame = ttk.LabelFrame(left_frame, text="Server Log", padding="5")
        log_frame.grid(row=2, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)
        
        self.vllm_log = self.create_log_widget(log_frame)
        self.vllm_log.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Right side - Monitor
        self.vllm_monitor = self.create_monitor_frame(vllm_tab, "vLLM")
        self.vllm_monitor.grid(row=0, column=1, sticky=(tk.N, tk.E, tk.W))
        
        self.log_to_widget(self.vllm_log, "vLLM Server ready to start")
    
    def create_openhands_tab(self):
        """Create OpenHands tab"""
        oh_tab = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(oh_tab, text="OpenHands")
        
        oh_tab.columnconfigure(0, weight=1)
        oh_tab.columnconfigure(1, weight=0)
        oh_tab.rowconfigure(2, weight=1)
        
        # Left side - Info and logs
        left_frame = ttk.Frame(oh_tab)
        left_frame.grid(row=0, column=0, rowspan=3, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(0, 10))
        left_frame.columnconfigure(0, weight=1)
        left_frame.rowconfigure(2, weight=1)
        
        # Info section
        info_frame = ttk.LabelFrame(left_frame, text="Agent Information", padding="10")
        info_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        
        ttk.Label(info_frame, text="Framework: OpenHands Agent").pack(anchor=tk.W)
        ttk.Label(info_frame, text="Python Version: 3.12").pack(anchor=tk.W)
        ttk.Label(info_frame, text="Command: uvx --python 3.12 openhands serve").pack(anchor=tk.W)
        
        # Control buttons
        button_frame = ttk.Frame(left_frame)
        button_frame.grid(row=1, column=0, pady=(0, 10))
        
        self.oh_start_btn = ttk.Button(
            button_frame,
            text="▶ Start Agent",
            command=self.start_openhands,
            width=15
        )
        self.oh_start_btn.pack(side=tk.LEFT, padx=5)
        
        self.oh_stop_btn = ttk.Button(
            button_frame,
            text="⏹ Stop Agent",
            command=self.stop_openhands,
            state=tk.DISABLED,
            width=15
        )
        self.oh_stop_btn.pack(side=tk.LEFT, padx=5)
        
        self.oh_kill_btn = ttk.Button(
            button_frame,
            text="⚠️ Force Kill",
            command=self.kill_openhands,
            state=tk.DISABLED,
            width=15
        )
        self.oh_kill_btn.pack(side=tk.LEFT, padx=5)
        
        ttk.Button(
            button_frame,
            text="🗑️ Clear Log",
            command=lambda: self.clear_log(self.oh_log),
            width=12
        ).pack(side=tk.LEFT, padx=5)
        
        # Log section
        log_frame = ttk.LabelFrame(left_frame, text="Agent Log", padding="5")
        log_frame.grid(row=2, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)
        
        self.oh_log = self.create_log_widget(log_frame)
        self.oh_log.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Right side - Monitor
        self.oh_monitor = self.create_monitor_frame(oh_tab, "OpenHands")
        self.oh_monitor.grid(row=0, column=1, sticky=(tk.N, tk.E, tk.W))
        
        self.log_to_widget(self.oh_log, "OpenHands ready to start")
    
    def create_testing_tab(self):
        """Create Testing tab"""
        test_tab = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(test_tab, text="Testing")
        
        test_tab.columnconfigure(0, weight=1)
        test_tab.rowconfigure(2, weight=1)
        
        # Info section
        info_frame = ttk.LabelFrame(test_tab, text="System Diagnostics", padding="10")
        info_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        
        ttk.Label(info_frame, text="Test your installation and verify paths").pack(anchor=tk.W)
        ttk.Label(info_frame, text="Run this before starting services for the first time").pack(anchor=tk.W)
        
        # Control buttons
        button_frame = ttk.Frame(test_tab)
        button_frame.grid(row=1, column=0, pady=(0, 10))
        
        ttk.Button(
            button_frame,
            text="🔍 Run All Tests",
            command=self.run_all_tests,
            width=20
        ).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(
            button_frame,
            text="🔧 Test vLLM Path",
            command=self.test_vllm_path,
            width=20
        ).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(
            button_frame,
            text="🔧 Test OpenHands",
            command=self.test_openhands,
            width=20
        ).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(
            button_frame,
            text="🗑️ Clear Log",
            command=lambda: self.clear_log(self.test_log),
            width=15
        ).pack(side=tk.LEFT, padx=5)
        
        # Log section
        log_frame = ttk.LabelFrame(test_tab, text="Test Results", padding="5")
        log_frame.grid(row=2, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)
        
        self.test_log = self.create_log_widget(log_frame)
        self.test_log.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        self.log_to_widget(self.test_log, "Ready to run diagnostics")
        self.log_to_widget(self.test_log, "Click 'Run All Tests' to verify your setup")
    
    def run_command(self, name, command, log_widget, start_btn, stop_btn, kill_btn, cwd=None):
        """Run command in separate isolated thread"""
        def run():
            process = None
            try:
                self.log_to_widget(log_widget, "=" * 60)
                self.log_to_widget(log_widget, f"STARTING {name}")
                self.log_to_widget(log_widget, "=" * 60)
                self.log_to_widget(log_widget, f"Working directory: {cwd or 'current'}")
                self.log_to_widget(log_widget, f"Command: {command}")
                self.log_to_widget(log_widget, "")
                
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
                
                self.processes[name] = process
                
                # Read output line by line
                try:
                    for line in process.stdout:
                        if line.strip():
                            self.log_to_widget(log_widget, line.rstrip())
                except Exception as e:
                    self.log_to_widget(log_widget, f"Stream reading error: {e}")
                
                process.wait()
                
                self.log_to_widget(log_widget, "")
                self.log_to_widget(log_widget, "=" * 60)
                if process.returncode == 0:
                    self.log_to_widget(log_widget, f"{name} STOPPED CLEANLY")
                elif process.returncode == -signal.SIGTERM:
                    self.log_to_widget(log_widget, f"{name} TERMINATED")
                elif process.returncode == -signal.SIGKILL:
                    self.log_to_widget(log_widget, f"{name} FORCE KILLED")
                else:
                    self.log_to_widget(log_widget, f"{name} EXITED WITH CODE: {process.returncode}")
                self.log_to_widget(log_widget, "=" * 60)
                
            except Exception as e:
                self.log_to_widget(log_widget, f"EXCEPTION: {str(e)}")
                import traceback
                self.log_to_widget(log_widget, traceback.format_exc())
            
            finally:
                # Cleanup
                if name in self.processes:
                    del self.processes[name]
                if name in self.monitors:
                    del self.monitors[name]
                
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
    
    def start_vllm(self):
        """Start vLLM server"""
        vllm_path = Path.home() / "LLMTK" / "vllm"
        
        if not vllm_path.exists():
            self.log_to_widget(self.vllm_log, "ERROR: vLLM directory not found!")
            self.log_to_widget(self.vllm_log, f"Expected path: {vllm_path}")
            return
        
        command = f"""
source {vllm_path}/.venv/bin/activate
echo "Virtual environment activated"
vllm serve casperhansen/deepseek-r1-distill-qwen-7b-awq \
  --host 0.0.0.0 \
  --port 8000 \
  --quantization awq_marlin \
  --gpu-memory-utilization 0.65 \
  --max-model-len 8192 \
  --dtype float16 \
  --api-key sk-vllm-local-abc123xyz789-qwen-coder
"""
        
        self.vllm_start_btn.configure(state=tk.DISABLED)
        self.vllm_stop_btn.configure(state=tk.NORMAL)
        self.vllm_kill_btn.configure(state=tk.NORMAL)
        self.run_command("vLLM", command, self.vllm_log, self.vllm_start_btn, 
                        self.vllm_stop_btn, self.vllm_kill_btn, cwd=str(vllm_path))
    
    def start_openhands(self):
        """Start OpenHands"""
        command = "uvx --python 3.12 openhands serve"
        
        self.oh_start_btn.configure(state=tk.DISABLED)
        self.oh_stop_btn.configure(state=tk.NORMAL)
        self.oh_kill_btn.configure(state=tk.NORMAL)
        self.run_command("OpenHands", command, self.oh_log, self.oh_start_btn,
                        self.oh_stop_btn, self.oh_kill_btn)
    
    def stop_vllm(self):
        """Stop vLLM server gracefully"""
        if "vLLM" in self.processes:
            self.log_to_widget(self.vllm_log, "Sending SIGTERM (graceful shutdown)...")
            try:
                os.killpg(os.getpgid(self.processes["vLLM"].pid), signal.SIGTERM)
            except:
                self.processes["vLLM"].terminate()
    
    def stop_openhands(self):
        """Stop OpenHands gracefully"""
        if "OpenHands" in self.processes:
            self.log_to_widget(self.oh_log, "Sending SIGTERM (graceful shutdown)...")
            try:
                os.killpg(os.getpgid(self.processes["OpenHands"].pid), signal.SIGTERM)
            except:
                self.processes["OpenHands"].terminate()
    
    def kill_vllm(self):
        """Force kill vLLM server"""
        if "vLLM" in self.processes:
            self.log_to_widget(self.vllm_log, "⚠️ FORCE KILLING PROCESS...")
            try:
                os.killpg(os.getpgid(self.processes["vLLM"].pid), signal.SIGKILL)
            except:
                self.processes["vLLM"].kill()
    
    def kill_openhands(self):
        """Force kill OpenHands"""
        if "OpenHands" in self.processes:
            self.log_to_widget(self.oh_log, "⚠️ FORCE KILLING PROCESS...")
            try:
                os.killpg(os.getpgid(self.processes["OpenHands"].pid), signal.SIGKILL)
            except:
                self.processes["OpenHands"].kill()
    
    def test_vllm_path(self):
        """Test vLLM installation"""
        self.log_to_widget(self.test_log, "")
        self.log_to_widget(self.test_log, "=" * 60)
        self.log_to_widget(self.test_log, "TESTING vLLM INSTALLATION")
        self.log_to_widget(self.test_log, "=" * 60)
        
        vllm_path = Path.home() / "LLMTK" / "vllm"
        self.log_to_widget(self.test_log, f"vLLM directory: {vllm_path}")
        
        if vllm_path.exists():
            self.log_to_widget(self.test_log, "✅ vLLM directory found")
            venv_path = vllm_path / ".venv"
            if venv_path.exists():
                self.log_to_widget(self.test_log, f"✅ Virtual environment found")
                activate_script = venv_path / "bin" / "activate"
                if activate_script.exists():
                    self.log_to_widget(self.test_log, "✅ Activate script exists")
                else:
                    self.log_to_widget(self.test_log, "❌ Activate script NOT found")
            else:
                self.log_to_widget(self.test_log, "❌ Virtual environment NOT found")
        else:
            self.log_to_widget(self.test_log, "❌ vLLM directory NOT found")
        
        self.log_to_widget(self.test_log, "=" * 60)
    
    def test_openhands(self):
        """Test OpenHands installation"""
        self.log_to_widget(self.test_log, "")
        self.log_to_widget(self.test_log, "=" * 60)
        self.log_to_widget(self.test_log, "TESTING OPENHANDS INSTALLATION")
        self.log_to_widget(self.test_log, "=" * 60)
        
        try:
            result = subprocess.run(
                ["which", "uvx"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                self.log_to_widget(self.test_log, f"✅ uvx found at: {result.stdout.strip()}")
            else:
                self.log_to_widget(self.test_log, "❌ uvx command NOT found")
                self.log_to_widget(self.test_log, "   Install with: pip install uvx")
        except Exception as e:
            self.log_to_widget(self.test_log, f"❌ Error checking uvx: {e}")
        
        self.log_to_widget(self.test_log, "=" * 60)
    
    def run_all_tests(self):
        """Run all diagnostic tests"""
        self.clear_log(self.test_log)
        self.log_to_widget(self.test_log, "RUNNING FULL SYSTEM DIAGNOSTICS")
        self.log_to_widget(self.test_log, "")
        
        # Test Python
        self.log_to_widget(self.test_log, "Testing Python...")
        try:
            result = subprocess.run(
                ["python3", "--version"],
                capture_output=True,
                text=True,
                timeout=5
            )
            self.log_to_widget(self.test_log, f"✅ {result.stdout.strip()}")
        except Exception as e:
            self.log_to_widget(self.test_log, f"❌ Error checking Python: {e}")
        
        # Test psutil
        self.log_to_widget(self.test_log, "")
        self.log_to_widget(self.test_log, "Testing psutil (for monitoring)...")
        try:
            import psutil
            self.log_to_widget(self.test_log, f"✅ psutil version {psutil.__version__} installed")
        except ImportError:
            self.log_to_widget(self.test_log, "❌ psutil NOT installed")
            self.log_to_widget(self.test_log, "   Install with: pip install psutil")
        
        # Test vLLM
        self.test_vllm_path()
        
        # Test OpenHands
        self.test_openhands()
        
        self.log_to_widget(self.test_log, "")
        self.log_to_widget(self.test_log, "DIAGNOSTICS COMPLETE")

def main():
    root = tk.Tk()
    app = LLMLauncher(root)
    root.mainloop()

if __name__ == "__main__":
    main()