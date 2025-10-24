#!/bin/bash

# Inky Photo Frame - Installation Script
# For Raspberry Pi with Inky Impression 7.3" display

set -e  # Exit on error

echo "╔════════════════════════════════════════════════════════╗"
echo "║     📷 Inky Photo Frame - Installation                 ║"
echo "║     Universal - All Inky Impression Models             ║"
echo "╚════════════════════════════════════════════════════════╝"
echo ""
echo "⚠️  IMPORTANT: This script will enable I2C and SPI interfaces"
echo "   These are REQUIRED for the Inky display to work properly"
echo ""

# Variables
USER_NAME="inky"
# Generate a random 10-character password (alphanumeric only for compatibility)
USER_PASSWORD=$(< /dev/urandom tr -dc 'A-Za-z0-9' | head -c 10)
SMB_SHARE_NAME="Images"
PHOTOS_DIR="/home/pi/Images"
INSTALL_DIR="/home/pi/inky-photo-frame"
PASSWORD_FILE="/home/pi/.inky_credentials"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored messages
print_status() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_info() {
    echo -e "${YELLOW}ℹ️  $1${NC}"
}

# Check if running on Raspberry Pi
if [ ! -f /proc/device-tree/model ]; then
    print_error "This script must be run on a Raspberry Pi"
    exit 1
fi

print_status "Starting installation..."

# STEP 1: Enable I2C and SPI interfaces FIRST (CRITICAL for Inky display)
print_info "STEP 1: Enabling I2C and SPI interfaces (REQUIRED for Inky display)..."
print_info "This is the FIRST and MOST IMPORTANT step"

# Enable I2C
sudo raspi-config nonint do_i2c 0
if [ $? -eq 0 ]; then
    print_status "✅ I2C enabled successfully"
else
    print_error "Failed to enable I2C - Installation cannot continue!"
    print_error "The Inky display REQUIRES I2C to function"
    exit 1
fi

# Enable SPI
sudo raspi-config nonint do_spi 0
if [ $? -eq 0 ]; then
    print_status "✅ SPI enabled successfully"
else
    print_error "Failed to enable SPI - Installation cannot continue!"
    print_error "The Inky display REQUIRES SPI to function"
    exit 1
fi

# Load modules immediately
print_info "Loading I2C and SPI kernel modules..."
sudo modprobe i2c-dev
sudo modprobe spi-bcm2835
print_status "✅ I2C and SPI kernel modules loaded"

# STEP 2: Fix GPIO conflict for Inky display (AFTER I2C/SPI)
print_info "STEP 2: Configuring GPIO for Inky display..."
# Check if the dtoverlay line already exists
if ! grep -q "dtoverlay=spi0-1cs,cs0_pin=7" /boot/config.txt; then
    echo "dtoverlay=spi0-1cs,cs0_pin=7" | sudo tee -a /boot/config.txt > /dev/null
    print_status "GPIO configuration added to /boot/config.txt"
    REBOOT_REQUIRED=true
else
    print_status "GPIO configuration already present"
fi

# Also check if the dtoverlay line exists in firmware config
if [ -f /boot/firmware/config.txt ]; then
    if ! grep -q "dtoverlay=spi0-1cs,cs0_pin=7" /boot/firmware/config.txt; then
        echo "dtoverlay=spi0-1cs,cs0_pin=7" | sudo tee -a /boot/firmware/config.txt > /dev/null
        print_status "GPIO configuration added to /boot/firmware/config.txt"
        REBOOT_REQUIRED=true
    fi
fi

# STEP 2.5: Disable Raspberry Pi LEDs (no light pollution)
print_info "STEP 2.5: Disabling Raspberry Pi LEDs via systemd service..."

# Create systemd service to disable LEDs (more reliable than config.txt)
sudo tee /etc/systemd/system/disable-leds.service > /dev/null << 'EOF'
[Unit]
Description=Disable Raspberry Pi LEDs
After=multi-user.target

[Service]
Type=oneshot
ExecStart=/bin/sh -c 'echo none > /sys/class/leds/ACT/trigger'
ExecStart=/bin/sh -c 'echo 1 > /sys/class/leds/ACT/brightness'
RemainAfterExit=yes

[Install]
WantedBy=multi-user.target
EOF

# Enable and start the service
sudo systemctl enable disable-leds.service > /dev/null 2>&1
sudo systemctl start disable-leds.service > /dev/null 2>&1
print_status "LED disable service installed and enabled"

# STEP 3: Update system
print_info "STEP 3: Updating system packages..."
sudo apt-get update

# STEP 4: Install required system packages
print_info "STEP 4: Installing required packages..."
sudo apt-get install -y python3-pip python3-venv samba samba-common-bin git hostapd dnsmasq fonts-dejavu fonts-dejavu-core swig python3-dev liblgpio-dev

