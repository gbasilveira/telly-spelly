from PyQt6.QtCore import QObject, pyqtSignal
from PyQt6.QtGui import QKeySequence
from PyQt6.QtWidgets import QApplication
import logging
from .desktop_env import get_desktop_environment, get_dbus_service_name

logger = logging.getLogger(__name__)

# Try to import D-Bus integration
try:
    import dbus
    import dbus.service
    DBUS_AVAILABLE = True
except ImportError:
    DBUS_AVAILABLE = False
    logger.warning("dbus-python not available, shortcuts will be limited")

# Detect desktop environment and set appropriate D-Bus service name
DESKTOP_ENV = get_desktop_environment()
DBUS_SERVICE = get_dbus_service_name(DESKTOP_ENV)
DBUS_PATH = "/TellySpelly"
DBUS_INTERFACE = DBUS_SERVICE
DESKTOP_FILE = "telly-spelly.desktop"


class DBusService(dbus.service.Object):
    """D-Bus service object that receives shortcut triggers"""

    def __init__(self, bus, path, shortcuts):
        dbus.service.Object.__init__(self, bus, path)
        self.shortcuts = shortcuts

    @dbus.service.method(DBUS_INTERFACE, in_signature='', out_signature='b')
    def StartRecording(self):
        logger.info("D-Bus: StartRecording called")
        self.shortcuts.start_recording_triggered.emit()
        return True

    @dbus.service.method(DBUS_INTERFACE, in_signature='', out_signature='b')
    def StopRecording(self):
        logger.info("D-Bus: StopRecording called")
        self.shortcuts.stop_recording_triggered.emit()
        return True

    @dbus.service.method(DBUS_INTERFACE, in_signature='', out_signature='b')
    def ToggleRecording(self):
        logger.info("D-Bus: ToggleRecording called")
        self.shortcuts.toggle_recording_triggered.emit()
        return True


class GlobalShortcuts(QObject):
    """Global Shortcuts via D-Bus API (supports both KDE and XFCE4)"""

    start_recording_triggered = pyqtSignal()
    stop_recording_triggered = pyqtSignal()
    toggle_recording_triggered = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.dbus_service = None
        self.bus_name = None
        self.registered = False
        self.session_bus = None
        self.desktop_env = DESKTOP_ENV

    def setup_shortcuts(self, start_key='Ctrl+Alt+R', stop_key='Ctrl+Alt+S'):
        """Setup D-Bus service and register shortcuts based on desktop environment"""
        if not DBUS_AVAILABLE:
            logger.warning("D-Bus not available")
            return False

        try:
            self.session_bus = dbus.SessionBus()

            # Request the service name
            self.bus_name = dbus.service.BusName(DBUS_SERVICE, self.session_bus)

            # Create the service object
            self.dbus_service = DBusService(self.bus_name, DBUS_PATH, self)

            self.registered = True
            logger.info(f"D-Bus service registered: {DBUS_SERVICE}")
            logger.info(f"Desktop environment detected: {self.desktop_env}")

            # Try to register shortcuts based on desktop environment
            if self.desktop_env == 'kde':
                self._register_kde_shortcuts()
            else:
                logger.info(f"For {self.desktop_env.upper()}: Configure shortcuts in Settings → Keyboard → Application Shortcuts")
                logger.info(f"Add command: dbus-send --session --type=method_call --dest={DBUS_SERVICE} {DBUS_PATH} {DBUS_INTERFACE}.ToggleRecording")

            return True

        except Exception as e:
            logger.error(f"Failed to setup D-Bus service: {e}")
            import traceback
            traceback.print_exc()
            return False

    def _register_kde_shortcuts(self):
        """Register shortcut with KGlobalAccel and listen for activation"""
        try:
            kglobalaccel = self.session_bus.get_object(
                'org.kde.kglobalaccel',
                '/kglobalaccel'
            )
            iface = dbus.Interface(kglobalaccel, 'org.kde.KGlobalAccel')

            # Use our own component name (not desktop file) for runtime shortcuts
            component_name = "telly_spelly"
            action_name = "toggle_recording"

            # Action ID format: [component, context, action, friendly_name]
            action_id = dbus.Array([
                dbus.String(component_name),
                dbus.String(""),
                dbus.String(action_name),
                dbus.String("Toggle Recording")
            ], signature='s')

            # Register the action
            iface.doRegister(action_id)

            # Ctrl+Alt+R key code
            key_code = 0x04000000 | 0x08000000 | ord('R')
            keys = dbus.Array([dbus.Int32(key_code)], signature='i')

            # Set the shortcut (use setShortcut with flags=0x02 for SetPresent)
            try:
                result = iface.setShortcut(action_id, keys, dbus.UInt32(0x02))
                if result and len(result) > 0:
                    logger.info(f"KDE shortcut set via setShortcut: {list(result)}")
                else:
                    # Fallback to setForeignShortcut
                    iface.setForeignShortcut(action_id, keys)
                    logger.info("KDE shortcut set via setForeignShortcut")
            except dbus.DBusException:
                iface.setForeignShortcut(action_id, keys)
                logger.info("KDE shortcut set via setForeignShortcut (fallback)")

            # Verify
            result = iface.shortcut(action_id)
            if result and len(result) > 0 and result[0] == key_code:
                logger.info("Registered Ctrl+Alt+R shortcut with KGlobalAccel")
            else:
                logger.warning(f"KDE shortcut verification returned: {list(result) if result else 'empty'}")

            # Listen for the shortcut signal
            self._listen_for_kde_shortcut(component_name)

        except dbus.DBusException as e:
            logger.warning(f"Could not register with KGlobalAccel: {e}")
        except Exception as e:
            logger.warning(f"KGlobalAccel registration error: {e}")
            import traceback
            traceback.print_exc()

    def _listen_for_kde_shortcut(self, component_name):
        """Listen for globalShortcutPressed signal from KDE"""
        try:
            # Component path uses the component name with underscores
            component_path = f"/component/{component_name}"
            component = self.session_bus.get_object('org.kde.kglobalaccel', component_path)

            component.connect_to_signal(
                'globalShortcutPressed',
                self._on_kde_shortcut_pressed,
                dbus_interface='org.kde.kglobalaccel.Component'
            )
            logger.info(f"Listening for KDE shortcut signals on {component_path}")
        except dbus.DBusException as e:
            logger.warning(f"Could not setup KDE shortcut listener on {component_path}: {e}")
            # Try alternative path
            try:
                alt_path = "/component/telly_spelly_desktop"
                component = self.session_bus.get_object('org.kde.kglobalaccel', alt_path)
                component.connect_to_signal(
                    'globalShortcutPressed',
                    self._on_kde_shortcut_pressed,
                    dbus_interface='org.kde.kglobalaccel.Component'
                )
                logger.info(f"Listening for KDE shortcut signals on {alt_path}")
            except dbus.DBusException:
                pass

    def _on_kde_shortcut_pressed(self, component_unique, shortcut_unique, timestamp):
        """Handle shortcut press signal from KGlobalAccel"""
        logger.info(f"KGlobalAccel shortcut pressed: {component_unique}/{shortcut_unique}")
        self.toggle_recording_triggered.emit()


    def remove_shortcuts(self):
        """Cleanup"""
        self.registered = False

    def __del__(self):
        self.remove_shortcuts()
