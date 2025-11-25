"""
Infrasven Tab

This tab provides a convenient interface for launching web browser profiles and 
pre-configured SSH connections. It is designed to streamline the developer's 
workflow by providing quick access to different browsing contexts and remote servers.

Key Features:
- Auto-discovery of Firefox and Google Chrome profiles (supports Snap and traditional installs).
- One-click launching of specific browser profiles.
- One-click launching of a terminal for a specific SSH connection.
- Robust error handling for missing applications (browsers, terminal) or configuration files.
- Centralized logging for all actions and errors.
"""

import tkinter as tk
from tkinter import ttk
import os
import shutil
import configparser
import json
from pathlib import Path
import subprocess

# --- Constants ---
TAB_TITLE = "Infrasven"
SSH_CONNECTION_STRING = "ssh -i ~/.ssh/0906hostingerinfra -p 65002 u442402519@147.79.95.137"

# --- Logging ---
def log(launcher, message, level="info"):
    """Centralized logging helper for the Infrasven tab."""
    log_message = f"[{TAB_TITLE}] {message}"
    print(log_message)  # For direct console feedback.
    if launcher and hasattr(launcher, 'log_to_global'):
        launcher.log_to_global(TAB_TITLE, message)

# --- Profile Discovery Functions ---

def find_firefox_profiles(launcher):
    """
    Finds Firefox profiles by parsing profiles.ini file.
    Supports both traditional installs and Snap packages.
    Returns a list of tuples: (display_name, profile_path, profiles_ini_dir)
    """
    profiles = []
    
    # Check multiple possible Firefox profile locations
    possible_locations = [
        Path.home() / ".mozilla/firefox",  # Traditional install
        Path.home() / "snap/firefox/common/.mozilla/firefox",  # Snap install
    ]
    
    for firefox_base_dir in possible_locations:
        profiles_ini_path = firefox_base_dir / "profiles.ini"
        
        if not profiles_ini_path.exists():
            continue
            
        log(launcher, f"Found profiles.ini at: {profiles_ini_path}")
        
        try:
            config = configparser.ConfigParser()
            config.read(profiles_ini_path)

            # Parse profiles from the ini file
            for section in config.sections():
                if section.startswith('Profile'):
                    if 'Name' in config[section] and 'Path' in config[section]:
                        profile_name = config[section]['Name']
                        profile_path = config[section]['Path']
                        is_relative = config[section].get('IsRelative', '1') == '1'
                        
                        # Build full path if relative
                        if is_relative:
                            full_path = firefox_base_dir / profile_path
                        else:
                            full_path = Path(profile_path)
                        
                        # Only add if the profile directory actually exists
                        if full_path.exists():
                            profiles.append((profile_name, profile_path, str(firefox_base_dir)))
                            log(launcher, f"Found Firefox profile: {profile_name} at {full_path}")
            
        except (configparser.Error, IOError) as e:
            log(launcher, f"Error parsing Firefox profiles.ini at {profiles_ini_path}: {e}", "error")
    
    if not profiles:
        log(launcher, "No valid Firefox profiles found", "warn")
    else:
        log(launcher, f"Found {len(profiles)} Firefox profile(s)")
        
    return profiles

def find_chrome_profiles(launcher):
    """
    Finds Google Chrome profiles by reading the Local State file.
    Returns a list of tuples: (display_name, profile_directory)
    """
    profiles = []
    try:
        chrome_config_path = Path.home() / ".config/google-chrome"
        local_state_path = chrome_config_path / "Local State"
        
        if not chrome_config_path.exists():
            log(launcher, "Google Chrome config directory not found.", "warn")
            return profiles
        
        if not local_state_path.exists():
            log(launcher, "Chrome Local State file not found.", "warn")
            return profiles

        # Read the Local State JSON file to get profile names
        with open(local_state_path, 'r') as f:
            local_state = json.load(f)
        
        # Extract profile information
        profile_info = local_state.get('profile', {}).get('info_cache', {})
        
        for profile_dir, info in profile_info.items():
            profile_name = info.get('name', profile_dir)
            # Verify the profile directory exists
            profile_path = chrome_config_path / profile_dir
            if profile_path.exists():
                profiles.append((profile_name, profile_dir))
                log(launcher, f"Found Chrome profile: {profile_name} ({profile_dir})")
        
        if not profiles:
            log(launcher, "No Chrome profiles found in Local State", "warn")
        else:
            log(launcher, f"Found {len(profiles)} Chrome profile(s)")
            
    except (json.JSONDecodeError, IOError, KeyError) as e:
        log(launcher, f"Error reading Chrome profiles: {e}", "error")
    
    return profiles

# --- Core Action Functions ---

