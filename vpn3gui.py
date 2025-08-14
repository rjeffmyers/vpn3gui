#!/usr/bin/env python3

"""
OpenVPN3 GUI - A simple GTK+ interface for OpenVPN3 on Linux
Copyright (c) 2024

MIT License

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, GLib, Gdk
import subprocess
import threading
import os
import shutil
import platform

class VPNManager(Gtk.Window):
    def __init__(self):
        Gtk.Window.__init__(self, title="OpenVPN3 GUI")
        self.set_border_width(20)
        self.set_default_size(400, 350)
        
        # Main vertical box
        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        self.add(vbox)
        
        # Title
        title_label = Gtk.Label()
        title_label.set_markup("<b><big>OpenVPN3 Manager</big></b>")
        vbox.pack_start(title_label, False, False, 0)
        
        # Separator
        vbox.pack_start(Gtk.Separator(), False, False, 0)
        
        # Config selection frame
        config_frame = Gtk.Frame(label="Configuration")
        vbox.pack_start(config_frame, False, False, 0)
        
        config_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
        config_box.set_border_width(10)
        config_frame.add(config_box)
        
        # Config dropdown
        config_hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=5)
        config_box.pack_start(config_hbox, False, False, 0)
        
        config_hbox.pack_start(Gtk.Label("Select Config:"), False, False, 0)
        self.config_combo = Gtk.ComboBoxText()
        config_hbox.pack_start(self.config_combo, True, True, 0)
        
        # Refresh configs button
        refresh_btn = Gtk.Button(label="Refresh")
        refresh_btn.connect("clicked", self.refresh_configs)
        config_hbox.pack_start(refresh_btn, False, False, 0)
        
        # Import config button
        import_btn = Gtk.Button(label="Import New Config File...")
        import_btn.connect("clicked", self.import_config)
        config_box.pack_start(import_btn, False, False, 0)
        
        # Control buttons frame
        control_frame = Gtk.Frame(label="Connection Control")
        vbox.pack_start(control_frame, False, False, 0)
        
        button_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        button_box.set_border_width(10)
        control_frame.add(button_box)
        
        # Start button
        self.start_button = Gtk.Button(label="Connect")
        self.start_button.connect("clicked", self.start_vpn)
        button_box.pack_start(self.start_button, True, True, 0)
        
        # Stop button  
        self.stop_button = Gtk.Button(label="Disconnect")
        self.stop_button.connect("clicked", self.stop_vpn)
        self.stop_button.set_sensitive(False)
        button_box.pack_start(self.stop_button, True, True, 0)
        
        # Status frame
        status_frame = Gtk.Frame(label="Status")
        vbox.pack_start(status_frame, True, True, 0)
        
        # Status text view with scroll
        scrolled_window = Gtk.ScrolledWindow()
        scrolled_window.set_border_width(10)
        scrolled_window.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        status_frame.add(scrolled_window)
        
        self.status_view = Gtk.TextView()
        self.status_view.set_editable(False)
        self.status_view.set_wrap_mode(Gtk.WrapMode.WORD)
        scrolled_window.add(self.status_view)
        
        self.status_buffer = self.status_view.get_buffer()
        
        # Add menu bar
        menubar = Gtk.MenuBar()
        vbox.pack_start(menubar, False, False, 0)
        vbox.reorder_child(menubar, 0)  # Move to top
        
        # Tools menu
        tools_menu = Gtk.Menu()
        tools_item = Gtk.MenuItem(label="Tools")
        tools_item.set_submenu(tools_menu)
        menubar.append(tools_item)
        
        # Install OpenVPN3 menu item
        install_item = Gtk.MenuItem(label="Install OpenVPN3...")
        install_item.connect("activate", self.show_install_dialog)
        tools_menu.append(install_item)
        
        # Initialize
        self.current_session = None
        self.config_paths = {}  # Initialize config paths mapping
        
        # Check if openvpn3 is installed
        if not self.check_openvpn3_installed():
            GLib.idle_add(self.show_install_prompt)
        else:
            self.refresh_configs()
            self.update_status()
            # Start periodic status updates
            GLib.timeout_add_seconds(5, self.update_status)
        
    def run_command(self, cmd, callback=None):
        """Run command in background thread"""
        def run():
            try:
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
                GLib.idle_add(callback, result) if callback else None
            except subprocess.TimeoutExpired:
                GLib.idle_add(self.show_error, "Command timed out")
            except Exception as e:
                GLib.idle_add(self.show_error, str(e))
        
        thread = threading.Thread(target=run)
        thread.daemon = True
        thread.start()
        
    def refresh_configs(self, widget=None):
        """Refresh the list of available configs"""
        def update_combo(result):
            self.config_combo.remove_all()
            self.config_paths = {}  # Store mapping of display names to paths
            if result.returncode == 0:
                lines = result.stdout.strip().split('\n')
                for line in lines[2:]:  # Skip header lines
                    if line.strip() and not line.startswith('-'):
                        # First column is the config path
                        parts = line.split()
                        if len(parts) >= 1:
                            config_path = parts[0]
                            # Use just the filename for display
                            display_name = os.path.basename(config_path)
                            self.config_combo.append_text(display_name)
                            self.config_paths[display_name] = config_path
                if self.config_combo.get_model().iter_n_children(None) > 0:
                    self.config_combo.set_active(0)
            else:
                self.config_combo.append_text("No configs available")
                
        self.run_command(["openvpn3", "configs-list"], update_combo)
        
    def import_config(self, widget):
        """Import a new config file"""
        dialog = Gtk.FileChooserDialog(
            title="Select OpenVPN Config File",
            parent=self,
            action=Gtk.FileChooserAction.OPEN
        )
        dialog.add_buttons(
            Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
            Gtk.STOCK_OPEN, Gtk.ResponseType.OK
        )
        
        # Add filter for .ovpn files
        filter_ovpn = Gtk.FileFilter()
        filter_ovpn.set_name("OpenVPN files")
        filter_ovpn.add_pattern("*.ovpn")
        dialog.add_filter(filter_ovpn)
        
        filter_all = Gtk.FileFilter()
        filter_all.set_name("All files")
        filter_all.add_pattern("*")
        dialog.add_filter(filter_all)
        
        response = dialog.run()
        if response == Gtk.ResponseType.OK:
            filepath = dialog.get_filename()
            dialog.destroy()
            
            def import_done(result):
                if result.returncode == 0:
                    self.update_status_text("Config imported successfully!")
                    self.refresh_configs()
                else:
                    self.show_error(f"Import failed: {result.stderr}")
                    
            self.run_command(["openvpn3", "config-import", "--config", filepath], import_done)
        else:
            dialog.destroy()
            
    def start_vpn(self, widget):
        """Start VPN connection"""
        display_name = self.config_combo.get_active_text()
        if not display_name or display_name == "No configs available":
            self.show_error("Please select a valid configuration")
            return
        
        # Get the actual config path
        config_path = self.config_paths.get(display_name)
        if not config_path:
            self.show_error("Configuration path not found")
            return
            
        self.update_status_text("Connecting...")
        self.start_button.set_sensitive(False)
        
        def start_done(result):
            if result.returncode == 0:
                self.start_button.set_sensitive(False)
                self.stop_button.set_sensitive(True)
                # Extract session path from output
                for line in result.stdout.split('\n'):
                    if 'Session path:' in line:
                        self.current_session = line.split('Session path:')[1].strip()
                self.update_status()
            else:
                self.start_button.set_sensitive(True)
                self.show_error(f"Connection failed: {result.stderr}")
                
        # Use --config with the full path
        self.run_command(["openvpn3", "session-start", "--config", config_path], start_done)
        
    def stop_vpn(self, widget):
        """Stop VPN connection"""
        if not self.current_session:
            # Try to find active session
            self.run_command(["openvpn3", "sessions-list"], self.find_and_disconnect)
        else:
            self.disconnect_session(self.current_session)
            
    def find_and_disconnect(self, result):
        """Find active session and disconnect"""
        if result.returncode == 0:
            lines = result.stdout.strip().split('\n')
            for line in lines:
                if '/net/openvpn/v3/sessions/' in line:
                    session_path = line.split()[0]
                    self.disconnect_session(session_path)
                    return
        self.show_error("No active session found")
        
    def disconnect_session(self, session_path):
        """Disconnect specific session"""
        self.update_status_text("Disconnecting...")
        
        def disconnect_done(result):
            if result.returncode == 0:
                self.current_session = None
                self.start_button.set_sensitive(True)
                self.stop_button.set_sensitive(False)
                self.update_status_text("Disconnected")
            else:
                self.show_error(f"Disconnect failed: {result.stderr}")
                
        self.run_command(["openvpn3", "session-manage", "--session-path", session_path, "--disconnect"], disconnect_done)
        
    def update_status(self):
        """Update connection status"""
        def process_status(result):
            if result.returncode == 0:
                # Check if we have active sessions
                if '/net/openvpn/v3/sessions/' in result.stdout:
                    self.stop_button.set_sensitive(True)
                    self.start_button.set_sensitive(False)
                    self.update_status_text("Connected\n\nActive Sessions:\n" + result.stdout)
                else:
                    self.stop_button.set_sensitive(False)
                    self.start_button.set_sensitive(True)
                    self.update_status_text("Disconnected")
            else:
                self.update_status_text("Status: Unable to get session info")
                
        self.run_command(["openvpn3", "sessions-list"], process_status)
        return True  # Continue periodic updates
        
    def update_status_text(self, text):
        """Update status text in UI"""
        self.status_buffer.set_text(text)
        
    def show_error(self, message):
        """Show error dialog"""
        dialog = Gtk.MessageDialog(
            transient_for=self,
            flags=0,
            message_type=Gtk.MessageType.ERROR,
            buttons=Gtk.ButtonsType.OK,
            text=message
        )
        dialog.run()
        dialog.destroy()
    
    def check_openvpn3_installed(self):
        """Check if openvpn3 is installed"""
        return shutil.which("openvpn3") is not None
    
    def show_install_prompt(self):
        """Show prompt to install OpenVPN3"""
        dialog = Gtk.MessageDialog(
            transient_for=self,
            flags=0,
            message_type=Gtk.MessageType.WARNING,
            buttons=Gtk.ButtonsType.YES_NO,
            text="OpenVPN3 Not Found"
        )
        dialog.format_secondary_text(
            "OpenVPN3 is not installed on your system. Would you like to install it?"
        )
        
        response = dialog.run()
        dialog.destroy()
        
        if response == Gtk.ResponseType.YES:
            self.show_install_dialog()
    
    def show_install_dialog(self, widget=None):
        """Show installation dialog with instructions"""
        dialog = Gtk.Dialog(
            title="Install OpenVPN3",
            parent=self,
            flags=0
        )
        dialog.add_buttons(
            Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
            "Install Automatically", Gtk.ResponseType.OK,
            "Copy Commands", Gtk.ResponseType.APPLY
        )
        
        dialog.set_default_size(700, 550)
        
        content_area = dialog.get_content_area()
        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        vbox.set_border_width(10)
        content_area.add(vbox)
        
        # Instructions label
        label = Gtk.Label()
        label.set_markup("<b>OpenVPN3 Installation for Linux Mint/Ubuntu</b>")
        vbox.pack_start(label, False, False, 0)
        
        # Text view with commands
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        scrolled.set_min_content_height(400)  # Set minimum height for the scrolled window
        vbox.pack_start(scrolled, True, True, 0)
        
        text_view = Gtk.TextView()
        text_view.set_editable(False)
        text_view.set_wrap_mode(Gtk.WrapMode.WORD)
        scrolled.add(text_view)
        
        # Detect distribution
        dist_info = self.get_distribution_info()
        
        commands = self.get_install_commands(dist_info)
        
        buffer = text_view.get_buffer()
        buffer.set_text(
            "Installation Instructions:\n\n"
            "The following commands will be executed to install OpenVPN3:\n\n"
            + commands + "\n\n"
            "Click 'Install Automatically' to run these commands (requires sudo password)\n"
            "Click 'Copy Commands' to copy them to clipboard for manual execution\n"
        )
        
        dialog.show_all()
        response = dialog.run()
        
        if response == Gtk.ResponseType.OK:
            dialog.destroy()
            self.run_installation(commands)
        elif response == Gtk.ResponseType.APPLY:
            # Copy to clipboard
            clipboard = Gtk.Clipboard.get(Gdk.SELECTION_CLIPBOARD)
            clipboard.set_text(commands, -1)
            dialog.destroy()
            self.show_info("Commands copied to clipboard. Run them in a terminal with sudo privileges.")
        else:
            dialog.destroy()
    
    def get_distribution_info(self):
        """Get distribution information"""
        try:
            # Try to read os-release file
            with open('/etc/os-release', 'r') as f:
                lines = f.readlines()
                info = {}
                for line in lines:
                    if '=' in line:
                        key, value = line.strip().split('=', 1)
                        info[key] = value.strip('"')
                
                # Determine Ubuntu base version for Mint
                if 'Linux Mint' in info.get('NAME', ''):
                    version = info.get('VERSION_ID', '22')
                    if version.startswith('22'):
                        return 'noble'  # Ubuntu 24.04
                    elif version.startswith('21'):
                        return 'jammy'  # Ubuntu 22.04
                    elif version.startswith('20'):
                        return 'focal'  # Ubuntu 20.04
                elif 'Ubuntu' in info.get('NAME', ''):
                    codename = info.get('VERSION_CODENAME', 'noble')
                    return codename
        except:
            pass
        
        return 'noble'  # Default to noble
    
    def get_install_commands(self, dist_codename):
        """Generate installation commands based on distribution"""
        arch = platform.machine()
        if arch == 'x86_64':
            arch = 'amd64'
        elif arch == 'aarch64':
            arch = 'arm64'
        
        commands = f"""# Install prerequisites
