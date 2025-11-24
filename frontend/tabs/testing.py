"""
Testing/Diagnostics Tab
System diagnostics and validation
"""

import tkinter as tk
from tkinter import ttk
import subprocess
from pathlib import Path
from utils import create_log_widget, log_to_widget, clear_log


def create_tab(notebook, launcher):
    """Create and configure the Testing tab"""
    test_tab = ttk.Frame(notebook, padding="10")
    notebook.add(test_tab, text="Testing")
    
    test_tab.columnconfigure(0, weight=1)
    test_tab.rowconfigure(2, weight=1)

    # Combined logger
    def log_message(message):
        log_to_widget(test_log, message)
        launcher.log_to_global("Testing", message)

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
        command=lambda: run_all_tests(log_message),
        width=20
    ).pack(side=tk.LEFT, padx=5)
    
    ttk.Button(
        button_frame,
        text="🔧 Test vLLM Path",
        command=lambda: test_vllm_path(log_message),
        width=20
    ).pack(side=tk.LEFT, padx=5)
    
    ttk.Button(
        button_frame,
        text="🔧 Test OpenHands",
        command=lambda: test_openhands(log_message),
        width=20
    ).pack(side=tk.LEFT, padx=5)
    
    ttk.Button(
        button_frame,
        text="🗑️ Clear Log",
        command=lambda: clear_log(test_log),
        width=15
    ).pack(side=tk.LEFT, padx=5)
    
    # Log section
    log_frame = ttk.LabelFrame(test_tab, text="Test Results", padding="5")
    log_frame.grid(row=2, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
    log_frame.columnconfigure(0, weight=1)
    log_frame.rowconfigure(0, weight=1)
    
    test_log = create_log_widget(log_frame)
    test_log.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
    
    log_message("Ready to run diagnostics")
    log_message("Click 'Run All Tests' to verify your setup")

def test_vllm_path(log_fn):
    """Test vLLM installation"""
    log_fn("")
    log_fn("=" * 60)
    log_fn("TESTING vLLM INSTALLATION")
    log_fn("=" * 60)
    
    vllm_path = Path.home() / "LLMTK" / "vllm"
    log_fn(f"vLLM directory: {vllm_path}")
    
    if vllm_path.exists():
        log_fn("✅ vLLM directory found")
        venv_path = vllm_path / ".venv"
        if venv_path.exists():
            log_fn(f"✅ Virtual environment found")
            activate_script = venv_path / "bin" / "activate"
            if activate_script.exists():
                log_fn("✅ Activate script exists")
            else:
                log_fn("❌ Activate script NOT found")
        else:
            log_fn("❌ Virtual environment NOT found")
    else:
        log_fn("❌ vLLM directory NOT found")
    
    log_fn("=" * 60)

def test_openhands(log_fn):
    """Test OpenHands installation"""
    log_fn("")
    log_fn("=" * 60)
    log_fn("TESTING OPENHANDS INSTALLATION")
    log_fn("=" * 60)
    
    try:
        result = subprocess.run(
            ["which", "uvx"],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            log_fn(f"✅ uvx found at: {result.stdout.strip()}")
        else:
            log_fn("❌ uvx command NOT found")
            log_fn("   Install with: pip install uvx")
    except Exception as e:
        log_fn(f"❌ Error checking uvx: {e}")
    
    log_fn("=" * 60)

def run_all_tests(log_fn):
    """Run all diagnostic tests"""
    log_fn("RUNNING FULL SYSTEM DIAGNOSTICS")
    log_fn("")
    
    # Test Python
    log_fn("Testing Python...")
    try:
        result = subprocess.run(
            ["python3", "--version"],
            capture_output=True,
            text=True,
            timeout=5
        )
        log_fn(f"✅ {result.stdout.strip()}")
    except Exception as e:
        log_fn(f"❌ Error checking Python: {e}")
    
    # Test psutil
    log_fn("")
    log_fn("Testing psutil (for monitoring)...")
    try:
        import psutil
        log_fn(f"✅ psutil version {psutil.__version__} installed")
    except ImportError:
        log_fn("❌ psutil NOT installed")
        log_fn("   Install with: pip install psutil")
    
    # Test vLLM
    test_vllm_path(log_fn)
    
    # Test OpenHands
    test_openhands(log_fn)
    
    log_fn("")
    log_fn("DIAGNOSTICS COMPLETE")
