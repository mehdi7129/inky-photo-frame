#!/usr/bin/env python3
"""
Inky Photo Frame - Digital photo frame for Inky Impression 7.3"
Displays photos from SMB share with immediate display of new photos
Changes daily at 5AM with intelligent rotation

Version: 1.1.5

Color Management:
-----------------
Change COLOR_MODE setting (line 44) to choose color handling:

1. 'pimoroni' - Official Pimoroni defaults (100% faithful)
   - Saturation: 0.5
   - No image processing (matches official Pimoroni behavior)
   - Best for: General use, Classic 7.3" displays

2. 'spectra_palette' - Calibrated 6-color palette (RECOMMENDED for Spectra)
   - Maps to actual Spectra RGB values (not idealized colors)
   - Uses quantization with Floyd-Steinberg dithering
   - Calibrated palette: R=#a02020, Y=#f0e050, G=#608050, B=#5080b8
   - Best for: Accurate colors on Spectra 6 displays

3. 'warmth_boost' - Aggressive warmth enhancement
   - Red +15%, Green -8%, Blue -25%
   - Brightness +12%, Saturation 0.3
   - Best for: Warm skin tones, portraits
"""

import os
# Set environment variable to skip GPIO check
os.environ['INKY_SKIP_GPIO_CHECK'] = '1'
import json
import random
from datetime import datetime, timedelta
from pathlib import Path
from PIL import Image, ImageOps, ImageDraw, ImageFont
import time as time_module
import logging
import sys
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import threading
from threading import Timer
import socket
import subprocess
import atexit
import signal
from functools import wraps

# Optional GPIO button support
try:
    from gpiozero import Button
    BUTTONS_AVAILABLE = True
except ImportError:
    BUTTONS_AVAILABLE = False

# Configuration
PHOTOS_DIR = Path('/home/pi/Images')
HISTORY_FILE = Path('/home/pi/.inky_history.json')
COLOR_MODE_FILE = Path('/home/pi/.inky_color_mode.json')
CHANGE_HOUR = 5  # Daily change hour (5AM)
LOG_FILE = '/home/pi/inky_photo_frame.log'
MAX_PHOTOS = 1000  # Maximum number of photos to keep (auto-delete oldest)
VERSION = "1.1.5"

# Color calibration settings for e-ink display
# COLOR_MODE options:
#   'pimoroni'        - Official Pimoroni default (saturation 0.5, NO processing)
#   'spectra_palette' - Direct mapping to calibrated 6-color Spectra palette
#   'warmth_boost'    - Aggressive RGB warmth adjustments
# NOTE: COLOR_MODE is now dynamically changeable at runtime via buttons or methods
COLOR_MODE = 'spectra_palette'  # Default color mode (can be changed at runtime)

# Pimoroni defaults
SATURATION = 0.5  # Pimoroni default saturation (matches official behavior)

# Spectra 6 calibrated palette (measured against sRGB monitor)
# These are the ACTUAL colors the e-ink can produce, not idealized RGB
SPECTRA_PALETTE = {
    'black':  (0x00, 0x00, 0x00),
    'white':  (0xff, 0xff, 0xff),
    'red':    (0xa0, 0x20, 0x20),  # Much darker than #FF0000
    'yellow': (0xf0, 0xe0, 0x50),  # Warmer than #FFFF00
    'green':  (0x60, 0x80, 0x50),  # Muted, shifted towards cyan
    'blue':   (0x50, 0x80, 0xb8),  # Much lighter/cyan than #0000FF
}

# Warmth boost settings (aggressive mode)
WARMTH_BOOST_CONFIG = {
    'red_boost': 1.15,      # +15% red
    'green_reduce': 0.92,   # -8% green
    'blue_reduce': 0.75,    # -25% blue
    'brightness': 1.12,     # +12% brightness
    'saturation': 0.3       # Very low saturation for Spectra
}

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler(sys.stdout)
    ]
)

# ============================================================================
# DISPLAY MANAGER - Singleton pattern for robust GPIO/SPI management
# ============================================================================

