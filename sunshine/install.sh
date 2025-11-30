#!/bin/bash
# Sunshine Build Script for Ubuntu 24.04
# Optimized for NVIDIA RTX 3060 with minimal system changes
# Location: ~/LLMTK/sunshine/build_sunshine.sh

set -e

# ============================================================================
# Configuration
# ============================================================================

SUNSHINE_DIR=~/LLMTK/sunshine
BUILD_DIR="$SUNSHINE_DIR/build"
LOG_FILE="$BUILD_DIR/build.log"

# Color output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# ============================================================================
# Helper Functions
# ============================================================================

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

check_command() {
    command -v "$1" &> /dev/null
}

# ============================================================================
# Pre-flight Checks
# ============================================================================

preflight_checks() {
    log_info "Running pre-flight checks..."
    
    # Check directory
    if [ ! -f "$SUNSHINE_DIR/CMakeLists.txt" ]; then
        log_error "Not in Sunshine source directory!"
        log_error "Expected: $SUNSHINE_DIR/CMakeLists.txt"
        exit 1
    fi
    
    # Check if git repo
    if [ ! -d "$SUNSHINE_DIR/.git" ]; then
        log_warning "Not a git repository!"
        log_warning "If you downloaded a zip, please clone instead:"
        echo "  cd ~/LLMTK && rm -rf sunshine"
        echo "  git clone --recurse-submodules https://github.com/LizardByte/Sunshine.git sunshine"
        echo ""
        read -p "Continue anyway? (y/N): " -n 1 -r
        echo
        [[ ! $REPLY =~ ^[Yy]$ ]] && exit 1
    fi
    
    log_success "Pre-flight checks passed"
}

# ============================================================================
# Git Submodules
# ============================================================================

init_submodules() {
    log_info "Checking git submodules..."
    
    cd "$SUNSHINE_DIR"
    
    if [ ! -d ".git" ]; then
        log_warning "Skipping submodule check (not a git repo)"
        return 0
    fi
    
    # Check if critical submodule exists
    if [ ! -f "third-party/moonlight-common-c/src/Limelight.h" ]; then
        log_info "Initializing git submodules (this may take a few minutes)..."
        git submodule update --init --recursive
        log_success "Submodules initialized"
    else
        log_success "Submodules already initialized"
    fi
}

# ============================================================================
# System Dependencies
# ============================================================================

install_dependencies() {
    log_info "Installing build dependencies..."
    
    # List of required packages
    local packages=(
        # Build tools
        build-essential
        cmake
        ninja-build
        git
        pkg-config
        
        # Core libraries
        libssl-dev
        libcurl4-openssl-dev
        
        # Boost libraries
        libboost-filesystem-dev
        libboost-locale-dev
        libboost-log-dev
        libboost-program-options-dev
        libboost-thread-dev
        
        # System libraries
        libcap-dev
        libdrm-dev
        libevdev-dev
        libnuma-dev
        udev
        
        # Audio/Video
        libopus-dev
        libpulse-dev
        libva-dev
        libvdpau-dev
        
        # Display server support
        libwayland-dev
        libx11-dev
        libxcb-shm0-dev
        libxcb-xfixes0-dev
        libxcb1-dev
        libxfixes-dev
        libxrandr-dev
        libxtst-dev
        
        # Web UI
        nodejs
        npm
        
        # Utilities
        wget
    )
    
    log_info "Updating package lists..."
    sudo apt-get update -qq
    
    log_info "Installing ${#packages[@]} packages..."
    sudo apt-get install -y "${packages[@]}" 2>&1 | grep -v "is already the newest version" || true
    
    log_success "Dependencies installed"
}

# ============================================================================
# NVIDIA CUDA Support
# ============================================================================