# STEP 5: Create photos directory
print_info "STEP 5: Creating photos directory..."
mkdir -p $PHOTOS_DIR
sudo chown pi:pi $PHOTOS_DIR
chmod 755 $PHOTOS_DIR

# STEP 6: Setup Python virtual environment
print_info "STEP 6: Setting up Python virtual environment..."
python3 -m venv ~/.virtualenvs/pimoroni
source ~/.virtualenvs/pimoroni/bin/activate

# STEP 7: Install Inky library
print_info "STEP 7: Installing Inky library..."
pip install --upgrade pip
pip install inky[rpi,example-depends]

# STEP 8: Install additional Python packages
print_info "STEP 8: Installing Python dependencies..."
pip install pillow pillow-heif watchdog lgpio RPi.GPIO gpiozero

# STEP 9: Create installation directory
print_info "STEP 9: Creating application directory..."
mkdir -p $INSTALL_DIR

# STEP 10: Download application files from GitHub
print_info "STEP 10: Downloading application files from GitHub..."

# List of files to download
FILES_TO_DOWNLOAD=(
    "inky_photo_frame.py"
    "update.sh"
    "inky-photo-frame-cli"
    "logrotate.conf"
)

# Always download from GitHub for consistency
for file in "${FILES_TO_DOWNLOAD[@]}"; do
    print_info "Downloading $file..."
    curl -sSL -o $INSTALL_DIR/$file https://raw.githubusercontent.com/mehdi7129/inky-photo-frame/main/$file
    if [ $? -ne 0 ]; then
        print_error "Failed to download $file"
        exit 1
    fi
    chmod +x $INSTALL_DIR/$file
done

print_status "Application files downloaded successfully"

# STEP 11: Configure Samba
print_info "STEP 11: Configuring SMB file sharing..."

# Backup existing smb.conf
sudo cp /etc/samba/smb.conf /etc/samba/smb.conf.backup

# Add SMB share configuration
sudo tee -a /etc/samba/smb.conf > /dev/null << EOF

[$SMB_SHARE_NAME]
   comment = Photo Frame Images
   path = $PHOTOS_DIR
   browseable = yes
   read only = no
   create mask = 0755
   directory mask = 0755
   valid users = $USER_NAME, pi
   write list = $USER_NAME, pi
   force user = pi
   force group = pi

   # iOS compatibility settings
   vfs objects = fruit streams_xattr
   fruit:metadata = stream
   fruit:model = MacSamba
   fruit:veto_appledouble = no
   fruit:posix_rename = yes
   fruit:zero_file_id = yes
   fruit:wipe_intentionally_left_blank_rfork = yes
   fruit:delete_empty_adfiles = yes
EOF

# STEP 12: Create SMB user
print_info "STEP 12: Creating SMB user '$USER_NAME'..."
# Check if user exists
if id "$USER_NAME" &>/dev/null; then
    print_info "User $USER_NAME already exists"
else
    sudo useradd -m $USER_NAME
fi

# Set SMB password
echo -e "$USER_PASSWORD\n$USER_PASSWORD" | sudo smbpasswd -a $USER_NAME -s
sudo smbpasswd -e $USER_NAME

# Also set pi user for SMB
echo -e "$USER_PASSWORD\n$USER_PASSWORD" | sudo smbpasswd -a pi -s
sudo smbpasswd -e pi

# Save credentials to file for display on Inky screen
print_info "Saving credentials..."
echo "$USER_NAME" | sudo tee "$PASSWORD_FILE" > /dev/null
echo "$USER_PASSWORD" | sudo tee -a "$PASSWORD_FILE" > /dev/null
sudo chmod 644 "$PASSWORD_FILE"
print_status "Credentials saved to $PASSWORD_FILE"

# Restart Samba
print_info "Restarting SMB service..."
sudo systemctl restart smbd
sudo systemctl enable smbd

# STEP 13: Create systemd service
print_info "STEP 13: Creating system service for automatic startup..."
sudo tee /etc/systemd/system/inky-photo-frame.service > /dev/null << EOF
[Unit]
Description=Inky Photo Frame Display Service
After=network.target

[Service]
Type=simple
User=pi
WorkingDirectory=$INSTALL_DIR
Environment="PATH=/home/pi/.virtualenvs/pimoroni/bin:/usr/bin:/bin"
ExecStart=/home/pi/.virtualenvs/pimoroni/bin/python $INSTALL_DIR/inky_photo_frame.py
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

# STEP 14: Install logrotate configuration
print_info "STEP 14: Installing log rotation..."
sudo cp $INSTALL_DIR/logrotate.conf /etc/logrotate.d/inky-photo-frame
sudo chown root:root /etc/logrotate.d/inky-photo-frame
sudo chmod 644 /etc/logrotate.d/inky-photo-frame
print_status "Log rotation configured (7 days retention)"

