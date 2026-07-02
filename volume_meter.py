from PyQt6.QtWidgets import QWidget
from PyQt6.QtCore import Qt, QRect
from PyQt6.QtGui import QPainter, QColor, QLinearGradient
import math
import time


class VolumeMeter(QWidget):
    """Peak-program level meter (PPM-style).

    Driven by normalised peak amplitude (0..1, fraction of full-scale
    int16) and rendered on a dBFS scale with fast-attack / slow-release
    ballistics. 0 dBFS == digital full scale == clipping, so the meter
    only reaches the top when the signal genuinely clips; the noise
    floor sits near the bottom instead of saturating the bar.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(200, 20)

        # Rendered state
        self.value = 0.0          # bar fill, 0..1
        self.peak_hold = 0.0      # peak-hold marker, 0..1
        self.gradient = self._create_gradient()

        # dBFS scale. Span chosen from the measured mic noise floor
        # (peak ~ -35..-39 dBFS in silence): -42 keeps silence pinned
        # near zero while letting normal speech span the middle and
        # clipping reach exactly 1.0.
        self.db_floor = -42.0

        # PPM ballistics, in dB.
        # Attack is effectively instant (snap to the incoming peak) so
        # a transient/clipping sample registers immediately. Release is
        # a slow linear dB decay so the bar falls smoothly after speech.
        self.release_db_per_s = 20.0   # DIN/Type-I PPM release rate
        self.hold_seconds = 1.2        # peak-hold marker dwell time

        # Envelope state (kept in dBFS; converted to 0..1 at paint time).
        self._env_db = self.db_floor
        self._hold_db = self.db_floor
        self._hold_expires = 0.0
        self._last_t = None

    def _create_gradient(self):
        gradient = QLinearGradient(0, 0, self.width(), 0)
        gradient.setColorAt(0.0, QColor(0, 255, 0))    # Green
        gradient.setColorAt(0.5, QColor(255, 255, 0))  # Yellow
        gradient.setColorAt(0.8, QColor(255, 128, 0))  # Orange
        gradient.setColorAt(1.0, QColor(255, 0, 0))    # Red
        return gradient

    def resizeEvent(self, event):
        self.gradient = self._create_gradient()
        super().resizeEvent(event)

    def _db_to_norm(self, db):
        norm = (db - self.db_floor) / (0.0 - self.db_floor)
        return min(1.0, max(0.0, norm))

    def set_value(self, value):
        """Drive the meter with a normalised peak level (0..1)."""
        now = time.monotonic()
        dt = (now - self._last_t) if self._last_t is not None else 0.0
        # Clamp absurd dt (first frame, or stalls) so release stays sane.
        dt = min(dt, 0.1)
        self._last_t = now

        input_db = 20.0 * math.log10(max(float(value), 1e-7))

        # Fast attack: rising signal snaps straight to the peak.
        # Slow release: falling signal decays linearly in dB per second.
        if input_db >= self._env_db:
            self._env_db = input_db
        else:
            self._env_db -= self.release_db_per_s * dt
            if self._env_db < input_db:
                self._env_db = input_db

        # Peak-hold marker: latch the loudest peak, dwell, then release.
        if input_db >= self._hold_db:
            self._hold_db = input_db
            self._hold_expires = now + self.hold_seconds
        elif now > self._hold_expires:
            self._hold_db -= self.release_db_per_s * dt
            if self._hold_db < self._env_db:
                self._hold_db = self._env_db

        self.value = self._db_to_norm(self._env_db)
        self.peak_hold = self._db_to_norm(self._hold_db)

        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Background
        painter.fillRect(self.rect(), Qt.GlobalColor.black)

        inner = self.rect().adjusted(2, 2, -2, -2)
        width = inner.width()
        height = inner.height()

        # Meter fill
        meter_width = int(width * self.value)
        if meter_width > 0:
            fill = QRect(inner)
            fill.setWidth(meter_width)
            painter.fillRect(fill, self.gradient)

        # Peak-hold marker
        if self.peak_hold > 0.001:
            painter.setPen(Qt.GlobalColor.white)
            peak_x = inner.left() + int(width * self.peak_hold)
            painter.drawLine(peak_x, inner.top(), peak_x, inner.bottom())
