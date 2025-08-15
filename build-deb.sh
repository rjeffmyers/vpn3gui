#!/bin/bash

# VPN3GUI Debian Package Builder
# This script builds a .deb package for VPN3GUI

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}VPN3GUI Debian Package Builder${NC}"
echo "================================"
echo ""

# Check for required tools
echo "Checking build dependencies..."

MISSING_DEPS=""

if ! command -v dpkg-buildpackage &> /dev/null; then
    MISSING_DEPS="$MISSING_DEPS dpkg-dev"
fi

if ! command -v debhelper &> /dev/null; then
    MISSING_DEPS="$MISSING_DEPS debhelper"
fi

if ! command -v dh_python3 &> /dev/null; then
    MISSING_DEPS="$MISSING_DEPS dh-python"
fi

if [ ! -z "$MISSING_DEPS" ]; then
    echo -e "${YELLOW}Missing build dependencies:${NC}$MISSING_DEPS"
    echo ""
    echo "Install them with:"
    echo -e "${GREEN}sudo apt install$MISSING_DEPS${NC}"
    echo ""
    read -p "Would you like to install them now? (y/N) " -n 1 -r
    echo ""
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        sudo apt update
        sudo apt install -y $MISSING_DEPS
    else
        echo -e "${RED}Cannot continue without build dependencies${NC}"
        exit 1
    fi
fi

# Clean previous builds
echo "Cleaning previous builds..."
rm -rf debian/vpn3gui
rm -f ../vpn3gui_*.deb
rm -f ../vpn3gui_*.dsc
rm -f ../vpn3gui_*.tar.*
rm -f ../vpn3gui_*.changes
rm -f ../vpn3gui_*.buildinfo

# Create source format file
echo "3.0 (native)" > debian/source/format
mkdir -p debian/source

# Build the package
echo ""
echo "Building package..."
echo ""

# Option 1: Build unsigned package (no GPG key required)
if dpkg-buildpackage -us -uc -b; then
    echo ""
    echo -e "${GREEN}✓ Package built successfully!${NC}"
    echo ""
    echo "Package created:"
    ls -la ../vpn3gui_*.deb
    echo ""
    echo "To install the package:"
    echo -e "${GREEN}sudo dpkg -i ../vpn3gui_*.deb${NC}"
    echo ""
    echo "If there are dependency issues, fix with:"
    echo -e "${GREEN}sudo apt install -f${NC}"
    echo ""
else
    echo ""
    echo -e "${RED}✗ Build failed${NC}"
    echo ""
    echo "Common issues:"
    echo "1. Missing build dependencies - install with:"
    echo "   sudo apt install dpkg-dev debhelper dh-python"
    echo ""
    echo "2. For a simpler build, you can also try:"
    echo "   dpkg-deb --build debian/vpn3gui ../vpn3gui_1.0.0_all.deb"
    exit 1
fi

# Optional: Lint the package
if command -v lintian &> /dev/null; then
    echo "Running lintian checks..."
    lintian ../vpn3gui_*.deb || true
    echo ""
fi

echo -e "${GREEN}Build complete!${NC}"