from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QComboBox, 
                           QPushButton, QLabel)
from PyQt6.QtCore import Qt, QTimer
import pyaudio
from .volume_meter import VolumeMeter
import numpy as np
import logging

logger = logging.getLogger(__name__)

class MicTestDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Microphone Test")
        self.setFixedSize(400, 200)
        
        # Initialize PyAudio
        self.audio = pyaudio.PyAudio()
        self.stream = None
        self.is_testing = False
        
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout(self)
        
        # Mic selection
        mic_layout = QHBoxLayout()
        mic_label = QLabel("Select Microphone:")
        self.mic_combo = QComboBox()
        self.populate_mic_list()
        mic_layout.addWidget(mic_label)
        mic_layout.addWidget(self.mic_combo)
        layout.addLayout(mic_layout)
        
        # Volume meter
        self.volume_meter = VolumeMeter()
        layout.addWidget(self.volume_meter)
        
        # Level indicator
        self.level_label = QLabel("Level: -∞ dB")
        layout.addWidget(self.level_label)
        
        # Buttons
        button_layout = QHBoxLayout()
        self.test_button = QPushButton("Start Test")
        self.test_button.clicked.connect(self.toggle_test)
        self.ok_button = QPushButton("OK")
        self.ok_button.clicked.connect(self.accept)
        
        button_layout.addWidget(self.test_button)
        button_layout.addWidget(self.ok_button)
        layout.addLayout(button_layout)
        
        # Timer for updating the meter
        self.update_timer = QTimer()
        self.update_timer.setInterval(50)  # 20fps
        self.update_timer.timeout.connect(self.update_level)
        
    def populate_mic_list(self):
        self.mic_combo.clear()
        for i in range(self.audio.get_device_count()):
            device_info = self.audio.get_device_info_by_index(i)
            if device_info.get('maxInputChannels') > 0:  # If it's an input device
                name = device_info.get('name')
                self.mic_combo.addItem(name, device_info)
                logger.info(f"Found input device: {name}")
                
    def toggle_test(self):
        if not self.is_testing:
            self.start_test()
        else:
            self.stop_test()
            
    def start_test(self):
        try:
            device_info = self.mic_combo.currentData()
            if not device_info:
                raise ValueError("No microphone selected")
                
            self.stream = self.audio.open(
                format=pyaudio.paFloat32,
                channels=1,
                rate=44100,
                input=True,
                input_device_index=device_info['index'],
                frames_per_buffer=1024,
                stream_callback=self._audio_callback
            )
            
            self.stream.start_stream()
            self.is_testing = True
            self.test_button.setText("Stop Test")
            self.update_timer.start()
            self.mic_combo.setEnabled(False)
            logger.info(f"Started testing microphone: {device_info['name']}")
            
        except Exception as e:
            logger.error(f"Failed to start microphone test: {e}")
            self.level_label.setText(f"Error: {str(e)}")
            
    def stop_test(self):
        if self.stream:
            self.stream.stop_stream()
            self.stream.close()
            self.stream = None
            
        self.is_testing = False
        self.test_button.setText("Start Test")
        self.update_timer.stop()
        self.mic_combo.setEnabled(True)
        self.volume_meter.set_value(0)
        self.level_label.setText("Level: -∞ dB")
        logger.info("Stopped microphone test")
        
    def _audio_callback(self, in_data, frame_count, time_info, status):
        if status:
            logger.warning(f"Audio callback status: {status}")
        return (in_data, pyaudio.paContinue)
        
    def update_level(self):
        if not self.stream or not self.is_testing:
            return
            
        try:
            data = self.stream.read(1024, exception_on_overflow=False)
            audio_data = np.frombuffer(data, dtype=np.float32)
            rms = np.sqrt(np.mean(np.square(audio_data)))
            
            # Convert to dB
            if rms > 0:
                db = 20 * np.log10(rms)
            else:
                db = -float('inf')
                
            # Update UI
            self.volume_meter.set_value(rms)
            self.level_label.setText(f"Level: {db:.1f} dB")
            
        except Exception as e:
            logger.error(f"Error reading audio data: {e}")
            
    def get_selected_mic_index(self):
        device_info = self.mic_combo.currentData()
        return device_info['index'] if device_info else None
        
    def closeEvent(self, event):
        self.stop_test()
        super().closeEvent(event) 