from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QLabel, QComboBox,
                            QGroupBox, QFormLayout, QPushButton,
                            QMessageBox, QCheckBox)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
import logging
import subprocess
import os
from .settings import Settings
from .desktop_env import get_desktop_environment, get_dbus_service_name

logger = logging.getLogger(__name__)

# Mapping from model name to cache filename
MODEL_CACHE_FILES = {
    'tiny': 'tiny.pt',
    'tiny.en': 'tiny.en.pt',
    'base': 'base.pt',
    'base.en': 'base.en.pt',
    'small': 'small.pt',
    'small.en': 'small.en.pt',
    'medium': 'medium.pt',
    'medium.en': 'medium.en.pt',
    'large': 'large-v3.pt',
    'large-v1': 'large-v1.pt',
    'large-v2': 'large-v2.pt',
    'large-v3': 'large-v3.pt',
    'turbo': 'large-v3-turbo.pt',
    'large-v3-turbo': 'large-v3-turbo.pt',
}


def is_model_cached(model_name):
    """Check if a model is already downloaded"""
    cache_file = MODEL_CACHE_FILES.get(model_name, f"{model_name}.pt")
    cache_path = os.path.join(os.path.expanduser("~"), ".cache", "whisper", cache_file)
    return os.path.exists(cache_path)


class ModelLoaderThread(QThread):
    """Thread to load whisper model without blocking UI"""
    progress = pyqtSignal(str)
    finished = pyqtSignal(object)  # Emits the loaded model
    error = pyqtSignal(str)

    def __init__(self, model_name):
        super().__init__()
        self.model_name = model_name

    def run(self):
        try:
            import whisper

            # Check if model needs to be downloaded
            if is_model_cached(self.model_name):
                self.progress.emit(f"Loading {self.model_name} model...")
            else:
                self.progress.emit(f"Downloading {self.model_name} model...")

            model = whisper.load_model(self.model_name)
            self.finished.emit(model)

        except Exception as e:
            logger.exception("Failed to load whisper model")
            self.error.emit(str(e))


