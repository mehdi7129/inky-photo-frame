#!/bin/bash

# Inky Photo Frame - Update Script
# Updates the application from GitHub

set -e

INSTALL_DIR="/home/pi/inky-photo-frame"
BACKUP_DIR="/home/pi/.inky-backups"
GITHUB_RAW="https://raw.githubusercontent.com/mehdi7129/inky-photo-frame/main"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

print_status() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_info() {
    echo -e "${YELLOW}ℹ️  $1${NC}"
}

echo "╔════════════════════════════════════════════════════════╗"
echo "║     🔄 Inky Photo Frame - Update from GitHub          ║"
echo "╚════════════════════════════════════════════════════════╝"
echo ""

# Check if installation exists
if [ ! -d "$INSTALL_DIR" ]; then
    print_error "Installation directory not found: $INSTALL_DIR"
    echo "Please run the installer first:"
    echo "  curl -sSL https://raw.githubusercontent.com/mehdi7129/inky-photo-frame/main/install.sh | bash"
    exit 1
fi

# Get current version
CURRENT_VERSION="unknown"
if [ -f "$INSTALL_DIR/inky_photo_frame.py" ]; then
    CURRENT_VERSION=$(grep "^VERSION = " "$INSTALL_DIR/inky_photo_frame.py" | cut -d'"' -f2)
fi

print_info "Current version: $CURRENT_VERSION"
print_info "Checking for updates..."

# Create backup directory
mkdir -p "$BACKUP_DIR"

# Backup current installation
BACKUP_NAME="backup_$(date +%Y%m%d_%H%M%S)"
print_info "Creating backup: $BACKUP_NAME"
cp -r "$INSTALL_DIR" "$BACKUP_DIR/$BACKUP_NAME"
print_status "Backup created"

# Stop the service
print_info "Stopping service..."
sudo systemctl stop inky-photo-frame

# Download new files
print_info "Downloading updates from GitHub..."

FILES_TO_UPDATE=(
    "inky_photo_frame.py"
    "update.sh"
    "inky-photo-frame-cli"
    "logrotate.conf"
)

for file in "${FILES_TO_UPDATE[@]}"; do
    print_info "Updating $file..."
    if curl -sSL -o "$INSTALL_DIR/$file.new" "$GITHUB_RAW/$file"; then
        mv "$INSTALL_DIR/$file.new" "$INSTALL_DIR/$file"
        chmod +x "$INSTALL_DIR/$file"
        print_status "$file updated"
    else
        print_error "Failed to download $file"
        print_info "Restoring from backup..."
        sudo systemctl stop inky-photo-frame
        rm -rf "$INSTALL_DIR"
        cp -r "$BACKUP_DIR/$BACKUP_NAME" "$INSTALL_DIR"
        sudo systemctl start inky-photo-frame
        print_error "Update failed, rolled back to previous version"
        exit 1
    fi
done

# Get new version
NEW_VERSION="unknown"
if [ -f "$INSTALL_DIR/inky_photo_frame.py" ]; then
    NEW_VERSION=$(grep "^VERSION = " "$INSTALL_DIR/inky_photo_frame.py" | cut -d'"' -f2)
fi

# Install/update Python dependencies
print_info "Installing Python dependencies..."
source ~/.virtualenvs/pimoroni/bin/activate
pip install --upgrade gpiozero pillow-heif watchdog > /dev/null 2>&1
print_status "Dependencies updated"

# Install CLI command to system
if [ -f "$INSTALL_DIR/inky-photo-frame-cli" ]; then
    print_info "Installing CLI command..."
    sudo cp "$INSTALL_DIR/inky-photo-frame-cli" /usr/local/bin/inky-photo-frame
    sudo chmod +x /usr/local/bin/inky-photo-frame
fi

# Install logrotate config
if [ -f "$INSTALL_DIR/logrotate.conf" ]; then
    print_info "Installing logrotate configuration..."
    sudo cp "$INSTALL_DIR/logrotate.conf" /etc/logrotate.d/inky-photo-frame
    sudo chown root:root /etc/logrotate.d/inky-photo-frame
    sudo chmod 644 /etc/logrotate.d/inky-photo-frame
fi

# Restart the service
print_info "Restarting service..."
sudo systemctl start inky-photo-frame

# Check if service started successfully
sleep 3
if sudo systemctl is-active --quiet inky-photo-frame; then
    print_status "Service restarted successfully"
    echo ""
    echo "╔════════════════════════════════════════════════════════╗"
    echo "║     ✅ Update completed successfully!                  ║"
    echo "╚════════════════════════════════════════════════════════╝"
    echo ""
    echo "Version: $CURRENT_VERSION → $NEW_VERSION"
    echo ""
    print_info "Backup saved to: $BACKUP_DIR/$BACKUP_NAME"
    print_info "Check logs: sudo journalctl -u inky-photo-frame -f"
else
    print_error "Service failed to start after update"
    print_info "Rolling back to previous version..."
    sudo systemctl stop inky-photo-frame
    rm -rf "$INSTALL_DIR"
    cp -r "$BACKUP_DIR/$BACKUP_NAME" "$INSTALL_DIR"
    sudo systemctl start inky-photo-frame
    print_error "Update failed, rolled back to version $CURRENT_VERSION"
    exit 1
fi

# Cleanup old backups (keep last 5)
print_info "Cleaning up old backups (keeping last 5)..."
cd "$BACKUP_DIR"
ls -t | tail -n +6 | xargs -r rm -rf
print_status "Cleanup complete"
