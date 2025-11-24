"""
Gemini API Usage Monitor Tab

Allows sending prompts to the Gemini API and tracks token usage
by logging it to a local file.
"""

import tkinter as tk
from tkinter import ttk
import threading
from tabs.utils import create_log_widget, log_to_widget, clear_log
from tabs import gemini_monitor # Import the new backend logic

# --- CONFIGURATION ---
TAB_TITLE = "Gemini Monitor"

def create_tab(notebook, launcher):
    """Create and configure the tab interface"""
    tab = ttk.Frame(notebook, padding="10")
    notebook.add(tab, text=TAB_TITLE)

    tab.columnconfigure(0, weight=1)
    tab.rowconfigure(3, weight=1) # Give weight to the log frame

    # --- 1. Prompt Input Section ---
    prompt_frame = ttk.LabelFrame(tab, text="Send a New Prompt", padding="10")
    prompt_frame.grid(row=0, column=0, sticky="ew", pady=(0, 10))
    prompt_frame.columnconfigure(0, weight=1)

    prompt_entry = ttk.Entry(prompt_frame, width=80)
    prompt_entry.grid(row=0, column=0, sticky="ew", padx=(0, 10))
    prompt_entry.insert(0, "Explain how a CPU works in one sentence.") # Default prompt

    send_btn = ttk.Button(
        prompt_frame,
        text="✉️ Send Prompt",
        command=lambda: send_prompt(prompt_entry.get(), log_widget, send_btn)
    )
    send_btn.grid(row=0, column=1, sticky="e")

    # --- 2. Control & Status Button Section ---
    button_frame = ttk.Frame(tab)
    button_frame.grid(row=1, column=0, sticky="w", pady=(0, 10))

    refresh_btn = ttk.Button(
        button_frame,
        text="🔄 Refresh Stats",
        command=lambda: show_current_stats(log_widget),
        width=15
    )
    refresh_btn.pack(side=tk.LEFT, padx=(0, 5))

    clear_btn = ttk.Button(
        button_frame,
        text="🗑️ Clear Log",
        command=lambda: clear_log(log_widget),
        width=15
    )
    clear_btn.pack(side=tk.LEFT, padx=5)

    # --- 3. Log Section ---
    log_frame = ttk.LabelFrame(tab, text="Activity & Usage Log", padding="5")
    log_frame.grid(row=3, column=0, sticky="nsew")
    log_frame.columnconfigure(0, weight=1)
    log_frame.rowconfigure(0, weight=1)

    log_widget = create_log_widget(log_frame)
    log_widget.grid(row=0, column=0, sticky="nsew")
    
    # --- Initial Status Check ---
    # Check if the client initialized correctly and show status
    if gemini_monitor.init_error:
        log_to_widget(log_widget, f"--- INITIALIZATION FAILED ---\n{gemini_monitor.init_error}")
        send_btn.config(state=tk.DISABLED)
    else:
        log_to_widget(log_widget, "Gemini Monitor loaded successfully.")
        log_to_widget(log_widget, "Ready to send requests.")
        show_current_stats(log_widget) # Show stats on load

def show_current_stats(log_widget):
    """Clears the log and displays the latest summary from the stats file."""
    clear_log(log_widget)
    log_to_widget(log_widget, "--- Current Usage Summary ---")
    summary = gemini_monitor.get_stats_summary()
    log_to_widget(log_widget, summary)

def send_prompt(prompt, log_widget, send_btn):
    """Handles the button click to send a prompt to the API."""
    if not prompt:
        log_to_widget(log_widget, "Error: Prompt cannot be empty.")
        return

    # Disable button to prevent multiple requests
    send_btn.config(state=tk.DISABLED)
    clear_log(log_widget)
    
    # Run the API call in a separate thread to keep the UI responsive
    def run_in_thread():
        # Define a callback to log messages from the backend to our widget
        def log_callback(message):
            # Schedule the GUI update to run in the main thread
            log_widget.after(0, lambda: log_to_widget(log_widget, message))
        
        gemini_monitor.run_monitored_request(prompt, log_callback)
        
        # Re-enable the button once the request is complete
        send_btn.after(0, lambda: send_btn.config(state=tk.NORMAL))

    thread = threading.Thread(target=run_in_thread)
    thread.daemon = True
    thread.start()
