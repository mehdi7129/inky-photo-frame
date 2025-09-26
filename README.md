# 🖼️ Inky Photo Frame

<div align="center">

![Inky Impression 7.3"](https://cdn.shopify.com/s/files/1/0174/1800/files/inky-impression-7-3-2_1500x1500_crop_center.jpg)

**Transform your Inky Impression 7.3" into a stunning digital photo frame**

[![GitHub](https://img.shields.io/github/stars/mehdi7129/inky-photo-frame?style=social)](https://github.com/mehdi7129/inky-photo-frame)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Platform](https://img.shields.io/badge/platform-Raspberry%20Pi-red)](https://www.raspberrypi.org/)
[![Display](https://img.shields.io/badge/display-Inky%207.3%22-purple)](https://shop.pimoroni.com/products/inky-impression-7-3)

[**📥 Quick Install**](#-quick-installation) • [**📱 Phone Setup**](#-upload-photos-from-your-phone) • [**🔧 WiFi Config**](#-smart-wifi-configuration) • [**📖 Full Guide**](INSTALLATION_GUIDE.md)

</div>

---

## ✨ What Makes It Special?

<table>
<tr>
<td width="50%">

### 🎨 **Beautiful E-Ink Display**
- **800x480 pixels** - Crystal clear
- **7 colors** - Vibrant Spectra display
- **No backlight** - Easy on the eyes
- **Persistent** - Image stays without power

</td>
<td width="50%">

### 🔋 **Ultra Low Power**
- **0.6W average** - Less than an LED bulb
- **Zero power** when displaying
- **10x more efficient** than LCD frames
- **< 1€/year** electricity cost

</td>
</tr>
</table>

## 📸 Features at a Glance

<div align="center">

| Feature | Description |
|---------|------------|
| 📲 **Instant Display** | New photos appear immediately when added |
| 🔄 **Smart Rotation** | Daily change at 5AM with intelligent history |
| 📱 **Universal** | Works with iPhone, Android, any smartphone |
| 🔵 **Smart Bluetooth** | 10-minute WiFi setup window after boot |
| 🖼️ **HEIC Support** | Native support for modern phone formats |
| ✂️ **Smart Cropping** | Automatic optimization for e-ink |

</div>

## 🚀 Quick Installation

### One-Line Install
```bash
curl -sSL https://raw.githubusercontent.com/mehdi7129/inky-photo-frame/main/install.sh | bash
```

That's it! The installer handles everything:
- ✅ Dependencies
- ✅ SMB file sharing
- ✅ Auto-start on boot
- ✅ Bluetooth configuration

## 📱 Upload Photos from Your Phone

<table>
<tr>
<td width="50%" align="center">

### iPhone / iPad

<img src="https://cdn.shopify.com/s/files/1/0174/1800/files/7colour-eink-2_1500x1500_crop_center.jpg" width="300">

1. Open **Files** app
2. Tap **Connect to Server**
3. Enter: `smb://[your-pi-ip]`
4. Login: `inky` / `inkyimpression73_2025`
5. Drop photos in **InkyPhotos**

</td>
<td width="50%" align="center">

### Android

<img src="https://cdn.shopify.com/s/files/1/0174/1800/files/inky-impression-7-3-4_1500x1500_crop_center.jpg" width="300">

1. Install **CX File Explorer**
2. Add network location (SMB)
3. Enter: `smb://[your-pi-ip]`
4. Login: `inky` / `inkyimpression73_2025`
5. Upload to **InkyPhotos**

</td>
</tr>
</table>

## 🎯 How It Works

<div align="center">
<img src="https://cdn.shopify.com/s/files/1/0174/1800/files/inky-impression-7-3-1_1500x1500_crop_center.jpg" width="600">
</div>

### Welcome Screen
When first powered on, the display shows:
- 📍 Your Raspberry Pi IP address
- 🔐 Login credentials
- 📝 Step-by-step instructions

### Smart Photo Management
```mermaid
graph LR
    A[Add Photo] -->|Instant| B[Display]
    B --> C[Save History]
    C --> D[Daily Rotation]
    D -->|5AM| E[Next Photo]
    E -->|Never Repeat| C
```

## 🔧 Smart WiFi Configuration

**Lost WiFi? No SSH needed!**

1. 🔌 **Reboot** your Raspberry Pi
2. 📱 **Connect** via Bluetooth within 10 minutes
3. ⚙️ **Configure** new WiFi settings
4. 🔋 **Auto-shutdown** Bluetooth after 10 min (saves energy!)

## 📦 What You Need

<table>
<tr>
<td align="center">

<img src="https://cdn.shopify.com/s/files/1/0174/1800/files/inky-impression-7-3-3_500x500_crop_center.jpg" width="200">

**Inky Impression 7.3"**

[Buy from Pimoroni](https://shop.pimoroni.com/products/inky-impression-7-3)

</td>
<td align="center">

<img src="https://www.raspberrypi.com/app/uploads/2022/02/zero2-close-up-500x283.jpg" width="200">

**Raspberry Pi Zero 2 W**

Works with Zero 2W, 3, 4, or 5

</td>
<td align="center">

<img src="https://cdn.shopify.com/s/files/1/0174/1800/files/standoff_500x500.jpg" width="200">

**Power Supply & SD Card**

8GB+ SD card recommended

</td>
</tr>
</table>

## 🌟 Perfect For

- 🎁 **Personalized Gifts** - Load family photos before gifting
- 🏠 **Home Decoration** - Modern, minimalist design
- 👵 **Grandparents** - Simple to use, no tech knowledge needed
- 🌱 **Eco-Friendly** - Ultra-low power consumption
- 🎓 **Educational** - Learn about e-ink technology

## 📊 Power Consumption Comparison

<div align="center">

| Device | Power Usage | Annual Cost |
|--------|------------|-------------|
| **Inky Photo Frame** | 0.6W | < 1€ |
| iPad Photo Frame | 2-3W | ~4€ |
| LCD Digital Frame | 5-10W | ~13€ |
| LED Light Bulb | 7W | ~9€ |

</div>

## 🛠️ Advanced Configuration

Edit `/home/pi/inky-photo-frame/inky_photo_frame.py`:

```python
CHANGE_HOUR = 5  # Change daily at this hour (24h format)
PHOTOS_DIR = Path('/home/pi/InkyPhotos')  # Photo storage location
```

## 📝 Commands

```bash
# Check status
sudo systemctl status inky-photo-frame

# View logs
sudo journalctl -u inky-photo-frame -f

# Restart service
sudo systemctl restart inky-photo-frame

# Manual test
python3 /home/pi/inky-photo-frame/inky_photo_frame.py
```

## 🤝 Contributing

Contributions are welcome! Feel free to:
- ⭐ Star this repo
- 🐛 Report bugs
- 💡 Suggest features
- 🔀 Submit pull requests

## 📄 License

MIT License - Feel free to use and modify!

## 🙏 Acknowledgments

- [Pimoroni](https://pimoroni.com) for the amazing Inky display
- Built with ❤️ for the Raspberry Pi community
- Powered by Python and e-ink technology

---

<div align="center">

**Made with 🖼️ by [mehdi7129](https://github.com/mehdi7129)**

[⬆ Back to top](#️-inky-photo-frame)

</div>