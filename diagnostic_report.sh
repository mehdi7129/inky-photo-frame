#!/bin/bash

# Diagnostic Report for Inky Photo Frame
# This script collects all relevant information about the current installation

OUTPUT_FILE="/home/pi/inky_diagnostic_report_$(date +%Y%m%d_%H%M%S).txt"

echo "=====================================" > $OUTPUT_FILE
echo "INKY PHOTO FRAME - DIAGNOSTIC REPORT" >> $OUTPUT_FILE
echo "=====================================" >> $OUTPUT_FILE
echo "Generated: $(date)" >> $OUTPUT_FILE
echo "" >> $OUTPUT_FILE

echo "1. SYSTEM INFORMATION" >> $OUTPUT_FILE
echo "---------------------" >> $OUTPUT_FILE
echo "Hostname: $(hostname)" >> $OUTPUT_FILE
echo "IP Address: $(hostname -I)" >> $OUTPUT_FILE
echo "Kernel: $(uname -a)" >> $OUTPUT_FILE
echo "Raspberry Pi Model:" >> $OUTPUT_FILE
cat /proc/device-tree/model >> $OUTPUT_FILE 2>/dev/null
echo "" >> $OUTPUT_FILE
echo "" >> $OUTPUT_FILE

echo "2. HARDWARE INTERFACES" >> $OUTPUT_FILE
echo "----------------------" >> $OUTPUT_FILE
echo "I2C Status:" >> $OUTPUT_FILE
ls -la /dev/i2c* >> $OUTPUT_FILE 2>&1
echo "" >> $OUTPUT_FILE
echo "SPI Status:" >> $OUTPUT_FILE
ls -la /dev/spidev* >> $OUTPUT_FILE 2>&1
echo "" >> $OUTPUT_FILE
echo "GPIO Chip Select Override:" >> $OUTPUT_FILE
vcgencmd get_config dtoverlay >> $OUTPUT_FILE 2>&1
echo "" >> $OUTPUT_FILE

echo "3. SERVICE STATUS" >> $OUTPUT_FILE
echo "-----------------" >> $OUTPUT_FILE
echo "Inky Photo Frame Service:" >> $OUTPUT_FILE
systemctl status inky-photo-frame --no-pager >> $OUTPUT_FILE 2>&1
echo "" >> $OUTPUT_FILE
echo "Bluetooth Config Service:" >> $OUTPUT_FILE
systemctl status inky-bluetooth-config --no-pager >> $OUTPUT_FILE 2>&1
echo "" >> $OUTPUT_FILE

echo "4. DIRECTORY STRUCTURE" >> $OUTPUT_FILE
echo "----------------------" >> $OUTPUT_FILE
echo "Images Directory:" >> $OUTPUT_FILE
ls -la /home/pi/Images/ >> $OUTPUT_FILE 2>&1
echo "Total images: $(find /home/pi/Images -type f \( -name "*.jpg" -o -name "*.png" -o -name "*.heic" \) 2>/dev/null | wc -l)" >> $OUTPUT_FILE
echo "" >> $OUTPUT_FILE
echo "Application Directory:" >> $OUTPUT_FILE
ls -la /home/pi/inky-photo-frame/ >> $OUTPUT_FILE 2>&1
echo "" >> $OUTPUT_FILE

echo "5. PYTHON ENVIRONMENT" >> $OUTPUT_FILE
echo "---------------------" >> $OUTPUT_FILE
echo "Python Version:" >> $OUTPUT_FILE
python3 --version >> $OUTPUT_FILE 2>&1
echo "" >> $OUTPUT_FILE
echo "Virtual Environment Packages:" >> $OUTPUT_FILE
/home/pi/.virtualenvs/pimoroni/bin/pip list >> $OUTPUT_FILE 2>&1
echo "" >> $OUTPUT_FILE

echo "6. SMB/SAMBA CONFIGURATION" >> $OUTPUT_FILE
echo "--------------------------" >> $OUTPUT_FILE
echo "SMB Status:" >> $OUTPUT_FILE
systemctl status smbd --no-pager | head -10 >> $OUTPUT_FILE 2>&1
echo "" >> $OUTPUT_FILE
echo "SMB Shares:" >> $OUTPUT_FILE
smbstatus -S >> $OUTPUT_FILE 2>&1
echo "" >> $OUTPUT_FILE
echo "SMB Users:" >> $OUTPUT_FILE
pdbedit -L >> $OUTPUT_FILE 2>&1
echo "" >> $OUTPUT_FILE

echo "7. RECENT LOGS (Last 50 lines)" >> $OUTPUT_FILE
echo "-------------------------------" >> $OUTPUT_FILE
echo "Service Logs:" >> $OUTPUT_FILE
journalctl -u inky-photo-frame -n 50 --no-pager >> $OUTPUT_FILE 2>&1
echo "" >> $OUTPUT_FILE

echo "8. HISTORY FILE" >> $OUTPUT_FILE
echo "---------------" >> $OUTPUT_FILE
if [ -f /home/pi/.inky_history.json ]; then
    echo "History file exists:" >> $OUTPUT_FILE
    cat /home/pi/.inky_history.json >> $OUTPUT_FILE 2>&1
else
    echo "No history file found" >> $OUTPUT_FILE
fi
echo "" >> $OUTPUT_FILE

echo "9. ISSUES FIXED DURING SESSION" >> $OUTPUT_FILE
echo "------------------------------" >> $OUTPUT_FILE
cat << 'EOF' >> $OUTPUT_FILE
RESOLVED ISSUES:
1. GPIO Conflict (GPIO8/Chip Select):
   - Added dtoverlay=spi0-1cs,cs0_pin=7 to /boot/config.txt
   - Fixed "pins we need are in use" error

2. SMB Permissions:
   - Changed from InkyPhotos to Images folder
   - Fixed write permissions (was read-only)
   - Removed duplicate "homes" share

3. File Watcher Stopping After First Image:
   - Fixed "Cannot send after transport endpoint shutdown" error
   - Added SPI connection cleanup after each display
   - Display now reinitializes after each image
   - File watcher continues detecting new images

4. Current Status:
   - System working correctly
   - Images display immediately when uploaded
   - Continuous detection working
   - No service restart needed
EOF
echo "" >> $OUTPUT_FILE

echo "10. CONFIG FILES" >> $OUTPUT_FILE
echo "----------------" >> $OUTPUT_FILE
echo "/boot/config.txt (relevant lines):" >> $OUTPUT_FILE
grep -E "(dtparam|dtoverlay|spi|i2c)" /boot/config.txt >> $OUTPUT_FILE 2>&1
echo "" >> $OUTPUT_FILE

echo "=====================================" >> $OUTPUT_FILE
echo "END OF DIAGNOSTIC REPORT" >> $OUTPUT_FILE
echo "=====================================" >> $OUTPUT_FILE

echo "Report saved to: $OUTPUT_FILE"
echo ""
echo "File size: $(ls -lh $OUTPUT_FILE | awk '{print $5}')"
echo ""
echo "You can copy this file before reformatting with:"
echo "scp pi@$(hostname -I | cut -d' ' -f1):$OUTPUT_FILE ."