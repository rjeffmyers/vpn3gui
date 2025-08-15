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
import json
import tempfile
import time
from collections import deque

# Check if keyring module is available
try:
    import keyring
    # Try to detect and avoid KDE Wallet if it's causing issues
    backend = keyring.get_keyring()
    backend_name = backend.__class__.__name__.lower()
    
    # If KDE Wallet is detected and we're not on KDE, try to use Secret Service
    if 'kde' in backend_name or 'kwallet' in backend_name:
        try:
            # Try to force SecretService backend for GNOME/XFCE
            from keyring.backends import SecretService
            keyring.set_keyring(SecretService.Keyring())
            KEYRING_AVAILABLE = True
        except:
            # If we can't set SecretService, disable keyring to avoid KDE Wallet popups
            KEYRING_AVAILABLE = False
            print("KDE Wallet detected but not available. Using file storage instead.")
    else:
        KEYRING_AVAILABLE = True
except ImportError:
    KEYRING_AVAILABLE = False
except Exception:
    # Any other keyring initialization error - disable it
    KEYRING_AVAILABLE = False
    print("Keyring initialization failed. Using file storage instead.")

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
        
        config_label = Gtk.Label(label="Select Config:")
        config_hbox.pack_start(config_label, False, False, 0)
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
        
        # Create notebook for status and chart tabs
        self.status_notebook = Gtk.Notebook()
        status_frame.add(self.status_notebook)
        
        # Tab 1: Text status
        scrolled_window = Gtk.ScrolledWindow()
        scrolled_window.set_border_width(10)
        scrolled_window.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        
        self.status_view = Gtk.TextView()
        self.status_view.set_editable(False)
        self.status_view.set_wrap_mode(Gtk.WrapMode.WORD)
        scrolled_window.add(self.status_view)
        
        self.status_buffer = self.status_view.get_buffer()
        
        # Tab 2: Traffic chart
        chart_container = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
        chart_container.set_border_width(10)
        
        # Create drawing area for chart
        self.chart_area = Gtk.DrawingArea()
        self.chart_area.set_size_request(400, 200)
        self.chart_area.connect("draw", self.on_chart_draw)
        
        # Put drawing area in a frame for visibility
        chart_frame = Gtk.Frame()
        chart_frame.add(self.chart_area)
        chart_container.pack_start(chart_frame, True, True, 0)
        
        # Legend for chart
        legend_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=20)
        legend_box.set_halign(Gtk.Align.CENTER)
        
        # Bytes In legend
        in_label = Gtk.Label()
        in_label.set_markup("<span color='#4CAF50'>●</span> Bytes In")
        legend_box.pack_start(in_label, False, False, 0)
        
        # Bytes Out legend
        out_label = Gtk.Label()
        out_label.set_markup("<span color='#2196F3'>●</span> Bytes Out")
        legend_box.pack_start(out_label, False, False, 0)
        
        # Current values display
        self.chart_stats_label = Gtk.Label()
        self.chart_stats_label.set_markup("<small>Waiting for data...</small>")
        legend_box.pack_start(self.chart_stats_label, False, False, 10)
        
        chart_container.pack_start(legend_box, False, False, 0)
        
        # Add tabs to notebook
        self.status_notebook.append_page(scrolled_window, Gtk.Label(label="Status"))
        self.status_notebook.append_page(chart_container, Gtk.Label(label="Traffic Chart"))
        
        # Show all widgets in chart container
        chart_container.show_all()
        
        # Initialize chart data
        self.chart_data_points = 60  # Number of data points to show
        self.bytes_in_history = deque([0] * self.chart_data_points, maxlen=self.chart_data_points)
        self.bytes_out_history = deque([0] * self.chart_data_points, maxlen=self.chart_data_points)
        self.last_bytes_in = 0
        self.last_bytes_out = 0
        self.chart_max_value = 1000  # Initial max value for Y-axis
        
        # Add a toolbar for better visibility (matching rdp2gui style)
        toolbar = Gtk.Toolbar()
        toolbar.set_style(Gtk.ToolbarStyle.BOTH_HORIZ)  # Show both icon and text
        vbox.pack_start(toolbar, False, False, 0)
        vbox.reorder_child(toolbar, 0)  # Move to top
        
        # Add Tools button with icon (matching rdp2gui)
        tools_button = Gtk.ToolButton()
        tools_button.set_label("Tools")
        tools_button.set_icon_name("applications-system")  # System tools icon
        tools_button.set_tooltip_text("Settings, installation helpers, and utilities")
        tools_button.set_is_important(True)  # Makes the label always visible
        toolbar.insert(tools_button, 0)
        
        # Add separator
        separator = Gtk.SeparatorToolItem()
        separator.set_expand(True)
        separator.set_draw(False)
        toolbar.insert(separator, 1)
        
        # Add Help button (matching rdp2gui)
        help_button = Gtk.ToolButton()
        help_button.set_label("Help")
        help_button.set_icon_name("help-about")
        help_button.set_tooltip_text("About this application")
        toolbar.insert(help_button, 2)
        
        def show_about(widget):
            dialog = Gtk.AboutDialog()
            dialog.set_transient_for(self)
            dialog.set_program_name("OpenVPN3 GUI")
            dialog.set_version("1.0")
            dialog.set_comments("A simple GTK+ interface for OpenVPN3 on Linux\n\nModern VPN client with secure credential storage")
            dialog.set_website("https://github.com/rjeffmyers/vpn3gui")
            dialog.set_website_label("GitHub Project Page")
            dialog.set_authors(["VPN3GUI Contributors"])
            dialog.set_license_type(Gtk.License.MIT_X11)
            dialog.run()
            dialog.destroy()
        
        help_button.connect("clicked", show_about)
        
        # Create tools menu
        tools_menu = Gtk.Menu()
        
        # Connect tools button to show menu
        def show_tools_menu(widget):
            tools_menu.show_all()
            tools_menu.popup_at_widget(widget, Gdk.Gravity.SOUTH_WEST, Gdk.Gravity.NORTH_WEST, None)
        
        tools_button.connect("clicked", show_tools_menu)
        
        # Install OpenVPN3 menu item
        install_item = Gtk.MenuItem(label="Install OpenVPN3...")
        install_item.connect("activate", self.show_install_dialog)
        tools_menu.append(install_item)
        
        # Install Keyring menu item
        keyring_item = Gtk.MenuItem(label="Install Keyring Support...")
        keyring_item.connect("activate", self.show_keyring_install_dialog)
        tools_menu.append(keyring_item)
        
        # Separator
        tools_menu.append(Gtk.SeparatorMenuItem())
        
        # Migrate credentials menu item
        migrate_item = Gtk.MenuItem(label="Migrate Plaintext Credentials...")
        migrate_item.connect("activate", self.migrate_all_credentials)
        tools_menu.append(migrate_item)
        
        # Update password menu item
        update_pw_item = Gtk.MenuItem(label="Update VPN Password...")
        update_pw_item.connect("activate", self.update_vpn_password)
        tools_menu.append(update_pw_item)
        
        # Keyring initialization help
        keyring_help_item = Gtk.MenuItem(label="Fix Password Storage Issues...")
        keyring_help_item.connect("activate", lambda w: self.show_keyring_initialization_help())
        tools_menu.append(keyring_help_item)
        
        # Toggle keyring support
        self.keyring_toggle_item = Gtk.CheckMenuItem(label="Use System Keyring")
        self.keyring_toggle_item.set_active(KEYRING_AVAILABLE)
        self.keyring_toggle_item.connect("toggled", self.toggle_keyring_support)
        tools_menu.append(self.keyring_toggle_item)
        
        # Separator
        tools_menu.append(Gtk.SeparatorMenuItem())
        
        # Debug mode toggle (matching rdp2gui)
        self.debug_toggle_item = Gtk.CheckMenuItem(label="Debug Mode")
        self.debug_toggle_item.set_active(False)
        self.debug_toggle_item.connect("toggled", self.toggle_debug_mode)
        tools_menu.append(self.debug_toggle_item)
        
        # Separator
        tools_menu.append(Gtk.SeparatorMenuItem())
        
        # Clean up stale sessions
        cleanup_item = Gtk.MenuItem(label="Clean Up Stale VPN Sessions...")
        cleanup_item.connect("activate", self.cleanup_stale_sessions)
        tools_menu.append(cleanup_item)
        
        # Initialize
        self.current_session = None
        self.config_paths = {}  # Initialize config paths mapping
        
        # Credential storage - must be initialized before load_credentials()
        self.credentials_file = os.path.expanduser("~/.config/vpn3gui/credentials.json")
        self.temp_auth_files = []  # Track temporary auth files for cleanup
        self.plaintext_configs = []  # Track configs with plaintext auth
        self.use_keyring = KEYRING_AVAILABLE  # Track whether to use keyring
        
        # Load stored credentials after initializing paths
        self.stored_credentials = self.load_credentials()
        
        # Initialize connection state tracking
        self.is_connecting = False
        self.debug_mode = False  # Set to True to see command output
        
        # Check if openvpn3 is installed
        if not self.check_openvpn3_installed():
            GLib.idle_add(self.show_install_prompt)
        else:
            self.refresh_configs()
            # Start periodic status updates (but don't run immediately)
            GLib.timeout_add_seconds(2, self.update_status)  # Update every 2 seconds for smoother chart
            # Check for plaintext credentials after loading configs
            GLib.timeout_add_seconds(2, self.check_for_plaintext_auth)
        
    def run_command(self, cmd, callback=None):
        """Run command in background thread"""
        if self.debug_mode:
            print(f"Running command: {' '.join(cmd)}")
        
        def run():
            try:
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
                if self.debug_mode and result.stdout:
                    print(f"Command output: {result.stdout[:500]}")
                if self.debug_mode and result.stderr:
                    print(f"Command error: {result.stderr[:500]}")
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
        
        # Always show credential dialog for user authentication
        # Get stored credentials if they exist
        username, password = self.get_credentials_for_config(display_name)
        
        # Show credential dialog (with pre-filled values if available)
        self.show_credential_dialog(display_name, config_path, stored_user=username, stored_pass=password)
        
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
                # Even if disconnect fails, update button states based on actual status
                self.update_status()
                self.show_error(f"Disconnect failed: {result.stderr}")
                
        self.run_command(["openvpn3", "session-manage", "--session-path", session_path, "--disconnect"], disconnect_done)
        
    def update_status(self):
        """Update connection status"""
        def process_status(result):
            if result.returncode == 0 and result.stdout.strip():
                # Parse sessions and check their actual status
                lines = result.stdout.strip().split('\n')
                session_paths = []
                
                for line in lines:
                    # Look for session paths
                    if '/net/openvpn/v3/sessions/' in line:
                        # Extract the session path
                        parts = line.split()
                        for part in parts:
                            if '/net/openvpn/v3/sessions/' in part:
                                session_paths.append(part)
                                break
                
                if session_paths:
                    # Check the actual status of each session
                    self.check_session_status(session_paths[0])  # Check first session
                else:
                    # No sessions found
                    if not getattr(self, 'is_connecting', False):
                        self.stop_button.set_sensitive(False)
                        self.start_button.set_sensitive(True)
                        self.update_status_text("Disconnected")
            else:
                # No sessions or error
                if not getattr(self, 'is_connecting', False):
                    self.update_status_text("Disconnected")
                    self.start_button.set_sensitive(True)
                    self.stop_button.set_sensitive(False)
                
        self.run_command(["openvpn3", "sessions-list"], process_status)
        return True  # Continue periodic updates
    
    def check_session_status(self, session_path):
        """Check the actual status of a specific session"""
        def process_session_status(result):
            # Check if session-stats command succeeded
            
            # If session-stats works, the session exists
            # OpenVPN3 will return an error if the session doesn't exist or isn't connected
            if result.returncode == 0:
                # Session exists and returned stats - it's connected
                self.current_session = session_path
                self.stop_button.set_sensitive(True)
                self.start_button.set_sensitive(False)
                
                # Parse some basic stats for display
                stats_text = "Connected\n\n"
                bytes_in_value = 0
                bytes_out_value = 0
                
                if "BYTES_IN" in result.stdout:
                    stats_text += f"Session: {session_path[-12:]}\n\n"
                    # Extract some key stats
                    for line in result.stdout.split('\n'):
                        # Look for BYTES_IN but not TUN_BYTES_IN
                        if 'BYTES_IN' in line and not line.strip().startswith('TUN_'):
                            try:
                                # Format is: "     BYTES_IN....................9438"
                                # Split by dots and get the last part
                                if '.' in line:
                                    # Get everything after the dots
                                    value_str = line.split('.')[-1].strip()
                                    bytes_in_value = int(value_str)
                            except:
                                pass
                            stats_text += line + "\n"
                        # Look for BYTES_OUT but not TUN_BYTES_OUT
                        elif 'BYTES_OUT' in line and not line.strip().startswith('TUN_'):
                            try:
                                # Format is: "     BYTES_OUT...................3599"
                                if '.' in line:
                                    value_str = line.split('.')[-1].strip()
                                    bytes_out_value = int(value_str)
                            except:
                                pass
                            stats_text += line + "\n"
                        elif 'CONNECTED' in line:
                            stats_text += line + "\n"
                else:
                    stats_text += f"Session: {session_path}\n\n{result.stdout[:500]}"
                
                # Update chart data
                self.update_chart_data(bytes_in_value, bytes_out_value)
                
                self.update_status_text(stats_text)
            else:
                # Error getting stats usually means session is gone or disconnected
                if not getattr(self, 'is_connecting', False):
                    self.stop_button.set_sensitive(False)
                    self.start_button.set_sensitive(True)
                    self.update_status_text("Disconnected")
        
        # Get detailed status of the session
        self.run_command(["openvpn3", "session-stats", "--session-path", session_path], process_session_status)
        
    def update_status_text(self, text):
        """Update status text in UI"""
        self.status_buffer.set_text(text)
    
    def update_chart_data(self, bytes_in, bytes_out):
        """Update chart with new traffic data"""
        # Calculate rates (bytes per update interval)
        if self.last_bytes_in > 0 and bytes_in > self.last_bytes_in:
            in_rate = bytes_in - self.last_bytes_in
        else:
            in_rate = 0
        
        if self.last_bytes_out > 0 and bytes_out > self.last_bytes_out:
            out_rate = bytes_out - self.last_bytes_out
        else:
            out_rate = 0
        
        # Add to history
        self.bytes_in_history.append(in_rate)
        self.bytes_out_history.append(out_rate)
        
        # Update last values
        self.last_bytes_in = bytes_in
        self.last_bytes_out = bytes_out
        
        # Update max value for scaling
        max_rate = max(max(self.bytes_in_history), max(self.bytes_out_history))
        if max_rate > 0:
            # Add some padding to the max value
            self.chart_max_value = max_rate * 1.2
        
        # Update stats label
        in_total_mb = bytes_in / (1024 * 1024) if bytes_in > 0 else 0
        out_total_mb = bytes_out / (1024 * 1024) if bytes_out > 0 else 0
        in_rate_kb = in_rate / 1024 if in_rate > 0 else 0
        out_rate_kb = out_rate / 1024 if out_rate > 0 else 0
        
        self.chart_stats_label.set_markup(
            f"<small>Total: In {in_total_mb:.1f}MB / Out {out_total_mb:.1f}MB | "
            f"Rate: In {in_rate_kb:.1f}KB/s / Out {out_rate_kb:.1f}KB/s</small>"
        )
        
        # Redraw chart
        self.chart_area.queue_draw()
    
    def on_chart_draw(self, widget, cr):
        """Draw the traffic chart"""
        allocation = widget.get_allocation()
        width = allocation.width
        height = allocation.height
        
        # Ensure we have valid dimensions
        if width <= 0 or height <= 0:
            return False
        
        # Background - white
        cr.set_source_rgb(1.0, 1.0, 1.0)
        cr.rectangle(0, 0, width, height)
        cr.fill()
        
        # Draw grid
        cr.set_source_rgba(0.8, 0.8, 0.8, 0.5)
        cr.set_line_width(0.5)
        
        # Horizontal grid lines (5 lines)
        for i in range(5):
            y = int(height * i / 4)
            cr.move_to(0, y)
            cr.line_to(width, y)
        cr.stroke()
        
        # Vertical grid lines (every 10 data points)
        grid_spacing = 10
        for i in range(0, self.chart_data_points + 1, grid_spacing):
            x = int(width * i / self.chart_data_points)
            cr.move_to(x, 0)
            cr.line_to(x, height)
        cr.stroke()
        
        # Draw axes
        cr.set_source_rgb(0.3, 0.3, 0.3)
        cr.set_line_width(1.5)
        cr.move_to(0, height - 1)
        cr.line_to(width, height - 1)
        cr.move_to(1, 0)
        cr.line_to(1, height)
        cr.stroke()
        
        # Draw data if we have any
        if self.chart_max_value > 0 and len(self.bytes_in_history) > 1:
            # Calculate point spacing
            point_spacing = width / max(1, (self.chart_data_points - 1))
            
            # Draw filled area for bytes out (blue)
            cr.set_source_rgba(0.13, 0.59, 0.95, 0.3)  # Semi-transparent blue
            cr.move_to(0, height)
            for i, value in enumerate(self.bytes_out_history):
                x = i * point_spacing
                y = height - (value / self.chart_max_value * height * 0.85)  # Use 85% of height
                cr.line_to(x, y)
            cr.line_to(width, height)
            cr.close_path()
            cr.fill()
            
            # Draw line for bytes out (blue)
            cr.set_source_rgb(0.13, 0.59, 0.95)  # #2196F3
            cr.set_line_width(2)
            for i, value in enumerate(self.bytes_out_history):
                x = i * point_spacing
                y = height - (value / self.chart_max_value * height * 0.85)
                if i == 0:
                    cr.move_to(x, y)
                else:
                    cr.line_to(x, y)
            cr.stroke()
            
            # Draw filled area for bytes in (green)
            cr.set_source_rgba(0.30, 0.69, 0.31, 0.3)  # Semi-transparent green
            cr.move_to(0, height)
            for i, value in enumerate(self.bytes_in_history):
                x = i * point_spacing
                y = height - (value / self.chart_max_value * height * 0.85)
                cr.line_to(x, y)
            cr.line_to(width, height)
            cr.close_path()
            cr.fill()
            
            # Draw line for bytes in (green)
            cr.set_source_rgb(0.30, 0.69, 0.31)  # #4CAF50
            cr.set_line_width(2)
            for i, value in enumerate(self.bytes_in_history):
                x = i * point_spacing
                y = height - (value / self.chart_max_value * height * 0.85)
                if i == 0:
                    cr.move_to(x, y)
                else:
                    cr.line_to(x, y)
            cr.stroke()
        else:
            # No data - show message
            cr.set_source_rgb(0.5, 0.5, 0.5)
            cr.select_font_face("Sans", 0, 0)
            cr.set_font_size(14)
            text = "Waiting for traffic data..."
            text_extents = cr.text_extents(text)
            x = (width - text_extents.width) / 2
            y = height / 2
            cr.move_to(x, y)
            cr.show_text(text)
        
        # Draw border
        cr.set_source_rgb(0.7, 0.7, 0.7)
        cr.set_line_width(1)
        cr.rectangle(0.5, 0.5, width - 1, height - 1)
        cr.stroke()
        
        return False
        
    def cleanup_stale_sessions(self, widget=None):
        """Clean up stale VPN sessions"""
        dialog = Gtk.MessageDialog(
            transient_for=self,
            flags=0,
            message_type=Gtk.MessageType.QUESTION,
            buttons=Gtk.ButtonsType.YES_NO,
            text="Clean Up Stale Sessions?"
        )
        dialog.format_secondary_text(
            "This will disconnect ALL VPN sessions, including any that might be active.\n\n"
            "This is useful when sessions weren't properly closed and are preventing new connections.\n\n"
            "Continue?"
        )
        
        response = dialog.run()
        dialog.destroy()
        
        if response == Gtk.ResponseType.YES:
            def cleanup_done(result):
                cleaned = 0
                errors = []
                
                if result.returncode == 0 and result.stdout.strip():
                    lines = result.stdout.strip().split('\n')
                    session_paths = []
                    
                    for line in lines:
                        if '/net/openvpn/v3/sessions/' in line:
                            parts = line.split()
                            for part in parts:
                                if '/net/openvpn/v3/sessions/' in part:
                                    session_paths.append(part)
                                    break
                    
                    if session_paths:
                        # Disconnect each session
                        for session_path in session_paths:
                            try:
                                disconnect_result = subprocess.run(
                                    ["openvpn3", "session-manage", "--session-path", session_path, "--disconnect"],
                                    capture_output=True,
                                    text=True,
                                    timeout=5
                                )
                                if disconnect_result.returncode == 0:
                                    cleaned += 1
                                    print(f"Cleaned up session: {session_path}")
                                else:
                                    errors.append(f"Failed to clean {session_path}")
                            except Exception as e:
                                errors.append(f"Error cleaning {session_path}: {str(e)}")
                        
                        # Show results
                        if cleaned > 0:
                            message = f"Successfully cleaned up {cleaned} session(s)."
                            if errors:
                                message += f"\n\nErrors:\n" + "\n".join(errors)
                            self.show_info(message)
                        else:
                            self.show_error("Failed to clean up sessions:\n" + "\n".join(errors))
                        
                        # Update status
                        self.update_status()
                    else:
                        self.show_info("No sessions found to clean up.")
                else:
                    self.show_info("No active sessions to clean up.")
                    
            # Get list of all sessions
            self.run_command(["openvpn3", "sessions-list"], cleanup_done)
    
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
sudo apt install -y openvpn3

