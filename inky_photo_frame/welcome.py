"""Welcome screen rendering for first-run display."""

import logging
import socket
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont


def get_ip_address():
    """Get the local IP address"""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except:
        return "192.168.1.xxx"


def get_credentials():
    """Read username and password from credentials file"""
    try:
        cred_file = Path("/home/pi/.inky_credentials")
        if cred_file.exists():
            lines = cred_file.read_text().strip().split('\n')
            if len(lines) >= 2:
                return lines[0], lines[1]  # username, password
    except Exception as e:
        logging.warning(f"Could not read credentials file: {e}")
    # Fallback to default values
    return "inky", "inkyimpression73_2025"


def display_welcome(display, width, height):
    """Display welcome screen with connection instructions - LARGE readable text.

    Args:
        display: Inky display object (to call set_image() and show())
        width: int, display width in pixels
        height: int, display height in pixels
    """
    logging.info('Displaying welcome screen')

    # Create welcome image - pure white background
    img = Image.new('RGB', (width, height), color='white')
    draw = ImageDraw.Draw(img)

    # Optimal readable fonts for e-ink display
    try:
        title_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 55)
        ip_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf", 50)
        info_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 32)
        cred_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf", 36)
    except:
        title_font = ImageFont.load_default()
        ip_font = title_font
        info_font = title_font
        cred_font = title_font

    ip_address = get_ip_address()
    username, password = get_credentials()

    # Title
    y_pos = 15
    title = "Photo Frame"
    bbox = draw.textbbox((0, 0), title, font=title_font)
    x = (width - (bbox[2] - bbox[0])) // 2
    draw.text((x, y_pos), title, font=title_font, fill='black')

    # Separator
    y_pos += 75
    draw.line([(80, y_pos), (720, y_pos)], fill='black', width=3)

    # IP Address - LARGE and prominent
    y_pos += 20
    ip_text = f"smb://{ip_address}"
    bbox = draw.textbbox((0, 0), ip_text, font=ip_font)
    x = (width - (bbox[2] - bbox[0])) // 2
    draw.text((x, y_pos), ip_text, font=ip_font, fill='darkblue')

    # Credentials - LARGE (dynamically read from file)
    y_pos += 95
    cred_text = f"Username: {username}"
    bbox = draw.textbbox((0, 0), cred_text, font=cred_font)
    x = (width - (bbox[2] - bbox[0])) // 2
    draw.text((x, y_pos), cred_text, font=cred_font, fill='black')

    y_pos += 55
    cred_text = f"Password: {password}"
    bbox = draw.textbbox((0, 0), cred_text, font=cred_font)
    x = (width - (bbox[2] - bbox[0])) // 2
    draw.text((x, y_pos), cred_text, font=cred_font, fill='black')

    # Separator
    y_pos += 60
    draw.line([(80, y_pos), (720, y_pos)], fill='gray', width=2)

    # Instructions - simplified
    y_pos += 20
    text1 = "iPhone: Files app"
    bbox = draw.textbbox((0, 0), text1, font=info_font)
    x = (width - (bbox[2] - bbox[0])) // 2
    draw.text((x, y_pos), text1, font=info_font, fill='darkgreen')

    y_pos += 50
    text2 = "Android: File Explorer"
    bbox = draw.textbbox((0, 0), text2, font=info_font)
    x = (width - (bbox[2] - bbox[0])) // 2
    draw.text((x, y_pos), text2, font=info_font, fill='darkgreen')

    # Display the welcome screen
    try:
        display.set_image(img, saturation=0.6)
    except TypeError:
        display.set_image(img)
    display.show()