class DisplayManager:
    """
    Singleton to manage Inky display with robust GPIO/SPI handling.
    Initializes once, cleans up only on exit.
    """
    _instance = None
    _display = None
    _initialized = False
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def initialize(self):
        """Initialize display once at startup"""
        with self._lock:
            if self._initialized:
                return self._display

            logging.info(f'🚀 Inky Photo Frame v{VERSION}')
            logging.info('Initializing display...')

            try:
                from inky.auto import auto
                self._display = auto()
                self._initialized = True

                width, height = self._display.resolution
                logging.info(f'✅ Display initialized: {width}x{height}')

                # Register cleanup handlers
                atexit.register(self.cleanup)
                signal.signal(signal.SIGTERM, lambda s, f: self.cleanup())
                signal.signal(signal.SIGINT, lambda s, f: self.cleanup())

                return self._display

            except Exception as e:
                logging.error(f'❌ Failed to initialize display: {e}')
                raise

    def get_display(self):
        """Get the display instance (initializes if needed)"""
        if not self._initialized:
            return self.initialize()
        return self._display

    def cleanup(self):
        """Cleanup display resources on exit"""
        with self._lock:
            if self._initialized and self._display:
                try:
                    if hasattr(self._display, '_spi'):
                        self._display._spi.close()
                    logging.info('🧹 Display cleaned up properly')
                except Exception as e:
                    logging.warning(f'Cleanup warning: {e}')
                finally:
                    self._initialized = False
                    self._display = None

