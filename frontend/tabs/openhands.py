"""
OpenHands Tab

This tab provides a user interface for managing the OpenHands agent, a 
long-running background service. It allows the user to start, stop, and 
force-kill the agent, while also providing a real-time log view and easy 
access to the agent's web documentation.

Key Features:
- Process control (Start, Stop, Kill) for the agent.
- Pre-start cleanup of old Docker containers.
- Real-time log display within the tab.
- A clickable link to the agent's documentation, with error handling.
- System resource monitoring for the agent process.
- Centralized logging for all actions and errors.
"""

import tkinter as tk
from tkinter import ttk
import os
import signal
import subprocess
import webbrowser
import shutil
from pathlib import Path
import tempfile

# Assuming utils provides these helper functions. If not, they would need to be defined.
from utils import create_log_widget, log_to_widget, clear_log, run_command, create_monitor_frame

# --- Configuration ---
# These values are centralized for easy modification.
TAB_TITLE = "OpenHands"
# Path to the OpenHands project. IMPORTANT: This may need to be adjusted based on the user's setup.
AGENT_WORKING_DIR = "/home/zacaron/LLMTK/openhands"
# The web URL for the agent's documentation/frontend.
AGENT_DOCS_URL = "http://localhost:3000"

# --- Logging Utility ---
def log(launcher, widget, message, level="info", is_realtime=False):
    """A centralized logging helper for this tab.

    Args:
        launcher: The main application instance to access the global logger.
        widget: The local log widget to display the message.
        message (str): The log message.
        level (str): The log level ('info', 'warn', 'error').
        is_realtime (bool): Whether this is real-time output (no timestamp).
    """
    log_message = f"[{TAB_TITLE}] {message}"
    print(log_message)  # Always print to console for debugging.
    if launcher and hasattr(launcher, 'log_to_global'):
        launcher.log_to_global(TAB_TITLE, message)
    if widget:
        log_to_widget(widget, message, is_realtime)

# --- Core Actions ---

def open_docs_url(launcher, widget):
    """Safely opens the agent's documentation URL in a web browser."""
    log(launcher, widget, f"Attempting to open documentation at: {AGENT_DOCS_URL}")
    try:
        if not webbrowser.open(AGENT_DOCS_URL):
            raise webbrowser.Error("No browser found to open URL.")
        log(launcher, widget, "Successfully opened documentation in browser.")
    except webbrowser.Error as e:
        error_msg = f"Could not open web browser: {e}"
        log(launcher, widget, error_msg, "error")

def create_wrapper_script():
    """
    Creates a wrapper script that removes the -it flag from Docker commands.
    This allows OpenHands to run from a GUI without TTY issues.
    """
    wrapper_content = '''#!/bin/bash
# Wrapper script to run OpenHands without TTY requirement
# This intercepts docker commands and removes the -it flag

# Find the real docker binary
REAL_DOCKER=$(which docker)
if [ -z "$REAL_DOCKER" ]; then
    echo "Error: Docker not found in PATH"
    exit 1
fi

# Create temporary directory for the wrapper
TEMP_DIR=$(mktemp -d)
trap "rm -rf $TEMP_DIR" EXIT

# Create docker wrapper script that removes -it flags
cat > "$TEMP_DIR/docker" << 'DOCKER_WRAPPER'
#!/bin/bash
REAL_DOCKER_PATH="DOCKER_PLACEHOLDER"

# Parse arguments and remove -it flags
args=()
for arg in "$@"; do
    if [ "$arg" = "-it" ] || [ "$arg" = "-ti" ]; then
        continue
    elif [ "$arg" = "-i" ] || [ "$arg" = "-t" ]; then
        continue
    else
        args+=("$arg")
    fi
done

# Call the real docker with modified arguments
exec "$REAL_DOCKER_PATH" "${args[@]}"
DOCKER_WRAPPER

# Replace placeholder with actual docker path
sed -i "s|DOCKER_PLACEHOLDER|$REAL_DOCKER|g" "$TEMP_DIR/docker"
chmod +x "$TEMP_DIR/docker"

# Add temp directory to PATH (at the beginning)
export PATH="$TEMP_DIR:$PATH"

# Verify docker is accessible (for debugging)
if ! docker info &>/dev/null; then
    echo "Warning: Docker daemon check failed, but continuing anyway..."
fi

# Now run uvx with the modified PATH
cd "$1" || exit 1
shift
exec uvx --python 3.12 openhands serve "$@"
'''
    
    # Create temp script file
    fd, script_path = tempfile.mkstemp(suffix='.sh', prefix='openhands_wrapper_')
    os.close(fd)
    
    with open(script_path, 'w') as f:
        f.write(wrapper_content)
    
    os.chmod(script_path, 0o755)
    return script_path