# STEP 15: Install CLI command
print_info "STEP 15: Installing CLI command..."
sudo cp $INSTALL_DIR/inky-photo-frame-cli /usr/local/bin/inky-photo-frame
sudo chmod +x /usr/local/bin/inky-photo-frame
print_status "CLI command installed: inky-photo-frame"

# STEP 16: Enable services (but don't start them if reboot is required)
print_info "STEP 16: Enabling automatic startup..."
sudo systemctl daemon-reload
sudo systemctl enable inky-photo-frame

# Only start services if no reboot is required (i.e., GPIO already configured)
if [ "$REBOOT_REQUIRED" != true ]; then
    print_info "Starting services..."
    sudo systemctl start inky-photo-frame
else
    print_info "Services will start automatically after reboot"
fi

# Get IP address
IP_ADDRESS=$(hostname -I | cut -d' ' -f1)

# Create README with instructions
cat > $INSTALL_DIR/README.md << EOF
# Inky Photo Frame

## 📱 How to Add Photos from Your Phone

### iPhone/iPad
1. Open the **Files** app
2. Tap **Connect to Server**
3. Enter: \`smb://$IP_ADDRESS\`
4. Use these credentials:
   - **Username:** $USER_NAME
   - **Password:** $USER_PASSWORD
5. Open the **Images** folder
6. Upload your photos (JPG, PNG, HEIC supported)

### Android
1. Use a file explorer app (CX File Explorer, Solid Explorer)
2. Connect to: \`smb://$IP_ADDRESS\`
3. Enter the same credentials as above
4. Navigate to **Images** folder
5. Upload your photos

## ✨ Features

- **Instant display** of new photos
- **Daily rotation** at 5AM
- **Smart history** - doesn't repeat recent photos
- **HEIC support** for iPhone photos
- **Smart cropping** for e-ink display

## 🛠 Useful Commands

\`\`\`bash
# Check service status
sudo systemctl status inky-photo-frame

# View logs
sudo journalctl -u inky-photo-frame -f

# Restart service
sudo systemctl restart inky-photo-frame

# Stop service
sudo systemctl stop inky-photo-frame
\`\`\`

## 📁 File Locations

- Photos: $PHOTOS_DIR
- Application: $INSTALL_DIR
- Logs: /home/pi/inky_photo_frame.log
- History: /home/pi/.inky_history.json
EOF

# Final status check only if services were started
if [ "$REBOOT_REQUIRED" != true ]; then
    print_info "Checking service status..."
    sleep 3
    sudo systemctl status inky-photo-frame --no-pager || true
fi

echo ""
echo "╔════════════════════════════════════════════════════════╗"
echo "║     ✅ Installation completed successfully!            ║"
echo "╚════════════════════════════════════════════════════════╝"
echo ""
echo "📱 HOW TO CONNECT FROM YOUR PHONE:"
echo "   iPhone/iPad: Open Files app"
echo "   Android: Use a file explorer (CX File Explorer, Solid Explorer)"
echo ""
echo "   For all devices:"
echo "   1. Connect to: smb://$IP_ADDRESS"
echo "   2. Username: $USER_NAME"
echo "   3. Password: $USER_PASSWORD"
echo ""
if [ "$REBOOT_REQUIRED" = true ]; then
    echo "📷 After reboot, the welcome screen will appear on your Inky display"
else
    echo "📷 The welcome screen is now displayed on your Inky display"
fi
echo "   Add photos to start your slideshow!"
echo ""
echo "🛠️  USEFUL COMMANDS:"
echo "   inky-photo-frame status    # Check service status"
echo "   inky-photo-frame logs      # View live logs"
echo "   inky-photo-frame update    # Update to latest version"
echo "   inky-photo-frame info      # Show system information"
echo "   inky-photo-frame help      # Show all commands"
echo ""
print_info "See $INSTALL_DIR/README.md for more info"

# Check if reboot is required
if [ "$REBOOT_REQUIRED" = true ]; then
    echo ""
    echo "╔════════════════════════════════════════════════════════╗"
    echo "║     ⚠️  REBOOT REQUIRED - IMPORTANT!                    ║"
    echo "╚════════════════════════════════════════════════════════╝"
    echo ""
    echo "The Inky display GPIO configuration has been updated."
    echo "A reboot is REQUIRED for the photo frame to work."
    echo ""
    echo "After reboot:"
    echo "1. The welcome screen will appear on your Inky display"
    echo "2. You can connect from your phone to add photos"
    echo ""
    echo "Please reboot now:"
    echo ""
    echo "  sudo reboot"
    echo ""
    echo "The photo frame will start automatically after reboot."
fi