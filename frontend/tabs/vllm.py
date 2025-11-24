"""
vLLM Server Tab
Manages the vLLM server process with monitoring
"""

import tkinter as tk
from tkinter import ttk
import os
import signal
from pathlib import Path
from utils import create_log_widget, log_to_widget, clear_log, run_command, create_monitor_frame

def create_tab(notebook, launcher):
    """Create and configure the vLLM tab"""
    vllm_tab = ttk.Frame(notebook, padding="10")
    notebook.add(vllm_tab, text="vLLM Server")
    
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
    
    ttk.Label(info_frame, text="Model: Qwen2.5-Coder-7B-Instruct-AWQ").pack(anchor=tk.W)
    ttk.Label(info_frame, text="Host: 0.0.0.0:8000").pack(anchor=tk.W)
    ttk.Label(info_frame, text="API Key: sk-vllm-local-abc123xyz789-qwen-coder").pack(anchor=tk.W)
    
    # Control buttons
    button_frame = ttk.Frame(left_frame)
    button_frame.grid(row=1, column=0, pady=(0, 10))
    
    vllm_start_btn = ttk.Button(
        button_frame,
        text="▶ Start Server",
        command=lambda: start_vllm(launcher, vllm_log, vllm_start_btn, vllm_stop_btn, vllm_kill_btn),
        width=15
    )
    vllm_start_btn.pack(side=tk.LEFT, padx=5)
    
    vllm_stop_btn = ttk.Button(
        button_frame,
        text="⏹ Stop Server",
        command=lambda: stop_vllm(launcher, vllm_log),
        state=tk.DISABLED,
        width=15
    )
    vllm_stop_btn.pack(side=tk.LEFT, padx=5)
    
    vllm_kill_btn = ttk.Button(
        button_frame,
        text="⚠️ Force Kill",
        command=lambda: kill_vllm(launcher, vllm_log),
        state=tk.DISABLED,
        width=15
    )
    vllm_kill_btn.pack(side=tk.LEFT, padx=5)
    
    ttk.Button(
        button_frame,
        text="🗑️ Clear Log",
        command=lambda: clear_log(vllm_log),
        width=12
    ).pack(side=tk.LEFT, padx=5)
    
    # Log section
    log_frame = ttk.LabelFrame(left_frame, text="Server Log", padding="5")
    log_frame.grid(row=2, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
    log_frame.columnconfigure(0, weight=1)
    log_frame.rowconfigure(0, weight=1)
    
    vllm_log = create_log_widget(log_frame)
    vllm_log.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
    
    # Right side - Monitor
    vllm_monitor = create_monitor_frame(vllm_tab, "vLLM", launcher)
    vllm_monitor.grid(row=0, column=1, sticky=(tk.N, tk.E, tk.W))
    
    log_to_widget(vllm_log, "vLLM Server ready to start")

def start_vllm(launcher, log_widget, start_btn, stop_btn, kill_btn):
    """Start vLLM server"""
    vllm_path = Path.home() / "LLMTK" / "vllm"
    
    if not vllm_path.exists():
        log_to_widget(log_widget, "ERROR: vLLM directory not found!")
        log_to_widget(log_widget, f"Expected path: {vllm_path}")
        return
    
    command = f"""
source {vllm_path}/.venv/bin/activate
echo "Virtual environment activated"
vllm serve Qwen/Qwen2.5-Coder-7B-Instruct-AWQ \
  --host 0.0.0.0 \
  --port 8000 \
  --quantization awq_marlin \
  --gpu-memory-utilization 0.65 \
  --max-model-len 8192 \
  --dtype float16 \
  --api-key sk-vllm-local-abc123xyz789-qwen-coder
"""
    
    start_btn.configure(state=tk.DISABLED)
    stop_btn.configure(state=tk.NORMAL)
    kill_btn.configure(state=tk.NORMAL)
    run_command(launcher, "vLLM", command, log_widget, start_btn, 
                stop_btn, kill_btn, cwd=str(vllm_path))

def stop_vllm(launcher, log_widget):
    """Stop vLLM server gracefully"""
    if "vLLM" in launcher.processes:
        log_to_widget(log_widget, "Sending SIGTERM (graceful shutdown)...")
        try:
            os.killpg(os.getpgid(launcher.processes["vLLM"].pid), signal.SIGTERM)
        except:
            launcher.processes["vLLM"].terminate()

def kill_vllm(launcher, log_widget):
    """Force kill vLLM server"""
    if "vLLM" in launcher.processes:
        log_to_widget(log_widget, "⚠️ FORCE KILLING PROCESS...")
        try:
            os.killpg(os.getpgid(launcher.processes["vLLM"].pid), signal.SIGKILL)
        except:
            launcher.processes["vLLM"].kill()