def check_docker_running():
    """Check if Docker daemon is running."""
    try:
        result = subprocess.run(
            ["docker", "info"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=5
        )
        return result.returncode == 0
    except (subprocess.SubprocessError, FileNotFoundError, subprocess.TimeoutExpired):
        return False

def start_service(launcher, log_fn, widget, buttons):
    """Validates environment and starts the OpenHands agent process."""
    start_btn, stop_btn, kill_btn = buttons

    # 1. Check if the working directory exists
    agent_path = Path(AGENT_WORKING_DIR)
    if not agent_path.is_dir():
        log_fn(f"Error: Working directory not found at '{agent_path.resolve()}'. Cannot start agent.", "error")
        return

    # 2. Check if Docker is installed and running
    if not shutil.which("docker"):
        log_fn("❌ Docker is not installed. OpenHands requires Docker to run.", "error")
        log_fn("💡 Install Docker: https://docs.docker.com/engine/install/", "error")
        return
    
    if not check_docker_running():
        log_fn("❌ Docker daemon is not running.", "error")
        log_fn("💡 Start Docker with: sudo systemctl start docker", "error")
        log_fn("💡 Or enable at boot: sudo systemctl enable docker", "error")
        return

    # 3. Clean up any stale Docker containers before starting.
    log_fn("🧹 Cleaning up any stale 'openhands-app' containers...")
    try:
        # This runs 'docker rm -f openhands-app' to remove the container if it exists.
        subprocess.run(
            ["docker", "rm", "-f", "openhands-app"], 
            stdout=subprocess.DEVNULL, 
            stderr=subprocess.DEVNULL,
            check=False,  # Don't raise an exception if the container doesn't exist.
            cwd=str(agent_path)
        )
        log_fn("✅ Docker cleanup complete.")
    except (subprocess.SubprocessError, FileNotFoundError) as e:
        log_fn(f"⚠️ Warning: Docker container cleanup failed: {e}", "warn")

    # 4. Create wrapper script to handle TTY issue
    try:
        wrapper_script = create_wrapper_script()
        log_fn("Created wrapper script to handle Docker TTY issue")
    except Exception as e:
        log_fn(f"Failed to create wrapper script: {e}", "error")
        return

    # 5. Update UI and launch the process using the wrapper script
    start_btn.config(state=tk.DISABLED)
    stop_btn.config(state=tk.NORMAL)
    kill_btn.config(state=tk.NORMAL)
    
    command = f"bash {wrapper_script} {agent_path}"
    log_fn(f"Starting OpenHands agent (non-interactive mode)")
    log_fn(f"Server will be available at: {AGENT_DOCS_URL}")
    
    # Store wrapper script path for cleanup
    if not hasattr(launcher, 'openhands_wrapper'):
        launcher.openhands_wrapper = wrapper_script
    
    run_command(launcher, TAB_TITLE, command, log_fn, widget, 
                start_btn, stop_btn, kill_btn, cwd=str(agent_path))

def stop_service(launcher, log_fn):
    """Sends a graceful SIGTERM signal to the agent process group."""
    if TAB_TITLE not in launcher.processes:
        log_fn("Agent process not found. Nothing to stop.", "warn")
        return

    log_fn("Attempting graceful shutdown (sending SIGTERM)...")
    try:
        # Get the process group ID (pgid) to terminate the entire process tree.
        pgid = os.getpgid(launcher.processes[TAB_TITLE].pid)
        os.killpg(pgid, signal.SIGTERM)
        log_fn("SIGTERM signal sent to process group.")
        
        # Clean up wrapper script if it exists
        if hasattr(launcher, 'openhands_wrapper'):
            try:
                os.remove(launcher.openhands_wrapper)
                delattr(launcher, 'openhands_wrapper')
            except:
                pass
                
    except ProcessLookupError:
        log_fn("Process already terminated.", "warn")
        launcher.processes.pop(TAB_TITLE, None)
    except Exception as e:
        log_fn(f"Error during graceful stop: {e}. Consider a force kill.", "error")

def kill_service(launcher, log_fn):
    """Forcibly terminates the agent process group with SIGKILL."""
    if TAB_TITLE not in launcher.processes:
        log_fn("Agent process not found. Nothing to kill.", "warn")
        return

    log_fn("⚠️ Forcibly terminating process (sending SIGKILL)...")
    try:
        pgid = os.getpgid(launcher.processes[TAB_TITLE].pid)
        os.killpg(pgid, signal.SIGKILL)
        log_fn("SIGKILL signal sent. The process has been terminated.")
        
        # Clean up wrapper script if it exists
        if hasattr(launcher, 'openhands_wrapper'):
            try:
                os.remove(launcher.openhands_wrapper)
                delattr(launcher, 'openhands_wrapper')
            except:
                pass
                
    except ProcessLookupError:
        log_fn("Process already terminated.", "warn")
        launcher.processes.pop(TAB_TITLE, None)
    except Exception as e:
        log_fn(f"Error during force kill: {e}", "error")

# --- UI Setup ---
def create_tab(notebook, launcher):
    """Creates and lays out the OpenHands tab and its widgets."""
    tab = ttk.Frame(notebook, padding="10")
    notebook.add(tab, text=TAB_TITLE)
    
    # --- Layout Configuration ---
    tab.columnconfigure(0, weight=1)  # Main content column
    tab.columnconfigure(1, weight=0)  # Monitor column (fixed width)
    tab.rowconfigure(2, weight=1)     # Log area row
    
    # --- Left Frame (Info, Controls, Logs) ---
    left_frame = ttk.Frame(tab)
    left_frame.grid(row=0, column=0, rowspan=3, sticky="nsew", padx=(0, 10))
    left_frame.columnconfigure(0, weight=1)
    left_frame.rowconfigure(2, weight=1)

    # --- Log Widget ---
    log_frame = ttk.LabelFrame(left_frame, text="Agent Log", padding="5")
    log_frame.grid(row=2, column=0, sticky="nsew")
    log_frame.columnconfigure(0, weight=1)
    log_frame.rowconfigure(0, weight=1)
    log_widget = create_log_widget(log_frame)
    log_widget.grid(row=0, column=0, sticky="nsew")

    # Create a specific logger instance for this tab
    # Important: Accept both 'level' and 'is_realtime' parameters
    def log_fn(message, level="info", is_realtime=False):
        log(launcher, log_widget, message, level, is_realtime)

    # --- Info Section ---
    info_frame = ttk.LabelFrame(left_frame, text="Agent Information", padding="10")
    info_frame.grid(row=0, column=0, sticky="ew", pady=(0, 10))
    
    # Check Docker status on load
    docker_installed = shutil.which("docker") is not None
    docker_running = check_docker_running() if docker_installed else False
    
    ttk.Label(info_frame, text="Framework: OpenHands Agent").pack(anchor="w")
    ttk.Label(info_frame, text="Mode: GUI Server (Non-Interactive)").pack(anchor="w")
    
    # Docker status indicator
    docker_status = "✅ Running" if docker_running else ("⚠️ Not Running" if docker_installed else "❌ Not Installed")
    docker_color = "green" if docker_running else ("orange" if docker_installed else "red")
    docker_label = ttk.Label(info_frame, text=f"Docker: {docker_status}", foreground=docker_color)
    docker_label.pack(anchor="w")
    
    # Clickable URL label
    url_label = ttk.Label(info_frame, text=AGENT_DOCS_URL, cursor="hand2", foreground="blue")
    url_label.bind("<Button-1>", lambda e: open_docs_url(launcher, log_widget))
    url_label.pack(anchor="w")

    # --- Control Buttons ---
    button_frame = ttk.Frame(left_frame)
    button_frame.grid(row=1, column=0, pady=(0, 10))
    
    start_btn = ttk.Button(button_frame, text="▶ Start Agent", width=15)
    stop_btn = ttk.Button(button_frame, text="⏹ Stop Agent", state=tk.DISABLED, width=15)
    kill_btn = ttk.Button(button_frame, text="⚠️ Force Kill", state=tk.DISABLED, width=15)
    clear_btn = ttk.Button(button_frame, text="🗑️ Clear Log", width=12)

    start_btn.pack(side=tk.LEFT, padx=5)
    stop_btn.pack(side=tk.LEFT, padx=5)
    kill_btn.pack(side=tk.LEFT, padx=5)
    clear_btn.pack(side=tk.LEFT, padx=5)

    # Button commands
    buttons = (start_btn, stop_btn, kill_btn)
    start_btn.config(command=lambda: start_service(launcher, log_fn, log_widget, buttons))
    stop_btn.config(command=lambda: stop_service(launcher, log_fn))
    kill_btn.config(command=lambda: kill_service(launcher, log_fn))
    clear_btn.config(command=lambda: clear_log(log_widget))
    
    # --- Right Frame (System Monitor) ---
    monitor_frame = create_monitor_frame(tab, TAB_TITLE, launcher)
    monitor_frame.grid(row=0, column=1, sticky="new")
    
    log_fn("OpenHands tab initialized and ready.")
    log_fn("💡 Tip: The wrapper removes Docker's -it flag to enable GUI operation.")