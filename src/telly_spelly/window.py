from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                           QPushButton, QComboBox, QLabel, QDialog,
                           QProgressBar, QMessageBox, QFrame, QStackedWidget)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer, QSize
from PyQt6.QtGui import QKeySequence, QIcon
from .settings import Settings
from .volume_meter import VolumeMeter
from .mic_test import MicTestDialog
from .recorder import AudioRecorder
from .transcriber import WhisperTranscriber
import numpy as np
import logging

logger = logging.getLogger(__name__)

class ModernFrame(QFrame):
    """A styled frame for grouping controls"""
    def __init__(self, title, parent=None):
        super().__init__(parent)
        self.setFrameStyle(QFrame.Shape.StyledPanel | QFrame.Shadow.Raised)
        
        layout = QVBoxLayout(self)
        
        # Add title
        title_label = QLabel(title)
        title_label.setStyleSheet("font-weight: bold; color: #1d99f3;")
        layout.addWidget(title_label)
        
        # Content widget
        self.content = QWidget()
        self.content_layout = QVBoxLayout(self.content)
        self.content_layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.content)

class RecordingDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Recording...")
        self.setFixedSize(300, 150)
        
        layout = QVBoxLayout(self)
        
        # Status label
        self.label = QLabel("Recording in progress...")
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.label.setStyleSheet("font-weight: bold;")
        
        # Progress bar
        self.progress = QProgressBar()
        self.progress.setRange(0, 0)  # Infinite progress animation
        
        # Volume meter
        self.volume_meter = VolumeMeter()
        
        # Status icon (using system theme icons)
        self.status_icon = QLabel()
        self.status_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.set_recording_status()
        
        # Layout
        layout.addWidget(self.status_icon)
        layout.addWidget(self.label)
        layout.addWidget(self.progress)
        layout.addWidget(self.volume_meter)
        
        # Stop button
        self.stop_btn = QPushButton(QIcon.fromTheme('media-playback-stop'), "Stop Recording")
        layout.addWidget(self.stop_btn)
        
        # Timer for updating volume meter
        self.update_timer = QTimer()
        self.update_timer.setInterval(50)  # 20fps
        self.update_timer.timeout.connect(self.update_volume)
        self.update_timer.start()
        
    def set_recording_status(self):
        """Show recording status"""
        self.status_icon.setPixmap(QIcon.fromTheme('media-record').pixmap(32, 32))
        self.label.setStyleSheet("font-weight: bold; color: #da4453;")  # Red color for recording
        
    def set_processing_status(self):
        """Show processing status"""
        self.status_icon.setPixmap(QIcon.fromTheme('view-refresh').pixmap(32, 32))
        self.label.setStyleSheet("font-weight: bold; color: #1d99f3;")  # Blue color for processing
        
    def set_message(self, message):
        self.label.setText(message)
        
    def set_transcribing(self):
        self.set_message("Processing audio... Please wait")
        self.set_processing_status()
        self.stop_btn.setEnabled(False)
        self.update_timer.stop()
        self.volume_meter.set_value(0)
        
    def update_volume(self, value=None):
        if hasattr(self.parent(), 'recorder'):
            if value is None and self.parent().recorder.frames:
                # Calculate RMS of the last frame if no value provided
                last_frame = np.frombuffer(self.parent().recorder.frames[-1], dtype=np.int16)
                value = np.sqrt(np.mean(np.square(last_frame))) / 32768.0
            if value is not None:
                self.volume_meter.set_value(value)