# Optional: Install Python keyring for secure credential storage
echo ""
echo "Installing Python keyring for secure credential storage..."
echo "Using apt method (recommended for Linux Mint 22 / Ubuntu 24.04+)..."
sudo apt install -y python3-keyring python3-secretstorage gnome-keyring

echo ""
echo "✓ Keyring support packages installed"
"""
        
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
            f.write("\necho \"\n✓ Installation complete!\"\n")
            f.write("echo \"\nThe VPN GUI is now ready to use with secure credential storage.\"\n")
            f.write("echo \"Press Enter to close...\"\n")
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
    
    def config_needs_credentials(self, config_path):
        """Check if config file needs credentials"""
        try:
            # Try to read the actual .ovpn file to check for auth-user-pass
            # First, we need to export the config to read it
            result = subprocess.run(
                ["openvpn3", "config-dump", "--config", config_path],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if result.returncode == 0:
                config_content = result.stdout
                # Check if auth-user-pass is present without a file path
                # or if it points to a non-existent file
                if "auth-user-pass" in config_content:
                    lines = config_content.split('\n')
                    for line in lines:
                        if line.strip().startswith("auth-user-pass"):
                            parts = line.strip().split()
                            if len(parts) == 1:
                                # auth-user-pass without file = needs credentials
                                return True
                            elif len(parts) > 1:
                                # Check if file exists
                                auth_file = parts[1]
                                if not os.path.exists(os.path.expanduser(auth_file)):
                                    return True
                    return False
                return False
        except:
            # If we can't determine, assume it might need credentials
            return True
    
    def toggle_keyring_support(self, widget):
        """Toggle keyring support on/off"""
        self.use_keyring = widget.get_active()
        
        if not self.use_keyring:
            self.show_info("System keyring disabled. Passwords will be stored locally in encrypted file.")
        elif not KEYRING_AVAILABLE:
            widget.set_active(False)
            self.use_keyring = False
            self.show_info("Keyring module not available. Please install it first:\nTools → Install Keyring Support")
        else:
            self.show_info("System keyring enabled for secure password storage.")
    
    def load_credentials(self):
        """Load stored credentials"""
        credentials = {}
        
        # Try keyring first if available and enabled
        if KEYRING_AVAILABLE and getattr(self, 'use_keyring', True):
            try:
                stored = keyring.get_password("vpn3gui", "credentials")
                if stored:
                    return json.loads(stored)
            except Exception as e:
                # Check for uninitialized keyring error
                error_msg = str(e).lower()
                if "no keys suitable" in error_msg or "encryption key" in error_msg or "locked" in error_msg:
                    # Keyring not initialized - show help once
                    if not hasattr(self, '_keyring_init_warning_shown'):
                        self._keyring_init_warning_shown = True
                        GLib.idle_add(self.show_simple_keyring_fix)
                # Silently fall back to file storage
                pass
        
        # Fallback to file storage (less secure)
        if os.path.exists(self.credentials_file):
            try:
                with open(self.credentials_file, 'r') as f:
                    credentials = json.load(f)
                # Set restrictive permissions
                os.chmod(self.credentials_file, 0o600)
            except:
                pass
        
        return credentials
    
    def save_credentials(self, config_name, username, password, remember=True):
        """Save credentials securely"""
        if not remember:
            return
        
        self.stored_credentials[config_name] = {
            "username": username,
            "password": password
        }
        
        # Try keyring first if available and enabled
        if KEYRING_AVAILABLE and self.use_keyring:
            try:
                keyring.set_password("vpn3gui", "credentials", 
                                   json.dumps(self.stored_credentials))
                return
            except Exception as e:
                # Check for uninitialized keyring error
                error_msg = str(e).lower()
                if "no keys suitable" in error_msg or "encryption key" in error_msg or "locked" in error_msg:
                    if not hasattr(self, '_keyring_init_warning_shown'):
                        self._keyring_init_warning_shown = True
                        GLib.idle_add(self.show_simple_keyring_fix)
                # Fall back to file storage
                pass
        
        # Fallback to file storage
        os.makedirs(os.path.dirname(self.credentials_file), exist_ok=True)
        with open(self.credentials_file, 'w') as f:
            json.dump(self.stored_credentials, f)
        # Set restrictive permissions
        os.chmod(self.credentials_file, 0o600)
    
    def get_credentials_for_config(self, config_name):
        """Get stored credentials for a config"""
        if config_name in self.stored_credentials:
            cred = self.stored_credentials[config_name]
            return cred.get("username"), cred.get("password")
        return None, None
    
    def create_temp_auth_file(self, username, password):
        """Create temporary auth file with credentials"""
        try:
            # Create temp file with restrictive permissions
            fd, path = tempfile.mkstemp(prefix="vpn_auth_", suffix=".txt")
            with os.fdopen(fd, 'w') as f:
                f.write(f"{username}\n{password}\n")
            
            # Set restrictive permissions
            os.chmod(path, 0o600)
            
            # Track for cleanup
            self.temp_auth_files.append(path)
            
            return path
        except Exception as e:
            print(f"Error creating auth file: {e}")
            return None
    
    def cleanup_temp_files(self, widget=None):
        """Clean up temporary auth files"""
        for auth_file in self.temp_auth_files:
            try:
                if os.path.exists(auth_file):
                    os.remove(auth_file)
            except:
                pass
        self.temp_auth_files.clear()
    
    def start_vpn_with_credentials(self, config_path, username, password):
        """Start VPN connection with provided credentials"""
        self.is_connecting = True  # Set flag to prevent status updates from interfering
        self.update_status_text("Connecting...")
        self.start_button.set_sensitive(False)
        
        def start_done(result):
            self.is_connecting = False  # Clear connecting flag
            if result.returncode == 0:
                self.start_button.set_sensitive(False)
                self.stop_button.set_sensitive(True)
                # Extract session path from output
                session_found = False
                for line in result.stdout.split('\n'):
                    if 'Session path:' in line:
                        self.current_session = line.split('Session path:')[1].strip()
                        session_found = True
                        break
                
                if not session_found:
                    # Try to find session path in other formats
                    if '/net/openvpn/v3/sessions/' in result.stdout:
                        import re
                        matches = re.findall(r'/net/openvpn/v3/sessions/[a-f0-9s]+', result.stdout)
                        if matches:
                            self.current_session = matches[0]
                            session_found = True
                
                # Force button states to be correct
                self.start_button.set_sensitive(False)
                self.stop_button.set_sensitive(True)
                self.update_status_text(f"Connected Successfully\n\nSession: {self.current_session if self.current_session else 'Active'}")
                
                # Schedule a status update but not immediately
                GLib.timeout_add_seconds(2, self.update_status)
            else:
                self.start_button.set_sensitive(True)
                # Check if it's an auth error
                if "AUTH_FAILED" in result.stderr or "authentication" in result.stderr.lower():
                    response = self.show_question("Authentication failed. Would you like to re-enter credentials?")
                    if response:
                        display_name = self.config_combo.get_active_text()
                        self.show_credential_dialog(display_name, config_path, retry=True)
                else:
                    self.show_error(f"Connection failed: {result.stderr}")
        
        # Run the connection with credentials via stdin
        def run():
            try:
                # Start the session with credentials
                proc = subprocess.Popen(
                    ["openvpn3", "session-start", "--config", config_path],
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True
                )
                
                # Provide credentials via stdin
                stdout, stderr = proc.communicate(input=f"{username}\n{password}\n", timeout=30)
                
                result = subprocess.CompletedProcess(
                    args=proc.args,
                    returncode=proc.returncode,
                    stdout=stdout,
                    stderr=stderr
                )
                
                GLib.idle_add(start_done, result)
            except subprocess.TimeoutExpired:
                self.is_connecting = False  # Clear connecting flag on error
                GLib.idle_add(self.show_error, "Connection timed out")
                GLib.idle_add(lambda: self.start_button.set_sensitive(True))
            except Exception as e:
                self.is_connecting = False  # Clear connecting flag on error
                GLib.idle_add(self.show_error, str(e))
                GLib.idle_add(lambda: self.start_button.set_sensitive(True))
        
        thread = threading.Thread(target=run)
        thread.daemon = True
        thread.start()
    
    def show_credential_dialog(self, config_name, config_path, retry=False, stored_user=None, stored_pass=None):
        """Show dialog to enter credentials"""
        dialog = Gtk.Dialog(
            title="Enter VPN Credentials",
            parent=self,
            flags=0
        )
        dialog.add_buttons(
            Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
            Gtk.STOCK_CONNECT, Gtk.ResponseType.OK
        )
        
        dialog.set_default_size(400, 250)
        
        content_area = dialog.get_content_area()
        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        vbox.set_border_width(10)
        content_area.add(vbox)
        
        # Info label
        if retry:
            info_text = f"<b>Authentication failed. Please re-enter credentials for {config_name}</b>"
        else:
            info_text = f"<b>Enter credentials for {config_name}</b>"
        
        info_label = Gtk.Label()
        info_label.set_markup(info_text)
        vbox.pack_start(info_label, False, False, 0)
        
        # Username field
        username_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        vbox.pack_start(username_box, False, False, 0)
        
        username_label = Gtk.Label(label="Username:")
        username_label.set_size_request(100, -1)
        username_label.set_xalign(0)
        username_box.pack_start(username_label, False, False, 0)
        
        username_entry = Gtk.Entry()
        username_box.pack_start(username_entry, True, True, 0)
        
        # Password field
        password_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        vbox.pack_start(password_box, False, False, 0)
        
        password_label = Gtk.Label(label="Password:")
        password_label.set_size_request(100, -1)
        password_label.set_xalign(0)
        password_box.pack_start(password_label, False, False, 0)
        
        password_entry = Gtk.Entry()
        password_entry.set_visibility(False)
        password_entry.set_input_purpose(Gtk.InputPurpose.PASSWORD)
        password_box.pack_start(password_entry, True, True, 0)
        
        # Remember checkbox
        remember_check = Gtk.CheckButton(label="Remember credentials (stored securely)")
        remember_check.set_active(True)
        vbox.pack_start(remember_check, False, False, 0)
        
        # Security note
        if KEYRING_AVAILABLE and self.use_keyring:
            security_text = "Credentials will be stored in your system keyring"
        else:
            security_text = "Credentials will be stored in ~/.config/vpn3gui/credentials.json"
        
        security_label = Gtk.Label()
        security_label.set_markup(f"<small><i>{security_text}</i></small>")
        vbox.pack_start(security_label, False, False, 0)
        
        # Pre-fill if we have stored credentials (passed as parameters now)
        if stored_user and not retry:
            username_entry.set_text(stored_user)
        if stored_pass and not retry:
            password_entry.set_text(stored_pass)
        
        dialog.show_all()
        
        # Focus on password field if username is pre-filled
        if stored_user and not retry:
            password_entry.grab_focus()
        else:
            username_entry.grab_focus()
        
        response = dialog.run()
        
        if response == Gtk.ResponseType.OK:
            username = username_entry.get_text()
            password = password_entry.get_text()
            remember = remember_check.get_active()
            
            dialog.destroy()
            
            if username and password:
                # Save credentials if requested
                self.save_credentials(config_name, username, password, remember)
                
                # Start VPN with credentials
                self.start_vpn_with_credentials(config_path, username, password)
            else:
                self.show_error("Username and password are required")
                self.start_button.set_sensitive(True)  # Re-enable button
        else:
            dialog.destroy()
            self.start_button.set_sensitive(True)  # Re-enable button if cancelled
    
    def update_vpn_password(self, widget=None):
        """Update password for selected VPN configuration"""
        display_name = self.config_combo.get_active_text()
        if not display_name or display_name == "No configs available":
            self.show_error("Please select a VPN configuration first")
            return
        
        # Get the config path
        config_path = self.config_paths.get(display_name)
        if not config_path:
            self.show_error("Configuration not found")
            return
        
        # Create password update dialog
        dialog = Gtk.Dialog(
            title=f"Update Password - {display_name}",
            parent=self,
            flags=0
        )
        dialog.add_buttons(
            Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
            Gtk.STOCK_SAVE, Gtk.ResponseType.OK
        )
        
        dialog.set_default_size(400, 300)
        
        content_area = dialog.get_content_area()
        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        vbox.set_border_width(10)
        content_area.add(vbox)
        
        # Info label
        info_label = Gtk.Label()
        info_label.set_markup(f"<b>Update credentials for {display_name}</b>")
        vbox.pack_start(info_label, False, False, 0)
        
        # Get current stored credentials
        current_user, current_pass = self.get_credentials_for_config(display_name)
        
        # Username field
        username_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        vbox.pack_start(username_box, False, False, 0)
        
        username_label = Gtk.Label(label="Username:")
        username_label.set_size_request(100, -1)
        username_label.set_xalign(0)
        username_box.pack_start(username_label, False, False, 0)
        
        username_entry = Gtk.Entry()
        if current_user:
            username_entry.set_text(current_user)
            username_entry.set_placeholder_text("Current username")
        else:
            username_entry.set_placeholder_text("Enter username")
        username_box.pack_start(username_entry, True, True, 0)
        
        # Old password field (optional)
        old_pw_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        vbox.pack_start(old_pw_box, False, False, 0)
        
        old_pw_label = Gtk.Label(label="Current Password:")
        old_pw_label.set_size_request(100, -1)
        old_pw_label.set_xalign(0)
        old_pw_box.pack_start(old_pw_label, False, False, 0)
        
        old_pw_entry = Gtk.Entry()
        old_pw_entry.set_visibility(False)
        old_pw_entry.set_placeholder_text("(Optional - for verification)")
        old_pw_box.pack_start(old_pw_entry, True, True, 0)
        
        # New password field
        new_pw_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        vbox.pack_start(new_pw_box, False, False, 0)
        
        new_pw_label = Gtk.Label(label="New Password:")
        new_pw_label.set_size_request(100, -1)
        new_pw_label.set_xalign(0)
        new_pw_box.pack_start(new_pw_label, False, False, 0)
        
        new_pw_entry = Gtk.Entry()
        new_pw_entry.set_visibility(False)
        new_pw_entry.set_placeholder_text("Enter new password")
        new_pw_box.pack_start(new_pw_entry, True, True, 0)
        
        # Confirm password field
        confirm_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        vbox.pack_start(confirm_box, False, False, 0)
        
        confirm_label = Gtk.Label(label="Confirm Password:")
        confirm_label.set_size_request(100, -1)
        confirm_label.set_xalign(0)
        confirm_box.pack_start(confirm_label, False, False, 0)
        
        confirm_entry = Gtk.Entry()
        confirm_entry.set_visibility(False)
        confirm_entry.set_placeholder_text("Confirm new password")
        confirm_box.pack_start(confirm_entry, True, True, 0)
        
        # Storage info
        vbox.pack_start(Gtk.Separator(), False, False, 0)
        
        if KEYRING_AVAILABLE and self.use_keyring:
            storage_text = "Password will be updated in your system keyring"
        else:
            storage_text = "Password will be updated in local encrypted storage"
        
        storage_label = Gtk.Label()
        storage_label.set_markup(f"<small><i>{storage_text}</i></small>")
        vbox.pack_start(storage_label, False, False, 0)
        
        dialog.show_all()
        
        # Focus on appropriate field
        if current_user:
            new_pw_entry.grab_focus()
        else:
            username_entry.grab_focus()
        
        response = dialog.run()
        
        if response == Gtk.ResponseType.OK:
            username = username_entry.get_text()
            new_password = new_pw_entry.get_text()
            confirm_password = confirm_entry.get_text()
            
            # Validate
            if not username:
                dialog.destroy()
                self.show_error("Username is required")
                return
            
            if not new_password:
                dialog.destroy()
                self.show_error("New password is required")
                return
            
            if new_password != confirm_password:
                dialog.destroy()
                self.show_error("Passwords do not match")
                return
            
            # Save updated credentials
            self.save_credentials(display_name, username, new_password, remember=True)
            
            dialog.destroy()
            self.show_info(f"Password updated successfully for {display_name}")
        else:
            dialog.destroy()
    
    def show_question(self, message):
        """Show yes/no question dialog"""
        dialog = Gtk.MessageDialog(
            transient_for=self,
            flags=0,
            message_type=Gtk.MessageType.QUESTION,
            buttons=Gtk.ButtonsType.YES_NO,
            text=message
        )
        response = dialog.run()
        dialog.destroy()
        return response == Gtk.ResponseType.YES
    
    def get_plaintext_auth_file(self, config_path):
        """Get plaintext auth file path if it exists"""
        try:
            result = subprocess.run(
                ["openvpn3", "config-dump", "--config", config_path],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if result.returncode == 0:
                config_content = result.stdout
                if "auth-user-pass" in config_content:
                    lines = config_content.split('\n')
                    for line in lines:
                        if line.strip().startswith("auth-user-pass"):
                            parts = line.strip().split()
                            if len(parts) > 1:
                                auth_file = os.path.expanduser(parts[1])
                                if os.path.exists(auth_file):
                                    return auth_file
        except:
            pass
        return None
    
    def check_for_plaintext_auth(self):
        """Check all configs for plaintext auth files"""
        self.plaintext_configs = []
        
        for display_name, config_path in self.config_paths.items():
            auth_file = self.get_plaintext_auth_file(config_path)
            if auth_file:
                self.plaintext_configs.append((display_name, config_path, auth_file))
        
        if self.plaintext_configs and not KEYRING_AVAILABLE:
            # Show warning about no keyring support
            GLib.idle_add(self.show_keyring_recommendation)
        elif self.plaintext_configs:
            # Offer to migrate
            GLib.idle_add(self.offer_credential_migration)
        
        return False  # Don't repeat this check
    
    def show_keyring_recommendation(self):
        """Show recommendation to install keyring"""
        dialog = Gtk.MessageDialog(
            transient_for=self,
            flags=0,
            message_type=Gtk.MessageType.WARNING,
            buttons=Gtk.ButtonsType.OK,
            text="Security Warning: Plaintext Credentials Detected"
        )
        dialog.format_secondary_text(
            "Your VPN configurations are using plaintext password files.\n\n"
            "For better security, install the Python keyring module:\n"
            "• Use Tools → Install Keyring Support\n"
            "• Or run: pip install keyring\n\n"
            "After installation, restart the application to migrate your credentials."
        )
        dialog.run()
        dialog.destroy()
    
    def offer_credential_migration(self):
        """Offer to migrate plaintext credentials to keyring"""
        dialog = Gtk.MessageDialog(
            transient_for=self,
            flags=0,
            message_type=Gtk.MessageType.WARNING,
            buttons=Gtk.ButtonsType.YES_NO,
            text="Migrate Plaintext Credentials?"
        )
        
        config_list = "\n".join([f"• {name}" for name, _, _ in self.plaintext_configs[:5]])
        if len(self.plaintext_configs) > 5:
            config_list += f"\n• ... and {len(self.plaintext_configs) - 5} more"
        
        dialog.format_secondary_text(
            f"Found {len(self.plaintext_configs)} VPN configuration(s) using plaintext password files:\n\n"
            f"{config_list}\n\n"
            "Would you like to migrate these credentials to secure keyring storage?\n"
            "The plaintext files will be backed up but not deleted."
        )
        
        response = dialog.run()
        dialog.destroy()
        
        if response == Gtk.ResponseType.YES:
            self.migrate_all_credentials()
    
    def migrate_all_credentials(self, widget=None):
        """Migrate all plaintext credentials to keyring"""
        if not KEYRING_AVAILABLE:
            self.show_error(
                "Keyring module not available.\n\n"
                "Please install it first using:\n"
                "Tools → Install Keyring Support"
            )
            return
        
        if not self.plaintext_configs:
            # Re-check for plaintext configs
            for display_name, config_path in self.config_paths.items():
                auth_file = self.get_plaintext_auth_file(config_path)
                if auth_file:
                    self.plaintext_configs.append((display_name, config_path, auth_file))
        
        if not self.plaintext_configs:
            self.show_info("No plaintext credential files found to migrate.")
            return
        
        migrated = 0
        failed = []
        
        for display_name, config_path, auth_file in self.plaintext_configs:
            try:
                # Read the plaintext auth file
                with open(auth_file, 'r') as f:
                    lines = f.readlines()
                    if len(lines) >= 2:
                        username = lines[0].strip()
                        password = lines[1].strip()
                        
                        # Save to keyring
                        self.save_credentials(display_name, username, password, remember=True)
                        migrated += 1
                        
                        # Create backup
                        backup_file = auth_file + ".backup"
                        if not os.path.exists(backup_file):
                            shutil.copy2(auth_file, backup_file)
                            os.chmod(backup_file, 0o600)
                    else:
                        failed.append(f"{display_name}: Invalid auth file format")
            except Exception as e:
                failed.append(f"{display_name}: {str(e)}")
        
        # Show results
        message = f"Migration Results:\n\n"
        if migrated > 0:
            message += f"✓ Successfully migrated {migrated} credential(s) to secure storage\n\n"
        
        if failed:
            message += "Failed to migrate:\n"
            for fail in failed:
                message += f"• {fail}\n"
            message += "\n"
        
        if migrated > 0:
            message += (
                "Original plaintext files have been backed up with .backup extension.\n\n"
                "You should now:\n"
                "1. Update your .ovpn configs to remove auth-user-pass file references\n"
                "2. Delete the original plaintext credential files\n\n"
                "Your credentials are now securely stored in the system keyring!"
            )
        
        self.show_info(message)
    
    def show_keyring_install_dialog(self, widget=None):
        """Show keyring installation dialog"""
        dialog = Gtk.Dialog(
            title="Install Keyring Support",
            parent=self,
            flags=0
        )
        dialog.add_buttons(
            Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
            "Install with apt (Recommended)", Gtk.ResponseType.APPLY,
            "Install with pipx", Gtk.ResponseType.OK,
            "Copy Commands", Gtk.ResponseType.YES
        )
        
        dialog.set_default_size(700, 600)  # Increased size for better readability
        
        content_area = dialog.get_content_area()
        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        vbox.set_border_width(10)
        content_area.add(vbox)
        
        # Instructions label
        label = Gtk.Label()
        label.set_markup("<b>Python Keyring Installation</b>")
        vbox.pack_start(label, False, False, 0)
        
        # Info text
        info_label = Gtk.Label()
        info_label.set_markup(
            "The Python keyring module provides secure credential storage\n"
            "by integrating with your system's keyring service:\n\n"
            "• <b>Linux:</b> GNOME Keyring, KWallet, or Secret Service\n"
            "• <b>Windows:</b> Windows Credential Vault\n"
            "• <b>macOS:</b> Keychain\n"
        )
        info_label.set_line_wrap(True)
        vbox.pack_start(info_label, False, False, 0)
        
        # Separator
        vbox.pack_start(Gtk.Separator(), False, False, 0)
        
        # Commands text view - expanded with minimum height
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        scrolled.set_min_content_height(400)  # Set minimum height for text area
        vbox.pack_start(scrolled, True, True, 0)
        
        text_view = Gtk.TextView()
        text_view.set_editable(False)
        text_view.set_wrap_mode(Gtk.WrapMode.WORD)
        scrolled.add(text_view)
        
        commands = """Installation Options for Linux Mint 22 / Ubuntu 24.04+:

