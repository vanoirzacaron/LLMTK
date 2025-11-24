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
        command=lambda: run_all_tests(test_log),
        width=20
    ).pack(side=tk.LEFT, padx=5)
    
    ttk.Button(
        button_frame,
        text="🔧 Test vLLM Path",
        command=lambda: test_vllm_path(test_log),
        width=20
    ).pack(side=tk.LEFT, padx=5)
    
    ttk.Button(
        button_frame,
        text="🔧 Test OpenHands",
        command=lambda: test_openhands(test_log),
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
    
    log_to_widget(test_log, "Ready to run diagnostics")
    log_to_widget(test_log, "Click 'Run All Tests' to verify your setup")

def test_vllm_path(log_widget):
    """Test vLLM installation"""
    log_to_widget(log_widget, "")
    log_to_widget(log_widget, "=" * 60)
    log_to_widget(log_widget, "TESTING vLLM INSTALLATION")
    log_to_widget(log_widget, "=" * 60)
    
    vllm_path = Path.home() / "LLMTK" / "vllm"
    log_to_widget(log_widget, f"vLLM directory: {vllm_path}")
    
    if vllm_path.exists():
        log_to_widget(log_widget, "✅ vLLM directory found")
        venv_path = vllm_path / ".venv"
        if venv_path.exists():
            log_to_widget(log_widget, f"✅ Virtual environment found")
            activate_script = venv_path / "bin" / "activate"
            if activate_script.exists():
                log_to_widget(log_widget, "✅ Activate script exists")
            else:
                log_to_widget(log_widget, "❌ Activate script NOT found")
        else:
            log_to_widget(log_widget, "❌ Virtual environment NOT found")
    else:
        log_to_widget(log_widget, "❌ vLLM directory NOT found")
    
    log_to_widget(log_widget, "=" * 60)

def test_openhands(log_widget):
    """Test OpenHands installation"""
    log_to_widget(log_widget, "")
    log_to_widget(log_widget, "=" * 60)
    log_to_widget(log_widget, "TESTING OPENHANDS INSTALLATION")
    log_to_widget(log_widget, "=" * 60)
    
    try:
        result = subprocess.run(
            ["which", "uvx"],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            log_to_widget(log_widget, f"✅ uvx found at: {result.stdout.strip()}")
        else:
            log_to_widget(log_widget, "❌ uvx command NOT found")
            log_to_widget(log_widget, "   Install with: pip install uvx")
    except Exception as e:
        log_to_widget(log_widget, f"❌ Error checking uvx: {e}")
    
    log_to_widget(log_widget, "=" * 60)

def run_all_tests(log_widget):
    """Run all diagnostic tests"""
    clear_log(log_widget)
    log_to_widget(log_widget, "RUNNING FULL SYSTEM DIAGNOSTICS")
    log_to_widget(log_widget, "")
    
    # Test Python
    log_to_widget(log_widget, "Testing Python...")
    try:
        result = subprocess.run(
            ["python3", "--version"],
            capture_output=True,
            text=True,
            timeout=5
        )
        log_to_widget(log_widget, f"✅ {result.stdout.strip()}")
    except Exception as e:
        log_to_widget(log_widget, f"❌ Error checking Python: {e}")
    
    # Test psutil
    log_to_widget(log_widget, "")
    log_to_widget(log_widget, "Testing psutil (for monitoring)...")
    try:
        import psutil
        log_to_widget(log_widget, f"✅ psutil version {psutil.__version__} installed")
    except ImportError:
        log_to_widget(log_widget, "❌ psutil NOT installed")
        log_to_widget(log_widget, "   Install with: pip install psutil")
    
    # Test vLLM
    test_vllm_path(log_widget)
    
    # Test OpenHands
    test_openhands(log_widget)
    
    log_to_widget(log_widget, "")
    log_to_widget(log_widget, "DIAGNOSTICS COMPLETE")
