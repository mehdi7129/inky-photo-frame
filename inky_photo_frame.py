#!/usr/bin/env python3
"""Inky Photo Frame - backward-compatible entry point for systemd service."""
from inky_photo_frame.app import InkyPhotoFrame
InkyPhotoFrame().run()