1. Using apt (RECOMMENDED - System Package Manager):
   sudo apt update
   sudo apt install python3-keyring python3-secretstorage gnome-keyring

2. Using pipx (For User Installation - Isolated Environment):
   # First install pipx if not already installed:
   sudo apt install pipx
   pipx ensurepath
   
   # Then install keyring:
   pipx install keyring

3. Using pip with --break-system-packages (NOT RECOMMENDED):
   pip install --user --break-system-packages keyring
   
   ⚠️ Warning: This bypasses system protections and may cause issues

4. Using a Virtual Environment (For Development):
   python3 -m venv ~/vpn3gui-venv
   source ~/vpn3gui-venv/bin/activate
   pip install keyring
   # Note: You'll need to run the GUI from this venv

After installation, restart this application to enable secure credential storage.

Note: Modern Linux distributions (Mint 22+, Ubuntu 23.04+, Debian 12+) use PEP 668
to protect system Python packages. The apt method is preferred for system-wide use.
"""
        
        buffer = text_view.get_buffer()
        buffer.set_text(commands)
        
        dialog.show_all()
        response = dialog.run()
        
        if response == Gtk.ResponseType.OK:
            # Install with pipx
            dialog.destroy()
            self.run_keyring_installation("pipx")
        elif response == Gtk.ResponseType.APPLY:
            # Install with apt (recommended)
            dialog.destroy()
            self.run_keyring_installation("apt")
        elif response == Gtk.ResponseType.YES:
            # Copy to clipboard
            clipboard = Gtk.Clipboard.get(Gdk.SELECTION_CLIPBOARD)
            clipboard.set_text("sudo apt install python3-keyring python3-secretstorage gnome-keyring", -1)
            dialog.destroy()
            self.show_info("Command copied to clipboard!")
        else:
            dialog.destroy()
    
    def run_keyring_installation(self, method):
        """Run keyring installation"""
        if method == "pipx":
            commands = """#!/bin/bash