def retry_on_error(max_attempts=3, delay=1, backoff=2):
    """
    Decorator to retry operations on GPIO/SPI errors
    Uses exponential backoff for resilience
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            for attempt in range(1, max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    error_msg = str(e).lower()
                    # Check if it's a recoverable error
                    is_recoverable = any(x in error_msg for x in [
                        'gpio', 'spi', 'pins', 'transport', 'endpoint', 'busy'
                    ])

                    if is_recoverable and attempt < max_attempts:
                        wait_time = delay * (backoff ** (attempt - 1))
                        logging.warning(f'⚠️ Attempt {attempt}/{max_attempts} failed: {e}')
                        logging.info(f'Retrying in {wait_time}s...')
                        time_module.sleep(wait_time)
                    else:
                        logging.error(f'❌ Operation failed after {attempt} attempts: {e}')
                        raise
            return None
        return wrapper
    return decorator

# ============================================================================
# BUTTON CONTROLLER - GPIO button handling for photo frame control
# ============================================================================

class ButtonController:
    """
    Handles 4 GPIO buttons for photo frame control
    - Button A (GPIO 5): Next photo
    - Button B (GPIO 6): Previous photo
    - Button C (GPIO 16): Cycle color modes
    - Button D (GPIO 24): Reset to pimoroni mode
    """
    def __init__(self, photo_frame):
        self.photo_frame = photo_frame
        self.busy = False  # Lock mechanism to prevent button presses during display

        # Initialize buttons with 20ms debouncing
        try:
            self.button_a = Button(5, bounce_time=0.02)  # Next photo
            self.button_b = Button(6, bounce_time=0.02)  # Previous photo
            self.button_c = Button(16, bounce_time=0.02)  # Cycle color mode
            self.button_d = Button(24, bounce_time=0.02)  # Reset color mode

            # Attach handlers
            self.button_a.when_pressed = self._on_button_a
            self.button_b.when_pressed = self._on_button_b
            self.button_c.when_pressed = self._on_button_c
            self.button_d.when_pressed = self._on_button_d

            logging.info('✅ Button controller initialized (GPIO 5,6,16,24)')
        except Exception as e:
            logging.warning(f'⚠️ Could not initialize buttons: {e}')

    def _on_button_a(self):
        """Button A: Next photo"""
        if not self.busy:
            self.busy = True
            try:
                self.photo_frame.next_photo()
            finally:
                self.busy = False

    def _on_button_b(self):
        """Button B: Previous photo"""
        if not self.busy:
            self.busy = True
            try:
                self.photo_frame.previous_photo()
            finally:
                self.busy = False

    def _on_button_c(self):
        """Button C: Cycle color modes"""
        if not self.busy:
            self.busy = True
            try:
                self.photo_frame.cycle_color_mode()
            finally:
                self.busy = False

    def _on_button_d(self):
        """Button D: Reset to pimoroni mode"""
        if not self.busy:
            self.busy = True
            try:
                self.photo_frame.reset_color_mode()
            finally:
                self.busy = False

# ============================================================================
# PHOTO HANDLER - File system event handler for new photos
# ============================================================================

class PhotoHandler(FileSystemEventHandler):
    """Handler for new photo files"""
    def __init__(self, slideshow):
        self.slideshow = slideshow
        self.image_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.heic'}
        self.pending_photos = []
        self.timer = None

    def on_created(self, event):
        if event.is_directory:
            return

        # Check if it's an image file
        path = Path(event.src_path)
        if path.suffix.lower() in self.image_extensions:
            logging.info(f'New photo detected: {path.name}')

            # Add to pending list
            self.pending_photos.append(str(path))

            # Cancel previous timer if exists
            if self.timer:
                self.timer.cancel()

            # Wait 3 seconds for more uploads, then display only the last one
            self.timer = threading.Timer(3.0, self.process_uploads)
            self.timer.start()

    def process_uploads(self):
        """Process uploaded photos - only display the last one"""
        if self.pending_photos:
            # Get the last photo uploaded
            last_photo = self.pending_photos[-1]
            other_photos = self.pending_photos[:-1]

            # Add all OTHER photos to pending queue (for 5AM rotation)
            if other_photos:
                logging.info(f'Adding {len(other_photos)} photos to queue for daily rotation')
                for photo in other_photos:
                    try:
                        self.slideshow.add_to_queue(photo)
                    except Exception as e:
                        logging.error(f'Error adding {photo} to queue: {e}')

            # Display only the LAST photo immediately
            logging.info(f'Displaying only the last uploaded photo: {Path(last_photo).name}')
            try:
                self.slideshow.display_new_photo(last_photo)
            except Exception as e:
                logging.error(f'Error displaying new photo: {e}')
                # Don't let errors stop the file watcher
                pass

            # Clear pending list
            self.pending_photos = []

class InkyPhotoFrame:
    def __init__(self):
        # Use DisplayManager singleton for robust GPIO/SPI handling
        self.display_manager = DisplayManager()
        self.display = self.display_manager.initialize()
        self.width, self.height = self.display.resolution

        # Load saved color mode preference (must be before detect_display_saturation)
        self.color_mode = self.load_color_mode()

        # Detect display model and optimize saturation
        self.saturation = self.detect_display_saturation()
        logging.info(f'🎨 Color mode: {self.color_mode}')
        logging.info(f'🎨 Display-specific saturation: {self.saturation}')

        if self.color_mode == 'spectra_palette' and self.is_spectra:
            logging.info('🎨 Using calibrated Spectra 6-color palette:')
            for name, rgb in SPECTRA_PALETTE.items():
                logging.info(f'   {name}: #{rgb[0]:02x}{rgb[1]:02x}{rgb[2]:02x}')
        elif self.color_mode == 'warmth_boost' and self.is_spectra:
            logging.info('🔥 Using aggressive warmth boost mode')

        # Register HEIF support if available
        try:
            import pillow_heif
            pillow_heif.register_heif_opener()
            logging.info('📱 HEIF support enabled for iPhone photos')
        except ImportError:
            logging.info('📱 HEIF support not available')

        # Create photos directory if not exists
        PHOTOS_DIR.mkdir(parents=True, exist_ok=True)

        # Load or create history
        self.history = self.load_history()

        # Threading lock for safe history updates
        self.lock = threading.Lock()

        # Storage management - cleanup old photos periodically
        self.last_cleanup = datetime.now()

        # Initialize button controller (optional - only if gpiozero is available)
        if BUTTONS_AVAILABLE:
            try:
                self.button_controller = ButtonController(self)
            except Exception as e:
                logging.warning(f'⚠️ Button controller initialization failed: {e}')
                self.button_controller = None
        else:
            logging.info('ℹ️ Button support disabled (gpiozero not available)')
            self.button_controller = None

    def detect_display_saturation(self):
        """
        Auto-detect display model and return optimal saturation
        Different Inky models have different color palettes and need different saturations
        Returns: (saturation, is_spectra)
        """
        display_class = type(self.display).__name__

        # Check display type from class name or resolution
        if 'e673' in str(type(self.display).__module__).lower() or 'E673' in display_class:
            logging.info('📺 Detected: Inky Impression 7.3" Spectra 2025 (6 colors)')
            self.is_spectra = True
        elif self.width == 800 and self.height == 480:
            logging.info('📺 Detected: Inky Impression 7.3" Classic (7 colors)')
            self.is_spectra = False
        elif self.width == 1600 and self.height == 1200:
            logging.info('📺 Detected: Inky Impression 13.3" 2025 (6 colors)')
            self.is_spectra = True
        else:
            logging.info(f'📺 Unknown display: {self.width}x{self.height}')
            self.is_spectra = False

        # Return saturation based on color mode
        if self.color_mode == 'warmth_boost':
            return WARMTH_BOOST_CONFIG['saturation']
        return SATURATION

    def get_ip_address(self):
        """Get the local IP address"""
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except:
            return "192.168.1.xxx"

    def get_credentials(self):
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

    def display_welcome(self):
        """Display welcome screen with connection instructions - LARGE readable text"""
        logging.info('Displaying welcome screen')

        # Create welcome image - pure white background
        img = Image.new('RGB', (self.width, self.height), color='white')
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

        ip_address = self.get_ip_address()
        username, password = self.get_credentials()

        # Title
        y_pos = 15
        title = "Photo Frame"
        bbox = draw.textbbox((0, 0), title, font=title_font)
        x = (self.width - (bbox[2] - bbox[0])) // 2
        draw.text((x, y_pos), title, font=title_font, fill='black')

        # Separator
        y_pos += 75
        draw.line([(80, y_pos), (720, y_pos)], fill='black', width=3)

        # IP Address - LARGE and prominent
        y_pos += 20
        ip_text = f"smb://{ip_address}"
        bbox = draw.textbbox((0, 0), ip_text, font=ip_font)
        x = (self.width - (bbox[2] - bbox[0])) // 2
        draw.text((x, y_pos), ip_text, font=ip_font, fill='darkblue')

        # Credentials - LARGE (dynamically read from file)
        y_pos += 95
        cred_text = f"Username: {username}"
        bbox = draw.textbbox((0, 0), cred_text, font=cred_font)
        x = (self.width - (bbox[2] - bbox[0])) // 2
        draw.text((x, y_pos), cred_text, font=cred_font, fill='black')

        y_pos += 55
        cred_text = f"Password: {password}"
        bbox = draw.textbbox((0, 0), cred_text, font=cred_font)
        x = (self.width - (bbox[2] - bbox[0])) // 2
        draw.text((x, y_pos), cred_text, font=cred_font, fill='black')

        # Separator
        y_pos += 60
        draw.line([(80, y_pos), (720, y_pos)], fill='gray', width=2)

        # Instructions - simplified
        y_pos += 20
        text1 = "iPhone: Files app"
        bbox = draw.textbbox((0, 0), text1, font=info_font)
        x = (self.width - (bbox[2] - bbox[0])) // 2
        draw.text((x, y_pos), text1, font=info_font, fill='darkgreen')

        y_pos += 50
        text2 = "Android: File Explorer"
        bbox = draw.textbbox((0, 0), text2, font=info_font)
        x = (self.width - (bbox[2] - bbox[0])) // 2
        draw.text((x, y_pos), text2, font=info_font, fill='darkgreen')

        # Display the welcome screen
        try:
            self.display.set_image(img, saturation=0.6)
        except TypeError:
            self.display.set_image(img)
        self.display.show()

    def load_history(self):
        """Load history from file or create new"""
        if HISTORY_FILE.exists():
            with open(HISTORY_FILE, 'r') as f:
                data = json.load(f)

                # Migrate old format to new format with metadata
                if 'photo_metadata' not in data:
                    data['photo_metadata'] = {}
                    logging.info('Migrated history to new format with metadata')

                logging.info(f'📚 Loaded history: {len(data["shown"])} shown, {len(data["pending"])} pending')
                return data
        else:
            return {
                'shown': [],
                'pending': [],
                'current': None,
                'last_change': None,
                'photo_metadata': {}  # New: track when photos were added
            }

    def save_history(self):
        """Save history to file"""
        with self.lock:
            with open(HISTORY_FILE, 'w') as f:
                json.dump(self.history, f, indent=2)
            logging.info('History saved')

    def get_all_photos(self):
        """Get all image files from the photos directory"""
        extensions = ['*.jpg', '*.jpeg', '*.png', '*.gif', '*.bmp', '*.heic', '*.HEIC',
                     '*.JPG', '*.JPEG', '*.PNG', '*.BMP']
        photos = []
        for ext in extensions:
            photos.extend(PHOTOS_DIR.glob(ext))

        # Convert to string paths
        return [str(p) for p in photos]

    def cleanup_old_photos(self):
        """
        Storage management: Delete oldest photos if exceeding MAX_PHOTOS
        Uses FIFO policy - keeps most recently added photos
        """
        with self.lock:
            all_photos = self.get_all_photos()

            # Update metadata for new photos
            for photo_path in all_photos:
                if photo_path not in self.history['photo_metadata']:
                    # New photo - add metadata
                    file_stat = Path(photo_path).stat()
                    self.history['photo_metadata'][photo_path] = {
                        'added_at': datetime.fromtimestamp(file_stat.st_mtime).isoformat(),
                        'size_bytes': file_stat.st_size,
                        'displayed_count': 0
                    }

            # Remove metadata for deleted photos
            existing_paths = set(all_photos)
            metadata_paths = set(self.history['photo_metadata'].keys())
            for removed_path in metadata_paths - existing_paths:
                del self.history['photo_metadata'][removed_path]

            # Check if we need to clean up
            total_photos = len(all_photos)
            if total_photos <= MAX_PHOTOS:
                return

            # Sort photos by date added (oldest first)
            photos_with_dates = []
            for photo_path in all_photos:
                metadata = self.history['photo_metadata'].get(photo_path, {})
                added_at = metadata.get('added_at', datetime.now().isoformat())
                photos_with_dates.append((photo_path, added_at))

            photos_with_dates.sort(key=lambda x: x[1])  # Sort by date

            # Delete oldest photos
            to_delete = total_photos - MAX_PHOTOS
            logging.info(f'🗑️ Storage cleanup: deleting {to_delete} oldest photos (keeping {MAX_PHOTOS})')

            for photo_path, added_at in photos_with_dates[:to_delete]:
                # Don't delete the currently displayed photo
                if photo_path == self.history['current']:
                    continue

                try:
                    Path(photo_path).unlink()
                    logging.info(f'Deleted: {Path(photo_path).name} (added {added_at})')

                    # Remove from history
                    if photo_path in self.history['shown']:
                        self.history['shown'].remove(photo_path)
                    if photo_path in self.history['pending']:
                        self.history['pending'].remove(photo_path)
                    if photo_path in self.history['photo_metadata']:
                        del self.history['photo_metadata'][photo_path]

                except Exception as e:
                    logging.error(f'Error deleting {photo_path}: {e}')

            self.save_history()
            logging.info(f'✅ Cleanup complete: {len(self.get_all_photos())} photos remaining')

    def refresh_pending_list(self):
        """Update pending list with new photos"""
        with self.lock:
            all_photos = self.get_all_photos()

            # Remove deleted photos from history
            self.history['shown'] = [p for p in self.history['shown'] if p in all_photos]
            self.history['pending'] = [p for p in self.history['pending'] if p in all_photos]

            # Add new photos to pending
            known_photos = set(self.history['shown'] + self.history['pending'])
            if self.history['current']:
                known_photos.add(self.history['current'])

            new_photos = [p for p in all_photos if p not in known_photos]
            if new_photos:
                self.history['pending'].extend(new_photos)
                logging.info(f'Added {len(new_photos)} new photos to pending')

            # If all photos have been shown, reset
            if not self.history['pending'] and self.history['shown']:
                logging.info('All photos shown, resetting cycle')
                self.history['pending'] = self.history['shown'].copy()
                self.history['shown'] = []
                random.shuffle(self.history['pending'])

            # If no pending and no shown (first run or all deleted)
            if not self.history['pending'] and not self.history['shown']:
                self.history['pending'] = all_photos
                random.shuffle(self.history['pending'])
                if all_photos:
                    logging.info(f'Initial setup: {len(self.history["pending"])} photos available')

        self.save_history()

    def _apply_spectra_palette(self, img):
        """
        Map image to calibrated Spectra 6-color palette using quantization.
        This gives more accurate colors by using the ACTUAL RGB values the e-ink can produce.
        """
        from PIL import ImageEnhance

        # Step 1: Pre-process for better palette mapping
        # Boost contrast and saturation slightly to compensate for e-ink limitations
        enhancer = ImageEnhance.Contrast(img)
        img = enhancer.enhance(1.2)  # +20% contrast

        enhancer = ImageEnhance.Color(img)
        img = enhancer.enhance(1.3)  # +30% saturation before mapping

        # Step 2: Create palette image with the 6 calibrated colors
        palette_colors = list(SPECTRA_PALETTE.values())

        # Create a palette image (must be 'P' mode)
        # PIL palette format: flat list of RGB values
        palette_data = []
        for color in palette_colors:
            palette_data.extend(color)

        # Pad palette to 256 colors (PIL requirement)
        while len(palette_data) < 768:  # 256 colors * 3 channels
            palette_data.extend([0, 0, 0])

        # Create palette image
        palette_img = Image.new('P', (1, 1))
        palette_img.putpalette(palette_data)

        # Step 3: Quantize image to our 6-color palette
        # Using Floyd-Steinberg dithering for smoother transitions
        img = img.quantize(palette=palette_img, dither=Image.Dither.FLOYDSTEINBERG)

        # Convert back to RGB for display
        img = img.convert('RGB')

        return img

    def _apply_warmth_boost(self, img):
        """
        Apply aggressive warmth boost via RGB channel adjustments.
        Boosts red, reduces blue to add warmth to skin tones.
        """
        from PIL import ImageEnhance

        # Step 1: Increase brightness
        brightness = ImageEnhance.Brightness(img)
        img = brightness.enhance(WARMTH_BOOST_CONFIG['brightness'])

        # Step 2: Channel balancing for warmth
        r, g, b = img.split()

        r_enhancer = ImageEnhance.Brightness(r)
        r = r_enhancer.enhance(WARMTH_BOOST_CONFIG['red_boost'])

        g_enhancer = ImageEnhance.Brightness(g)
        g = g_enhancer.enhance(WARMTH_BOOST_CONFIG['green_reduce'])

        b_enhancer = ImageEnhance.Brightness(b)
        b = b_enhancer.enhance(WARMTH_BOOST_CONFIG['blue_reduce'])

        img = Image.merge('RGB', (r, g, b))

        return img

    def process_image(self, image_path):
        """Process image for e-ink display with smart cropping and color correction"""
        logging.info(f'Processing: {Path(image_path).name}')
        img = Image.open(image_path)

        # No color profile manipulation - let PIL handle it natively

        # Convert to RGB
        if img.mode != 'RGB':
            if img.mode == 'RGBA':
                background = Image.new('RGB', img.size, (255, 255, 255))
                background.paste(img, mask=img.split()[3])
                img = background
            else:
                img = img.convert('RGB')

        # Smart crop to display ratio
        img_ratio = img.width / img.height
        display_ratio = self.width / self.height

        if img_ratio > display_ratio:
            # Image wider - crop horizontally (keep center)
            new_width = int(img.height * display_ratio)
            left = (img.width - new_width) // 2
            img = img.crop((left, 0, left + new_width, img.height))
        else:
            # Image taller - crop vertically (bias towards top for portraits)
            new_height = int(img.width / display_ratio)
            top = (img.height - new_height) // 3
            img = img.crop((0, top, img.width, top + new_height))

        # Resize to display size
        img = img.resize((self.width, self.height), Image.Resampling.LANCZOS)

        # Apply color mode processing
        if self.color_mode == 'pimoroni':
            # Pimoroni default: NO processing, let Inky library handle everything
            # This matches official Pimoroni behavior (just saturation=0.5 in set_image)
            logging.debug('Applied Pimoroni default (no processing)')

        elif self.color_mode == 'spectra_palette' and self.is_spectra:
            # Spectra palette mode: map to calibrated 6-color palette
            img = self._apply_spectra_palette(img)
            logging.info('✨ Applied calibrated Spectra 6-color palette mapping')

        elif self.color_mode == 'warmth_boost' and self.is_spectra:
            # Aggressive warmth boost mode
            img = self._apply_warmth_boost(img)
            logging.info('🔥 Applied aggressive warmth boost')

        else:
            # Fallback: no processing (same as pimoroni mode)
            logging.debug('No color processing applied (fallback)')

        return img

    @retry_on_error(max_attempts=3, delay=1, backoff=2)
    def display_photo(self, photo_path):
        """
        Display a photo on the Inky screen
        Uses robust retry logic with exponential backoff
        """
        try:
            img = self.process_image(photo_path)

            # Set image with display-specific saturation
            try:
                self.display.set_image(img, saturation=self.saturation)
                logging.debug(f'Applied saturation: {self.saturation}')
            except TypeError:
                self.display.set_image(img)

            logging.info('📺 Displaying on screen...')
            self.display.show()
            logging.info(f'✅ Successfully displayed: {Path(photo_path).name}')

            # Update display count in metadata
            with self.lock:
                if photo_path in self.history['photo_metadata']:
                    self.history['photo_metadata'][photo_path]['displayed_count'] += 1

            return True

        except Exception as e:
            logging.error(f'❌ Error displaying photo: {e}')
            return False

    def add_to_queue(self, photo_path):
        """Add a photo to the pending queue without displaying it"""
        with self.lock:
            # Add to pending list if not already there
            if photo_path not in self.history['pending'] and photo_path != self.history['current']:
                if photo_path not in self.history['shown']:
                    self.history['pending'].append(photo_path)
                    logging.info(f'Added {Path(photo_path).name} to queue for daily rotation')

        # Save history
        self.save_history()

    def display_new_photo(self, photo_path):
        """Display a newly added photo immediately"""
        logging.info(f'🆕 Displaying new photo immediately: {Path(photo_path).name}')

        with self.lock:
            # Add metadata for new photo
            if photo_path not in self.history['photo_metadata']:
                file_stat = Path(photo_path).stat()
                self.history['photo_metadata'][photo_path] = {
                    'added_at': datetime.now().isoformat(),
                    'size_bytes': file_stat.st_size,
                    'displayed_count': 0
                }

            # Move current to shown if exists
            if self.history['current']:
                self.history['shown'].append(self.history['current'])

            # Set new photo as current
            self.history['current'] = photo_path

            # Remove from pending if it's there
            if photo_path in self.history['pending']:
                self.history['pending'].remove(photo_path)

        # Display the photo (retry logic handled by decorator)
        success = self.display_photo(photo_path)

        # Save history
        self.save_history()

        return success

    def change_photo(self):
        """Change to next photo in queue"""
        self.refresh_pending_list()

        if not self.history['pending']:
            logging.warning('No photos available')
            return False

        with self.lock:
            # Pick next photo from pending
            next_photo = self.history['pending'].pop(0)

            # Move current to shown (if exists)
            if self.history['current']:
                self.history['shown'].append(self.history['current'])

            # Set new current
            self.history['current'] = next_photo
            self.history['last_change'] = datetime.now().isoformat()

        # Display the photo
        success = self.display_photo(next_photo)

        # Save history
        self.save_history()

        logging.info(f'Photos - Shown: {len(self.history["shown"])}, Pending: {len(self.history["pending"])}')

        return success

    def next_photo(self):
        """Display next photo (triggered by button A)"""
        self.refresh_pending_list()

        if not self.history['pending']:
            logging.info('No more photos available')
            return False

        with self.lock:
            # Pick next photo from pending
            next_photo = self.history['pending'].pop(0)

            # Move current to shown (if exists)
            if self.history['current']:
                self.history['shown'].append(self.history['current'])

            # Set new current
            self.history['current'] = next_photo

        # Display the photo
        success = self.display_photo(next_photo)

        # Save history
        self.save_history()

        return success

    def previous_photo(self):
        """Display previous photo (triggered by button B)"""
        with self.lock:
            if not self.history['shown']:
                logging.info('No previous photos available')
                return False

            # Get last shown photo
            prev_photo = self.history['shown'].pop()

            # Move current back to pending (at front)
            if self.history['current']:
                self.history['pending'].insert(0, self.history['current'])

            # Set previous as current
            self.history['current'] = prev_photo

        # Display the photo
        success = self.display_photo(prev_photo)

        # Save history
        self.save_history()

        return success

    def cycle_color_mode(self):
        """Cycle through color modes: pimoroni -> spectra_palette -> warmth_boost -> pimoroni"""
        modes = ['pimoroni', 'spectra_palette', 'warmth_boost']
        current_index = modes.index(self.color_mode) if self.color_mode in modes else 0
        next_index = (current_index + 1) % len(modes)
        self.color_mode = modes[next_index]

        # Update saturation based on new color mode
        if self.color_mode == 'warmth_boost':
            self.saturation = WARMTH_BOOST_CONFIG['saturation']
        else:
            self.saturation = SATURATION

        # Save the new color mode
        self.save_color_mode()

        # Re-display current photo with new color mode
        if self.history['current']:
            self.display_photo(self.history['current'])

        return True

    def reset_color_mode(self):
        """Reset to pimoroni color mode (triggered by button D)"""
        self.color_mode = 'pimoroni'
        self.saturation = SATURATION

        # Save the color mode
        self.save_color_mode()

        # Re-display current photo with pimoroni mode
        if self.history['current']:
            self.display_photo(self.history['current'])

        return True

    def load_color_mode(self):
        """Load saved color mode from file"""
        if COLOR_MODE_FILE.exists():
            try:
                with open(COLOR_MODE_FILE, 'r') as f:
                    data = json.load(f)
                    color_mode = data.get('color_mode', COLOR_MODE)
                    logging.info(f'Loaded saved color mode: {color_mode}')
                    return color_mode
            except Exception as e:
                logging.warning(f'Could not load color mode: {e}')
                return COLOR_MODE
        else:
            return COLOR_MODE

    def save_color_mode(self):
        """Save current color mode to file"""
        try:
            with open(COLOR_MODE_FILE, 'w') as f:
                json.dump({'color_mode': self.color_mode}, f, indent=2)
            logging.info(f'Saved color mode: {self.color_mode}')
        except Exception as e:
            logging.error(f'Error saving color mode: {e}')

    def should_change_photo(self):
        """Check if it's time for daily photo change"""
        now = datetime.now()

        # Check if we've never changed
        if not self.history['last_change']:
            return True

        # Parse last change time
        last_change = datetime.fromisoformat(self.history['last_change'])

        # Check if it's past CHANGE_HOUR and we haven't changed today
        if now.hour >= CHANGE_HOUR and last_change.date() < now.date():
            return True

        return False

    def display_current_or_change(self):
        """Display current photo or change if needed"""
        # Check if we have any photos
        photos = self.get_all_photos()

        if not photos:
            # No photos yet, show welcome screen
            self.display_welcome()
            return

        if self.should_change_photo():
            logging.info('Time for daily photo change')
            self.change_photo()
        elif self.history['current']:
            # Just display current (useful after reboot)
            logging.info('Displaying current photo after startup')
            self.display_photo(self.history['current'])
        else:
            # No current photo, pick one
            logging.info('No current photo, selecting one')
            self.change_photo()

    def run(self):
        """Main loop with file watching"""
        logging.info(f'⏰ Daily change time: {CHANGE_HOUR:02d}:00')
        logging.info(f'📁 Watching folder: {PHOTOS_DIR}')
        logging.info(f'🗄️ Storage limit: {MAX_PHOTOS} photos (auto-cleanup enabled)')

        # Display current or welcome screen
        self.display_current_or_change()

        # Setup file watcher
        event_handler = PhotoHandler(self)
        observer = Observer()
        observer.schedule(event_handler, str(PHOTOS_DIR), recursive=False)
        observer.start()
        logging.info('📸 File watcher started - new photos will display immediately!')

        try:
            # Main loop
            while True:
                # Check every minute
                time_module.sleep(60)

                # Check for daily change
                if self.should_change_photo():
                    try:
                        self.change_photo()
                    except Exception as e:
                        logging.error(f'Error changing photo: {e}')

                # Periodic maintenance every hour
                if datetime.now().minute == 0:
                    # Refresh pending list
                    self.refresh_pending_list()

                    # Show welcome if no photos
                    if not self.get_all_photos() and self.history['current'] is None:
                        self.display_welcome()

                # Storage cleanup check every 6 hours
                time_since_cleanup = datetime.now() - self.last_cleanup
                if time_since_cleanup > timedelta(hours=6):
                    logging.info('🧹 Running periodic storage cleanup...')
                    self.cleanup_old_photos()
                    self.last_cleanup = datetime.now()

                # Check if observer is still alive, restart if needed
                if not observer.is_alive():
                    logging.warning('⚠️ File watcher stopped, restarting...')
                    observer = Observer()
                    observer.schedule(event_handler, str(PHOTOS_DIR), recursive=False)
                    observer.start()
                    logging.info('✅ File watcher restarted')

        except KeyboardInterrupt:
            logging.info('👋 Stopping photo frame')
            observer.stop()
        except Exception as e:
            logging.error(f'❌ Error in main loop: {e}')
            observer.stop()

        observer.join()

if __name__ == '__main__':
    frame = InkyPhotoFrame()
    frame.run()