# VPN3GUI - OpenVPN3 GUI for Linux

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)
[![Python Version](https://img.shields.io/badge/python-3.6%2B-blue)](https://www.python.org/downloads/)
[![GTK Version](https://img.shields.io/badge/GTK-3.0-green)](https://www.gtk.org/)

A modern, user-friendly GTK+ interface for OpenVPN3 on Linux systems. VPN3GUI provides secure credential management, intuitive connection controls, and seamless integration with the OpenVPN3 command-line client.

## 🌟 Features

### Core Functionality
- **Easy VPN Management**: Connect and disconnect from VPN servers with a single click
- **Configuration Import**: Import `.ovpn` configuration files directly through the GUI
- **Real-time Status Monitoring**: View connection status and statistics in real-time
- **Session Management**: Automatic detection and management of VPN sessions
- **Multi-config Support**: Manage multiple VPN configurations from a single interface

### 🔐 Security Features
- **Secure Credential Storage**: 
  - System keyring integration (GNOME Keyring, KWallet, Secret Service)
  - Encrypted local storage fallback
  - No plaintext password storage
- **Credential Migration Tool**: Automatically migrate existing plaintext credentials to secure storage
- **Password Management**: Update and manage VPN passwords securely
- **Authentication Retry**: Automatic prompt for re-authentication on connection failure

### 🛠️ Tools & Utilities
- **Automatic Installation Helper**: Built-in installer for OpenVPN3 and dependencies
- **Keyring Setup Assistant**: Step-by-step guide for configuring secure password storage
- **Session Cleanup**: Clean up stale VPN sessions that weren't properly disconnected
- **Debug Mode**: Toggle detailed command output for troubleshooting
- **Distribution Detection**: Automatic detection of Linux distribution for optimized installation

### 💻 User Interface
- **Modern GTK3 Design**: Clean, intuitive interface following GNOME HIG
- **Toolbar with Icons**: Quick access to Tools and Help functions
- **Status Display**: Scrollable text area showing connection logs and statistics
- **Dropdown Config Selection**: Easy selection from imported configurations
- **About Dialog**: Project information and GitHub link

## 📋 Requirements

### System Requirements
- Linux (tested on Ubuntu 20.04+, Linux Mint 20+, Debian 10+)
- Python 3.6 or higher
- GTK+ 3.0
- OpenVPN3 Linux client

### Python Dependencies
- `gi` (PyGObject)
- `keyring` (optional, for secure credential storage)

## 🚀 Installation

### Quick Install
```bash
# Clone the repository
git clone https://github.com/rjeffmyers/vpn3gui.git
cd vpn3gui

# Make the script executable
chmod +x vpn3gui.py

# Run the application
./vpn3gui.py
```

### Installing OpenVPN3
If OpenVPN3 is not installed, the application will prompt you to install it. You can also install manually:

```bash
# For Ubuntu/Debian/Linux Mint
sudo apt update
sudo apt install -y apt-transport-https curl gpg

# Add OpenVPN repository
curl -fsSL https://packages.openvpn.net/packages-repo.gpg | sudo gpg --dearmor -o /etc/apt/keyrings/openvpn.asc
echo "deb [arch=amd64 signed-by=/etc/apt/keyrings/openvpn.asc] https://packages.openvpn.net/openvpn3/debian $(lsb_release -cs) main" | sudo tee /etc/apt/sources.list.d/openvpn3.list

# Install OpenVPN3
sudo apt update
sudo apt install -y openvpn3
```

### Installing Keyring Support (Recommended)
For secure credential storage:

```bash
# Using apt (recommended)
sudo apt install -y python3-keyring python3-secretstorage gnome-keyring

# Or using pipx
pipx install keyring
```

## 🎯 Usage

### Basic Usage
1. **Launch the application**: `./vpn3gui.py`
2. **Import a VPN configuration**: Click "Import New Config File..." and select your `.ovpn` file
3. **Select configuration**: Choose from the dropdown menu
4. **Connect**: Click "Connect" and enter your credentials
5. **Monitor**: View connection status in the status area
6. **Disconnect**: Click "Disconnect" when done

### Advanced Features

#### Credential Management
- **Save Credentials**: Check "Remember credentials" when connecting
- **Update Password**: Tools → Update VPN Password
- **Migrate Plaintext Credentials**: Tools → Migrate Plaintext Credentials

#### Troubleshooting
- **Enable Debug Mode**: Tools → Debug Mode (shows detailed command output)
- **Clean Stale Sessions**: Tools → Clean Up Stale VPN Sessions
- **Fix Keyring Issues**: Tools → Fix Password Storage Issues

## 🔧 Configuration

### Configuration Files
The application stores its configuration in:
- `~/.config/vpn3gui/credentials.json` - Encrypted credential storage (fallback)
- System keyring (when available) - Primary secure storage

### Security Notes
- Credentials are never stored in plaintext
- Local storage uses restrictive file permissions (0600)
- System keyring integration provides the highest security
- Automatic detection and migration of insecure configurations

## 🤝 Contributing

Contributions are welcome! Please feel free to submit pull requests or open issues for bugs and feature requests.

### Development Setup
```bash
# Clone the repository
git clone https://github.com/rjeffmyers/vpn3gui.git
cd vpn3gui

# Install development dependencies
pip install -r requirements-dev.txt  # If available

# Run the application in debug mode
python3 vpn3gui.py
```

## 📝 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🙏 Acknowledgments

- OpenVPN3 Linux client developers
- GTK+ and PyGObject teams
- Python keyring library maintainers
- All contributors and users

## 📧 Support

For issues, questions, or suggestions:
- Open an issue on [GitHub](https://github.com/rjeffmyers/vpn3gui/issues)
- Check existing issues for solutions
- Enable debug mode for troubleshooting

## 🚦 Status

This project is actively maintained and regularly updated with new features and bug fixes.

---

**Note**: This application requires OpenVPN3 Linux client to be installed. It provides a graphical interface for the command-line client and does not include VPN functionality itself.