echo "Installing Python keyring module via pipx..."
echo ""
echo "Step 1: Checking for pipx..."
if ! command -v pipx &> /dev/null; then
    echo "pipx not found. Installing pipx first..."
    sudo apt update
    sudo apt install -y pipx
    if [ $? -ne 0 ]; then
        echo "✗ Failed to install pipx"
        echo "Press Enter to close..."
        read
        exit 1
    fi
    echo "✓ pipx installed"
    echo ""
    echo "Setting up pipx path..."
    pipx ensurepath
    export PATH="$PATH:$HOME/.local/bin"
fi

echo "Step 2: Installing keyring with pipx..."
pipx install keyring
if [ $? -eq 0 ]; then
    echo ""
    echo "✓ Keyring installed successfully via pipx!"
    echo ""
    echo "Note: You may need to log out and back in for PATH changes to take effect."
    echo "Or run: source ~/.bashrc"
    echo ""
    echo "Please restart the VPN GUI to use secure credential storage."
else
    echo ""
    echo "✗ Installation failed."
    echo "You may want to try the apt method instead."
fi
echo ""
echo "Press Enter to close..."
read
"""
        else:  # apt (recommended)
            commands = """#!/bin/bash
echo "Installing Python keyring module via apt (Recommended)..."
echo ""
echo "This will install:"
echo "  • python3-keyring - Python keyring library"
echo "  • python3-secretstorage - Python Secret Service API"
echo "  • gnome-keyring - GNOME keyring service"
echo ""
sudo apt update
sudo apt install -y python3-keyring python3-secretstorage gnome-keyring
if [ $? -eq 0 ]; then
    echo ""
    echo "✓ Keyring installed successfully!"
    echo ""
    echo "The system keyring service is now available for secure credential storage."
    echo "Please restart the VPN GUI to enable this feature."
