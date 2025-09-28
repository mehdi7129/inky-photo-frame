#!/usr/bin/env python3
"""
Inky Photo Frame - Digital photo frame for Inky Impression 7.3"
Displays photos from SMB share with immediate display of new photos
Changes daily at 5AM with intelligent rotation
"""

import os
import json
import random
from datetime import datetime
from pathlib import Path
from PIL import Image, ImageOps, ImageDraw, ImageFont
from inky.auto import auto
import time as time_module
import logging
import sys
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import threading
from threading import Timer
import socket

# Configuration
PHOTOS_DIR = Path('/home/pi/InkyPhotos')
HISTORY_FILE = Path('/home/pi/.inky_history.json')
CHANGE_HOUR = 5  # Daily change hour (5AM)
LOG_FILE = '/home/pi/inky_photo_frame.log'

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler(sys.stdout)
    ]
)

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
                    self.slideshow.add_to_queue(photo)

            # Display only the LAST photo immediately
            logging.info(f'Displaying only the last uploaded photo: {Path(last_photo).name}')
            self.slideshow.display_new_photo(last_photo)

            # Clear pending list
            self.pending_photos = []

class InkyPhotoFrame:
    def __init__(self):
        # Initialize display
        self.display = auto()
        self.width, self.height = self.display.resolution
        logging.info(f'Display initialized: {self.width}x{self.height}')

        # Create photos directory if not exists
        PHOTOS_DIR.mkdir(parents=True, exist_ok=True)

        # Load or create history
        self.history = self.load_history()

        # Threading lock for safe history updates
        self.lock = threading.Lock()

        # Register HEIF support if available
        try:
            import pillow_heif
            pillow_heif.register_heif_opener()
            logging.info('HEIF support enabled for iPhone/modern phone photos')
        except ImportError:
            logging.info('HEIF support not available')

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
        """Display welcome screen with IP address only"""
        logging.info('Displaying welcome screen')

        # Create welcome image - pure white background
        img = Image.new('RGB', (self.width, self.height), color='white')
        draw = ImageDraw.Draw(img)

        # Try to use large bold font
        try:
            # Use the largest font size for maximum readability
            ip_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 72)
            status_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 36)
        except:
            ip_font = ImageFont.load_default()
            status_font = ip_font

        ip_address = self.get_ip_address()

        # Display IP address in the center - large and bold
        ip_text = ip_address
        bbox = draw.textbbox((0, 0), ip_text, font=ip_font)
        x = (self.width - (bbox[2] - bbox[0])) // 2
        y = (self.height - (bbox[3] - bbox[1])) // 2 - 50
        draw.text((x, y), ip_text, font=ip_font, fill='black')

        # Add status message below
        status_text = "Connected to Internet"
        bbox = draw.textbbox((0, 0), status_text, font=status_font)
        x = (self.width - (bbox[2] - bbox[0])) // 2
        y = y + 100
        draw.text((x, y), status_text, font=status_font, fill='black')

        # Add second line
        status_text2 = "Installation almost complete"
        bbox = draw.textbbox((0, 0), status_text2, font=status_font)
        x = (self.width - (bbox[2] - bbox[0])) // 2
        y = y + 50
        draw.text((x, y), status_text2, font=status_font, fill='black')

        # Display the welcome screen
        try:
            self.display.set_image(img, saturation=0.5)
        except TypeError:
            self.display.set_image(img)
        self.display.show()

    def load_history(self):
        """Load history from file or create new"""
        if HISTORY_FILE.exists():
            with open(HISTORY_FILE, 'r') as f:
                data = json.load(f)
                logging.info(f'Loaded history: {len(data["shown"])} shown, {len(data["pending"])} pending')
                return data
        else:
            return {'shown': [], 'pending': [], 'current': None, 'last_change': None}

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
        """Process image for e-ink display with smart cropping"""
        logging.info(f'Processing: {Path(image_path).name}')
        img = Image.open(image_path)

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

        # Enhance contrast for e-ink
        img = ImageOps.autocontrast(img, cutoff=2)

        return img

    def display_photo(self, photo_path):
        """Display a photo on the Inky screen"""
        try:
            img = self.process_image(photo_path)

            # Set image with saturation for color display
            try:
                self.display.set_image(img, saturation=0.5)
            except TypeError:
                self.display.set_image(img)

            logging.info('Displaying on screen...')
            self.display.show()
            logging.info(f'Successfully displayed: {Path(photo_path).name}')
            return True

        except Exception as e:
            logging.error(f'Error displaying photo: {e}')
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
            # Move current to shown if exists
            if self.history['current']:
                self.history['shown'].append(self.history['current'])

            # Set new photo as current
            self.history['current'] = photo_path

            # Remove from pending if it's there
            if photo_path in self.history['pending']:
                self.history['pending'].remove(photo_path)

        # Display the photo
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
        logging.info('🚀 Starting Inky Photo Frame')
        logging.info(f'⏰ Daily change time: {CHANGE_HOUR:02d}:00')
        logging.info(f'📁 Watching folder: {PHOTOS_DIR}')

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
                    self.change_photo()

                # Check for new photos periodically
                if datetime.now().minute == 0:  # Every hour
                    self.refresh_pending_list()

                    # Show welcome if no photos
                    if not self.get_all_photos() and self.history['current'] is None:
                        self.display_welcome()

        except KeyboardInterrupt:
            logging.info('Stopping photo frame')
            observer.stop()
        except Exception as e:
            logging.error(f'Error in main loop: {e}')
            observer.stop()

        observer.join()

if __name__ == '__main__':
    frame = InkyPhotoFrame()
    frame.run()