#!/bin/bash

# Simple .deb package builder for VPN3GUI
# This creates a basic .deb without the full Debian build system

set -e

VERSION="1.0.0"
ARCH="all"
PACKAGE="vpn3gui"

echo "Simple VPN3GUI Package Builder"
echo "=============================="
echo ""

# Create package directory structure
echo "Creating package structure..."
rm -rf pkg-build
mkdir -p pkg-build/${PACKAGE}/DEBIAN
mkdir -p pkg-build/${PACKAGE}/usr/bin
mkdir -p pkg-build/${PACKAGE}/usr/share/applications
mkdir -p pkg-build/${PACKAGE}/usr/share/doc/${PACKAGE}

# Copy files
echo "Copying files..."
cp vpn3gui.py pkg-build/${PACKAGE}/usr/bin/vpn3gui
chmod 755 pkg-build/${PACKAGE}/usr/bin/vpn3gui

cp vpn3gui.desktop pkg-build/${PACKAGE}/usr/share/applications/
cp README.md pkg-build/${PACKAGE}/usr/share/doc/${PACKAGE}/

# Create control file
cat > pkg-build/${PACKAGE}/DEBIAN/control << EOF
Package: ${PACKAGE}
Version: ${VERSION}
Architecture: ${ARCH}
Maintainer: VPN3GUI Contributors <noreply@example.com>
Depends: python3 (>= 3.6), python3-gi, python3-gi-cairo, gir1.2-gtk-3.0
Recommends: openvpn3, python3-keyring, python3-secretstorage, gnome-keyring
Section: net
Priority: optional
Homepage: https://github.com/rjeffmyers/vpn3gui
Description: GUI for OpenVPN3 on Linux
 VPN3GUI is a modern GTK+ interface for OpenVPN3 that provides:
 - Easy VPN connection management
 - Secure credential storage
 - Configuration import
 - Real-time status monitoring
EOF

# Create postinst script
cat > pkg-build/${PACKAGE}/DEBIAN/postinst << 'EOF'
#!/bin/sh
set -e

# Update desktop database
if which update-desktop-database >/dev/null 2>&1 ; then
    update-desktop-database -q /usr/share/applications 2>/dev/null || true
fi

# Check for OpenVPN3
if ! which openvpn3 >/dev/null 2>&1 ; then
    echo ""
    echo "==========================================="
    echo "NOTE: OpenVPN3 is not installed"
    echo "==========================================="
    echo "Run VPN3GUI and use Tools -> Install OpenVPN3"
    echo "Or install manually: sudo apt install openvpn3"
    echo ""
fi

exit 0
EOF

chmod 755 pkg-build/${PACKAGE}/DEBIAN/postinst

# Build the package
echo "Building package..."
dpkg-deb --build pkg-build/${PACKAGE}

# Move to parent directory with proper name
mv pkg-build/${PACKAGE}.deb ${PACKAGE}_${VERSION}_${ARCH}.deb

echo ""
echo "✓ Package built successfully!"
echo ""
echo "Package created: ${PACKAGE}_${VERSION}_${ARCH}.deb"
echo ""
echo "To install:"
echo "  sudo dpkg -i ${PACKAGE}_${VERSION}_${ARCH}.deb"
echo "  sudo apt install -f  # (if needed to fix dependencies)"
echo ""
echo "To remove:"
echo "  sudo apt remove ${PACKAGE}"
echo ""

# Clean up
rm -rf pkg-build