class SettingsWindow(QWidget):
    model_changed = pyqtSignal(object, str)  # Emits (new_model, model_name)

    def __init__(self, transcriber=None):
        super().__init__()
        self.transcriber = transcriber
        self.setWindowTitle("Telly Spelly Settings")
        self.setWindowFlags(Qt.WindowType.WindowStaysOnTopHint)

        # Initialize settings
        self.settings = Settings()

        # Track loading state
        self.loader_thread = None
        self.is_loading = False

        layout = QVBoxLayout()
        self.setLayout(layout)

        # Model settings group
        model_group = QGroupBox("Model Settings")
        model_layout = QFormLayout()

        self.model_combo = QComboBox()
        # Only show models available for current hardware
        available_models = self.settings.get_available_models()
        self.model_combo.addItems(available_models)
        current_model = self.settings.get('model', 'base')
        if current_model in available_models:
            self.model_combo.setCurrentText(current_model)
        self.model_combo.currentTextChanged.connect(self.on_model_changed)
        model_layout.addRow("Whisper Model:", self.model_combo)

        # Status label for loading/downloading
        self.status_label = QLabel("")
        self.status_label.setStyleSheet("color: #666; font-style: italic;")
        model_layout.addRow("", self.status_label)

        # Show GPU info and excluded models
        gpu_memory = self.settings.get_gpu_memory()
        if gpu_memory:
            gpu_text = f"GPU: {gpu_memory:.1f} GB VRAM"
        else:
            gpu_text = "GPU: Not detected (CPU mode)"

        # Check for excluded models
        all_models = Settings.ALL_MODELS
        excluded = [m for m in all_models if m not in available_models]
        if excluded:
            gpu_text += f"\nExcluded models (insufficient VRAM): {', '.join(excluded)}"

        gpu_label = QLabel(gpu_text)
        gpu_label.setStyleSheet("color: gray; font-size: 10px;")
        gpu_label.setWordWrap(True)
        model_layout.addRow("", gpu_label)

        # Force CPU checkbox
        self.force_cpu_checkbox = QCheckBox("Disable GPU (use CPU only)")
        self.force_cpu_checkbox.setChecked(self.settings.get_force_cpu())
        self.force_cpu_checkbox.stateChanged.connect(self.on_force_cpu_changed)
        model_layout.addRow("", self.force_cpu_checkbox)

        self.lang_combo = QComboBox()
        # Add all supported languages
        for code, name in Settings.VALID_LANGUAGES.items():
            self.lang_combo.addItem(name, code)
        current_lang = self.settings.get('language', 'auto')
        # Find and set the current language
        index = self.lang_combo.findData(current_lang)
        if index >= 0:
            self.lang_combo.setCurrentIndex(index)
        self.lang_combo.currentIndexChanged.connect(self.on_language_changed)
        model_layout.addRow("Language:", self.lang_combo)

        model_group.setLayout(model_layout)
        layout.addWidget(model_group)

        # Recording settings group
        recording_group = QGroupBox("Recording Settings")
        recording_layout = QFormLayout()

        self.device_combo = QComboBox()
        self.device_combo.addItems(["Default Microphone"])
        current_mic = self.settings.get('mic_index', 0)
        self.device_combo.setCurrentIndex(current_mic)
        self.device_combo.currentIndexChanged.connect(self.on_device_changed)
        recording_layout.addRow("Input Device:", self.device_combo)

        recording_group.setLayout(recording_layout)
        layout.addWidget(recording_group)

        # Add shortcuts group
        shortcuts_group = QGroupBox("Keyboard Shortcuts")
        shortcuts_layout = QVBoxLayout()

        shortcuts_label = QLabel("Shortcuts are managed by the system.\nClick below to configure them.")
        shortcuts_layout.addWidget(shortcuts_label)

        open_shortcuts_btn = QPushButton("Open System Shortcuts Settings")
        open_shortcuts_btn.clicked.connect(self.open_system_shortcuts)
        shortcuts_layout.addWidget(open_shortcuts_btn)

        shortcuts_group.setLayout(shortcuts_layout)
        layout.addWidget(shortcuts_group)

        # Add stretch to keep widgets at the top
        layout.addStretch()

        # Set a reasonable size
        self.setMinimumWidth(300)

        # Track current model name
        self.current_model_name = current_model

        # Show initial model status
        self._update_initial_status()

    def _update_initial_status(self):
        """Show status of currently loaded model"""
        if self.transcriber and self.transcriber.model:
            self.status_label.setText(f"Model {self.current_model_name} loaded")
        elif is_model_cached(self.current_model_name):
            self.status_label.setText(f"Model {self.current_model_name} ready (cached)")
        else:
            self.status_label.setText(f"Model {self.current_model_name} not downloaded")

    def set_transcriber(self, transcriber):
        """Set the transcriber reference for model updates"""
        self.transcriber = transcriber
        self._update_initial_status()

    def on_force_cpu_changed(self, state):
        force_cpu = state == Qt.CheckState.Checked.value
        self.settings.set_force_cpu(force_cpu)
        QMessageBox.information(self, "Restart Required",
            "Please restart Telly Spelly for this change to take effect.")

    def on_language_changed(self, index):
        language_code = self.lang_combo.currentData()
        try:
            self.settings.set('language', language_code)
        except ValueError as e:
            logger.error(f"Failed to set language: {e}")
            QMessageBox.warning(self, "Error", str(e))

    def on_device_changed(self, index):
        try:
            self.settings.set('mic_index', index)
        except ValueError as e:
            logger.error(f"Failed to set microphone: {e}")
            QMessageBox.warning(self, "Error", str(e))

    def on_model_changed(self, model_name):
        if model_name == self.current_model_name:
            return

        if self.is_loading:
            # Revert selection if already loading
            self.model_combo.blockSignals(True)
            self.model_combo.setCurrentText(self.current_model_name)
            self.model_combo.blockSignals(False)
            QMessageBox.warning(self, "Loading", "Please wait for current model to finish loading.")
            return

        try:
            self.settings.set('model', model_name)
        except ValueError as e:
            logger.error(f"Failed to set model: {e}")
            QMessageBox.warning(self, "Error", str(e))
            return

        # Disable combo while loading
        self.is_loading = True
        self.model_combo.setEnabled(False)

        # Start loading in background thread
        self.loader_thread = ModelLoaderThread(model_name)
        self.loader_thread.progress.connect(self._on_load_progress)
        self.loader_thread.finished.connect(lambda model: self._on_load_finished(model, model_name))
        self.loader_thread.error.connect(self._on_load_error)
        self.loader_thread.start()

    def _on_load_progress(self, message):
        self.status_label.setText(message)

    def _on_load_finished(self, model, model_name):
        self.is_loading = False
        self.model_combo.setEnabled(True)
        self.status_label.setText(f"Model {model_name} loaded")

        # Update the transcriber with new model
        if self.transcriber:
            # Clear old model from memory
            import gc
            old_model = self.transcriber.model
            self.transcriber.model = model
            del old_model
            gc.collect()

            # Try to free GPU memory
            try:
                import torch
                if torch.cuda.is_available():
                    torch.cuda.empty_cache()
            except ImportError:
                pass

            logger.info(f"Transcriber model updated to {model_name}")

        self.current_model_name = model_name
        self.model_changed.emit(model, model_name)

        # Clean up thread
        if self.loader_thread:
            self.loader_thread.deleteLater()
            self.loader_thread = None

    def _on_load_error(self, error):
        self.is_loading = False
        self.model_combo.setEnabled(True)
        self.status_label.setText(f"Error: {error}")

        # Revert to previous model
        self.model_combo.blockSignals(True)
        self.model_combo.setCurrentText(self.current_model_name)
        self.model_combo.blockSignals(False)

        # Restore setting
        try:
            self.settings.set('model', self.current_model_name)
        except ValueError:
            pass

        QMessageBox.critical(self, "Model Load Error", f"Failed to load model: {error}")

        # Clean up thread
        if self.loader_thread:
            self.loader_thread.deleteLater()
            self.loader_thread = None

    def open_system_shortcuts(self):
        """Open keyboard/shortcut settings based on desktop environment"""
        desktop_env = get_desktop_environment()
        dbus_service = get_dbus_service_name(desktop_env)

        if desktop_env == 'kde':
            # Open KDE System Settings
            try:
                # Try KDE 6 first, then KDE 5
                subprocess.Popen(['systemsettings', 'kcm_keys'], start_new_session=True)
            except FileNotFoundError:
                try:
                    subprocess.Popen(['systemsettings5', 'kcm_keys'], start_new_session=True)
                except FileNotFoundError:
                    QMessageBox.information(self, "Shortcuts",
                        "Could not open System Settings.\n\n"
                        "Please open System Settings manually and navigate to:\n"
                        "Shortcuts → Shortcuts → Telly Spelly")
        else:
            # Open XFCE4 keyboard settings
            try:
                subprocess.Popen(['xfce4-keyboard-settings'], start_new_session=True)
            except FileNotFoundError:
                QMessageBox.information(self, "Shortcuts",
                    "Could not open Keyboard Settings.\n\n"
                    "Please open Settings → Keyboard → Application Shortcuts manually\n"
                    "and add a shortcut with this command:\n\n"
                    f"dbus-send --session --type=method_call --dest={dbus_service} "
                    f"/TellySpelly {dbus_service}.ToggleRecording\n\n"
                    "Assign it to Ctrl+Alt+R when prompted.")
