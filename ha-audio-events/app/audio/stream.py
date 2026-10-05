from __future__ import annotations

import asyncio
import logging
import os
import shutil
import sys
import wave
from collections import deque
from collections.abc import AsyncIterator
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from app.audio.resample import ensure_mono, pcm_s16le_to_float32
from app.config import AudioSourceConfig, HomeAssistantConfig, normalize_ha_url

_LOGGER = logging.getLogger(__name__)


class NoAudioStreamError(RuntimeError):
    """Raised when a source delivers no audio bytes at all.

    Typical cause: an HA camera proxy stream that is video-only (MJPEG),
    or a device whose microphone isn't streaming. Without this guard the
    pipeline blocks forever on the first read and the user just sees
    "no detections ever" with no hint why.
    """


@dataclass
class AudioStreamSource:
    config: AudioSourceConfig
    ha_config: HomeAssistantConfig | None = None
    chunk_seconds: float = 0.5
    # How long to wait for the FIRST audio byte before declaring the source
    # dead. Generous: slow cameras/networks must not trip it.
    first_byte_timeout: float = 20.0

    @staticmethod
    def build_camera_stream_url(ha_url: str, entity_id: str) -> str:
        """Build the HA camera audio-proxy URL for an entity id."""
        base = normalize_ha_url(ha_url) or "http://supervisor/core"
        return f"{base.rstrip('/')}/api/camera_proxy_stream/{entity_id}"

    async def stream(self) -> AsyncIterator[np.ndarray]:
        if self.config.source_path:
            source = str(self.config.source_path).strip()
            path = Path(source)

            if source.startswith("camera."):
                ha_url = (
                    self.ha_config.url if self.ha_config else "http://supervisor/core"
                )
                stream_url = self.build_camera_stream_url(ha_url, source)

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

        # Drain stderr in the background. If nobody reads the stderr pipe,
        # ffmpeg blocks once the OS pipe buffer fills (~64KB), which deadlocks
        # long-running streams (e.g. chatty RTSP sources).
        stderr_tail: deque[str] = deque(maxlen=10)
        stderr_task: asyncio.Task[None] | None = None
        if proc.stderr is not None:
            stderr_task = asyncio.create_task(
                self._drain_stderr(proc.stderr, stderr_tail)
            )

        unexpected_exit: int | str | None = None
        got_first_byte = False
        try:
            while True:
                if proc.stdout is None:
                    raise RuntimeError("ffmpeg subprocess has no stdout pipe")
                try:
                    if got_first_byte:
                        raw = await proc.stdout.read(chunk_size)
                    else:
                        # First byte decides whether the source carries audio
                        # at all; without this a video-only proxy blocks the
                        # read forever and the add-on looks simply "quiet".
                        raw = await asyncio.wait_for(
                            proc.stdout.read(chunk_size),
                            timeout=self.first_byte_timeout,
                        )
                except TimeoutError:
                    raise NoAudioStreamError(
                        f"No audio received from source within "
                        f"{self.first_byte_timeout:.0f}s. The stream is "
                        f"likely video-only (e.g. an HA camera MJPEG proxy) "
                        f"or the device is not streaming its microphone. "
                        f"Use an audio-capable URL (direct camera RTSP, "
                        f"go2rtc, or an ESP32 mic stream)."
                    ) from None
                if not raw:
                    break
                got_first_byte = True
                yield pcm_s16le_to_float32(raw, self.config.channels)
            # stdout hit EOF: either the source finished (file) or ffmpeg
            # died (unreachable camera/URL). Give it a few seconds to exit
            # so we can tell the two apart instead of going silent zombie.
            try:
                unexpected_exit = await asyncio.wait_for(proc.wait(), timeout=5)
            except TimeoutError:
                pass
        except Exception:
            _LOGGER.exception("Error in ffmpeg audio stream reader")
            raise
        finally:
            if stderr_task is not None:
                stderr_task.cancel()
                await asyncio.gather(stderr_task, return_exceptions=True)
            if proc.returncode is None:
                try:
                    proc.terminate()
                    await proc.wait()
                except Exception:
                    _LOGGER.exception("Error terminating ffmpeg process")
            if unexpected_exit not in (None, 0):
                _LOGGER.error(
                    "Audio stream ended unexpectedly: ffmpeg exited with "
                    "code %s. The source is likely unreachable or has no "
                    "audio track. Recent ffmpeg output:\n%s",
                    unexpected_exit,
                    "\n".join(stderr_tail) or "(no stderr captured)",
                )

    @staticmethod
    async def _drain_stderr(
        stderr: asyncio.StreamReader, tail: deque[str] | None = None
    ) -> None:
        """Consume ffmpeg stderr, logging each line, until EOF."""
        while True:
            line = await stderr.readline()
            if not line:
                break
            text = line.decode("utf-8", errors="replace").strip()
            if text:
                _LOGGER.warning("ffmpeg stderr: %s", text)
                if tail is not None:
                    tail.append(text)

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
        chunk_frames = int(self.config.sample_rate * self.chunk_seconds)

        # Reads happen per-chunk via asyncio.to_thread so the whole file is
        # never held in memory.
        with wave.open(str(path), "rb") as handle:
            sample_rate = handle.getframerate()
            if sample_rate != self.config.sample_rate:
                raise ValueError(
                    f"WAV sample rate {sample_rate} does not match configured sample rate {self.config.sample_rate}"
                )
            if handle.getsampwidth() != 2:
                raise ValueError("Only 16-bit WAV files are supported")

            while True:
                raw = await asyncio.to_thread(handle.readframes, chunk_frames)
                if not raw:
                    break
                audio = pcm_s16le_to_float32(raw, channels=self.config.channels)
                yield ensure_mono(audio, self.config.channels)