sudo apt update
sudo apt install -y apt-transport-https curl gpg

# Create keyrings directory if it doesn't exist (for newer apt versions)
sudo mkdir -p /etc/apt/keyrings

# Add OpenVPN repository key
# For newer systems (using /etc/apt/keyrings):
curl -fsSL https://packages.openvpn.net/packages-repo.gpg | sudo gpg --dearmor -o /etc/apt/keyrings/openvpn.asc

# Add OpenVPN3 repository
echo "deb [arch={arch} signed-by=/etc/apt/keyrings/openvpn.asc] https://packages.openvpn.net/openvpn3/debian {dist_codename} main" | sudo tee /etc/apt/sources.list.d/openvpn3.list

# Update and install OpenVPN3
sudo apt update
sudo apt install -y openvpn3"""
        
        return commands
    
    def run_installation(self, commands):
        """Run installation commands"""
        # Create a terminal window to run the commands
        terminal_cmd = self.get_terminal_command(commands)
        
        if terminal_cmd:
            subprocess.Popen(terminal_cmd, shell=True)
            
            dialog = Gtk.MessageDialog(
                transient_for=self,
                flags=0,
                message_type=Gtk.MessageType.INFO,
                buttons=Gtk.ButtonsType.OK,
                text="Installation Started"
            )
            dialog.format_secondary_text(
                "The installation has been started in a new terminal window.\n"
                "Please enter your sudo password when prompted.\n"
                "After installation completes, restart this application."
            )
            dialog.run()
            dialog.destroy()
        else:
            self.show_error("Could not determine terminal emulator. Please copy commands and run manually.")
    
    def get_terminal_command(self, commands):
        """Get the appropriate terminal command for the system"""
        # Save commands to a temporary script
        script_path = "/tmp/install_openvpn3.sh"
        with open(script_path, 'w') as f:
            f.write("#!/bin/bash\n")
            f.write(commands)
            f.write("\necho \"\nInstallation complete. Press Enter to close...\"\n")
            f.write("read\n")
        
        os.chmod(script_path, 0o755)
        
        # Try different terminal emulators
        terminals = [
            ("gnome-terminal", f"gnome-terminal -- bash {script_path}"),
            ("xfce4-terminal", f"xfce4-terminal -e 'bash {script_path}'"),
            ("mate-terminal", f"mate-terminal -e 'bash {script_path}'"),
            ("konsole", f"konsole -e bash {script_path}"),
            ("xterm", f"xterm -e bash {script_path}"),
        ]
        
        for term_name, term_cmd in terminals:
            if shutil.which(term_name):
                return term_cmd
        
        return None
    
    def show_info(self, message):
        """Show info dialog"""
        dialog = Gtk.MessageDialog(
            transient_for=self,
            flags=0,
            message_type=Gtk.MessageType.INFO,
            buttons=Gtk.ButtonsType.OK,
            text=message
        )
        dialog.run()
        dialog.destroy()

if __name__ == "__main__":
    win = VPNManager()
    win.connect("destroy", Gtk.main_quit)
    win.show_all()
    Gtk.main()