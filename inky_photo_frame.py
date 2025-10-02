#!/usr/bin/env python3
"""
Inky Photo Frame - Digital photo frame for Inky Impression 7.3"
Displays photos from SMB share with immediate display of new photos
Changes daily at 5AM with intelligent rotation

Version: 2.0.0
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

# Configuration
PHOTOS_DIR = Path('/home/pi/Images')
HISTORY_FILE = Path('/home/pi/.inky_history.json')
CHANGE_HOUR = 5  # Daily change hour (5AM)
LOG_FILE = '/home/pi/inky_photo_frame.log'
MAX_PHOTOS = 1000  # Maximum number of photos to keep (auto-delete oldest)
VERSION = "2.1.5"

# Color calibration settings for e-ink display
# Note: SATURATION is now auto-detected per display model (see detect_display_saturation)
# Based on user-calibrated Spectra 6 real RGB values:
#   Red=#a02020, Yellow=#f0e050, Green=#608050, Blue=#5080b8 (very muted vs standard RGB)
# - Spectra 2025 (6 colors): 0.3 (very low - Spectra has muted palette)
# - Classic 7.3" (7 colors): 0.6 (standard)
# - Unknown displays: 0.5 (safe default)
AUTO_CONTRAST = True  # Enable/disable auto-contrast enhancement
CONTRAST_CUTOFF = 2  # Auto-contrast cutoff (0-5, lower = less aggressive)

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

        # Detect display model and optimize saturation
        self.saturation = self.detect_display_saturation()
        logging.info(f'🎨 Display-specific saturation: {self.saturation}')

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

    def detect_display_saturation(self):
        """
        Auto-detect display model and return optimal saturation
        Different Inky models have different color palettes and need different saturations
        Returns: (saturation, is_spectra)
        """
        display_class = type(self.display).__name__

        # Check display type from class name or resolution
        if 'e673' in str(type(self.display).__module__).lower() or 'E673' in display_class:
            # Inky Impression 7.3" Spectra 2025 (6 colors) - needs MUCH LOWER saturation
            # Spectra real colors: Red=#a02020, Yellow=#f0e050, Green=#608050, Blue=#5080b8
            # These are very different from pure RGB, so low saturation is key
            logging.info('📺 Detected: Inky Impression 7.3" Spectra 2025 (6 colors)')
            self.is_spectra = True
            return 0.3  # Very low saturation to work with Spectra's muted palette
        elif self.width == 800 and self.height == 480:
            # Inky Impression 7.3" Classic (7 colors) - can handle more saturation
            logging.info('📺 Detected: Inky Impression 7.3" Classic (7 colors)')
            self.is_spectra = False
            return 0.6  # Standard saturation
        elif self.width == 1600 and self.height == 1200:
            # Inky Impression 13.3" 2025 (6 colors) - needs lower saturation + color correction
            logging.info('📺 Detected: Inky Impression 13.3" 2025 (6 colors)')
            self.is_spectra = True
            return 0.4  # Lower saturation like Spectra
        else:
            # Unknown display - use conservative default
            logging.info(f'📺 Unknown display: {self.width}x{self.height}, using default saturation')
            self.is_spectra = False
            return 0.5  # Safe middle ground

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

        # Credentials - LARGE
        y_pos += 95
        cred_text = "Username: inky"
        bbox = draw.textbbox((0, 0), cred_text, font=cred_font)
        x = (self.width - (bbox[2] - bbox[0])) // 2
        draw.text((x, y_pos), cred_text, font=cred_font, fill='black')

        y_pos += 55
        cred_text = "Password: inkyimpression73_2025"
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

        # Spectra 2025 specific color correction
        if self.is_spectra:
            from PIL import ImageEnhance

            # Spectra 6 has a very limited, muted color palette:
            # Real colors: Red=#a02020, Yellow=#f0e050, Green=#608050, Blue=#5080b8
            # Problem: Spectra renders too cold/blue, lacks warmth
            # Solution: Reduce blue channel, boost red slightly for warmth

            # Step 1: Increase brightness (Spectra renders dark)
            brightness = ImageEnhance.Brightness(img)
            img = brightness.enhance(1.12)  # +12% brightness

            # Step 2: Channel balancing - aggressive warmth boost
            r, g, b = img.split()
            r_enhancer = ImageEnhance.Brightness(r)
            r = r_enhancer.enhance(1.15)  # +15% red for strong warmth (was 1.05)
            g_enhancer = ImageEnhance.Brightness(g)
            g = g_enhancer.enhance(0.92)  # -8% green (reduces yellow, was -5%)
            b_enhancer = ImageEnhance.Brightness(b)
            b = b_enhancer.enhance(0.75)  # -25% blue (aggressive reduction, was -15%)
            img = Image.merge('RGB', (r, g, b))

            # Step 3: NO contrast enhancement (preserve natural tones)
            # Spectra's limited palette means contrast makes colors worse

            logging.info('Applied Spectra calibration (saturation 0.3 + warmth boost + blue reduction)')
        else:
            # Classic displays: standard contrast enhancement
            img = ImageOps.autocontrast(img, cutoff=CONTRAST_CUTOFF)

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