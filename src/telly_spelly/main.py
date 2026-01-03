import sys

# Initialize D-Bus GLib main loop BEFORE importing Qt
# This is required for proper D-Bus/Qt integration
from dbus.mainloop.glib import DBusGMainLoop
DBusGMainLoop(set_as_default=True)

from PyQt6.QtWidgets import (QApplication, QMessageBox, QSystemTrayIcon, QMenu)
from PyQt6.QtCore import Qt, QTimer, QCoreApplication
from PyQt6.QtGui import QIcon, QAction
import logging
from .settings_window import SettingsWindow
from .progress_window import ProgressWindow
from .processing_window import ProcessingWindow
from .recorder import AudioRecorder
from .transcriber import WhisperTranscriber
from PyQt6.QtCore import pyqtSignal
import warnings
import ctypes
import os
from .shortcuts import GlobalShortcuts
from .settings import Settings
from .install import install_silent
from . import gpu
# from mic_debug import MicDebugWindow

# Setup logging with systemd journal support
class JournalHandler(logging.Handler):
    """Custom journal handler that writes to systemd journal"""

    def __init__(self):
        super().__init__()
        self.level = logging.INFO

    def emit(self, record):
        try:
            import sys
            # Format message
            msg = self.format(record)

            # Write to stdout which systemd captures
            # Add prefix for systemd to categorize
            prefix = ""
            if record.levelno >= logging.ERROR:
                prefix = "<3>"  # Error
            elif record.levelno >= logging.WARNING:
                prefix = "<4>"  # Warning
            elif record.levelno >= logging.INFO:
                prefix = "<6>"  # Info
            else:
                prefix = "<7>"  # Debug

            # Write to stdout with systemd priority prefix
            sys.stdout.write(f"{prefix}telly-spelly: {msg}\n")
            sys.stdout.flush()

        except Exception:
            self.handleError(record)

def setup_logging():
    """Setup logging that works well with systemd"""
    import logging
    import sys

    # Check if we're running under systemd
    running_under_systemd = 'INVOCATION_ID' in os.environ or 'JOURNAL_STREAM' in os.environ

    if running_under_systemd:
        # Use systemd-friendly logging
        journal_handler = JournalHandler()
        journal_handler.setLevel(logging.INFO)

        formatter = logging.Formatter('%(message)s')
        journal_handler.setFormatter(formatter)

        root_logger = logging.getLogger()
        root_logger.setLevel(logging.INFO)
        root_logger.addHandler(journal_handler)

        # Also keep stderr for errors
        error_handler = logging.StreamHandler(sys.stderr)
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(logging.Formatter('ERROR: %(name)s: %(message)s'))
        root_logger.addHandler(error_handler)

    else:
        # Regular console logging for development
        logging.basicConfig(
            level=logging.INFO,
            format='%(name)s: %(levelname)s: %(message)s',
            stream=sys.stderr
        )

    return logging.getLogger(__name__)

logger = setup_logging()

# Suppress ALSA error messages
try:
    # Load ALSA error handler
    ERROR_HANDLER_FUNC = ctypes.CFUNCTYPE(None, ctypes.c_char_p, ctypes.c_int,
                                        ctypes.c_char_p, ctypes.c_int,
                                        ctypes.c_char_p)

    def py_error_handler(filename, line, function, err, fmt):
        pass

    c_error_handler = ERROR_HANDLER_FUNC(py_error_handler)

    # Set error handler
    asound = ctypes.cdll.LoadLibrary('libasound.so.2')
    asound.snd_lib_error_set_handler(c_error_handler)
except:
    warnings.warn("Failed to suppress ALSA warnings", RuntimeWarning)

def check_dependencies():
    required_packages = ['whisper', 'pyaudio']
    missing_packages = []
    
    for package in required_packages:
        try:
            __import__(package)
        except ImportError:
            missing_packages.append(package)
            logger.error(f"Failed to import required dependency: {package}")
    
    if missing_packages:
        error_msg = (
            "Missing required dependencies:\n"
            f"{', '.join(missing_packages)}\n\n"
            "Please install them using:\n"
            f"pip install {' '.join(missing_packages)}"
        )
        QMessageBox.critical(None, "Missing Dependencies", error_msg)
        return False
        
    return True

