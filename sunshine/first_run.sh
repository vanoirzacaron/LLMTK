#!/bin/bash
# Sunshine First Run & Configuration Guide
# Location: ~/LLMTK/sunshine/first_run.sh

set -e

echo "=== Sunshine Post-Installation Setup ==="
echo ""

# ============================================================================
# Step 1: Verify Installation
# ============================================================================

echo "Step 1: Verifying installation..."
echo ""

if command -v sunshine &> /dev/null; then
    SUNSHINE_BIN=$(which sunshine)
    echo "✓ Sunshine installed: $SUNSHINE_BIN"
    
    # Try version (may not work, that's OK)
    sunshine --version 2>/dev/null || echo "  (Version check skipped)"
else
    echo "❌ Sunshine not found in PATH"
    echo "   Check if installation completed successfully"
    exit 1
fi

echo ""

# ============================================================================
# Step 2: Check Configuration Directory
# ============================================================================

echo "Step 2: Checking configuration directory..."
echo ""

CONFIG_DIR=~/.config/sunshine
if [ ! -d "$CONFIG_DIR" ]; then
    echo "  Creating config directory: $CONFIG_DIR"
    mkdir -p "$CONFIG_DIR"
fi

echo "✓ Config directory: $CONFIG_DIR"
echo ""

# ============================================================================
# Step 3: Set Up Permissions (Important for input capture)
# ============================================================================

echo "Step 3: Setting up permissions for input capture..."
echo ""

# Add user to input group (needed for virtual gamepads)
if ! groups | grep -q input; then
    echo "  Adding $USER to 'input' group..."
    sudo usermod -a -G input "$USER"
    echo "  ✓ Added (requires logout/login to take effect)"
    NEED_RELOGIN=true
else
    echo "  ✓ Already in 'input' group"
fi

# Check uinput module
if [ ! -e /dev/uinput ]; then
    echo "  Loading uinput kernel module..."
    sudo modprobe uinput
    echo "  ✓ uinput module loaded"
    
    # Make it persistent
    if ! grep -q "^uinput" /etc/modules 2>/dev/null; then
        echo "  Making uinput load at boot..."
        echo "uinput" | sudo tee -a /etc/modules > /dev/null
        echo "  ✓ Added to /etc/modules"
    fi
else
    echo "  ✓ /dev/uinput exists"
fi

# Set udev rules for uinput
UDEV_RULE="/etc/udev/rules.d/85-sunshine-input.rules"
if [ ! -f "$UDEV_RULE" ]; then
    echo "  Creating udev rule for uinput access..."
    echo 'KERNEL=="uinput", SUBSYSTEM=="misc", TAG+="uaccess", OPTIONS+="static_node=uinput"' | sudo tee "$UDEV_RULE" > /dev/null
    sudo udevadm control --reload-rules
    sudo udevadm trigger
    echo "  ✓ udev rule created"
else
    echo "  ✓ udev rule exists"
fi

echo ""

# ============================================================================
# Step 4: Firewall Configuration
# ============================================================================

echo "Step 4: Checking firewall..."
echo ""

if command -v ufw &> /dev/null && sudo ufw status | grep -q "Status: active"; then
    echo "  UFW firewall is active"
    
    # Check if Sunshine ports are open
    if ! sudo ufw status | grep -q "47984\|47989\|47990\|48010"; then
        echo "  Opening Sunshine ports..."
        sudo ufw allow 47984:48010/tcp comment "Sunshine"
        sudo ufw allow 47998:48010/udp comment "Sunshine"
        echo "  ✓ Ports opened"
    else
        echo "  ✓ Sunshine ports already open"
    fi
else
    echo "  ✓ UFW not active or not installed"
fi

echo ""

# ============================================================================
# Step 5: Service Setup (Optional)
# ============================================================================

echo "Step 5: Service configuration (optional)..."
echo ""

echo "Sunshine can run as:"
echo "  a) Manual launch (sunshine command)"
echo "  b) User service (auto-start on login)"
echo "  c) System service (always running)"
echo ""

read -p "Enable auto-start? (y/N): " -n 1 -r
echo

