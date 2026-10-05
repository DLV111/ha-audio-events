"""Tests for the no-audio-stream guard.

Regression for a live incident: HA camera proxy streams that carry no
audio track made ffmpeg produce zero stdout bytes forever -- the pipeline
blocked silently on the first read and users just saw 'no detections
ever' with no explanation.
"""

from __future__ import annotations

import asyncio
from unittest.mock import patch

import numpy as np
import pytest
from app.audio.stream import AudioStreamSource, NoAudioStreamError
from app.config import AudioSourceConfig


class _HangingStdout:
    """Simulates ffmpeg connected to a video-only proxy: never outputs."""

    async def read(self, size: int) -> bytes:
        await asyncio.Event().wait()  # blocks until cancelled
        return b""  # pragma: no cover


class _FakeProc:
    def __init__(self, stdout):
        self.stdout = stdout
        self.stderr = None
        self.returncode = None
        self.terminated = False

    def terminate(self):
        self.terminated = True

    async def wait(self):
        return 0


def _source(timeout: float) -> AudioStreamSource:
    return AudioStreamSource(
        AudioSourceConfig(sample_rate=16000, channels=1),
        first_byte_timeout=timeout,
    )


@pytest.mark.asyncio
async def test_video_only_source_raises_no_audio_stream_error():
    """A source that never delivers audio bytes must fail fast and loudly."""

    async def fake_exec(*args, **kwargs):
        return _FakeProc(_HangingStdout())

    source = _source(0.1)
    with (
        patch("asyncio.create_subprocess_exec", side_effect=fake_exec),
        pytest.raises(NoAudioStreamError, match="video-only"),
    ):
        async for _ in source._stream_ffmpeg("http://camera/x"):
            pass


@pytest.mark.asyncio
async def test_healthy_source_unaffected_by_first_byte_guard():
    """A normal stream (bytes arrive immediately) must flow untouched."""

    class _FastStdout:
        def __init__(self):
            self.calls = 0

        async def read(self, size: int) -> bytes:
            self.calls += 1
            if self.calls == 1:
                return b"\x00\x00" * 64
            return b""  # EOF

    proc = _FakeProc(_FastStdout())

    async def fake_exec(*args, **kwargs):
        return proc

    chunks = []
    with patch("asyncio.create_subprocess_exec", side_effect=fake_exec):
        async for chunk in _source(5)._stream_ffmpeg("rtsp://cam/x"):
            chunks.append(chunk)

    assert len(chunks) == 1
    assert isinstance(chunks[0], np.ndarray)


@pytest.mark.asyncio
async def test_late_audio_within_timeout_still_flows():
    """Slow sources are tolerated: audio arriving just inside the window
    must not be mistaken for a dead stream."""

    class _SlowStartStdout:
        def __init__(self):
            self.calls = 0

        async def read(self, size: int) -> bytes:
            self.calls += 1
            if self.calls == 1:
                await asyncio.sleep(0.05)  # slower than nothing, under limit
                return b"\x01\x00" * 32
            return b""

    async def fake_exec(*args, **kwargs):
        return _FakeProc(_SlowStartStdout())

    chunks = []
    with patch("asyncio.create_subprocess_exec", side_effect=fake_exec):
        async for chunk in _source(2)._stream_ffmpeg("http://cam/x"):
            chunks.append(chunk)

    assert len(chunks) == 1
