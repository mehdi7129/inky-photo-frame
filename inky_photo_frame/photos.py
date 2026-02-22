"""Photo handling: file system events, photo discovery, and history management."""

import json
import logging
import threading
from pathlib import Path
from watchdog.events import FileSystemEventHandler

from inky_photo_frame.config import PHOTOS_DIR, HISTORY_FILE


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


def get_all_photos():
    """Get all image files from the photos directory"""
    extensions = ['*.jpg', '*.jpeg', '*.png', '*.gif', '*.bmp', '*.heic', '*.HEIC',
                 '*.JPG', '*.JPEG', '*.PNG', '*.BMP']
    photos = []
    for ext in extensions:
        photos.extend(PHOTOS_DIR.glob(ext))

    # Convert to string paths
    return [str(p) for p in photos]


def load_history():
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