def launch_firefox_profile(launcher, profile_name, profile_path, profiles_ini_dir):
    """Launches Firefox with a specific profile."""
    try:
        # Detect if this is a Snap install
        is_snap = 'snap/firefox' in profiles_ini_dir
        
        if is_snap:
            # For Snap Firefox, we need to use the profile name
            command = ["firefox", "-P", profile_name, "--new-instance"]
            log(launcher, f"Launching Snap Firefox with profile '{profile_name}'")
        else:
            # For traditional Firefox, we can also use profile name
            command = ["firefox", "-P", profile_name, "--new-instance"]
            log(launcher, f"Launching Firefox with profile '{profile_name}'")
        
        subprocess.Popen(
            command,
            start_new_session=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        log(launcher, f"Successfully launched Firefox with profile '{profile_name}'")
        
    except (FileNotFoundError, OSError) as e:
        error_message = f"Failed to launch Firefox: {e}. Please ensure it is installed and in your PATH."
        log(launcher, error_message, "error")

def launch_chrome_profile(launcher, profile_name, profile_directory):
    """Launches Chrome with a specific profile."""
    try:
        # Chrome uses --profile-directory with the directory name (e.g., "Default", "Profile 1")
        command = [
            "google-chrome",
            f"--profile-directory={profile_directory}"
        ]
        log(launcher, f"Launching Chrome with profile '{profile_name}' (directory: {profile_directory})")
        
        subprocess.Popen(
            command,
            start_new_session=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        log(launcher, f"Successfully launched Chrome with profile '{profile_name}'")
        
    except (FileNotFoundError, OSError) as e:
        error_message = f"Failed to launch Chrome: {e}. Please ensure it is installed and in your PATH."
        log(launcher, error_message, "error")

def launch_ssh_in_terminal(launcher):
    """Launches the pre-configured SSH command in a new gnome-terminal window."""
    if not shutil.which("gnome-terminal"):
        error_message = "gnome-terminal is not installed. Cannot launch SSH session."
        log(launcher, error_message, "error")
        return

    try:
        # This command opens a new terminal and runs the SSH command.
        # The `exec bash` ensures the terminal stays open after the SSH command exits.
        command = ["gnome-terminal", "--", "bash", "-c", f"{SSH_CONNECTION_STRING}; exec bash"]
        log(launcher, f"Launching SSH session: {SSH_CONNECTION_STRING}")
        subprocess.Popen(command, start_new_session=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        log(launcher, "Successfully launched SSH session in new terminal.")
    except (FileNotFoundError, OSError) as e:
        error_message = f"Failed to launch gnome-terminal: {e}."
        log(launcher, error_message, "error")

# --- UI Setup ---

def create_tab(notebook, launcher):
    """Creates and configures the UI for the Infrasven tab."""
    tab = ttk.Frame(notebook, padding="10")
    notebook.add(tab, text=TAB_TITLE)

    tab.columnconfigure(0, weight=1)
    tab.columnconfigure(1, weight=1)

    # --- Firefox Profiles Section ---
    firefox_frame = ttk.LabelFrame(tab, text="Firefox Profiles", padding="10")
    firefox_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 5), pady=(0, 10))
    firefox_frame.columnconfigure(0, weight=1)

    if shutil.which("firefox"):
        ff_profiles = find_firefox_profiles(launcher)
        if ff_profiles:
            for i, (profile_name, profile_path, profiles_dir) in enumerate(ff_profiles):
                # Show Snap indicator if applicable
                display_text = f"🦊 {profile_name}"
                if 'snap' in profiles_dir:
                    display_text += " (Snap)"
                
                btn = ttk.Button(
                    firefox_frame,
                    text=display_text,
                    command=lambda pn=profile_name, pp=profile_path, pd=profiles_dir: 
                        launch_firefox_profile(launcher, pn, pp, pd)
                )
                btn.grid(row=i, column=0, sticky="ew", pady=2)
        else:
            ttk.Label(firefox_frame, text="No Firefox profiles found.").pack()
    else:
        ttk.Label(firefox_frame, text="Firefox executable not found.").pack()

    # --- Chrome Profiles Section ---
    chrome_frame = ttk.LabelFrame(tab, text="Chrome Profiles", padding="10")
    chrome_frame.grid(row=0, column=1, sticky="nsew", padx=(5, 0), pady=(0, 10))
    chrome_frame.columnconfigure(0, weight=1)

    if shutil.which("google-chrome"):
        ch_profiles = find_chrome_profiles(launcher)
        if ch_profiles:
            for i, (profile_name, profile_dir) in enumerate(ch_profiles):
                btn = ttk.Button(
                    chrome_frame,
                    text=f"🔵 {profile_name}",
                    command=lambda pn=profile_name, pd=profile_dir: launch_chrome_profile(launcher, pn, pd)
                )
                btn.grid(row=i, column=0, sticky="ew", pady=2)
        else:
            ttk.Label(chrome_frame, text="No Chrome profiles found.").pack()
    else:
        ttk.Label(chrome_frame, text="Google Chrome executable not found.").pack()

    # --- SSH Launcher Section ---
    ssh_frame = ttk.LabelFrame(tab, text="SSH Connections", padding="10")
    ssh_frame.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(10, 0))
    ssh_frame.columnconfigure(0, weight=1)

    ssh_button = ttk.Button(
        ssh_frame,
        text="🔐 Connect to Hostinger Infra",
        command=lambda: launch_ssh_in_terminal(launcher)
    )
    ssh_button.grid(row=0, column=0, sticky="ew", pady=5)