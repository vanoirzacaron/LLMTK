#!/usr/bin/env python3
"""
LLM Services Launcher - Debug Version
A simple GUI to start OpenHands and vLLM services
"""

import tkinter as tk
from tkinter import ttk, scrolledtext
import subprocess
import threading
import os
from pathlib import Path

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
        main_frame.rowconfigure(2, weight=1)
        
        # Title
        title = ttk.Label(main_frame, text="🚀 LLM Services", font=('Arial', 16, 'bold'))
        title.grid(row=0, column=0, pady=(0, 20))
        
        # Buttons frame
        buttons_frame = ttk.Frame(main_frame)
        buttons_frame.grid(row=1, column=0, pady=(0, 10), sticky=(tk.W, tk.E))
        buttons_frame.columnconfigure(0, weight=1)
        buttons_frame.columnconfigure(1, weight=1)
        buttons_frame.columnconfigure(2, weight=1)
        
        # vLLM Button
        self.vllm_btn = ttk.Button(
            buttons_frame, 
            text="▶ Start vLLM Server",
            command=self.start_vllm,
            width=20
        )
        self.vllm_btn.grid(row=0, column=0, padx=5, pady=5, sticky=(tk.W, tk.E))
        
        # OpenHands Button
        self.openhands_btn = ttk.Button(
            buttons_frame,
            text="▶ Start OpenHands",
            command=self.start_openhands,
            width=20
        )
        self.openhands_btn.grid(row=0, column=1, padx=5, pady=5, sticky=(tk.W, tk.E))
        
        # Test Button
        test_btn = ttk.Button(
            buttons_frame,
            text="🔍 Test Paths",
            command=self.test_paths,
            width=20
        )
        test_btn.grid(row=0, column=2, padx=5, pady=5, sticky=(tk.W, tk.E))
        
        # Stop vLLM Button
        self.stop_vllm_btn = ttk.Button(
            buttons_frame,
            text="⏹ Stop vLLM",
            command=self.stop_vllm,
            state=tk.DISABLED,
            width=20
        )
        self.stop_vllm_btn.grid(row=1, column=0, padx=5, pady=5, sticky=(tk.W, tk.E))
        
        # Stop OpenHands Button
        self.stop_openhands_btn = ttk.Button(
            buttons_frame,
            text="⏹ Stop OpenHands",
            command=self.stop_openhands,
            state=tk.DISABLED,
            width=20
        )
        self.stop_openhands_btn.grid(row=1, column=1, padx=5, pady=5, sticky=(tk.W, tk.E))
        
        # Clear Log Button
        clear_btn = ttk.Button(
            buttons_frame,
            text="🗑️ Clear Log",
            command=self.clear_log,
            width=20
        )
        clear_btn.grid(row=1, column=2, padx=5, pady=5, sticky=(tk.W, tk.E))
        
        # Status frame
        status_frame = ttk.LabelFrame(main_frame, text="Status & Logs", padding="5")
        status_frame.grid(row=2, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(10, 0))
        status_frame.columnconfigure(0, weight=1)
        status_frame.rowconfigure(0, weight=1)
        
        # Log output
        self.log_output = scrolledtext.ScrolledText(
            status_frame,
            wrap=tk.WORD,
            height=20,
            state=tk.DISABLED,
            bg='#1e1e1e',
            fg='#00ff00',
            font=('Courier', 9)
        )
        self.log_output.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        self.log("=" * 60)
        self.log("LLM Services Launcher - Debug Version")
        self.log("=" * 60)
        self.log("Click 'Test Paths' to verify your setup first!")
        self.log("")
        
    def clear_log(self):
        """Clear the log output"""
        self.log_output.configure(state=tk.NORMAL)
        self.log_output.delete(1.0, tk.END)
        self.log_output.configure(state=tk.DISABLED)
        
    def log(self, message):
        """Add message to log output"""
        self.log_output.configure(state=tk.NORMAL)
        self.log_output.insert(tk.END, f"{message}\n")
        self.log_output.see(tk.END)
        self.log_output.configure(state=tk.DISABLED)
    
    def test_paths(self):
        """Test if paths and commands exist"""
        self.log("")
        self.log("=" * 60)
        self.log("TESTING PATHS AND COMMANDS")
        self.log("=" * 60)
        
        # Test vLLM path
        vllm_path = Path.home() / "LLMTK" / "vllm"
        self.log(f"vLLM directory: {vllm_path}")
        if vllm_path.exists():
            self.log("✅ vLLM directory found")
            venv_path = vllm_path / ".venv"
            if venv_path.exists():
                self.log(f"✅ Virtual environment found at {venv_path}")
                activate_script = venv_path / "bin" / "activate"
                if activate_script.exists():
                    self.log("✅ Activate script exists")
                else:
                    self.log("❌ Activate script NOT found")
            else:
                self.log("❌ Virtual environment NOT found")
        else:
            self.log("❌ vLLM directory NOT found")
        
        # Test uvx command
        self.log("")
        self.log("Testing uvx command...")
        try:
            result = subprocess.run(
                ["which", "uvx"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                self.log(f"✅ uvx found at: {result.stdout.strip()}")
            else:
                self.log("❌ uvx command NOT found")
                self.log("   Install with: pip install uvx")
        except Exception as e:
            self.log(f"❌ Error checking uvx: {e}")
        
        # Test Python version
        self.log("")
        self.log("Testing Python...")
        try:
            result = subprocess.run(
                ["python3", "--version"],
                capture_output=True,
                text=True,
                timeout=5
            )
            self.log(f"✅ Python version: {result.stdout.strip()}")
        except Exception as e:
            self.log(f"❌ Error checking Python: {e}")
        
        self.log("")
        self.log("=" * 60)
        self.log("PATH TEST COMPLETE")
        self.log("=" * 60)
        self.log("")
    
    def run_command(self, name, command, cwd=None):
        """Run command in separate thread"""
        def run():
            try:
                self.log("")
                self.log("=" * 60)
                self.log(f"[{name}] STARTING")
                self.log("=" * 60)
                self.log(f"Working directory: {cwd or 'current'}")
                self.log(f"Command: {command}")
                self.log("")
                
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
                        self.log(f"[{name}] {line.rstrip()}")
                
                process.wait()
                
                self.log("")
                self.log("=" * 60)
                if process.returncode == 0:
                    self.log(f"[{name}] STOPPED CLEANLY")
                else:
                    self.log(f"[{name}] EXITED WITH ERROR CODE: {process.returncode}")
                self.log("=" * 60)
                self.log("")
                
                # Re-enable start button
                if name == "vLLM":
                    self.vllm_btn.configure(state=tk.NORMAL)
                    self.stop_vllm_btn.configure(state=tk.DISABLED)
                else:
                    self.openhands_btn.configure(state=tk.NORMAL)
                    self.stop_openhands_btn.configure(state=tk.DISABLED)
                    
            except Exception as e:
                self.log(f"[{name}] EXCEPTION: {str(e)}")
                import traceback
                self.log(traceback.format_exc())
                
                # Re-enable button on error
                if name == "vLLM":
                    self.vllm_btn.configure(state=tk.NORMAL)
                    self.stop_vllm_btn.configure(state=tk.DISABLED)
                else:
                    self.openhands_btn.configure(state=tk.NORMAL)
                    self.stop_openhands_btn.configure(state=tk.DISABLED)
        
        thread = threading.Thread(target=run, daemon=True)
        thread.start()
    
    def start_vllm(self):
        """Start vLLM server"""
        vllm_path = Path.home() / "LLMTK" / "vllm"
        
        if not vllm_path.exists():
            self.log("")
            self.log("=" * 60)
            self.log("[vLLM] ERROR: Directory not found!")
            self.log(f"Expected path: {vllm_path}")
            self.log("=" * 60)
            self.log("")
            return
        
        # Build command with explicit bash
        command = f"""
source {vllm_path}/.venv/bin/activate
echo "Virtual environment activated"
which python
which vllm
vllm serve casperhansen/deepseek-r1-distill-qwen-7b-awq \
  --host 0.0.0.0 \
  --port 8000 \
  --quantization awq_marlin \
  --gpu-memory-utilization 0.65 \
  --max-model-len 8192 \
  --dtype float16 \
  --api-key sk-vllm-local-abc123xyz789-qwen-coder
"""
        
        self.vllm_btn.configure(state=tk.DISABLED)
        self.stop_vllm_btn.configure(state=tk.NORMAL)
        self.run_command("vLLM", command, cwd=str(vllm_path))
    
    def start_openhands(self):
        """Start OpenHands"""
        command = "uvx --python 3.12 openhands serve"
        
        self.openhands_btn.configure(state=tk.DISABLED)
        self.stop_openhands_btn.configure(state=tk.NORMAL)
        self.run_command("OpenHands", command)
    
    def stop_vllm(self):
        """Stop vLLM server"""
        if "vLLM" in self.processes:
            self.log("")
            self.log("[vLLM] Sending termination signal...")
            self.processes["vLLM"].terminate()
            del self.processes["vLLM"]
    
    def stop_openhands(self):
        """Stop OpenHands"""
        if "OpenHands" in self.processes:
            self.log("")
            self.log("[OpenHands] Sending termination signal...")
            self.processes["OpenHands"].terminate()
            del self.processes["OpenHands"]

def main():
    root = tk.Tk()
    app = LLMLauncher(root)
    root.mainloop()

if __name__ == "__main__":
    main()
