from __future__ import annotations

import asyncio
import logging
import os
import shutil
import sys
import wave
from collections.abc import AsyncIterator
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from app.audio.resample import ensure_mono, pcm_s16le_to_float32
from app.config import AudioSourceConfig, HomeAssistantConfig

_LOGGER = logging.getLogger(__name__)


@dataclass
class AudioStreamSource:
    config: AudioSourceConfig
    ha_config: HomeAssistantConfig | None = None
    chunk_seconds: float = 0.5

    async def stream(self) -> AsyncIterator[np.ndarray]:
        if self.config.source_path:
            source = str(self.config.source_path).strip()
            path = Path(source)

            if source.startswith("camera."):
                ha_url = (
                    self.ha_config.url
                    if self.ha_config
                    else "http://supervisor/core"
                ).rstrip("/")
                if ha_url.endswith("/homeassistant"):
                    stream_url = f"{ha_url}/api/camera_proxy_stream/{source}"
                elif ha_url.endswith("/api"):
                    stream_url = f"{ha_url}/camera_proxy_stream/{source}"
                else:
                    stream_url = f"{ha_url}/api/camera_proxy_stream/{source}"

                token = (
                    (self.ha_config.token if self.ha_config else None)
                    or os.getenv("SUPERVISOR_TOKEN")
                    or os.getenv("HASS_TOKEN")
                )
                headers = f"Authorization: Bearer {token}\r\n" if token else None

                _LOGGER.info(
                    "Streaming audio from Home Assistant camera entity via ffmpeg: %s (%s)",
                    source,
                    stream_url,
                )
                async for chunk in self._stream_ffmpeg(stream_url, headers=headers):
                    yield chunk
                return

            if source.startswith(("rtsp://", "http://", "https://", "rtmp://")):
                _LOGGER.info("Streaming audio from network URL via ffmpeg: %s", source)
                async for chunk in self._stream_ffmpeg(source):
                    yield chunk
                return

            if path.exists():
                if path.suffix.lower() == ".wav":
                    _LOGGER.info("Streaming audio from local WAV file: %s", path)
                    async for chunk in self._stream_wav(path):
                        yield chunk
                    return
                if path.suffix.lower() in (
                    ".mp3",
                    ".aac",
                    ".flac",
                    ".ogg",
                    ".m4a",
                    ".mp4",
                    ".mkv",
                ):
                    _LOGGER.info("Streaming audio from media file via ffmpeg: %s", path)
                    async for chunk in self._stream_ffmpeg(source):
                        yield chunk
                    return
                _LOGGER.info("Streaming raw PCM audio from file: %s", path)
                async for chunk in self._stream_pcm_file(path):
                    yield chunk
                return

            if shutil.which("ffmpeg"):
                _LOGGER.info("Attempting ffmpeg stream for path/device: %s", source)
                async for chunk in self._stream_ffmpeg(source):
                    yield chunk
                return

        # Default mode (no source_path specified)
        if shutil.which("ffmpeg"):
            _LOGGER.info(
                "No source_path specified. Capturing live audio from PulseAudio default source via ffmpeg."
            )
            try:
                async for chunk in self._stream_ffmpeg("default", is_pulse=True):
                    yield chunk
                return
            except Exception:
                _LOGGER.exception(
                    "PulseAudio ffmpeg capture failed, falling back to stdin stream"
                )

        _LOGGER.info("Streaming raw audio from stdin")
        async for chunk in self._stream_stdin():
            yield chunk

    async def _stream_ffmpeg(
        self,
        target: str,
        is_pulse: bool = False,
        is_alsa: bool = False,
        headers: str | None = None,
    ) -> AsyncIterator[np.ndarray]:
        chunk_size = int(
            self.config.sample_rate * self.config.channels * 2 * self.chunk_seconds
        )
        cmd = ["ffmpeg", "-loglevel", "error"]
        if headers:
            cmd.extend(["-headers", headers])
        if is_pulse:
            cmd.extend(["-f", "pulse", "-i", target or "default"])
        elif is_alsa:
            cmd.extend(["-f", "alsa", "-i", target or "default"])
        else:
            cmd.extend(["-i", target])

        cmd.extend(
            [
                "-vn",
                "-acodec",
                "pcm_s16le",
                "-ar",
                str(self.config.sample_rate),
                "-ac",
                str(self.config.channels),
                "-f",
                "s16le",
                "pipe:1",
            ]
        )

        _LOGGER.debug("Spawning ffmpeg command: %s", " ".join(cmd))
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        try:
            while True:
                assert proc.stdout is not None
                raw = await proc.stdout.read(chunk_size)
                if not raw:
                    break
                yield pcm_s16le_to_float32(raw, self.config.channels)
        except Exception:
            _LOGGER.exception("Error in ffmpeg audio stream reader")
            raise
        finally:
            if proc.returncode is None:
                try:
                    proc.terminate()
                    await proc.wait()
                except Exception:
                    _LOGGER.exception("Error terminating ffmpeg process")

    async def _stream_stdin(self) -> AsyncIterator[np.ndarray]:
        chunk_size = int(
            self.config.sample_rate * self.config.channels * 2 * self.chunk_seconds
        )
        while True:
            raw = await asyncio.to_thread(sys.stdin.buffer.read, chunk_size)
            if not raw:
                break
            yield pcm_s16le_to_float32(raw, self.config.channels)

    async def _stream_pcm_file(self, path: Path) -> AsyncIterator[np.ndarray]:
        chunk_size = int(
            self.config.sample_rate * self.config.channels * 2 * self.chunk_seconds
        )
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
                if sample_rate != self.config.sample_rate:
                    raise ValueError(
                        f"WAV sample rate {sample_rate} does not match configured sample rate {self.config.sample_rate}"
                    )
                if handle.getsampwidth() != 2:
                    raise ValueError("Only 16-bit WAV files are supported")
                chunks = []
                while True:
                    raw = handle.readframes(
                        int(self.config.sample_rate * self.chunk_seconds)
                    )
                    if not raw:
                        break
                    chunks.append(raw)
                return chunks

        raw_chunks = await asyncio.to_thread(read_wav_frames)
        for raw in raw_chunks:
            audio = pcm_s16le_to_float32(raw, channels=self.config.channels)
            yield ensure_mono(audio, self.config.channels)
