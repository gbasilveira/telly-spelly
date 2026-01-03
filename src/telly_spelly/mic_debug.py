from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel
from PyQt6.QtCore import Qt
import numpy as np

class MicDebugWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Microphone Debug")
        self.setMinimumSize(300, 150)
        
        layout = QVBoxLayout()
        
        # Current value display
        self.value_label = QLabel("Current Value: 0")
        self.value_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.value_label)
        
        # Peak value display
        self.peak_label = QLabel("Peak Value: 0")
        self.peak_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.peak_label)
        
        # Min/Max display
        self.minmax_label = QLabel("Min/Max: 0/0")
        self.minmax_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.minmax_label)
        
        self.setLayout(layout)
        
        # Keep track of values
        self.min_value = float('inf')
        self.max_value = float('-inf')
        self.peak_value = 0
        
    def update_values(self, value):
        if value is None:
            return
            
        # Update min/max
        self.min_value = min(self.min_value, value)
        self.max_value = max(self.max_value, value)
        
        # Update peak with decay
        self.peak_value = max(value, self.peak_value * 0.95)
        
        # Update labels
        self.value_label.setText(f"Current Value: {value:.6f}")
        self.peak_label.setText(f"Peak Value: {self.peak_value:.6f}")
        self.minmax_label.setText(f"Min/Max: {self.min_value:.6f}/{self.max_value:.6f}") 