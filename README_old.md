# 📷 Inky Photo Frame

Transform your Inky Impression 7.3" e-ink display into a beautiful digital photo frame controlled from any smartphone!

![Inky Impression 7.3"](https://img.shields.io/badge/Display-Inky%20Impression%207.3%22-purple)
![Raspberry Pi](https://img.shields.io/badge/Platform-Raspberry%20Pi-red)
![Python](https://img.shields.io/badge/Python-3.7+-blue)

## ✨ Features

- **Instant Display**: New photos appear immediately when added
- **Daily Rotation**: Automatic photo change every day at 5AM
- **Smart History**: Never repeats photos until all have been shown
- **Smartphone Compatible**: Upload photos from any phone (iPhone/Android) via SMB
- **HEIC Support**: Native support for iPhone photos + all common formats
- **Smart Cropping**: Intelligent image processing for e-ink display
- **Welcome Screen**: Shows connection instructions when no photos available
- **Smart Bluetooth**: WiFi config via Bluetooth (10 min window after boot - saves energy)

## 🚀 Quick Installation

### Prerequisites
- Raspberry Pi (Zero 2W, 3, 4, or 5)
- Inky Impression 7.3" display
- WiFi connection
- 30 minutes setup time

### One-Line Install

```bash
curl -sSL https://raw.githubusercontent.com/mehdi7129/inky-photo-frame/main/install.sh | bash
```

### Manual Installation

1. Clone the repository:
```bash
git clone https://github.com/mehdi7129/inky-photo-frame.git
cd inky-photo-frame
```

2. Run the installer:
```bash
chmod +x install.sh
./install.sh
```

## 📱 Adding Photos from Your Phone

### From iPhone/iPad:
1. Open the **Files** app
2. Tap **Connect to Server** (in Browse tab, tap ...)

### From Android:
1. Use a file manager like **Solid Explorer** or **CX File Explorer**
2. Add a network location (SMB)
3. Enter: `smb://[your-pi-ip]`
4. Use credentials:
   - **Username:** inky
   - **Password:** inkyimpression73_2025
5. Open the **InkyPhotos** folder
6. Add your photos (JPG, PNG, HEIC supported)

Photos will display immediately on your Inky screen!

## 📶 Smart WiFi Configuration via Bluetooth

If your WiFi settings change or you need to connect to a new network:

1. **Reboot the Raspberry Pi** (unplug/replug power)
2. **Within 10 minutes**, on your phone:
   - Enable Bluetooth
   - Pair with 'Inky-PhotoFrame'
   - Use a Bluetooth terminal app (Serial Bluetooth Terminal on Android or BlueTerm on iOS)
   - Follow the menu to configure WiFi

**🔋 Energy Smart:** Bluetooth automatically shuts down after 10 minutes to save power!

## 🎨 How It Works

The Inky Photo Frame uses a combination of:
- **File Watching**: Monitors the photos folder for new additions
- **Smart Queue**: Maintains history to avoid repetition
- **Daily Schedule**: Changes photos at 5AM automatically
- **Image Processing**: Optimizes photos for e-ink display

## 📁 File Structure

```
/home/pi/
├── InkyPhotos/              # Your photo library
├── inky-photo-frame/        # Application files
│   ├── inky_photo_frame.py  # Main application
│   └── README.md           # Documentation
├── .inky_history.json      # Photo history tracking
└── inky_photo_frame.log    # Application logs
```

## 🛠 Useful Commands

```bash
# Check status
sudo systemctl status inky-photo-frame

# View logs
sudo journalctl -u inky-photo-frame -f

# Restart service
sudo systemctl restart inky-photo-frame

# Stop service
sudo systemctl stop inky-photo-frame

# View photo history
cat ~/.inky_history.json | python3 -m json.tool
```

## 🔧 Configuration

Edit the configuration in `inky_photo_frame.py`:

```python
CHANGE_HOUR = 5  # Hour for daily change (24h format)
PHOTOS_DIR = Path('/home/pi/InkyPhotos')  # Photos location
```

## 🗑 Uninstallation

To remove the Inky Photo Frame:

```bash
chmod +x uninstall.sh
./uninstall.sh
```

## 📝 Troubleshooting

### Can't connect from iPhone
- Ensure Pi and iPhone are on same network
- Check Pi IP address: `hostname -I`
- Verify SMB service: `sudo systemctl status smbd`

### Photos not displaying
- Check supported formats: JPG, PNG, HEIC
- Verify service running: `sudo systemctl status inky-photo-frame`
- Check logs: `tail -f /home/pi/inky_photo_frame.log`

### Display not updating
- E-ink displays take ~30 seconds to refresh
- Check power connection to display
- Restart service: `sudo systemctl restart inky-photo-frame`

## 📄 License

MIT License - Feel free to modify and share!

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## 🙏 Acknowledgments

- [Pimoroni](https://shop.pimoroni.com) for the amazing Inky display
- Built with ❤️ for the Raspberry Pi community

---

**Enjoy your digital photo frame!** 📷✨