if [[ $REPLY =~ ^[Yy]$ ]]; then
    # Create user service
    SERVICE_DIR=~/.config/systemd/user
    mkdir -p "$SERVICE_DIR"
    
    cat > "$SERVICE_DIR/sunshine.service" << 'EOF'
[Unit]
Description=Sunshine Game Streaming Server
After=graphical-session.target

[Service]
Type=simple
ExecStart=/usr/local/bin/sunshine
Restart=on-failure
RestartSec=5

[Install]
WantedBy=default.target
EOF
    
    # Enable and start
    systemctl --user daemon-reload
    systemctl --user enable sunshine
    echo "  ✓ User service enabled (will start on next login)"
    
    read -p "Start Sunshine now? (Y/n): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Nn]$ ]]; then
        systemctl --user start sunshine
        sleep 2
        if systemctl --user is-active --quiet sunshine; then
            echo "  ✓ Sunshine started successfully"
        else
            echo "  ⚠️  Service failed to start. Check: systemctl --user status sunshine"
        fi
    fi
else
    echo "  Skipped auto-start setup"
fi

echo ""

# ============================================================================
# Summary
# ============================================================================

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "                    ✅ SUNSHINE READY!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "🌐 Web Interface"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "1. Start Sunshine (if not running):"
if systemctl --user is-active --quiet sunshine 2>/dev/null; then
    echo "   ✓ Already running as service"
else
    echo "   sunshine"
fi
echo ""
echo "2. Open web UI in browser:"
echo "   https://localhost:47990"
echo ""
echo "   ⚠️  You'll see a certificate warning - this is normal"
echo "       Click 'Advanced' → 'Proceed' (or similar)"
echo ""
echo "3. First-time setup:"
echo "   • Create username and password"
echo "   • This becomes your admin account"
echo ""

echo "⚙️  Configuration for RTX 3060"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "Recommended settings in web UI:"
echo ""
echo "Video:"
echo "  • Encoder: NVIDIA NVENC H.264"
echo "  • Resolution: 3440x1440 (match your monitor)"
echo "  • Bitrate: 30-50 Mbps (adjust for your network)"
echo "  • Frame rate: 60 FPS"
echo ""
echo "Audio:"
echo "  • Codec: Opus"
echo "  • Bitrate: 128-256 kbps"
echo ""
echo "Network:"
echo "  • Port: 47989 (default)"
echo "  • UPnP: Enable (if using router port forwarding)"
echo ""

echo "📱 Pairing Moonlight Client"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "1. Install Moonlight on your client device:"
echo "   • Android: Play Store"
echo "   • iOS: App Store"
echo "   • Windows/Mac/Linux: moonlight-stream.org"
echo ""
echo "2. On the client, add PC:"
echo "   • Enter this PC's IP address"
echo "   • Enter PIN shown in Sunshine web UI"
echo ""
echo "3. Start streaming:"
echo "   • Select an application from the list"
echo "   • Enjoy low-latency game streaming!"
echo ""

echo "🖥️  Virtual Display Setup"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "For headless streaming (virtual display):"
echo ""
echo "1. Set up virtual display workflow:"
echo "   cd ~/LLMTK/apollo"
echo "   bash x11_complete_workflow.sh"
echo ""
echo "2. After reboot, run:"
echo "   ~/LLMTK/apollo/run_sunshine.sh"
echo ""
echo "This will:"
echo "  • Disable your physical monitor"
echo "  • Enable 1920x1080 virtual display"
echo "  • Run Sunshine on the virtual display"
echo "  • Restore your monitor when you press Ctrl+C"
echo ""

echo "📋 Useful Commands"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "Start/stop service:"
echo "  systemctl --user start sunshine"
echo "  systemctl --user stop sunshine"
echo "  systemctl --user restart sunshine"
echo ""
echo "Check status:"
echo "  systemctl --user status sunshine"
echo ""
echo "View logs:"
echo "  journalctl --user -u sunshine -f"
echo ""
echo "Config files:"
echo "  ~/.config/sunshine/"
echo ""

if [ "${NEED_RELOGIN:-false}" = true ]; then
    echo "⚠️  IMPORTANT"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
    echo "You were added to the 'input' group."
    echo "Please log out and log back in for changes to take effect."
    echo ""
fi

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "🎮 Ready to stream! Open https://localhost:47990 to begin"
echo ""
