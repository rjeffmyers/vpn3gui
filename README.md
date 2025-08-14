# OpenVPN3 GUI

A simple GTK+ GUI wrapper for OpenVPN3 on Linux, designed for Linux Mint and Ubuntu systems.

## Features

- Simple graphical interface for OpenVPN3
- Import and manage VPN configurations
- Connect/disconnect with one click
- Automatic installation helper for OpenVPN3
- Real-time connection status monitoring
- Support for multiple VPN configurations

## Requirements

- Python 3
- GTK+ 3.0
- OpenVPN3 (can be installed through the GUI)

## Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/vpn3gui.git
cd vpn3gui
```

2. Run the application:
```bash
python3 vpn3gui.py
```

If OpenVPN3 is not installed, the application will prompt you to install it automatically.

## Usage

1. Launch the application
2. If OpenVPN3 is not installed, follow the installation prompts
3. Import your .ovpn configuration files using the "Import New Config File..." button
4. Select a configuration from the dropdown
5. Click "Connect" to establish VPN connection
6. Click "Disconnect" to close the connection

## Tested On

- Linux Mint 22.1
- Ubuntu 24.04 (Noble)
- Ubuntu 22.04 (Jammy)

## License

MIT License - See LICENSE file for details. Feel free to use, modify, and distribute as needed.
