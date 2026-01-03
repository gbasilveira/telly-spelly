from PyQt6.QtWidgets import QDialog, QVBoxLayout, QLabel, QProgressBar
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QIcon

class LoadingWindow(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Loading Telly Spelly")
        self.setFixedSize(400, 150)
        self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.CustomizeWindowHint)
        
        layout = QVBoxLayout(self)
        
        # Icon and title
        title_layout = QVBoxLayout()
        icon_label = QLabel()
        icon_label.setPixmap(QIcon.fromTheme('audio-input-microphone').pixmap(64, 64))
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label = QLabel("Loading Telly Spelly")
        title_label.setStyleSheet("font-size: 16pt; font-weight: bold; color: #1d99f3;")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        title_layout.addWidget(icon_label)
        title_layout.addWidget(title_label)
        layout.addLayout(title_layout)
        
        # Status message
        self.status_label = QLabel("Initializing...")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_label.setStyleSheet("color: #666;")
        layout.addWidget(self.status_label)
        
        # Progress bar
        self.progress = QProgressBar()
        self.progress.setRange(0, 0)  # Infinite progress
        layout.addWidget(self.progress)
        
    def set_status(self, message):
        self.status_label.setText(message) 