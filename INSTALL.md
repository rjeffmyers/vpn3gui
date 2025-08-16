# Installation Guide for VPN3GUI

## Quick Install from .deb Package

### Download Latest Release
Visit the [Releases Page](https://github.com/rjeffmyers/vpn3gui/releases) and download the latest `.deb` package.

### Install via Command Line
```bash
# Download the latest release
wget https://github.com/rjeffmyers/vpn3gui/releases/latest/download/vpn3gui_1.0.2_all.deb

# Install the package
sudo dpkg -i vpn3gui_1.0.2_all.deb

# Fix any dependency issues
sudo apt install -f
```

### One-Line Install
```bash
wget -O- https://github.com/rjeffmyers/vpn3gui/releases/latest/download/vpn3gui_1.0.2_all.deb | sudo dpkg -i - && sudo apt install -f
```

## Install from Source

### Clone and Run
```bash
git clone https://github.com/rjeffmyers/vpn3gui.git
cd vpn3gui
chmod +x vpn3gui.py
./vpn3gui.py
```

### Build Your Own .deb Package
```bash
git clone https://github.com/rjeffmyers/vpn3gui.git
cd vpn3gui
./build-simple-deb.sh
sudo dpkg -i vpn3gui_*.deb
```

## Adding a PPA (Future Enhancement)

For automatic updates via apt, we may add a PPA in the future:
```bash
# This is a planned feature
sudo add-apt-repository ppa:vpn3gui/stable
sudo apt update
sudo apt install vpn3gui
```

## System Requirements

- **OS**: Ubuntu 20.04+, Linux Mint 20+, Debian 10+, or derivatives
- **Python**: 3.6 or higher
- **Dependencies**: Automatically installed with .deb package
  - python3-gi (GTK bindings)
  - gir1.2-gtk-3.0 (GTK3)
  - openvpn3 (recommended)
  - python3-keyring (optional, for secure storage)

## Verifying Installation

After installation, you can:
- Find VPN3GUI in your application menu
- Run from terminal: `vpn3gui`
- Check version: `dpkg -l | grep vpn3gui`

## Uninstallation

```bash
sudo apt remove vpn3gui
# Or to remove with config files:
sudo apt purge vpn3gui
```

## Troubleshooting

### Missing Dependencies
If you get dependency errors:
```bash
sudo apt update
sudo apt install -f
```

### OpenVPN3 Not Installed
VPN3GUI will prompt to install OpenVPN3, or manually:
```bash
# The app includes an installer in Tools menu
# Or manually:
sudo apt install openvpn3
```

### Manual Dependency Installation
If the .deb install fails:
```bash
sudo apt install python3-gi python3-gi-cairo gir1.2-gtk-3.0
sudo apt install python3-keyring python3-secretstorage  # Optional
```