#!/bin/bash
# Fix static libstdc++ linking error in Sunshine
# Error: "referência indefinida a símbolo" with GLIBCXX_3.4.31
# Location: ~/LLMTK/sunshine/fix_linking.sh

set -e

SUNSHINE_DIR=~/LLMTK/sunshine
BUILD_DIR="$SUNSHINE_DIR/build"

echo "=== Fixing Static Linking Error ==="
echo ""

cd "$SUNSHINE_DIR"

# The issue: CMake is forcing -static-libgcc -static-libstdc++
# Solution: Patch the CMakeLists.txt to remove these flags

echo "Step 1: Backing up CMakeLists.txt..."
cp CMakeLists.txt CMakeLists.txt.backup
echo "✓ Backup created: CMakeLists.txt.backup"
echo ""

echo "Step 2: Removing static stdlib linking flags..."

# Find and comment out the static linking lines
sed -i 's/^\(.*-static-libgcc.*\)$/# \1  # Disabled for Ubuntu compatibility/' CMakeLists.txt
sed -i 's/^\(.*-static-libstdc++.*\)$/# \1  # Disabled for Ubuntu compatibility/' CMakeLists.txt

# Alternative: use more aggressive find/replace if above doesn't work
grep -n "static-lib" CMakeLists.txt || echo "No static-lib flags found in top-level CMakeLists.txt"

# Check if it worked
if grep -q "static-libstdc++" CMakeLists.txt | grep -v "^#"; then
    echo "⚠️  Warning: Some static flags may remain"
fi

echo "✓ Static linking flags removed/commented"
echo ""

echo "Step 3: Reconfiguring build..."
cd "$BUILD_DIR"

# Detect previous CUDA setting
if [ -f build.log ] && grep -q "CUDA Compiler Version" build.log; then
    ENABLE_CUDA=ON
    echo "  CUDA: Enabled (detected from previous build)"
else
    ENABLE_CUDA=OFF
    echo "  CUDA: Disabled"
fi

# Reconfigure without cleaning (preserve compiled objects)
cmake .. \
    -G Ninja \
    -DCMAKE_BUILD_TYPE=Release \
    -DCMAKE_INSTALL_PREFIX=/usr/local \
    -DSUNSHINE_ENABLE_WAYLAND=ON \
    -DSUNSHINE_ENABLE_X11=ON \
    -DSUNSHINE_ENABLE_DRM=ON \
    -DSUNSHINE_ENABLE_CUDA=$ENABLE_CUDA \
    -DSUNSHINE_BUILD_WERROR=OFF \
    -DBUILD_DOCS=OFF \
    -DCMAKE_CXX_FLAGS="-O3" \
    -DCMAKE_EXE_LINKER_FLAGS=""

echo ""
echo "✓ Build reconfigured with dynamic linking"
echo ""

echo "Step 4: Rebuilding (only linking needs to be redone)..."
echo ""

if ninja 2>&1 | tee build_fixed.log; then
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "                    ✅ BUILD SUCCESSFUL!"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
    echo "Binary: $BUILD_DIR/sunshine"
    echo ""
    
    # Test binary
    if [ -f sunshine ]; then
        echo "Testing binary..."
        ldd sunshine | head -20
        echo ""
        
        # Check dependencies
        if ldd sunshine | grep -q "not found"; then
            echo "⚠️  Warning: Some dependencies missing"
            ldd sunshine | grep "not found"
        else
            echo "✓ All dependencies satisfied"
        fi
        
        echo ""
        echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        echo "                    INSTALLATION"
        echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        echo ""
        echo "Install system-wide:"
        echo "  cd $BUILD_DIR"
        echo "  sudo ninja install"
        echo ""
        echo "Or test without installing:"
        echo "  cd $BUILD_DIR"
        echo "  ./sunshine"
        echo ""
        echo "Web UI will be at: https://localhost:47990"
        echo ""
    fi
else
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "                    ❌ BUILD FAILED"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
    echo "The static linking patch didn't work."
    echo ""
    echo "Try the nuclear option (full clean rebuild):"
    echo "  cd ~/LLMTK/sunshine"
    echo "  bash nuclear_rebuild.sh"
    echo ""
    exit 1
fi