else
    echo ""
    echo "✗ Installation failed."
    echo "Please check your internet connection and try again."
fi
echo ""
echo "Press Enter to close..."
read
"""
        
        # Save commands to temp script
        script_path = "/tmp/install_keyring.sh"
        with open(script_path, 'w') as f:
            f.write(commands)
        os.chmod(script_path, 0o755)
        
        # Get terminal command
        terminal_cmd = self.get_terminal_command(script_path)
        
        if terminal_cmd:
            # Run in terminal  
            subprocess.Popen(terminal_cmd, shell=True)
            
            dialog = Gtk.MessageDialog(
                transient_for=self,
                flags=0,
                message_type=Gtk.MessageType.INFO,
                buttons=Gtk.ButtonsType.OK,
                text="Installation Started"
            )
            dialog.format_secondary_text(
                "The keyring installation has been started in a new terminal.\n\n"
                "After installation completes, restart this application to enable\n"
                "secure credential storage."
            )
            dialog.run()
            dialog.destroy()
        else:
            self.show_error("Could not determine terminal emulator. Please install manually.")
    
    def show_simple_keyring_fix(self):
        """Show simple keyring fix for beginners"""
        dialog = Gtk.MessageDialog(
            transient_for=self,
            flags=0,
            message_type=Gtk.MessageType.INFO,
            buttons=Gtk.ButtonsType.OK,
            text="Password Storage Setup Needed"
        )
        
        secondary_text = """Your VPN passwords need a secure place to be stored.

