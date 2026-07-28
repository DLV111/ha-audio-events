from __future__ import annotations

import numpy as np


def pcm_s16le_to_float32(raw_bytes: bytes, channels: int = 1) -> np.ndarray:
    audio = np.frombuffer(raw_bytes, dtype=np.int16).astype(np.float32)
    if channels > 1:
        audio = audio.reshape(-1, channels).mean(axis=1)
    return audio / 32768.0


def ensure_mono(audio: np.ndarray, channels: int) -> np.ndarray:
    if channels == 1 or audio.ndim == 1:
        return audio
    if audio.ndim == 2:
        return audio.mean(axis=1).astype(np.float32)
    raise ValueError("Unsupported audio shape for mono conversion")
