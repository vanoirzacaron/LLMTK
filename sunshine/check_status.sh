#!/bin/bash
# Sunshine Setup Status Checker
# Location: ~/LLMTK/sunshine/check_status.sh

echo "=== Sunshine Setup Status Check ==="
echo ""

# Check 1: Session Type
echo "1. Display Server:"
SESSION_TYPE=$(loginctl show-session $(loginctl | grep $(whoami) | awk '{print $1}') -p Type | cut -d= -f2)
if [ "$SESSION_TYPE" = "x11" ]; then
    echo "   ✅ X11 (Ready for virtual displays)"
elif [ "$SESSION_TYPE" = "wayland" ]; then
    echo "   ⚠️  Wayland (Virtual displays need X11)"
    echo "      Switch at login: Select 'Ubuntu on Xorg'"
else
    echo "   ❓ Unknown: $SESSION_TYPE"
fi

# Check 2: Git Submodules
echo ""
echo "2. Git Submodules:"
if [ -d ~/LLMTK/sunshine/.git ]; then
    cd ~/LLMTK/sunshine
    if [ -f "third-party/moonlight-common-c/src/Limelight.h" ]; then
        echo "   ✅ Initialized"
    else
        echo "   ❌ Not initialized"
        echo "      Run: cd ~/LLMTK/sunshine && git submodule update --init --recursive"
    fi
else
    echo "   ⚠️  Not a git repository"
    echo "      If downloaded as zip, clone instead:"
    echo "      cd ~/LLMTK && rm -rf sunshine"
    echo "      git clone --recurse-submodules https://github.com/LizardByte/Sunshine.git sunshine"
fi

# Check 3: Build Status
echo ""
echo "3. Sunshine Build:"
if [ -f ~/LLMTK/sunshine/build/sunshine ]; then
    echo "   ✅ Built"
    ~/LLMTK/sunshine/build/sunshine --version 2>/dev/null || echo "   (Version check failed)"
else
    echo "   ❌ Not built"
    echo "      Run: cd ~/LLMTK/sunshine && bash build_sunshine.sh"
fi

# Check 4: Installation
echo ""
echo "4. Sunshine Installation:"
if command -v sunshine &> /dev/null; then
    echo "   ✅ Installed system-wide"
    INSTALLED_VERSION=$(sunshine --version 2>/dev/null | head -1 || echo "unknown")
    echo "      Version: $INSTALLED_VERSION"
    echo "      Location: $(which sunshine)"
elif [ -f ~/LLMTK/sunshine/build/sunshine ]; then
    echo "   ⚠️  Built but not installed"
    echo "      Install with: cd ~/LLMTK/sunshine/build && sudo ninja install"
else
    echo "   ❌ Not installed"
fi

# Check 5: NVIDIA GPU
echo ""
echo "5. NVIDIA GPU:"
if command -v nvidia-smi &> /dev/null; then
    GPU_NAME=$(nvidia-smi --query-gpu=name --format=csv,noheader | head -1)
    DRIVER_VERSION=$(nvidia-smi --query-gpu=driver_version --format=csv,noheader | head -1)
    echo "   ✅ $GPU_NAME"
    echo "      Driver: $DRIVER_VERSION"
    
    # Check CUDA
    if command -v nvcc &> /dev/null; then
        CUDA_VERSION=$(nvcc --version | grep "release" | sed 's/.*release //' | cut -d',' -f1)
        echo "      CUDA: $CUDA_VERSION ✅"
    else
        echo "      CUDA: Not installed (optional, NVENC works without it)"
    fi
else
    echo "   ❌ NVIDIA drivers not detected"
    echo "      Install with: sudo ubuntu-drivers autoinstall"
fi

# Check 6: Display Configuration
echo ""
echo "6. Display Configuration:"
if command -v xrandr &> /dev/null && [ -n "$DISPLAY" ]; then
    CONNECTED=$(xrandr | grep " connected" | wc -l)
    PRIMARY=$(xrandr | grep "primary" | awk '{print $1}')
    echo "   Connected displays: $CONNECTED"
    echo "   Primary: $PRIMARY"
    
    # Show your ultrawide
    xrandr | grep "DP-4 connected" | head -1
