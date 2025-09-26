#!/usr/bin/env python3
"""
Bluetooth WiFi Configuration for Inky Photo Frame
Allows WiFi configuration via Bluetooth when no network connection
"""

import os
import sys
import json
import subprocess
import time
import threading
from pathlib import Path
import dbus
import dbus.service
import dbus.mainloop.glib
from gi.repository import GLib

# Configuration file
WIFI_CONFIG_FILE = Path('/home/pi/.inky_wifi_config.json')

class WiFiConfig:
    """Manage WiFi configuration"""

    @staticmethod
    def scan_networks():
        """Scan for available WiFi networks"""
        try:
            result = subprocess.run(['sudo', 'iwlist', 'wlan0', 'scan'],
                                  capture_output=True, text=True)
            networks = []
            for line in result.stdout.split('\n'):
                if 'ESSID:' in line:
                    ssid = line.split('ESSID:')[1].strip('"')
                    if ssid and ssid not in networks:
                        networks.append(ssid)
            return networks
        except Exception as e:
            print(f"Error scanning networks: {e}")
            return []

    @staticmethod
    def connect_to_network(ssid, password):
        """Connect to a WiFi network"""
        try:
            # Create wpa_supplicant entry
            wpa_config = f'''
country=FR
ctrl_interface=DIR=/var/run/wpa_supplicant GROUP=netdev
update_config=1

network={{
    ssid="{ssid}"
    psk="{password}"
    key_mgmt=WPA-PSK
}}
'''
            # Write configuration
            with open('/tmp/wpa_temp.conf', 'w') as f:
                f.write(wpa_config)

            # Apply configuration
            subprocess.run(['sudo', 'cp', '/tmp/wpa_temp.conf',
                          '/etc/wpa_supplicant/wpa_supplicant.conf'], check=True)

            # Restart WiFi
            subprocess.run(['sudo', 'wpa_cli', '-i', 'wlan0', 'reconfigure'], check=True)

            # Wait for connection
            time.sleep(5)

            # Check if connected
            result = subprocess.run(['iwgetid', '-r'], capture_output=True, text=True)
            connected_ssid = result.stdout.strip()

            if connected_ssid == ssid:
                # Save configuration
                config = {'ssid': ssid, 'password': password}
                with open(WIFI_CONFIG_FILE, 'w') as f:
                    json.dump(config, f)
                return True

            return False

        except Exception as e:
            print(f"Error connecting to network: {e}")
            return False

    @staticmethod
    def get_current_ip():
        """Get current IP address"""
        try:
            result = subprocess.run(['hostname', '-I'], capture_output=True, text=True)
            ips = result.stdout.strip().split()
            return ips[0] if ips else None
        except:
            return None

class BluetoothService(dbus.service.Object):
    """Bluetooth LE GATT Service for WiFi configuration"""

    UART_SERVICE_UUID = '6e400001-b5a3-f393-e0a9-e50e24dcca9e'
    RX_CHAR_UUID = '6e400002-b5a3-f393-e0a9-e50e24dcca9e'
    TX_CHAR_UUID = '6e400003-b5a3-f393-e0a9-e50e24dcca9e'

    def __init__(self, bus, path):
        super().__init__(bus, path)
        self.wifi_config = WiFiConfig()
        self.command_buffer = ""

    @dbus.service.method('org.bluez.GattCharacteristic1',
                        in_signature='ay', out_signature='')
    def WriteValue(self, value, options):
        """Handle incoming data from Bluetooth"""
        try:
            # Convert byte array to string
            data = ''.join([chr(b) for b in value])
            self.command_buffer += data

            # Check for complete command (ending with \n)
            if '\n' in self.command_buffer:
                command = self.command_buffer.strip()
                self.command_buffer = ""

                # Process command
                response = self.process_command(command)

                # Send response back
                self.send_response(response)

        except Exception as e:
            self.send_response(f"ERROR: {str(e)}")

    def process_command(self, command):
        """Process incoming commands"""
        try:
            parts = command.split(':')
            cmd = parts[0].upper()

            if cmd == 'SCAN':
                # Scan for WiFi networks
                networks = self.wifi_config.scan_networks()
                return 'NETWORKS:' + ','.join(networks)

            elif cmd == 'CONNECT' and len(parts) == 3:
                # Connect to WiFi network
                ssid = parts[1]
                password = parts[2]
                success = self.wifi_config.connect_to_network(ssid, password)
                if success:
                    ip = self.wifi_config.get_current_ip()
                    return f'CONNECTED:{ip}'
                else:
                    return 'FAILED:Could not connect'

            elif cmd == 'STATUS':
                # Get current status
                ip = self.wifi_config.get_current_ip()
                if ip:
                    return f'STATUS:Connected,{ip}'
                else:
                    return 'STATUS:Not connected'

            elif cmd == 'HELP':
                return 'COMMANDS:SCAN,CONNECT:ssid:password,STATUS,HELP'

            else:
                return 'ERROR:Unknown command'

        except Exception as e:
            return f'ERROR:{str(e)}'

    def send_response(self, response):
        """Send response via Bluetooth notification"""
        # This would send notification to connected device
        print(f"BT Response: {response}")

