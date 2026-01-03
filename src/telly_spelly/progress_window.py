from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QLabel, QProgressBar, 
                            QApplication, QPushButton, QHBoxLayout)
from PyQt6.QtCore import Qt, pyqtSignal
from .volume_meter import VolumeMeter

class ProgressWindow(QWidget):
    stop_clicked = pyqtSignal()  # Signal emitted when stop button is clicked

    def __init__(self, title="Recording"):
        super().__init__()
        self.setWindowTitle(title)
        # Frameless window that stays on top
        self.setWindowFlags(Qt.WindowType.WindowStaysOnTopHint |
                          Qt.WindowType.FramelessWindowHint |
                          Qt.WindowType.Tool)

        # Prevent closing while processing
        self.processing = False

        # Create main layout
        layout = QVBoxLayout()
        layout.setContentsMargins(10, 10, 10, 10)
        self.setLayout(layout)

        # Add status label
        self.status_label = QLabel("Recording...")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.status_label)

        # Create volume meter
        self.volume_meter = VolumeMeter()
        layout.addWidget(self.volume_meter)

        # Add stop button
        self.stop_button = QPushButton("Stop Recording")
        self.stop_button.clicked.connect(self.stop_clicked.emit)
        layout.addWidget(self.stop_button)

        # Set window size
        self.setFixedSize(300, 120)

        # Style the frameless window
        self.setStyleSheet("""
            ProgressWindow {
                background-color: #2d2d2d;
                border: 1px solid #555;
                border-radius: 8px;
            }
            QLabel {
                color: #fff;
            }
            QPushButton {
                background-color: #c0392b;
                color: white;
                border: none;
                padding: 8px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #e74c3c;
            }
        """)

        # Position in lower right corner
        self._position_lower_right()
    
    def closeEvent(self, event):
        if self.processing:
            event.ignore()
        else:
            super().closeEvent(event)
    
    def set_status(self, text):
        self.status_label.setText(text)
    
    def update_volume(self, value):
        self.volume_meter.set_value(value)
    
    def set_processing_mode(self):
        """Switch UI to processing mode"""
        self.processing = True
        self.volume_meter.hide()
        self.stop_button.hide()
        self.status_label.setText("Processing audio with Whisper...")
        self.setFixedHeight(60)
        self._position_lower_right()
    
    def set_recording_mode(self):
        """Switch back to recording mode"""
        self.processing = False
        self.volume_meter.show()
        self.stop_button.show()
        self.status_label.setText("Recording...")
        self.setFixedHeight(120)
        self._position_lower_right()

    def _position_lower_right(self):
        """Position window in lower right corner with margin"""
        screen = QApplication.primaryScreen().availableGeometry()
        margin = 20
        self.move(
            screen.right() - self.width() - margin,
            screen.bottom() - self.height() - margin
        ) 