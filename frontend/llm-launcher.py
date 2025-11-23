#!/usr/bin/env python3
"""
LLM Services Launcher - Tabbed Interface
A simple GUI to start OpenHands and vLLM services
"""

import tkinter as tk
from tkinter import ttk, scrolledtext
import subprocess
import threading
import os
from pathlib import Path
from datetime import datetime

class LLMLauncher:
    def __init__(self, root):
        self.root = root
        self.root.title("LLM Services Launcher")
        self.root.geometry("800x600")
        self.root.resizable(True, True)
        
        # Store process references
        self.processes = {}
        
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
        widget.configure(state=tk.NORMAL)
        timestamp = datetime.now().strftime("%H:%M:%S")
        widget.insert(tk.END, f"[{timestamp}] {message}\n")
        widget.see(tk.END)
        widget.configure(state=tk.DISABLED)
    
    def clear_log(self, widget):
        """Clear specific log widget"""
        widget.configure(state=tk.NORMAL)
        widget.delete(1.0, tk.END)
        widget.configure(state=tk.DISABLED)
    
    def create_vllm_tab(self):
        """Create vLLM tab"""
        vllm_tab = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(vllm_tab, text="vLLM Server")
        
        vllm_tab.columnconfigure(0, weight=1)
        vllm_tab.rowconfigure(2, weight=1)
        
        # Info section
        info_frame = ttk.LabelFrame(vllm_tab, text="Server Information", padding="10")
        info_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        
        ttk.Label(info_frame, text="Model: DeepSeek-R1-Distill-Qwen-7B-AWQ").pack(anchor=tk.W)
        ttk.Label(info_frame, text="Host: 0.0.0.0:8000").pack(anchor=tk.W)
        ttk.Label(info_frame, text="API Key: sk-vllm-local-abc123xyz789-qwen-coder").pack(anchor=tk.W)
        
        # Control buttons
        button_frame = ttk.Frame(vllm_tab)
        button_frame.grid(row=1, column=0, pady=(0, 10))
        
        self.vllm_start_btn = ttk.Button(
            button_frame,
            text="▶ Start vLLM Server",
            command=self.start_vllm,
            width=20
        )
        self.vllm_start_btn.pack(side=tk.LEFT, padx=5)
        
        self.vllm_stop_btn = ttk.Button(
            button_frame,
            text="⏹ Stop Server",
            command=self.stop_vllm,
            state=tk.DISABLED,
            width=20
        )
        self.vllm_stop_btn.pack(side=tk.LEFT, padx=5)
        
        ttk.Button(
            button_frame,
            text="🗑️ Clear Log",
            command=lambda: self.clear_log(self.vllm_log),
            width=15
        ).pack(side=tk.LEFT, padx=5)
        
        # Log section
        log_frame = ttk.LabelFrame(vllm_tab, text="Server Log", padding="5")
        log_frame.grid(row=2, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)
        
        self.vllm_log = self.create_log_widget(log_frame)
        self.vllm_log.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        self.log_to_widget(self.vllm_log, "vLLM Server ready to start")
    
    def create_openhands_tab(self):
        """Create OpenHands tab"""
        oh_tab = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(oh_tab, text="OpenHands")
        
        oh_tab.columnconfigure(0, weight=1)
        oh_tab.rowconfigure(2, weight=1)
        
        # Info section
        info_frame = ttk.LabelFrame(oh_tab, text="Agent Information", padding="10")
        info_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        
        ttk.Label(info_frame, text="Framework: OpenHands Agent").pack(anchor=tk.W)
        ttk.Label(info_frame, text="Python Version: 3.12").pack(anchor=tk.W)
        ttk.Label(info_frame, text="Command: uvx --python 3.12 openhands serve").pack(anchor=tk.W)
        
        # Control buttons
        button_frame = ttk.Frame(oh_tab)
        button_frame.grid(row=1, column=0, pady=(0, 10))
        
        self.oh_start_btn = ttk.Button(
            button_frame,
            text="▶ Start OpenHands",
            command=self.start_openhands,
            width=20
        )
        self.oh_start_btn.pack(side=tk.LEFT, padx=5)
        
        self.oh_stop_btn = ttk.Button(
            button_frame,
            text="⏹ Stop Agent",
            command=self.stop_openhands,
            state=tk.DISABLED,
            width=20
        )
        self.oh_stop_btn.pack(side=tk.LEFT, padx=5)
        
        ttk.Button(
            button_frame,
            text="🗑️ Clear Log",
            command=lambda: self.clear_log(self.oh_log),
            width=15
        ).pack(side=tk.LEFT, padx=5)
        
        # Log section
        log_frame = ttk.LabelFrame(oh_tab, text="Agent Log", padding="5")
        log_frame.grid(row=2, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)
        
        self.oh_log = self.create_log_widget(log_frame)
        self.oh_log.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
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
    
    def run_command(self, name, command, log_widget, start_btn, stop_btn, cwd=None):
        """Run command in separate thread"""
        def run():
            try:
                self.log_to_widget(log_widget, "=" * 60)
                self.log_to_widget(log_widget, f"STARTING {name}")
                self.log_to_widget(log_widget, "=" * 60)
                self.log_to_widget(log_widget, f"Working directory: {cwd or 'current'}")
                self.log_to_widget(log_widget, f"Command: {command}")
                self.log_to_widget(log_widget, "")
                
                # Use bash explicitly to ensure shell features work
                process = subprocess.Popen(
                    ["/bin/bash", "-c", command],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    cwd=cwd,
                    bufsize=1,
                    env=os.environ.copy()
                )
                
                self.processes[name] = process
                
                # Read output line by line
                for line in process.stdout:
                    if line.strip():
                        self.log_to_widget(log_widget, line.rstrip())
                
                process.wait()
                
                self.log_to_widget(log_widget, "")
                self.log_to_widget(log_widget, "=" * 60)
                if process.returncode == 0:
                    self.log_to_widget(log_widget, f"{name} STOPPED CLEANLY")
                else:
                    self.log_to_widget(log_widget, f"{name} EXITED WITH ERROR CODE: {process.returncode}")
                self.log_to_widget(log_widget, "=" * 60)
                
                # Re-enable buttons
                start_btn.configure(state=tk.NORMAL)
                stop_btn.configure(state=tk.DISABLED)
                    
            except Exception as e:
                self.log_to_widget(log_widget, f"EXCEPTION: {str(e)}")
                import traceback
                self.log_to_widget(log_widget, traceback.format_exc())
                
                start_btn.configure(state=tk.NORMAL)
                stop_btn.configure(state=tk.DISABLED)
        
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
        self.run_command("vLLM", command, self.vllm_log, self.vllm_start_btn, self.vllm_stop_btn, cwd=str(vllm_path))
    
    def start_openhands(self):
        """Start OpenHands"""
        command = "uvx --python 3.12 openhands serve"
        
        self.oh_start_btn.configure(state=tk.DISABLED)
        self.oh_stop_btn.configure(state=tk.NORMAL)
        self.run_command("OpenHands", command, self.oh_log, self.oh_start_btn, self.oh_stop_btn)
    
    def stop_vllm(self):
        """Stop vLLM server"""
        if "vLLM" in self.processes:
            self.log_to_widget(self.vllm_log, "Sending termination signal...")
            self.processes["vLLM"].terminate()
            del self.processes["vLLM"]
    
    def stop_openhands(self):
        """Stop OpenHands"""
        if "OpenHands" in self.processes:
            self.log_to_widget(self.oh_log, "Sending termination signal...")
            self.processes["OpenHands"].terminate()
            del self.processes["OpenHands"]
    
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