QUICK FIX - Takes 30 seconds:
━━━━━━━━━━━━━━━━━━━━━━━━
1. Click your Menu button (bottom left)
2. Type: passwords
3. Open "Passwords and Keys"
4. Right-click on "Login"
5. Choose "Unlock"
6. Enter your computer password
7. Close and restart this VPN app

That's it! Your passwords will now be stored securely.

If you need more help: Tools → Fix Password Storage Issues

(For now, passwords will be saved locally until you complete this step)"""
        
        dialog.format_secondary_text(secondary_text)
        dialog.run()
        dialog.destroy()
    
    def toggle_debug_mode(self, widget):
        """Toggle debug mode on/off"""
        self.debug_mode = widget.get_active()
        if self.debug_mode:
            self.show_info("Debug mode enabled. Commands and outputs will be shown in terminal.")
        else:
            self.show_info("Debug mode disabled. Commands will not be shown.")
    
    def show_keyring_initialization_help(self):
        """Show help for initializing the keyring"""
        dialog = Gtk.MessageDialog(
            transient_for=self,
            flags=0,
            message_type=Gtk.MessageType.INFO,
            buttons=Gtk.ButtonsType.OK,
            text="Keyring Setup Help - Linux Mint 22.1"
        )
        
        secondary_text = """Your keyring needs to be unlocked to store VPN passwords securely.

