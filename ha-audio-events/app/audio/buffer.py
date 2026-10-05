from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass
class CircularAudioBuffer:
    sample_rate: int
    channels: int
    buffer_seconds: float

    def __post_init__(self) -> None:
        self.capacity = int(self.sample_rate * self.buffer_seconds)
        self._buffer = np.zeros(self.capacity, dtype=np.float32)
        self._write_index = 0
        self._filled = 0

    def append(self, samples: np.ndarray) -> None:
        if samples.ndim != 1:
            raise ValueError("Audio samples must be a 1D numpy array")
        if samples.dtype != np.float32:
            samples = samples.astype(np.float32)

        remaining = self.capacity - self._write_index
        if len(samples) <= remaining:
            self._buffer[self._write_index : self._write_index + len(samples)] = samples
            self._write_index = (self._write_index + len(samples)) % self.capacity
        else:
            self._buffer[self._write_index :] = samples[:remaining]
            overflow = len(samples) - remaining
            self._buffer[:overflow] = samples[remaining:]
            self._write_index = overflow

        self._filled = min(self.capacity, self._filled + len(samples))

    def get_all(self) -> np.ndarray:
        if self._filled < self.capacity:
            return self._buffer[: self._filled].copy()
        return np.concatenate(
            (self._buffer[self._write_index :], self._buffer[: self._write_index])
        )

    def get_window(self, seconds: float) -> np.ndarray:
        requested = int(self.sample_rate * seconds)
        requested = min(requested, self._filled)
        if requested == 0:
            return np.zeros(0, dtype=np.float32)

        if self._filled < self.capacity:
            return self._buffer[self._filled - requested : self._filled].copy()

        start = (self._write_index - requested) % self.capacity
        if start + requested <= self.capacity:
            return self._buffer[start : start + requested].copy()
        second_piece = self._buffer[: (start + requested) - self.capacity]
        return np.concatenate((self._buffer[start:], second_piece))

    @property
    def filled_seconds(self) -> float:
        return self._filled / float(self.sample_rate)
