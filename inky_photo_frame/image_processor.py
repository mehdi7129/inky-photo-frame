"""Image processing pipeline for e-ink display."""

import logging
from pathlib import Path
from PIL import Image

from inky_photo_frame.config import SPECTRA_PALETTE, WARMTH_BOOST_CONFIG


def _apply_spectra_palette(img):
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


def _apply_warmth_boost(img):
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


def process_image(image_path, width, height, color_mode, is_spectra):
    """Process image for e-ink display with smart cropping and color correction.

    Args:
        image_path: str or Path to the image file
        width: int, display width in pixels
        height: int, display height in pixels
        color_mode: str, one of 'pimoroni', 'spectra_palette', 'warmth_boost'
        is_spectra: bool, whether the display is a Spectra model
    """
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
    display_ratio = width / height

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
    img = img.resize((width, height), Image.Resampling.LANCZOS)

    # Apply color mode processing
    if color_mode == 'pimoroni':
        # Pimoroni default: NO processing, let Inky library handle everything
        # This matches official Pimoroni behavior (just saturation=0.5 in set_image)
        logging.debug('Applied Pimoroni default (no processing)')

    elif color_mode == 'spectra_palette' and is_spectra:
        # Spectra palette mode: map to calibrated 6-color palette
        img = _apply_spectra_palette(img)
        logging.info('✨ Applied calibrated Spectra 6-color palette mapping')

    elif color_mode == 'warmth_boost' and is_spectra:
        # Aggressive warmth boost mode
        img = _apply_warmth_boost(img)
        logging.info('🔥 Applied aggressive warmth boost')

    else:
        # Fallback: no processing (same as pimoroni mode)
        logging.debug('No color processing applied (fallback)')

    return img