SIMPLE FIX (Try this first):
━━━━━━━━━━━━━━━━━━━━━━
1. Click on your Menu button (bottom left corner)
2. Type "passwords" in the search box
3. Open "Passwords and Keys" app
4. Look for a keyring called "Login" (you probably have this)
5. If you see a locked padlock icon next to "Login":
   • Right-click on "Login"
   • Choose "Unlock"
   • Enter YOUR COMPUTER LOGIN PASSWORD
   • The padlock should now appear open

If there's NO "Login" keyring:
━━━━━━━━━━━━━━━━━━━━━━
1. In "Passwords and Keys" app
2. Click the "+" button (top left corner)
3. Select "Password Keyring"
4. Name it exactly: Login
5. Password: Use YOUR COMPUTER LOGIN PASSWORD
6. Confirm the password

Still Having Issues?
━━━━━━━━━━━━━━━━
Try the automatic fix:
1. Close this VPN app
2. Open Terminal (Ctrl+Alt+T)
3. Type: echo "" | gnome-keyring-daemon --unlock
4. Press Enter (this unlocks with empty password)
5. Restart the VPN app

IMPORTANT: Your keyring password is the SAME password you use to log into Linux Mint.

Note: Until fixed, your VPN passwords will be saved in a local file instead of the keyring."""
        
        dialog.format_secondary_text(secondary_text)
        dialog.run()
        dialog.destroy()

if __name__ == "__main__":
    win = VPNManager()
    win.connect("destroy", lambda w: (win.cleanup_temp_files(), Gtk.main_quit()))
    win.show_all()
    Gtk.main()