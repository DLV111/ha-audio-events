from __future__ import annotations

import asyncio
import sys
import wave
from dataclasses import dataclass
from pathlib import Path
from typing import AsyncIterator

import numpy as np

from app.audio.resample import pcm_s16le_to_float32, ensure_mono
from app.config import AudioSourceConfig


@dataclass
class AudioStreamSource:
    config: AudioSourceConfig
    chunk_seconds: float = 0.5

    async def stream(self) -> AsyncIterator[np.ndarray]:
        if self.config.source_path:
            path = Path(self.config.source_path)
            if path.suffix.lower() == ".wav":
                async for chunk in self._stream_wav(path):
                    yield chunk
                return
            async for chunk in self._stream_pcm_file(path):
                yield chunk
            return

        async for chunk in self._stream_stdin():
            yield chunk

    async def _stream_stdin(self) -> AsyncIterator[np.ndarray]:
        chunk_size = int(self.config.sample_rate * self.config.channels * 2 * self.chunk_seconds)
        while True:
            raw = await asyncio.to_thread(sys.stdin.buffer.read, chunk_size)
            if not raw:
                break
            yield pcm_s16le_to_float32(raw, self.config.channels)

    async def _stream_pcm_file(self, path: Path) -> AsyncIterator[np.ndarray]:
        chunk_size = int(self.config.sample_rate * self.config.channels * 2 * self.chunk_seconds)
        with path.open("rb") as handle:
            while True:
                raw = await asyncio.to_thread(handle.read, chunk_size)
                if not raw:
                    break
                yield pcm_s16le_to_float32(raw, self.config.channels)

    async def _stream_wav(self, path: Path) -> AsyncIterator[np.ndarray]:
        def read_wav_frames() -> list[bytes]:
            with wave.open(str(path), "rb") as handle:
                sample_rate = handle.getframerate()
                channels = handle.getnchannels()
                if sample_rate != self.config.sample_rate:
                    raise ValueError(
                        f"WAV sample rate {sample_rate} does not match configured sample rate {self.config.sample_rate}"
                    )
                if handle.getsampwidth() != 2:
                    raise ValueError("Only 16-bit WAV files are supported")
                chunks = []
                chunk_size = int(self.config.sample_rate * channels * 2 * self.chunk_seconds)
                while True:
                    raw = handle.readframes(int(self.config.sample_rate * self.chunk_seconds))
                    if not raw:
                        break
                    chunks.append(raw)
                return chunks

        raw_chunks = await asyncio.to_thread(read_wav_frames)
        for raw in raw_chunks:
            audio = pcm_s16le_to_float32(raw, channels=self.config.channels)
            yield ensure_mono(audio, self.config.channels)
