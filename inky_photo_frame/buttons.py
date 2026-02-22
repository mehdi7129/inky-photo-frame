"""GPIO button controller for photo frame navigation."""

import logging

# Optional GPIO button support
try:
    from gpiozero import Button
    BUTTONS_AVAILABLE = True
except ImportError:
    BUTTONS_AVAILABLE = False


class ButtonController:
    """
    Handles 4 GPIO buttons for photo frame control
    Dynamically assigns GPIO pins based on detected display model:
    - Button A: Next photo
    - Button B: Previous photo
    - Button C: Cycle color modes
    - Button D: Reset to pimoroni mode
    """
    def __init__(self, photo_frame):
        """
        Args:
            photo_frame: InkyPhotoFrame instance (injected, not imported).
        """
        self.photo_frame = photo_frame
        self.busy = False  # Lock mechanism to prevent button presses during display

        # Get GPIO pins from display configuration
        pins = photo_frame.display_config['gpio_pins']
        gpio_a = pins['button_a']
        gpio_b = pins['button_b']
        gpio_c = pins['button_c']
        gpio_d = pins['button_d']
        display_name = photo_frame.display_config['name']

        # Initialize buttons with 20ms debouncing
        try:
            self.button_a = Button(gpio_a, bounce_time=0.02)
            self.button_b = Button(gpio_b, bounce_time=0.02)
            self.button_c = Button(gpio_c, bounce_time=0.02)
            self.button_d = Button(gpio_d, bounce_time=0.02)

            # Attach handlers
            self.button_a.when_pressed = self._on_button_a
            self.button_b.when_pressed = self._on_button_b
            self.button_c.when_pressed = self._on_button_c
            self.button_d.when_pressed = self._on_button_d

            logging.info(f'✅ Button controller initialized for {display_name} (GPIO {gpio_a},{gpio_b},{gpio_c},{gpio_d})')
        except Exception as e:
            logging.warning(f'⚠️ Could not initialize buttons: {e}')

    def _on_button_a(self):
        """Button A: Next photo"""
        logging.info('🔘 Button A pressed - Next photo')
        if not self.busy:
            self.busy = True
            try:
                self.photo_frame.next_photo()
            finally:
                self.busy = False

    def _on_button_b(self):
        """Button B: Previous photo"""
        logging.info('🔘 Button B pressed - Previous photo')
        if not self.busy:
            self.busy = True
            try:
                self.photo_frame.previous_photo()
            finally:
                self.busy = False

    def _on_button_c(self):
        """Button C: Cycle color modes"""
        gpio_c = self.photo_frame.display_config['gpio_pins']['button_c']
        logging.info(f'🔘 Button C pressed - Cycle color mode')
        if not self.busy:
            self.busy = True
            try:
                self.photo_frame.cycle_color_mode()
            finally:
                self.busy = False

    def _on_button_d(self):
        """Button D: Reset to pimoroni mode"""
        logging.info('🔘 Button D pressed - Reset to pimoroni mode')
        if not self.busy:
            self.busy = True
            try:
                self.photo_frame.reset_color_mode()
            finally:
                self.busy = False