class WhisperWindow(QMainWindow):
    start_recording = pyqtSignal()
    stop_recording = pyqtSignal()
    output_method_changed = pyqtSignal(str)
    initialization_complete = pyqtSignal()
    
    def __init__(self):
        super().__init__()
        self.settings = Settings()
        self.recording_dialog = None
        self.transcriber = None
        self.recorder = None
        
        # Don't initialize UI yet
        self.central_widget = None
        
    def initialize(self, loading_window):
        """Initialize components with loading feedback"""
        try:
            loading_window.set_status("Loading settings...")
            self.settings = Settings()
            
            loading_window.set_status("Initializing audio system...")
            self.recorder = AudioRecorder()
            
            loading_window.set_status("Loading Whisper model...")
            self.transcriber = WhisperTranscriber()
            
            loading_window.set_status("Creating user interface...")
            self.init_ui()
            self.setup_shortcuts()
            
            loading_window.set_status("Ready!")
            self.initialization_complete.emit()
            
        except Exception as e:
            logger.error(f"Initialization failed: {e}")
            QMessageBox.critical(self, "Error", 
                f"Failed to initialize application: {str(e)}")
            self.initialization_complete.emit()  # Emit anyway to close loading window
        
    def init_ui(self):
        self.setWindowTitle('Telly Spelly')
        self.setWindowIcon(QIcon.fromTheme('audio-input-microphone'))
        self.setMinimumWidth(500)
        
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        
        # Model selection frame
        model_frame = ModernFrame("Whisper Model")
        self.model_combo = QComboBox()
        self.model_combo.addItems(['tiny', 'base', 'small', 'medium', 'large', 'turbo'])
        self.model_combo.setCurrentText(self.settings.get('model', 'turbo'))
        model_frame.content_layout.addWidget(self.model_combo)
        main_layout.addWidget(model_frame)
        
        # Microphone frame
        mic_frame = ModernFrame("Microphone")
        mic_layout = QHBoxLayout()
        
        # Volume meter
        self.volume_meter = VolumeMeter()
        self.volume_meter.setMinimumHeight(30)
        
        # Mic selection
        self.mic_combo = QComboBox()
        self.populate_mic_list()
        
        # Test button
        self.test_button = QPushButton(QIcon.fromTheme('audio-volume-high'), "Test")
        self.test_button.setCheckable(True)
        self.test_button.clicked.connect(self.toggle_mic_test)
        
        mic_layout.addWidget(self.mic_combo, 1)
        mic_layout.addWidget(self.test_button)
        
        mic_frame.content_layout.addLayout(mic_layout)
        mic_frame.content_layout.addWidget(self.volume_meter)
        
        # Level indicator
        self.level_label = QLabel("Level: -∞ dB")
        self.level_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        mic_frame.content_layout.addWidget(self.level_label)
        
        main_layout.addWidget(mic_frame)
        
        # Output frame
        output_frame = ModernFrame("Output")
        self.output_combo = QComboBox()
        self.output_combo.addItems(['Clipboard', 'Active Window'])
        self.output_combo.setCurrentText(self.settings.get('output', 'Clipboard'))
        output_frame.content_layout.addWidget(self.output_combo)
        main_layout.addWidget(output_frame)
        
        # Record button
        record_layout = QHBoxLayout()
        self.record_btn = QPushButton(QIcon.fromTheme('media-record'), 'Start Recording')
        self.record_btn.setIconSize(QSize(32, 32))
        self.record_btn.setStyleSheet("""
            QPushButton {
                padding: 10px;
                background-color: #1d99f3;
                color: white;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #2eaaff;
            }
            QPushButton:pressed {
                background-color: #1a87d7;
            }
        """)
        shortcut_label = QLabel("(Ctrl+Alt+R)")
        shortcut_label.setStyleSheet("color: gray;")
        
        record_layout.addWidget(self.record_btn)
        record_layout.addWidget(shortcut_label)
        record_layout.addStretch()
        
        main_layout.addLayout(record_layout)
        main_layout.addStretch()
        
        # Timer for updating volume meter
        self.update_timer = QTimer()
        self.update_timer.setInterval(50)
        self.update_timer.timeout.connect(self.update_volume)
        
        # Connect signals
        self.record_btn.clicked.connect(self.toggle_recording)
        self.output_combo.currentTextChanged.connect(self.on_output_method_changed)
        
    def populate_mic_list(self):
        self.mic_combo.clear()
        if not self.recorder:
            return
            
        for i in range(self.recorder.audio.get_device_count()):
            device_info = self.recorder.audio.get_device_info_by_index(i)
            if device_info.get('maxInputChannels') > 0:
                name = device_info.get('name')
                self.mic_combo.addItem(name, i)  # Store index directly as integer
                
        # Select previously used mic
        try:
            mic_index = int(self.settings.get('mic_index', -1))
            if mic_index >= 0:
                for i in range(self.mic_combo.count()):
                    if self.mic_combo.itemData(i) == mic_index:
                        self.mic_combo.setCurrentIndex(i)
                        break
        except (ValueError, TypeError):
            pass
        
    def setup_shortcuts(self):
        self.shortcut = QKeySequence("Ctrl+Alt+R")
        # TODO: Add system-wide shortcut registration
        
    def set_transcriber(self, transcriber):
        """Set up transcriber and connect its signals"""
        self.transcriber = transcriber
        self.transcriber.transcription_progress.connect(self.update_transcription_progress)
        self.transcriber.transcription_finished.connect(self.handle_transcription_finished)
        self.transcriber.transcription_error.connect(self.handle_transcription_error)
        
    def toggle_recording(self):
        if not self.recording_dialog:
            # Start recording
            self.start_recording.emit()
            self.recording_dialog = RecordingDialog(self)
            self.recording_dialog.recorder = self.recorder  # Add reference to recorder
            self.recording_dialog.stop_btn.clicked.connect(self.stop_current_recording)
            self.recording_dialog.show()
        
    def stop_current_recording(self):
        if self.recording_dialog:
            self.stop_recording.emit()
            self.recording_dialog.set_transcribing()  # Show processing status

    def update_transcription_progress(self, message):
        if self.recording_dialog:
            self.recording_dialog.set_message(message)
            
    def handle_transcription_finished(self, text):
        if self.recording_dialog:
            self.recording_dialog.close()
            self.recording_dialog = None

    def on_output_method_changed(self, method):
        self.settings.set('output_method', method)
        self.output_method_changed.emit(method)

    def handle_transcription_error(self, error_message):
        QMessageBox.warning(self, "Transcription Error", error_message)
        if self.recording_dialog:
            self.recording_dialog.close()
            self.recording_dialog = None

    def set_recorder(self, recorder):
        """Set up recorder instance"""
        self.recorder = recorder 

    def update_volume(self):
        """Update volume meter during mic test"""
        if not self.recorder or not self.test_button.isChecked():
            self.volume_meter.set_value(0)
            self.level_label.setText("Level: -∞ dB")
            return
            
        try:
            data = self.recorder.get_current_audio_level()
            if data > 0:
                db = 20 * np.log10(data)
                self.level_label.setText(f"Level: {db:.1f} dB")
            else:
                self.level_label.setText("Level: -∞ dB")
            self.volume_meter.set_value(data)
        except Exception as e:
            logger.error(f"Error updating volume: {e}")
            
    def toggle_mic_test(self):
        """Toggle microphone testing"""
        if self.test_button.isChecked():
            # Start testing
            self.start_mic_test()
        else:
            # Stop testing
            self.stop_mic_test()
            
    def start_mic_test(self):
        """Start microphone test"""
        if not self.recorder:
            return
            
        try:
            device_index = self.mic_combo.currentData()
            if device_index is not None:
                self.recorder.start_mic_test(device_index)
                self.update_timer.start()
                self.mic_combo.setEnabled(False)
                # Save the selected mic index
                self.settings.set('mic_index', device_index)
        except Exception as e:
            logger.error(f"Failed to start mic test: {e}")
            self.test_button.setChecked(False)
            QMessageBox.warning(self, "Error", f"Failed to start microphone test: {str(e)}")
            
    def stop_mic_test(self):
        """Stop microphone test"""
        if self.recorder:
            self.recorder.stop_mic_test()
        self.update_timer.stop()
        self.volume_meter.set_value(0)
        self.level_label.setText("Level: -∞ dB")
        self.mic_combo.setEnabled(True) 