check_cuda_support() {
    log_info "Checking NVIDIA CUDA support..."
    
    # Check if NVIDIA GPU exists
    if ! check_command nvidia-smi; then
        log_warning "NVIDIA driver not detected"
        echo "CUDA_ENABLED=OFF"
        return 0
    fi
    
    local gpu_name=$(nvidia-smi --query-gpu=name --format=csv,noheader 2>/dev/null | head -1)
    local driver_version=$(nvidia-smi --query-gpu=driver_version --format=csv,noheader 2>/dev/null | head -1)
    
    log_success "NVIDIA GPU detected: $gpu_name"
    log_info "Driver version: $driver_version"
    
    # Check if CUDA toolkit is installed
    if check_command nvcc; then
        local cuda_version=$(nvcc --version | grep "release" | sed 's/.*release //' | cut -d',' -f1)
        log_success "CUDA toolkit found: $cuda_version"
        echo "CUDA_ENABLED=ON"
        return 0
    fi
    
    # Offer to install CUDA toolkit
    log_warning "CUDA toolkit not installed"
    log_info "NVENC hardware encoding will still work via runtime linking"
    log_info "Installing CUDA toolkit provides build-time optimization"
    echo ""
    read -p "Install CUDA toolkit? (y/N): " -n 1 -r
    echo
    
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        log_info "Installing nvidia-cuda-toolkit..."
        sudo apt-get install -y nvidia-cuda-toolkit
        log_success "CUDA toolkit installed"
        echo "CUDA_ENABLED=ON"
    else
        log_info "Building without CUDA toolkit"
        echo "CUDA_ENABLED=OFF"
    fi
}

# ============================================================================
# Build Configuration
# ============================================================================

configure_build() {
    log_info "Configuring build with CMake..."
    
    # Get CUDA setting
    local cuda_setting=$(check_cuda_support)
    local enable_cuda=$(echo "$cuda_setting" | grep "CUDA_ENABLED" | cut -d'=' -f2)
    
    # Clean and create build directory
    log_info "Preparing build directory..."
    rm -rf "$BUILD_DIR"
    mkdir -p "$BUILD_DIR"
    cd "$BUILD_DIR"
    
    # Display configuration
    echo ""
    log_info "Build configuration:"
    echo "  Build type: Release"
    echo "  Install prefix: /usr/local"
    echo "  Wayland support: ON"
    echo "  X11 support: ON"
    echo "  DRM/KMS support: ON"
    echo "  CUDA/NVENC: $enable_cuda"
    echo ""
    
    # Run CMake with documentation disabled (not needed for runtime)
    cmake .. \
        -G Ninja \
        -DCMAKE_BUILD_TYPE=Release \
        -DCMAKE_INSTALL_PREFIX=/usr/local \
        -DSUNSHINE_ENABLE_WAYLAND=ON \
        -DSUNSHINE_ENABLE_X11=ON \
        -DSUNSHINE_ENABLE_DRM=ON \
        -DSUNSHINE_ENABLE_CUDA="$enable_cuda" \
        -DSUNSHINE_BUILD_WERROR=OFF \
        -DBUILD_DOCS=OFF \
        2>&1 | tee "$LOG_FILE"
    
    local cmake_exit=${PIPESTATUS[0]}
    
    if [ $cmake_exit -eq 0 ]; then
        log_success "CMake configuration complete"
    else
        log_error "CMake configuration failed!"
        log_error "Check log: $LOG_FILE"
        exit 1
    fi
}

# ============================================================================
# Build
# ============================================================================

build_sunshine() {
    log_info "Building Sunshine..."
    
    cd "$BUILD_DIR"
    
    # Get CPU count for parallel build
    local cpu_count=$(nproc)
    log_info "Building with $cpu_count parallel jobs"
    
    # Estimate build time
    echo ""
    log_info "Estimated build time: 5-15 minutes depending on CPU"
    log_info "Build log: $LOG_FILE"
    echo ""
    
    # Build
    if ninja -j"$cpu_count" 2>&1 | tee -a "$LOG_FILE"; then
        log_success "Build completed successfully!"
    else
        log_error "Build failed!"
        echo ""
        log_error "Common issues:"
        echo "  1. Missing submodules: git submodule update --init --recursive"
        echo "  2. Missing dependencies: Check error messages above"
        echo "  3. Boost version mismatch: Ubuntu 24.04 should be compatible"
        echo ""
        log_error "Full log: $LOG_FILE"
        exit 1
    fi
}

