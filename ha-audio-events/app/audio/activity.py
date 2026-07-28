from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

import numpy as np

from app.config import ActivityConfig


@dataclass
class ActivityDetector:
    config: ActivityConfig
    _last_activity: datetime | None = None

    def compute_rms(self, audio: np.ndarray) -> float:
        if audio.size == 0:
            return 0.0
        return float(np.sqrt(np.mean(np.square(audio), dtype=np.float64)))

    def compute_peak(self, audio: np.ndarray) -> float:
        if audio.size == 0:
            return 0.0
        return float(np.max(np.abs(audio)))

    def should_analyze(self, audio: np.ndarray, now: datetime | None = None) -> bool:
        now = now or datetime.now(timezone.utc)
        rms = self.compute_rms(audio)
        peak = self.compute_peak(audio)
        active = rms >= self.config.rms_threshold or peak >= self.config.peak_threshold
        if active:
            self._last_activity = now
            return True

        if self._last_activity is None:
            return False

        if now - self._last_activity <= timedelta(seconds=self.config.hold_time):
            return True

        self._last_activity = None
        return False
