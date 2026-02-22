"""Configuration constants for Inky Photo Frame."""

import os

# Must be set before any inky import anywhere in the package
os.environ['INKY_SKIP_GPIO_CHECK'] = '1'

import logging
import sys
from pathlib import Path

# Application metadata
VERSION = "2.0.0"

# Paths
PHOTOS_DIR = Path('/home/pi/Images')
HISTORY_FILE = Path('/home/pi/.inky_history.json')
COLOR_MODE_FILE = Path('/home/pi/.inky_color_mode.json')

# Timing constants
CHANGE_HOUR = 5  # Daily change hour (5AM) - used when CHANGE_INTERVAL_MINUTES is 0
CHANGE_INTERVAL_MINUTES = 0  # 0 = daily mode (change at CHANGE_HOUR), >0 = change every N minutes

# Logging
LOG_FILE = '/home/pi/inky_photo_frame.log'

# Storage
MAX_PHOTOS = 1000  # Maximum number of photos to keep (auto-delete oldest)

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

# ============================================================================
# DISPLAY CONFIGURATION - Structured display type definitions
# ============================================================================

DISPLAY_CONFIGS = {
    'spectra_7.3': {
        'name': 'Inky Impression 7.3" Spectra 2025 (6 colors)',
        'resolution': (800, 480),
        'is_spectra': True,
        'is_13inch': False,
        'gpio_pins': {
            'button_a': 5,
            'button_b': 6,
            'button_c': 16,
            'button_d': 24,
        },
        'detection': {
            'module_contains': 'e673',
            'class_contains': 'E673',
        },
    },
    'classic_7.3': {
        'name': 'Inky Impression 7.3" Classic (7 colors)',
        'resolution': (800, 480),
        'is_spectra': False,
        'is_13inch': False,
        'gpio_pins': {
            'button_a': 5,
            'button_b': 6,
            'button_c': 16,
            'button_d': 24,
        },
        'detection': {
            'resolution': (800, 480),
        },
    },
    'spectra_13.3': {
        'name': 'Inky Impression 13.3" 2025 (6 colors)',
        'resolution': (1600, 1200),
        'is_spectra': True,
        'is_13inch': True,
        'gpio_pins': {
            'button_a': 5,
            'button_b': 6,
            'button_c': 25,   # GPIO 16 is used by display CS1 on 13.3"
            'button_d': 24,
        },
        'detection': {
            'resolution': (1600, 1200),
        },
    },
}


def setup_logging():
    """Configure logging. Call only from entry points, never at import time."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(message)s',
        handlers=[
            logging.FileHandler(LOG_FILE),
            logging.StreamHandler(sys.stdout)
        ]
    )