else
    echo "   ⚠️  xrandr not available or not in X11"
fi

# Check 7: Virtual Display Setup
echo ""
echo "7. Virtual Display Workflow:"
if [ -f ~/LLMTK/apollo/scripts/sunshine_pre_start.sh ]; then
    echo "   ✅ Scripts created"
    echo "      Run with: ~/LLMTK/apollo/run_sunshine.sh"
else
    echo "   ❌ Not set up"
    echo "      Run: cd ~/LLMTK/apollo && bash x11_complete_workflow.sh"
fi

# Check 8: Kernel EDID Parameter
echo ""
echo "8. EDID Firmware:"
if grep -q "drm.edid_firmware" /proc/cmdline; then
    echo "   ✅ Kernel parameter configured"
    grep -o "drm.edid_firmware=[^ ]*" /proc/cmdline
else
    echo "   ❌ Not configured"
    echo "      Will be set up by x11_complete_workflow.sh"
fi

if [ -f /lib/firmware/edid/virtual_1920x1080.bin ]; then
    echo "   ✅ EDID file exists: /lib/firmware/edid/virtual_1920x1080.bin"
else
    echo "   ❌ EDID file not found"
fi

# Summary
echo ""
echo "==================================================================="
echo "                         SUMMARY"
echo "==================================================================="
echo ""

# Determine what needs to be done
NEEDS_SUBMODULES=false
NEEDS_BUILD=false
NEEDS_INSTALL=false
NEEDS_WORKFLOW=false
NEEDS_REBOOT=false

[ ! -f ~/LLMTK/sunshine/third-party/moonlight-common-c/src/Limelight.h ] && NEEDS_SUBMODULES=true
[ ! -f ~/LLMTK/sunshine/build/sunshine ] && NEEDS_BUILD=true
! command -v sunshine &> /dev/null && NEEDS_INSTALL=true
[ ! -f ~/LLMTK/apollo/scripts/sunshine_pre_start.sh ] && NEEDS_WORKFLOW=true
! grep -q "drm.edid_firmware" /proc/cmdline && NEEDS_REBOOT=true

if [ "$NEEDS_SUBMODULES" = false ] && [ "$NEEDS_BUILD" = false ] && [ "$NEEDS_INSTALL" = false ] && [ "$NEEDS_WORKFLOW" = false ] && [ "$NEEDS_REBOOT" = false ]; then
    echo "🎉 Everything is ready!"
    echo ""
    echo "Start Sunshine:"
    echo "  sunshine"
    echo ""
    echo "Or with virtual display:"
    echo "  ~/LLMTK/apollo/run_sunshine.sh"
    echo ""
    echo "Web UI: https://localhost:47990"
else
    echo "📋 Next steps:"
    echo ""
    
    STEP=1
    if [ "$NEEDS_SUBMODULES" = true ]; then
        echo "$STEP. Initialize submodules:"
        echo "   cd ~/LLMTK/sunshine"
        echo "   git submodule update --init --recursive"
        echo ""
        STEP=$((STEP+1))
    fi
    
    if [ "$NEEDS_BUILD" = true ]; then
        echo "$STEP. Build Sunshine:"
        echo "   cd ~/LLMTK/sunshine"
        echo "   bash build_sunshine.sh"
        echo ""
        STEP=$((STEP+1))
    fi
    
    if [ "$NEEDS_INSTALL" = true ]; then
        echo "$STEP. Install Sunshine:"
        echo "   cd ~/LLMTK/sunshine/build"
        echo "   sudo ninja install"
        echo ""
        STEP=$((STEP+1))
    fi
    
    if [ "$NEEDS_WORKFLOW" = true ]; then
        echo "$STEP. Set up virtual display workflow:"
        echo "   mkdir -p ~/LLMTK/apollo"
        echo "   cd ~/LLMTK/apollo"
        echo "   bash x11_complete_workflow.sh"
        echo ""
        STEP=$((STEP+1))
    fi
    
    if [ "$NEEDS_REBOOT" = true ]; then
        echo "$STEP. Reboot (after workflow setup):"
        echo "   sudo reboot"
        echo ""
    fi
fi

echo "==================================================================="
