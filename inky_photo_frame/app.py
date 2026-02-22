"""Inky Photo Frame application orchestrator."""

import json
import logging
import random
import threading
import time as time_module
from datetime import datetime, timedelta
from pathlib import Path
from watchdog.observers import Observer

from inky_photo_frame.config import (
    PHOTOS_DIR, HISTORY_FILE, COLOR_MODE_FILE,
    CHANGE_HOUR, CHANGE_INTERVAL_MINUTES,
    MAX_PHOTOS, COLOR_MODE, SATURATION,
    SPECTRA_PALETTE, WARMTH_BOOST_CONFIG,
    DISPLAY_CONFIGS, setup_logging,
)
from inky_photo_frame.display import DisplayManager, retry_on_error
from inky_photo_frame.image_processor import process_image
from inky_photo_frame.photos import PhotoHandler, get_all_photos, load_history
from inky_photo_frame.buttons import BUTTONS_AVAILABLE, ButtonController
from inky_photo_frame.welcome import display_welcome


class InkyPhotoFrame:
    def __init__(self):
        # Configure logging first (replaces module-level logging.basicConfig)
        setup_logging()

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
        self.history = load_history()

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
        Sets self.display_config with all display-specific properties
        Returns: saturation value
        """
        display_class = type(self.display).__name__
        display_module = str(type(self.display).__module__).lower()
        resolution = (self.width, self.height)

        # Try to match against known display configurations
        self.display_config = None
        for config_key, config in DISPLAY_CONFIGS.items():
            detection = config['detection']

            # Check by module/class name (most specific)
            if 'module_contains' in detection:
                if detection['module_contains'].lower() in display_module:
                    self.display_config = config
                    break
            if 'class_contains' in detection and not self.display_config:
                if detection['class_contains'] in display_class:
                    self.display_config = config
                    break

            # Check by resolution (fallback)
            if 'resolution' in detection and not self.display_config:
                if detection['resolution'] == resolution:
                    self.display_config = config
                    break

        # If no match found, create a minimal config
        if not self.display_config:
            logging.warning(f'⚠️ Unknown display: {self.width}x{self.height}')
            self.display_config = {
                'name': f'Unknown Display {self.width}x{self.height}',
                'resolution': resolution,
                'is_spectra': False,
                'is_13inch': False,
                'gpio_pins': {
                    'button_a': 5,
                    'button_b': 6,
                    'button_c': 16,
                    'button_d': 24,
                },
            }

        # Set convenient attributes for backward compatibility
        self.is_spectra = self.display_config['is_spectra']
        self.is_13inch = self.display_config.get('is_13inch', False)

        logging.info(f'📺 Detected: {self.display_config["name"]}')
        logging.info(f'📊 GPIO pins: {self.display_config["gpio_pins"]}')

        # Return saturation based on color mode
        if self.color_mode == 'warmth_boost':
            return WARMTH_BOOST_CONFIG['saturation']
        return SATURATION

    def save_history(self):
        """Save history to file"""
        with self.lock:
            with open(HISTORY_FILE, 'w') as f:
                json.dump(self.history, f, indent=2)
            logging.info('History saved')

    def cleanup_old_photos(self):
        """
        Storage management: Delete oldest photos if exceeding MAX_PHOTOS
        Uses FIFO policy - keeps most recently added photos
        """
        with self.lock:
            all_photos = get_all_photos()

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
            logging.info(f'✅ Cleanup complete: {len(get_all_photos())} photos remaining')

    def refresh_pending_list(self):
        """Update pending list with new photos"""
        with self.lock:
            all_photos = get_all_photos()

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

    @retry_on_error(max_attempts=3, delay=1, backoff=2)
    def display_photo(self, photo_path):
        """
        Display a photo on the Inky screen
        Uses robust retry logic with exponential backoff
        """
        try:
            img = process_image(photo_path, self.width, self.height, self.color_mode, self.is_spectra)

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
        """Check if it's time for a photo change

        Two modes:
        - CHANGE_INTERVAL_MINUTES = 0: Daily mode, change once at CHANGE_HOUR
        - CHANGE_INTERVAL_MINUTES > 0: Interval mode, change every N minutes
        """
        now = datetime.now()

        # Check if we've never changed
        if not self.history['last_change']:
            return True

        # Parse last change time
        last_change = datetime.fromisoformat(self.history['last_change'])

        if CHANGE_INTERVAL_MINUTES > 0:
            # Interval mode: change every N minutes
            elapsed = (now - last_change).total_seconds() / 60
            return elapsed >= CHANGE_INTERVAL_MINUTES
        else:
            # Daily mode: change once at CHANGE_HOUR
            if now.hour >= CHANGE_HOUR and last_change.date() < now.date():
                return True

        return False

    def display_current_or_change(self):
        """Display current photo or change if needed"""
        # Check if we have any photos
        photos = get_all_photos()

        if not photos:
            # No photos yet, show welcome screen
            display_welcome(self.display, self.width, self.height)
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
        if CHANGE_INTERVAL_MINUTES > 0:
            logging.info(f'⏰ Photo change interval: every {CHANGE_INTERVAL_MINUTES} minutes')
        else:
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
                    if not get_all_photos() and self.history['current'] is None:
                        display_welcome(self.display, self.width, self.height)

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