class InkyBluetoothConfig:
    """Main Bluetooth configuration service"""

    def __init__(self):
        self.running = False

    def setup_bluetooth(self):
        """Setup Bluetooth LE advertising"""
        try:
            # Enable Bluetooth
            subprocess.run(['sudo', 'hciconfig', 'hci0', 'up'], check=True)

            # Set device name
            subprocess.run(['sudo', 'hciconfig', 'hci0', 'name', 'Inky-PhotoFrame'],
                         check=True)

            # Set device as discoverable
            subprocess.run(['sudo', 'hciconfig', 'hci0', 'leadv', '0'], check=True)

            print("✅ Bluetooth enabled: Inky-PhotoFrame")
            return True

        except Exception as e:
            print(f"❌ Error setting up Bluetooth: {e}")
            return False

    def run(self):
        """Run the Bluetooth service"""
        if not self.setup_bluetooth():
            return

        print("🔵 Bluetooth WiFi configuration service started")
        print("📱 Connect to 'Inky-PhotoFrame' from your phone's Bluetooth settings")
        print("")
        print("Available commands (via Bluetooth terminal app):")
        print("  SCAN              - List available WiFi networks")
        print("  CONNECT:ssid:pass - Connect to WiFi network")
        print("  STATUS            - Get connection status")
        print("  HELP              - Show commands")
        print("")
        print("Press Ctrl+C to stop")

        self.running = True

        try:
            # Initialize D-Bus
            dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
            bus = dbus.SystemBus()

            # Create service
            service = BluetoothService(bus, '/org/bluez/inky')

            # Run main loop
            loop = GLib.MainLoop()
            loop.run()

        except KeyboardInterrupt:
            print("\n👋 Stopping Bluetooth service")
        except Exception as e:
            print(f"❌ Error: {e}")
        finally:
            self.running = False
            subprocess.run(['sudo', 'hciconfig', 'hci0', 'noleadv'], check=False)

# Simple terminal-based alternative (without D-Bus)
class SimpleBluetoothConfig:
    """Simplified Bluetooth configuration using rfcomm"""

    def __init__(self):
        self.wifi_config = WiFiConfig()

    def setup_rfcomm(self):
        """Setup RFCOMM for serial communication"""
        try:
            # Enable Bluetooth
            subprocess.run(['sudo', 'systemctl', 'start', 'bluetooth'], check=True)
            subprocess.run(['sudo', 'hciconfig', 'hci0', 'up'], check=True)
            subprocess.run(['sudo', 'hciconfig', 'hci0', 'piscan'], check=True)

            # Set friendly name
            subprocess.run(['sudo', 'hciconfig', 'hci0', 'name', 'Inky-PhotoFrame'],
                         check=True)

            # Start rfcomm listen
            print("✅ Bluetooth enabled: Inky-PhotoFrame")
            print("📱 Pair with 'Inky-PhotoFrame' from your phone")
            print("📲 Use a Bluetooth terminal app to connect")
            print("")

            return True

        except Exception as e:
            print(f"❌ Error: {e}")
            return False

    def handle_connection(self):
        """Handle Bluetooth serial connection"""
        import serial

        try:
            # Open RFCOMM port
            with serial.Serial('/dev/rfcomm0', 9600, timeout=1) as bt_serial:
                print("✅ Client connected via Bluetooth")

                # Send welcome message
                bt_serial.write(b'\r\n=== Inky Photo Frame WiFi Config ===\r\n')
                bt_serial.write(b'Commands:\r\n')
                bt_serial.write(b'  1 - Scan WiFi networks\r\n')
                bt_serial.write(b'  2 - Connect to WiFi\r\n')
                bt_serial.write(b'  3 - Show status\r\n')
                bt_serial.write(b'  4 - Exit\r\n')
                bt_serial.write(b'> ')

                while True:
                    # Read command
                    if bt_serial.in_waiting:
                        cmd = bt_serial.readline().decode().strip()

                        if cmd == '1':
                            # Scan networks
                            bt_serial.write(b'\r\nScanning...\r\n')
                            networks = self.wifi_config.scan_networks()
                            for i, ssid in enumerate(networks, 1):
                                bt_serial.write(f'{i}. {ssid}\r\n'.encode())

                        elif cmd == '2':
                            # Connect to network
                            bt_serial.write(b'Enter SSID: ')
                            ssid = bt_serial.readline().decode().strip()
                            bt_serial.write(b'Enter password: ')
                            password = bt_serial.readline().decode().strip()

                            bt_serial.write(b'Connecting...\r\n')
                            if self.wifi_config.connect_to_network(ssid, password):
                                ip = self.wifi_config.get_current_ip()
                                bt_serial.write(f'✅ Connected! IP: {ip}\r\n'.encode())
                            else:
                                bt_serial.write(b'❌ Failed to connect\r\n')

                        elif cmd == '3':
                            # Show status
                            ip = self.wifi_config.get_current_ip()
                            if ip:
                                bt_serial.write(f'Connected - IP: {ip}\r\n'.encode())
                            else:
                                bt_serial.write(b'Not connected\r\n')

                        elif cmd == '4':
                            bt_serial.write(b'Goodbye!\r\n')
                            break

                        bt_serial.write(b'\r\n> ')

        except Exception as e:
            print(f"Connection error: {e}")

    def run(self):
        """Run the simplified Bluetooth service"""
        if not self.setup_rfcomm():
            return

        print("Waiting for Bluetooth connections...")
        print("Press Ctrl+C to stop")

        try:
            # Create RFCOMM socket
            subprocess.run(['sudo', 'rfcomm', 'release', '0'], check=False)
            proc = subprocess.Popen(['sudo', 'rfcomm', 'listen', '/dev/rfcomm0', '1'],
                                   stdout=subprocess.PIPE, stderr=subprocess.PIPE)

            # Wait for connection and handle it
            while True:
                time.sleep(1)
                if Path('/dev/rfcomm0').exists():
                    self.handle_connection()

        except KeyboardInterrupt:
            print("\n👋 Stopping Bluetooth service")
        finally:
            subprocess.run(['sudo', 'rfcomm', 'release', '0'], check=False)
            subprocess.run(['sudo', 'hciconfig', 'hci0', 'noscan'], check=False)

if __name__ == '__main__':
    # Use the simple version that doesn't require D-Bus
    config = SimpleBluetoothConfig()
    config.run()