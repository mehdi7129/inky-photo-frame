#!/bin/bash

# Inky Photo Frame - Uninstall Script

echo "╔════════════════════════════════════════════════════════╗"
echo "║     🗑️  Inky Photo Frame - Désinstallation             ║"
echo "╚════════════════════════════════════════════════════════╝"
echo ""

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

print_status() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_info() {
    echo -e "${YELLOW}ℹ️  $1${NC}"
}

# Confirmation
echo -e "${YELLOW}⚠️  Cette action va désinstaller Inky Photo Frame${NC}"
echo "Les photos dans /home/pi/InkyPhotos seront conservées"
read -p "Voulez-vous continuer? (y/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Désinstallation annulée"
    exit 1
fi

# Stop and disable services
print_info "Arrêt des services..."
sudo systemctl stop inky-photo-frame
sudo systemctl disable inky-photo-frame
sudo rm /etc/systemd/system/inky-photo-frame.service
sudo systemctl daemon-reload

# Remove SMB share
print_info "Suppression du partage SMB..."
sudo cp /etc/samba/smb.conf /etc/samba/smb.conf.uninstall-backup
sudo sed -i '/\[InkyPhotos\]/,/^$/d' /etc/samba/smb.conf
sudo systemctl restart smbd

# Remove application files
print_info "Suppression des fichiers de l'application..."
rm -rf /home/pi/inky-photo-frame

# Keep photos and history
print_info "Conservation des photos et de l'historique..."

# Optional: Remove user
echo ""
read -p "Voulez-vous supprimer l'utilisateur 'inky'? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    sudo smbpasswd -x inky
    sudo userdel inky
    print_status "Utilisateur inky supprimé"
fi

# Optional: Remove photos
echo ""
read -p "Voulez-vous supprimer les photos? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    rm -rf /home/pi/InkyPhotos
    rm -f /home/pi/.inky_history.json
    rm -f /home/pi/inky_photo_frame.log
    print_status "Photos et historique supprimés"
else
    print_info "Photos conservées dans /home/pi/InkyPhotos"
fi

echo ""
print_status "Désinstallation terminée!"
echo ""
echo "Pour réinstaller, exécutez:"
echo "  ./install.sh"