# ============================================================================
# Verification
# ============================================================================

verify_build() {
    log_info "Verifying build..."
    
    if [ ! -f "$BUILD_DIR/sunshine" ]; then
        log_error "Sunshine binary not found!"
        exit 1
    fi
    
    # Test binary
    log_info "Testing binary..."
    if "$BUILD_DIR/sunshine" --version > /dev/null 2>&1; then
        log_success "Binary verification passed"
        echo ""
        "$BUILD_DIR/sunshine" --version
    else
        log_warning "Binary exists but version check failed (may be normal)"
    fi
}

# ============================================================================
# Post-Build Instructions
# ============================================================================

show_next_steps() {
    echo ""
    echo "==================================================================="
    log_success "BUILD COMPLETE! 🎉"
    echo "==================================================================="
    echo ""
    echo "Binary location: $BUILD_DIR/sunshine"
    echo "Build log: $LOG_FILE"
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "                    INSTALLATION OPTIONS"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
    echo "1. Install system-wide (recommended):"
    echo "   ${BLUE}cd $BUILD_DIR${NC}"
    echo "   ${BLUE}sudo ninja install${NC}"
    echo ""
    echo "2. Run from build directory (testing):"
    echo "   ${BLUE}cd $BUILD_DIR${NC}"
    echo "   ${BLUE}./sunshine${NC}"
    echo ""
    echo "3. Enable as system service (auto-start):"
    echo "   ${BLUE}sudo ninja install${NC}"
    echo "   ${BLUE}sudo systemctl enable --now sunshine${NC}"
    echo ""
    echo "4. Enable as user service (no root access needed):"
    echo "   ${BLUE}sudo ninja install${NC}"
    echo "   ${BLUE}systemctl --user enable --now sunshine${NC}"
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "                    CONFIGURATION"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
    echo "After installation:"
    echo ""
    echo "1. Access web UI:"
    echo "   ${BLUE}https://localhost:47990${NC}"
    echo "   (Accept self-signed certificate warning)"
    echo ""
    echo "2. First-time setup:"
    echo "   - Create username and password"
    echo "   - Configure your RTX 3060 settings"
    echo "   - Add applications to stream"
    echo ""
    echo "3. Recommended settings for RTX 3060:"
    echo "   - Encoder: NVIDIA NVENC H.264/H.265"
    echo "   - Resolution: 3440x1440 (or match client)"
    echo "   - Bitrate: 20-50 Mbps (adjust for network)"
    echo "   - Frame rate: 60 FPS"
    echo ""
    echo "4. Pair Moonlight client:"
    echo "   - Install Moonlight on your client device"
    echo "   - Enter the PIN shown in Sunshine web UI"
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "                    VIRTUAL DISPLAY SETUP"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
    echo "To set up virtual display (for headless streaming):"
    echo ""
    echo "1. Run the workflow setup:"
    echo "   ${BLUE}mkdir -p ~/LLMTK/apollo${NC}"
    echo "   ${BLUE}cd ~/LLMTK/apollo${NC}"
    echo "   ${BLUE}bash x11_complete_workflow.sh${NC}"
    echo ""
    echo "2. Reboot (required for EDID loading)"
    echo ""
    echo "3. Test virtual display:"
    echo "   ${BLUE}~/LLMTK/apollo/run_sunshine.sh${NC}"
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
    log_info "Your system was NOT changed (still running: $XDG_SESSION_TYPE)"
    log_info "X11 session detected - virtual displays will work!"
    echo ""
    echo "==================================================================="
}

# ============================================================================
# Main Execution
# ============================================================================

main() {
    echo "==================================================================="
    echo "        Sunshine Build Script for Ubuntu 24.04"
    echo "        Optimized for NVIDIA RTX 3060"
    echo "==================================================================="
    echo ""
    
    cd "$SUNSHINE_DIR" || {
        log_error "Cannot access $SUNSHINE_DIR"
        exit 1
    }
    
    preflight_checks
    init_submodules
    install_dependencies
    configure_build
    build_sunshine
    verify_build
    show_next_steps
}

# Run main function
main "$@"
