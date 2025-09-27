#!/bin/bash

# Inky Photo Frame - Installation Script
# For Raspberry Pi with Inky Impression 7.3" display

set -e  # Exit on error

echo "╔════════════════════════════════════════════════════════╗"
echo "║     📷 Inky Photo Frame - Installation                 ║"
echo "║     Pour Inky Impression 7.3\" (800x480)               ║"
echo "╚════════════════════════════════════════════════════════╝"
echo ""
echo "⚠️  IMPORTANT: This script will enable I2C and SPI interfaces"
echo "   These are REQUIRED for the Inky display to work properly"
echo ""

# Variables
USER_NAME="inky"
USER_PASSWORD="inkyimpression73_2025"
SMB_SHARE_NAME="InkyPhotos"
PHOTOS_DIR="/home/pi/InkyPhotos"
INSTALL_DIR="/home/pi/inky-photo-frame"

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

# Enable I2C and SPI interfaces (REQUIRED for Inky display)
print_info "Enabling I2C and SPI interfaces for Inky display..."
sudo raspi-config nonint do_i2c 0
if [ $? -eq 0 ]; then
    print_status "I2C enabled successfully"
else
    print_error "Failed to enable I2C - Inky display may not work!"
fi

sudo raspi-config nonint do_spi 0
if [ $? -eq 0 ]; then
    print_status "SPI enabled successfully"
else
    print_error "Failed to enable SPI - Inky display may not work!"
fi

# Load modules immediately
sudo modprobe i2c-dev
sudo modprobe spi-bcm2835

# Update system
print_info "Updating system packages..."
sudo apt-get update

# Install required system packages
print_info "Installing required packages..."
sudo apt-get install -y python3-pip python3-venv samba samba-common-bin git bluetooth bluez python3-serial

# Create photos directory
print_info "Creating photos directory..."
mkdir -p $PHOTOS_DIR
sudo chown pi:pi $PHOTOS_DIR
chmod 755 $PHOTOS_DIR

# Setup Python virtual environment
print_info "Setting up Python virtual environment..."
python3 -m venv ~/.virtualenvs/pimoroni
source ~/.virtualenvs/pimoroni/bin/activate

# Install Inky library
print_info "Installing Inky library..."
pip install --upgrade pip
pip install inky[rpi,example-depends]

# Install additional Python packages
print_info "Installing Python dependencies..."
pip install pillow pillow-heif watchdog

# Create installation directory
print_info "Creating application directory..."
mkdir -p $INSTALL_DIR

# Copy application files
print_info "Copying application files..."
cp inky_photo_frame.py $INSTALL_DIR/
cp bluetooth_wifi_smart.py $INSTALL_DIR/
chmod +x $INSTALL_DIR/inky_photo_frame.py
chmod +x $INSTALL_DIR/bluetooth_wifi_smart.py

# Configure Samba
print_info "Configuring SMB file sharing..."

# Backup existing smb.conf
sudo cp /etc/samba/smb.conf /etc/samba/smb.conf.backup

# Add SMB share configuration
sudo tee -a /etc/samba/smb.conf > /dev/null << EOF

[$SMB_SHARE_NAME]
   comment = Inky Photo Frame Photos
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

# Create SMB user
print_info "Creating SMB user '$USER_NAME'..."
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

# Restart Samba
print_info "Restarting SMB service..."
sudo systemctl restart smbd
sudo systemctl enable smbd

# Create systemd service
print_info "Creating system service for automatic startup..."
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

# Create Bluetooth configuration service (auto-shutdown after 10 min)
print_info "Creating Smart Bluetooth WiFi configuration service..."
sudo tee /etc/systemd/system/inky-bluetooth-config.service > /dev/null << EOF
[Unit]
Description=Inky Smart Bluetooth Config (10 min auto-shutdown)
After=bluetooth.target network-pre.target
Before=network.target

[Service]
Type=simple
User=root
WorkingDirectory=$INSTALL_DIR
ExecStart=/usr/bin/python3 $INSTALL_DIR/bluetooth_wifi_smart.py
RemainAfterExit=no
StandardOutput=journal
StandardError=journal

# Don't restart - runs once at boot for 10 minutes only
Restart=no

[Install]
WantedBy=multi-user.target
EOF

# Enable and start services
print_info "Enabling automatic startup..."
sudo systemctl daemon-reload
sudo systemctl enable inky-photo-frame
sudo systemctl start inky-photo-frame
sudo systemctl enable inky-bluetooth-config
sudo systemctl start inky-bluetooth-config

# Get IP address
IP_ADDRESS=$(hostname -I | cut -d' ' -f1)

# Create README with instructions
cat > $INSTALL_DIR/README.md << EOF
# Inky Photo Frame

## 📱 Comment ajouter des photos depuis iPhone

1. Ouvrez l'app **Files/Fichiers** sur votre iPhone
2. Appuyez sur **Connect to Server** / **Se connecter au serveur**
3. Entrez: \`smb://$IP_ADDRESS\`
4. Utilisez ces identifiants:
   - **Utilisateur:** $USER_NAME
   - **Mot de passe:** $USER_PASSWORD
5. Ouvrez le dossier **$SMB_SHARE_NAME**
6. Déposez vos photos (JPG, PNG, HEIC supportés)

## ✨ Fonctionnalités

- **Affichage instantané** des nouvelles photos
- **Rotation quotidienne** à 5h du matin
- **Historique intelligent** - ne répète pas les photos
- **Support HEIC** pour les photos iPhone
- **Recadrage intelligent** pour l'écran e-ink

## 🛠 Commandes utiles

\`\`\`bash
# Voir le statut
sudo systemctl status inky-photo-frame

# Voir les logs
sudo journalctl -u inky-photo-frame -f

# Redémarrer le service
sudo systemctl restart inky-photo-frame

# Arrêter le service
sudo systemctl stop inky-photo-frame
\`\`\`

## 📁 Emplacements

- Photos: $PHOTOS_DIR
- Application: $INSTALL_DIR
- Logs: /home/pi/inky_photo_frame.log
- Historique: /home/pi/.inky_history.json
EOF

# Final status check
print_info "Checking service status..."
sleep 3
sudo systemctl status inky-photo-frame --no-pager

echo ""
echo "╔════════════════════════════════════════════════════════╗"
echo "║     ✅ Installation terminée avec succès!              ║"
echo "╚════════════════════════════════════════════════════════╝"
echo ""
echo "📱 CONNEXION DEPUIS VOTRE TÉLÉPHONE:"
echo "   iPhone/iPad: Ouvrez Files/Fichiers"
echo "   Android: Utilisez un explorateur de fichiers (CX File Explorer, Solid Explorer)"
echo ""
echo "   Pour tous:"
echo "   2. Connectez-vous à: smb://$IP_ADDRESS"
echo "   3. Utilisateur: $USER_NAME"
echo "   4. Mot de passe: $USER_PASSWORD"
echo ""
echo "📷 L'écran affiche actuellement un message de bienvenue"
echo "   Ajoutez des photos pour commencer!"
echo ""
print_info "Consultez $INSTALL_DIR/README.md pour plus d'infos"