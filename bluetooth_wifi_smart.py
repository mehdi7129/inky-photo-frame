#!/usr/bin/env python3
"""
Smart Bluetooth WiFi Configuration for Inky Photo Frame
- Auto-starts at boot
- Runs for 10 minutes only
- Auto-shutdown to save energy
"""

import os
import sys
import json
import subprocess
import time
import threading
from datetime import datetime, timedelta
from pathlib import Path
import logging

# Configuration
WIFI_CONFIG_FILE = Path('/home/pi/.inky_wifi_config.json')
BLUETOOTH_TIMEOUT_MINUTES = 10  # Bluetooth active for 10 minutes after boot
LOG_FILE = '/home/pi/bluetooth_config.log'

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler(sys.stdout)
    ]
)

class SmartBluetoothConfig:
    """Smart Bluetooth configuration with auto-shutdown"""

    def __init__(self):
        self.start_time = datetime.now()
        self.shutdown_time = self.start_time + timedelta(minutes=BLUETOOTH_TIMEOUT_MINUTES)
        self.running = False
        self.connected_client = False

    def check_boot_time(self):
        """Check system uptime to see if we just booted"""
        try:
            with open('/proc/uptime', 'r') as f:
                uptime_seconds = float(f.readline().split()[0])
                uptime_minutes = uptime_seconds / 60
                return uptime_minutes
        except:
            return 999  # Return high value if can't determine

    def should_run_bluetooth(self):
        """Determine if Bluetooth should be active"""
        uptime = self.check_boot_time()

        # Run if system booted less than 10 minutes ago
        if uptime <= BLUETOOTH_TIMEOUT_MINUTES:
            return True

        # Or if we're within our 10-minute window
        if datetime.now() < self.shutdown_time:
            return True

        return False

    def setup_bluetooth(self):
        """Enable Bluetooth with low power mode"""
        try:
            # Enable Bluetooth
            subprocess.run(['sudo', 'systemctl', 'start', 'bluetooth'], check=True)
            subprocess.run(['sudo', 'hciconfig', 'hci0', 'up'], check=True)

            # Set low power mode
            subprocess.run(['sudo', 'hciconfig', 'hci0', 'lp'], check=False)

            # Make discoverable
            subprocess.run(['sudo', 'hciconfig', 'hci0', 'piscan'], check=True)

            # Set friendly name
            subprocess.run(['sudo', 'hciconfig', 'hci0', 'name', 'Inky-PhotoFrame'], check=True)

            logging.info(f"✅ Bluetooth enabled for {BLUETOOTH_TIMEOUT_MINUTES} minutes")
            return True

        except Exception as e:
            logging.error(f"❌ Error setting up Bluetooth: {e}")
            return False

    def disable_bluetooth(self):
        """Disable Bluetooth to save energy"""
        try:
            logging.info("🔋 Disabling Bluetooth to save energy...")

            # Turn off Bluetooth
            subprocess.run(['sudo', 'hciconfig', 'hci0', 'down'], check=False)
            subprocess.run(['sudo', 'systemctl', 'stop', 'bluetooth'], check=False)

            logging.info("✅ Bluetooth disabled - saving power")

        except Exception as e:
            logging.error(f"Error disabling Bluetooth: {e}")

    def scan_wifi_networks(self):
        """Scan for available WiFi networks"""
        try:
            result = subprocess.run(['sudo', 'iwlist', 'wlan0', 'scan'],
                                  capture_output=True, text=True, timeout=10)
            networks = []
            for line in result.stdout.split('\n'):
                if 'ESSID:' in line:
                    ssid = line.split('ESSID:')[1].strip('"')
                    if ssid and ssid not in networks:
                        networks.append(ssid)
            return networks
        except Exception as e:
            logging.error(f"Error scanning networks: {e}")
            return []

    def connect_wifi(self, ssid, password):
        """Connect to WiFi network"""
        try:
            # Create wpa_supplicant config
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
            # Write config
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
            if result.stdout.strip() == ssid:
                # Save config
                config = {'ssid': ssid, 'password': password, 'configured_at': datetime.now().isoformat()}
                with open(WIFI_CONFIG_FILE, 'w') as f:
                    json.dump(config, f, indent=2)
                return True

            return False

        except Exception as e:
            logging.error(f"Error connecting to WiFi: {e}")
            return False

    def get_ip_address(self):
        """Get current IP address"""
        try:
            result = subprocess.run(['hostname', '-I'], capture_output=True, text=True)
            ips = result.stdout.strip().split()
            return ips[0] if ips else None
        except:
            return None

    def handle_bluetooth_connection(self):
        """Handle Bluetooth serial connection"""
        import serial

        try:
            # Setup RFCOMM
            subprocess.run(['sudo', 'rfcomm', 'release', '0'], check=False)

            # Start listening in background
            rfcomm_proc = subprocess.Popen(
                ['sudo', 'rfcomm', 'listen', '/dev/rfcomm0', '1'],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )

            logging.info("📱 Waiting for Bluetooth connections...")

            # Wait for device file to appear
            timeout = 0
            while not Path('/dev/rfcomm0').exists() and timeout < 30:
                time.sleep(1)
                timeout += 1

                # Check if we should shutdown
                if not self.should_run_bluetooth():
                    logging.info("⏰ Bluetooth timeout - shutting down")
                    rfcomm_proc.terminate()
                    return

            if not Path('/dev/rfcomm0').exists():
                return

            # Handle connection
            with serial.Serial('/dev/rfcomm0', 9600, timeout=1) as bt:
                self.connected_client = True
                logging.info("✅ Client connected via Bluetooth")

                # Send welcome
                bt.write(b'\r\n=== Inky WiFi Config (10 min window) ===\r\n')
                bt.write(b'1 - Scan WiFi\r\n')
                bt.write(b'2 - Connect WiFi\r\n')
                bt.write(b'3 - Status\r\n')
                bt.write(b'> ')

                while self.connected_client and self.should_run_bluetooth():
                    if bt.in_waiting:
                        cmd = bt.readline().decode().strip()

                        if cmd == '1':
                            bt.write(b'\r\nScanning...\r\n')
                            networks = self.scan_wifi_networks()
                            for i, ssid in enumerate(networks, 1):
                                bt.write(f'{i}. {ssid}\r\n'.encode())

                        elif cmd == '2':
                            bt.write(b'SSID: ')
                            ssid = bt.readline().decode().strip()
                            bt.write(b'Password: ')
                            password = bt.readline().decode().strip()

                            bt.write(b'Connecting...\r\n')
                            if self.connect_wifi(ssid, password):
                                ip = self.get_ip_address()
                                bt.write(f'✅ Connected! IP: {ip}\r\n'.encode())
                                # Extend timeout by 2 minutes after successful config
                                self.shutdown_time = datetime.now() + timedelta(minutes=2)
                            else:
                                bt.write(b'❌ Failed\r\n')

                        elif cmd == '3':
                            ip = self.get_ip_address()
                            if ip:
                                bt.write(f'Connected: {ip}\r\n'.encode())
                            else:
                                bt.write(b'Not connected\r\n')

                        bt.write(b'\r\n> ')

        except Exception as e:
            logging.error(f"Bluetooth error: {e}")
        finally:
            subprocess.run(['sudo', 'rfcomm', 'release', '0'], check=False)
            self.connected_client = False

    def run(self):
        """Main run loop with auto-shutdown"""
        uptime = self.check_boot_time()

        # Don't run if system has been up too long
        if uptime > BLUETOOTH_TIMEOUT_MINUTES + 5:  # 5 min grace period
            logging.info(f"System uptime {uptime:.1f} min - Bluetooth not needed")
            return

        logging.info(f"🚀 Starting Smart Bluetooth Config")
        logging.info(f"⏰ Will auto-shutdown in {BLUETOOTH_TIMEOUT_MINUTES} minutes")
        logging.info(f"🔋 Energy-saving mode enabled")

        if not self.setup_bluetooth():
            return

        self.running = True

        # Auto-shutdown timer
        def shutdown_timer():
            while self.running:
                if not self.should_run_bluetooth():
                    logging.info("⏰ Time's up - shutting down Bluetooth")
                    self.running = False
                    break
                time.sleep(10)

            self.disable_bluetooth()

        # Start shutdown timer in background
        timer_thread = threading.Thread(target=shutdown_timer)
        timer_thread.daemon = True
        timer_thread.start()

        # Main loop
        try:
            while self.running:
                self.handle_bluetooth_connection()

                # Check if we should continue
                if not self.should_run_bluetooth():
                    break

                time.sleep(1)

        except KeyboardInterrupt:
            logging.info("Interrupted by user")
        finally:
            self.running = False
            self.disable_bluetooth()

if __name__ == '__main__':
    # Only run if we're early in boot cycle
    config = SmartBluetoothConfig()
    config.run()