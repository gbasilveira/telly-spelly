from PyQt6.QtCore import QObject
from PyQt6.QtGui import QClipboard, QGuiApplication
import subprocess
import logging

logger = logging.getLogger(__name__)

class ClipboardManager(QObject):
    def __init__(self):
        super().__init__()
        self.clipboard = QGuiApplication.clipboard()
        
    def paste_text(self, text):
        if not text:
            logger.warning("Received empty text, skipping clipboard operation")
            return
            
        logger.info(f"Copying text to clipboard: {text[:50]}...")
        self.clipboard.setText(text)
        
        # If set to paste to active window, simulate Ctrl+V
        if self.should_paste_to_active_window():
            self.paste_to_active_window()
    
    def should_paste_to_active_window(self):
        # TODO: Get this from settings
        return False
        
    def paste_to_active_window(self):
        try:
            # Use xdotool to simulate Ctrl+V
            subprocess.run(['xdotool', 'key', 'ctrl+v'], check=True)
        except Exception as e:
            logger.error(f"Failed to paste to active window: {e}") 