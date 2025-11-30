#!/bin/bash
# Fix frozen npm install
# Location: ~/LLMTK/sunshine/fix_npm.sh

set -e

SUNSHINE_DIR=~/LLMTK/sunshine

echo "=== Fixing Frozen npm install ==="
echo ""

cd "$SUNSHINE_DIR"

# Kill any stuck npm processes
echo "1. Killing any stuck npm processes..."
pkill -9 npm || true
pkill -9 node || true
sleep 2
echo "✓ Processes cleared"
echo ""

# Clean npm cache
echo "2. Cleaning npm cache..."
npm cache clean --force
echo "✓ Cache cleaned"
echo ""

# Remove lock files and node_modules
echo "3. Removing old installation files..."
rm -rf node_modules package-lock.json .npm
echo "✓ Old files removed"
echo ""

# Verify Node.js version
echo "4. Verifying Node.js version..."
NODE_VERSION=$(node -v)
echo "   Node.js: $NODE_VERSION"
NPM_VERSION=$(npm -v)
echo "   npm: $NPM_VERSION"
echo ""

NODE_MAJOR=$(echo "$NODE_VERSION" | cut -d'v' -f2 | cut -d'.' -f1)
if [ "$NODE_MAJOR" -lt 20 ]; then
    echo "❌ Node.js version too old (need 20+)"
    echo ""
    echo "Upgrade with:"
    echo "  curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -"
    echo "  sudo apt-get install -y nodejs"
    exit 1
fi
echo "✓ Node.js version OK"
echo ""

# Try install with verbose output and timeout
echo "5. Installing npm packages (with verbose output)..."
echo "   (This will show what's happening)"
echo ""

# Set npm to use verbose mode and reasonable timeout
npm install --verbose --fetch-timeout=60000 --fetch-retries=3 2>&1 | tee npm_install.log

if [ ${PIPESTATUS[0]} -eq 0 ]; then
    echo ""
    echo "✓ npm packages installed successfully"
    echo ""
    echo "Installed packages:"
    npm list --depth=0
else
    echo ""
    echo "❌ npm install failed"
    echo ""
    echo "Check log: $SUNSHINE_DIR/npm_install.log"
    echo ""
    echo "Common fixes:"
    echo "1. Network issues: Check internet connection"
    echo "2. Registry timeout: npm config set registry https://registry.npmjs.org/"
    echo "3. Try with different network"
    echo "4. Use npm ci instead: npm ci --verbose"
    exit 1
fi
