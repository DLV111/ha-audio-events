from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

import numpy as np

from app.config import ActivityConfig


@dataclass
class ActivityDetector:
    config: ActivityConfig
    _last_activity: datetime | None = None
    _quiet_since: datetime | None = None
    _currently_active: bool = False

    def compute_rms(self, audio: np.ndarray) -> float:
        if audio.size == 0:
            return 0.0
        return float(np.sqrt(np.mean(np.square(audio), dtype=np.float64)))

    def compute_peak(self, audio: np.ndarray) -> float:
        if audio.size == 0:
            return 0.0
        return float(np.max(np.abs(audio)))

    def should_analyze(self, audio: np.ndarray, now: datetime | None = None) -> bool:
        now = now or datetime.now(UTC)
        rms = self.compute_rms(audio)
        peak = self.compute_peak(audio)
        active = rms >= self.config.rms_threshold or peak >= self.config.peak_threshold
        self._currently_active = active
        if active:
            self._last_activity = now
            self._quiet_since = None
            return True

        if self._quiet_since is None:
            self._quiet_since = now
        if self._last_activity is None:
            return False

        if now - self._last_activity <= timedelta(seconds=self.config.hold_time):
            return True

        self._last_activity = None
        return False

    @property
    def currently_active(self) -> bool:
        return self._currently_active

    def silence_timed_out(self, now: datetime | None = None) -> bool:
        if self._quiet_since is None:
            return False
        now = now or datetime.now(UTC)
        return now - self._quiet_since >= timedelta(seconds=self.config.silence_timeout)
