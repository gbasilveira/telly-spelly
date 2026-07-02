from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QLabel, QComboBox, 
                            QGroupBox, QFormLayout, QProgressBar, QPushButton,
                            QLineEdit, QMessageBox, QCheckBox)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
import logging
import keyboard
import pyaudio
from PyQt6.QtGui import QKeySequence
from settings import Settings  # Add this import at the top

logger = logging.getLogger(__name__)

class ShortcutEdit(QLineEdit):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setReadOnly(True)
        self.setPlaceholderText("Click to set shortcut...")
        self.recording = False
        
    def keyPressEvent(self, event):
        if not self.recording:
            return
            
        modifiers = event.modifiers()
        key = event.key()
        
        if key == Qt.Key.Key_Escape:
            self.recording = False
            return
            
        if key in (Qt.Key.Key_Control, Qt.Key.Key_Shift, Qt.Key.Key_Alt, Qt.Key.Key_Meta):
            return
            
        # Create key sequence
        sequence = QKeySequence(modifiers.value | key)
        self.setText(sequence.toString())
        self.recording = False
        self.clearFocus()
        
    def mousePressEvent(self, event):
        self.recording = True
        self.setText("Press shortcut keys...")
        
    def focusOutEvent(self, event):
        super().focusOutEvent(event)
        self.recording = False