class TrayRecorder(QSystemTrayIcon):
    initialization_complete = pyqtSignal()
    
    def __init__(self):
        super().__init__()
        
        # Initialize basic state
        self.recording = False
        self.settings_window = None
        self.progress_window = None
        self.processing_window = None
        self.recorder = None
        self.transcriber = None
        
        # Create debug window but don't show it
        # self.debug_window = MicDebugWindow()
        
        # Set tooltip
        self.setToolTip("Telly Spelly")
        
        # Enable activation by left click
        self.activated.connect(self.on_activate)
        
        # Add shortcuts handler
        self.shortcuts = GlobalShortcuts()
        self.shortcuts.start_recording_triggered.connect(self.start_recording)
        self.shortcuts.stop_recording_triggered.connect(self.stop_recording)
        self.shortcuts.toggle_recording_triggered.connect(self.toggle_recording)

    def initialize(self):
        """Initialize the tray recorder after showing loading window"""
        # Set application icon
        self.app_icon = QIcon.fromTheme("telly-spelly")
        if self.app_icon.isNull():
            # Fallback to theme icons if custom icon not found
            self.app_icon = QIcon.fromTheme("media-record")
            logger.warning("Could not load telly-spelly icon, using system theme icon")
            
        # Set the icon for both app and tray
        QApplication.instance().setWindowIcon(self.app_icon)
        self.setIcon(self.app_icon)
        
        # Use app icon for normal state and red recording icon for recording
        self.normal_icon = self.app_icon
        self.recording_icon = QIcon.fromTheme("media-record")
        if self.recording_icon.isNull():
            # Fallback to audio-input-microphone if media-record not available
            self.recording_icon = QIcon.fromTheme("audio-input-microphone")
        if self.recording_icon.isNull():
            # Last resort: use the app icon
            self.recording_icon = self.app_icon
        
        # Create menu
        self.setup_menu()
        
        # Setup global shortcuts
        if not self.shortcuts.setup_shortcuts():
            logger.warning("Failed to register global shortcuts")
            
    def setup_menu(self):
        menu = QMenu()
        
        # Add recording action
        self.record_action = QAction("Start Recording", menu)
        self.record_action.triggered.connect(self.toggle_recording)
        menu.addAction(self.record_action)
        
        # Add settings action
        self.settings_action = QAction("Settings", menu)
        self.settings_action.triggered.connect(self.toggle_settings)
        menu.addAction(self.settings_action)
        
        # Add debug window action
        # self.debug_action = QAction("Show Debug Window", menu)
        # self.debug_action.triggered.connect(self.toggle_debug_window)
        # menu.addAction(self.debug_action)
        
        # Add separator before quit
        menu.addSeparator()
        
        # Add quit action
        quit_action = QAction("Quit", menu)
        quit_action.triggered.connect(self.quit_application)
        menu.addAction(quit_action)
        
        # Set the context menu
        self.setContextMenu(menu)

    @staticmethod
    def isSystemTrayAvailable():
        return QSystemTrayIcon.isSystemTrayAvailable()

    def toggle_recording(self):
        if self.recording:
            # Stop recording
            self.recording = False
            self.record_action.setText("Start Recording")
            self.setIcon(self.normal_icon)
            
            # Update progress window before stopping recording
            if self.progress_window:
                self.progress_window.set_processing_mode()
                self.progress_window.set_status("Processing audio...")
            
            # Stop the actual recording
            if self.recorder:
                try:
                    self.recorder.stop_recording()
                except Exception as e:
                    logger.error(f"Error stopping recording: {e}")
                    if self.progress_window:
                        self.progress_window.close()
                        self.progress_window = None
                    return
        else:
            # Start recording
            self.recording = True
            # Show progress window
            if not self.progress_window:
                self.progress_window = ProgressWindow("Voice Recording")
                self.progress_window.stop_clicked.connect(self.stop_recording)
            self.progress_window.show()
            
            # Start recording
            self.record_action.setText("Stop Recording")
            self.setIcon(self.recording_icon)
            self.recorder.start_recording()

    def stop_recording(self):
        """Handle stopping the recording and starting processing"""
        logger.info(f"TrayRecorder: stop_recording called, recording={self.recording}")
        if not self.recording:
            return

        logger.info("TrayRecorder: Stopping recording")
        self.toggle_recording()  # This is now safe since toggle_recording handles everything

    def toggle_settings(self):
        if not self.settings_window:
            self.settings_window = SettingsWindow(transcriber=self.transcriber)

        if self.settings_window.isVisible():
            self.settings_window.hide()
        else:
            self.settings_window.show()

    def on_activate(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.Trigger:  # Left click
            self.toggle_recording()

    def quit_application(self):
        # Cleanup recorder
        if self.recorder:
            self.recorder.cleanup()
            self.recorder = None
        
        # Close all windows
        if self.settings_window and self.settings_window.isVisible():
            self.settings_window.close()
            
        if self.progress_window and self.progress_window.isVisible():
            self.progress_window.close()
            
        # Stop recording if active
        if self.recording:
            self.stop_recording()
            
        # Quit the application
        QApplication.quit()

    def update_volume_meter(self, value):
        # Update debug window first
        if hasattr(self, 'debug_window'):
            self.debug_window.update_values(value)
            
        # Then update volume meter as before
        if self.progress_window and self.recording:
            self.progress_window.update_volume(value)
    
    def handle_recording_finished(self, audio_file):
        """Called when recording is saved to file"""
        logger.info("TrayRecorder: Recording finished, starting transcription")
        
        # Ensure progress window is in processing mode
        if self.progress_window:
            self.progress_window.set_processing_mode()
            self.progress_window.set_status("Starting transcription...")
        
        if self.transcriber:
            self.transcriber.transcribe_file(audio_file)
        else:
            logger.error("Transcriber not initialized")
            if self.progress_window:
                self.progress_window.close()
                self.progress_window = None
            QMessageBox.critical(None, "Error", "Transcriber not initialized")
    
    def handle_recording_error(self, error):
        """Handle recording errors"""
        logger.error(f"TrayRecorder: Recording error: {error}")
        QMessageBox.critical(None, "Recording Error", error)
        self.stop_recording()
        if self.progress_window:
            self.progress_window.close()
            self.progress_window = None
    
    def update_processing_status(self, status):
        if self.progress_window:
            self.progress_window.set_status(status)
    
    def handle_transcription_finished(self, text):
        if text:
            # Copy text to clipboard
            QApplication.clipboard().setText(text)
            self.showMessage("Transcription Complete", 
                           "Text has been copied to clipboard",
                           self.normal_icon)
        
        # Close the progress window
        if self.progress_window:
            self.progress_window.close()
            self.progress_window = None
    
    def handle_transcription_error(self, error):
        QMessageBox.critical(None, "Transcription Error", error)
        if self.progress_window:
            self.progress_window.close()
            self.progress_window = None

    def start_recording(self):
        """Start a new recording"""
        logger.info("TrayRecorder: start_recording called")
        if not self.recording:
            self.toggle_recording()

    def toggle_debug_window(self):
        """Toggle debug window visibility"""
        if self.debug_window.isVisible():
            self.debug_window.hide()
            self.debug_action.setText("Show Debug Window")
        else:
            self.debug_window.show()
            self.debug_action.setText("Hide Debug Window")

def setup_application_metadata():
    QCoreApplication.setApplicationName("Telly Spelly")
    QCoreApplication.setApplicationVersion("1.0")
    QCoreApplication.setOrganizationName("Telly Spelly")
    QCoreApplication.setOrganizationDomain("tellyspelly.org")

def check_already_running():
    """Check if another instance is already running via D-Bus"""
    try:
        import dbus
        from .desktop_env import get_dbus_service_name
        bus = dbus.SessionBus()
        dbus_service = get_dbus_service_name()
        # Try to get the existing service
        proxy = bus.get_object(dbus_service, '/TellySpelly')
        # If we get here, the service exists - another instance is running
        return True
    except dbus.DBusException:
        # Service doesn't exist, no other instance running
        return False
    except Exception:
        return False

def send_notification(title, message, timeout_ms=20000, replaces_id=0):
    """Send a desktop notification via D-Bus"""
    try:
        import dbus
        bus = dbus.SessionBus()
        notify = bus.get_object('org.freedesktop.Notifications', '/org/freedesktop/Notifications')
        iface = dbus.Interface(notify, 'org.freedesktop.Notifications')
        nid = iface.Notify('Telly Spelly', dbus.UInt32(replaces_id), 'telly-spelly', title, message, [], {}, timeout_ms)
        return int(nid)
    except Exception as e:
        logger.warning(f"Could not send notification: {e}")
        return 0

def close_notification(notification_id):
    """Close a notification by ID"""
    if not notification_id:
        return
    try:
        import dbus
        bus = dbus.SessionBus()
        notify = bus.get_object('org.freedesktop.Notifications', '/org/freedesktop/Notifications')
        iface = dbus.Interface(notify, 'org.freedesktop.Notifications')
        iface.CloseNotification(dbus.UInt32(notification_id))
    except Exception as e:
        logger.debug(f"Could not close notification: {e}")

def main():
    try:
        app = QApplication(sys.argv)
        setup_application_metadata()

        # Check if already running
        if check_already_running():
            send_notification('Telly Spelly', 'Already running. Check your system tray.', 3000)
            return 0

        # Auto-install desktop integration on first run
        if install_silent():
            logger.info("Desktop integration installed automatically")

        # Detect GPU and configure available models on every start
        settings = Settings()
        force_cpu = settings.get_force_cpu()

        # Always check GPU availability (it may have changed since last run)
        if force_cpu:
            config = gpu.detect_and_configure(force_cpu=True)
        else:
            config = gpu.detect_and_configure()

        # Check if hardware situation changed
        previous_gpu_memory = settings.get_gpu_memory()
        current_gpu_memory = config['gpu_memory_gb']

        # GPU became unavailable (was available, now not)
        if previous_gpu_memory is not None and current_gpu_memory is None and not force_cpu:
            logger.warning("GPU no longer available, switching to CPU mode")
        # GPU became available (was not available, now is)
        elif previous_gpu_memory is None and current_gpu_memory is not None and not force_cpu:
            logger.info(f"GPU now available: {current_gpu_memory:.1f}GB VRAM")

        # Update settings
        settings.set_gpu_memory(config['gpu_memory_gb'])
        settings.set_available_models(config['available_models'])

        # Adjust model if current one is no longer available
        current_model = settings.get('model', None)
        if current_model is None or current_model not in config['available_models']:
            settings.set('model', config['default_model'])
            logger.info(f"Model set to: {config['default_model']}")

        settings.set_hardware_detected(True)
        logger.info(f"Hardware config: GPU={config['gpu_memory_gb']}GB, Models={config['available_models']}")

        # Send startup notification (0 = no expiry, will be replaced when ready)
        startup_notification_id = send_notification('Telly Spelly', 'Starting up...', 0)

        # Check if system tray is available
        if not TrayRecorder.isSystemTrayAvailable():
            close_notification(startup_notification_id)
            send_notification('Telly Spelly', 'Error: System tray not available.', 5000)
            return 1

        # Create tray icon but don't initialize yet
        tray = TrayRecorder()

        # Replace startup notification with ready notification when initialization completes
        def on_init_complete():
            # Check if shortcut was registered successfully
            if tray.shortcuts and tray.shortcuts.registered:
                msg = 'Ready! Press Ctrl+Alt+R to toggle recording.'
            else:
                msg = 'Ready! Configure shortcut in System Settings → Shortcuts → Telly Spelly'
            send_notification('Telly Spelly', msg, 8000, startup_notification_id)

        tray.initialization_complete.connect(on_init_complete)

        # Check dependencies
        if not check_dependencies():
            close_notification(startup_notification_id)
            return 1

        # Ensure the application doesn't quit when last window is closed
        app.setQuitOnLastWindowClosed(False)

        # Initialize tray in background
        QTimer.singleShot(100, lambda: initialize_tray(tray, startup_notification_id, app))
        
        return app.exec()
        
    except Exception as e:
        logger.exception("Failed to start application")
        QMessageBox.critical(None, "Error", 
            f"Failed to start application: {str(e)}")
        return 1

def initialize_tray(tray, startup_notification_id, app):
    try:
        # Initialize basic tray setup
        tray.initialize()

        # Initialize recorder
        tray.recorder = AudioRecorder()

        # Initialize transcriber
        tray.transcriber = WhisperTranscriber()

        # Connect signals
        tray.recorder.volume_updated.connect(tray.update_volume_meter)
        tray.recorder.recording_finished.connect(tray.handle_recording_finished)
        tray.recorder.recording_error.connect(tray.handle_recording_error)

        tray.transcriber.transcription_progress.connect(tray.update_processing_status)
        tray.transcriber.transcription_finished.connect(tray.handle_transcription_finished)
        tray.transcriber.transcription_error.connect(tray.handle_transcription_error)

        # Make tray visible
        tray.setVisible(True)

        # Signal completion
        tray.initialization_complete.emit()

    except Exception as e:
        logger.error(f"Initialization failed: {e}")
        close_notification(startup_notification_id)
        send_notification('Telly Spelly', f'Failed to start: {str(e)}', 10000)

if __name__ == "__main__":
    sys.exit(main()) 