class SettingsWindow(QWidget):
    initialization_complete = pyqtSignal()
    shortcuts_changed = pyqtSignal(str, str)  # start_key, stop_key

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Telly Spelly Settings")
        self.setWindowFlags(Qt.WindowType.WindowStaysOnTopHint)
        
        # Initialize settings
        self.settings = Settings()
        
        layout = QVBoxLayout()
        self.setLayout(layout)
        
        # Model settings group
        model_group = QGroupBox("Model Settings")
        model_layout = QFormLayout()
        
        self.model_combo = QComboBox()
        self.model_combo.addItems(Settings.VALID_MODELS)
        current_model = self.settings.get('model', 'base')
        self.model_combo.setCurrentText(current_model)
        self.model_combo.currentTextChanged.connect(self.on_model_changed)
        model_layout.addRow("Whisper Model:", self.model_combo)
        
        self.auto_detect_cb = QCheckBox("Auto-detect language")
        auto_detect = self.settings.get('auto_detect', True)
        self.auto_detect_cb.setChecked(auto_detect)
        self.auto_detect_cb.toggled.connect(self.on_auto_detect_changed)
        model_layout.addRow(self.auto_detect_cb)
        
        self.lang_combo = QComboBox()
        for code, name in Settings.VALID_LANGUAGES.items():
            self.lang_combo.addItem(name, code)
        current_lang = self.settings.get('language', 'en')
        index = self.lang_combo.findData(current_lang)
        if index >= 0:
            self.lang_combo.setCurrentIndex(index)
        self.lang_combo.setEnabled(not auto_detect)
        self.lang_combo.currentIndexChanged.connect(self.on_language_changed)
        model_layout.addRow("Language:", self.lang_combo)

        # GPU / device selection
        self.force_gpu_cb = QCheckBox("Force GPU (CUDA) acceleration")
        force_gpu = self.settings.get('force_gpu', False)
        self.force_gpu_cb.setChecked(force_gpu)
        self.force_gpu_cb.toggled.connect(self.on_force_gpu_changed)
        model_layout.addRow(self.force_gpu_cb)

        # Live device status label, refreshed whenever the setting changes
        # or a model load finishes.
        self.device_status_label = QLabel()
        self.device_status_label.setStyleSheet("color: #666;")
        self._refresh_device_status()
        model_layout.addRow("Active device:", self.device_status_label)

        model_group.setLayout(model_layout)
        layout.addWidget(model_group)
        
        # Recording settings group
        recording_group = QGroupBox("Recording Settings")
        recording_layout = QFormLayout()
        
        self.device_combo = QComboBox()
        self._populate_audio_devices()
        current_mic = self.settings.get('mic_index', 0)
        for i in range(self.device_combo.count()):
            if self.device_combo.itemData(i) == current_mic:
                self.device_combo.setCurrentIndex(i)
                break
        self.device_combo.currentIndexChanged.connect(self.on_device_changed)
        recording_layout.addRow("Input Device:", self.device_combo)
        
        recording_group.setLayout(recording_layout)
        layout.addWidget(recording_group)
        
        # Loading progress
        self.progress_group = QGroupBox("Model Loading")
        progress_layout = QVBoxLayout()
        self.progress_bar = QProgressBar()
        self.progress_label = QLabel("Select a model to load")
        progress_layout.addWidget(self.progress_label)
        progress_layout.addWidget(self.progress_bar)
        self.progress_group.setLayout(progress_layout)
        layout.addWidget(self.progress_group)
        
        # Add shortcuts group
        shortcuts_group = QGroupBox("Keyboard Shortcuts")
        shortcuts_layout = QFormLayout()
        
        self.start_shortcut = ShortcutEdit()
        self.start_shortcut.setText(self.settings.get('start_shortcut', 'ctrl+alt+r'))
        self.stop_shortcut = ShortcutEdit()
        self.stop_shortcut.setText(self.settings.get('stop_shortcut', 'ctrl+alt+s'))
        
        shortcuts_layout.addRow("Start Recording:", self.start_shortcut)
        shortcuts_layout.addRow("Stop Recording:", self.stop_shortcut)
        
        apply_btn = QPushButton("Apply Shortcuts")
        apply_btn.clicked.connect(self.apply_shortcuts)
        shortcuts_layout.addRow(apply_btn)
        
        shortcuts_group.setLayout(shortcuts_layout)
        layout.addWidget(shortcuts_group)
        
        # Add stretch to keep widgets at the top
        layout.addStretch()
        
        # Set a reasonable size
        self.setMinimumWidth(300)
        
        # Initialize whisper model
        self.whisper_model = None
        self.current_model = None

    def _populate_audio_devices(self):
        """Enumerate and populate audio input devices"""
        try:
            p = pyaudio.PyAudio()
            self.device_combo.clear()
            
            default_info = p.get_default_input_device_info()
            default_idx = default_info['index']
            self.device_combo.addItem(f"Default ({default_info['name']})", default_idx)
            
            for i in range(p.get_device_count()):
                try:
                    info = p.get_device_info_by_index(i)
                    if info['maxInputChannels'] > 0 and i != default_idx:
                        self.device_combo.addItem(f"{info['name']}", i)
                except Exception:
                    pass
            p.terminate()
        except Exception as e:
            logger.error(f"Failed to enumerate audio devices: {e}")
            self.device_combo.addItem("Default Microphone", 0)

    def on_auto_detect_changed(self, checked):
        self.lang_combo.setEnabled(not checked)
        try:
            self.settings.set('auto_detect', checked)
        except ValueError as e:
            logger.error(f"Failed to set auto_detect: {e}")

    def on_force_gpu_changed(self, checked):
        try:
            self.settings.set('force_gpu', checked)
        except ValueError as e:
            logger.error(f"Failed to set force_gpu: {e}")
        self._refresh_device_status()

    def _refresh_device_status(self):
        """Show the device that will actually be used given the current
        force_gpu setting and the detected hardware."""
        from transcriber import resolve_device
        force_gpu = self.settings.get('force_gpu', False)
        device, fp16 = resolve_device(force_gpu=force_gpu)
        if device == "cuda":
            try:
                import torch
                gpu_name = torch.cuda.get_device_name(0)
            except Exception:
                gpu_name = "CUDA GPU"
            text = f"GPU: {gpu_name} (fp16)"
        else:
            text = "CPU (fp32)"
            if force_gpu:
                text += " - GPU not available"
        self.device_status_label.setText(text)

    def on_language_changed(self, index):
        language_code = self.lang_combo.currentData()
        try:
            self.settings.set('language', language_code)
        except ValueError as e:
            logger.error(f"Failed to set language: {e}")
            QMessageBox.warning(self, "Error", str(e))

    def on_device_changed(self, index):
        try:
            device_index = self.device_combo.itemData(index)
            self.settings.set('mic_index', device_index)
            logger.info(f"Microphone changed to device index: {device_index}")
        except ValueError as e:
            logger.error(f"Failed to set microphone: {e}")
            QMessageBox.warning(self, "Error", str(e))

    def on_model_changed(self, model_name):
        if model_name == self.current_model:
            return
            
        try:
            self.settings.set('model', model_name)
        except ValueError as e:
            logger.error(f"Failed to set model: {e}")
            QMessageBox.warning(self, "Error", str(e))
            return

        self.progress_label.setText(f"Loading {model_name} model...")
        self.progress_bar.setRange(0, 0)  # Indeterminate progress
        
        # Load model in a separate thread to prevent UI freezing
        QTimer.singleShot(100, lambda: self.load_model(model_name))

    def load_model(self, model_name):
        try:
            import whisper
            from transcriber import resolve_device
            force_gpu = self.settings.get('force_gpu', False)
            device, fp16 = resolve_device(force_gpu=force_gpu)
            self.whisper_model = whisper.load_model(model_name, device=device)
            self.current_model = model_name
            self.progress_label.setText(
                f"Model {model_name} loaded on {device.upper()}"
            )
            self.progress_bar.setRange(0, 100)
            self.progress_bar.setValue(100)
            self._refresh_device_status()
            self.initialization_complete.emit()
        except Exception as e:
            logger.exception("Failed to load whisper model")
            self.progress_label.setText(f"Failed to load model: {str(e)}")
            self.progress_bar.setRange(0, 100)
            self.progress_bar.setValue(0)

    def apply_shortcuts(self):
        try:
            start_key = self.start_shortcut.text()
            stop_key = self.stop_shortcut.text()
            
            if not start_key or not stop_key:
                QMessageBox.warning(self, "Invalid Shortcuts", 
                    "Please set both start and stop shortcuts.")
                return
            
            if start_key == stop_key:
                QMessageBox.warning(self, "Invalid Shortcuts", 
                    "Start and stop shortcuts must be different.")
                return
            
            # Save shortcuts to settings
            self.settings.set('start_shortcut', start_key)
            self.settings.set('stop_shortcut', stop_key)
            
            self.shortcuts_changed.emit(start_key, stop_key)
            
        except Exception as e:
            logger.error(f"Error applying shortcuts: {e}")
            QMessageBox.critical(self, "Error", 
                "Failed to apply shortcuts. Please try different combinations.") 