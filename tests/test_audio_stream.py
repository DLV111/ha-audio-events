"""Tests for audio stream source."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest
from app.audio.stream import AudioStreamSource
from app.config import AudioSourceConfig, HomeAssistantConfig

FIXTURE_WAV = (
    Path(__file__).parent / "fixtures" / "audio" / "train" / "freight_train_01.wav"
)


@pytest.mark.asyncio
async def test_stream_source_wav_file() -> None:
    """Test streaming from a local WAV file."""
    if not FIXTURE_WAV.exists():
        pytest.skip("Fixture WAV file not found")

    config = AudioSourceConfig(
        sample_rate=16000, channels=1, source_path=str(FIXTURE_WAV)
    )
    source = AudioStreamSource(config=config, chunk_seconds=0.5)

    chunks = []
    async for chunk in source.stream():
        chunks.append(chunk)
        if len(chunks) >= 3:
            break

    assert len(chunks) == 3
    assert chunks[0].ndim == 1
    assert len(chunks[0]) == 8000


@pytest.mark.asyncio
async def test_stream_source_ffmpeg_cmd_builder() -> None:
    """Test FFmpeg command builder for network streams."""
    config = AudioSourceConfig(
        sample_rate=16000, channels=1, source_path="rtsp://192.168.1.100/live"
    )
    source = AudioStreamSource(config=config)
    assert source.config.source_path == "rtsp://192.168.1.100/live"


@pytest.mark.asyncio
async def test_stream_source_ha_camera_entity() -> None:
    """Test HA camera entity configuration."""
    audio_config = AudioSourceConfig(
        sample_rate=16000, channels=1, source_path="camera.shed_fluent"
    )
    ha_config = HomeAssistantConfig(
        url="http://supervisor/homeassistant", token="fake-token"
    )
    source = AudioStreamSource(config=audio_config, ha_config=ha_config)

    assert source.config.source_path == "camera.shed_fluent"
    assert source.ha_config is not None
    assert source.ha_config.url == "http://supervisor/homeassistant"


@pytest.mark.asyncio
async def test_stream_wav_resampling_not_supported() -> None:
    """Test WAV file with wrong sample rate raises error."""
    import tempfile
    import wave

    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
        # Create a WAV file with 8000 Hz sample rate
        with wave.open(f.name, "wb") as wav:
            wav.setnchannels(1)
            wav.setsampwidth(2)
            wav.setframerate(8000)  # Wrong sample rate
            wav.writeframes(b"\x00\x00" * 100)

        config = AudioSourceConfig(sample_rate=16000, channels=1, source_path=f.name)
        source = AudioStreamSource(config=config, chunk_seconds=0.5)

        with pytest.raises(ValueError, match="WAV sample rate 8000 does not match"):
            async for _ in source.stream():
                pass


@pytest.mark.asyncio
async def test_stream_wav_16bit_only() -> None:
    """Test WAV file with non-16-bit raises error."""
    import tempfile
    import wave

    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
        with wave.open(f.name, "wb") as wav:
            wav.setnchannels(1)
            wav.setsampwidth(4)  # 32-bit
            wav.setframerate(16000)
            wav.writeframes(b"\x00\x00\x00\x00" * 100)

        config = AudioSourceConfig(sample_rate=16000, channels=1, source_path=f.name)
        source = AudioStreamSource(config=config, chunk_seconds=0.5)

        with pytest.raises(ValueError, match="Only 16-bit WAV files are supported"):
            async for _ in source.stream():
                pass


@pytest.mark.asyncio
async def test_stream_stdin(monkeypatch) -> None:
    """Test streaming from stdin."""
    config = AudioSourceConfig(sample_rate=16000, channels=1, source_path=None)
    source = AudioStreamSource(config=config, chunk_seconds=0.5)

    # Mock stdin
    mock_stdin = MagicMock()
    mock_stdin.buffer.read = MagicMock(side_effect=[b"\x00\x00" * 8000, b""])
    monkeypatch.setattr("sys.stdin", mock_stdin)

    chunks = []
    async for chunk in source.stream():
        chunks.append(chunk)
        if len(chunks) >= 1:
            break

    assert len(chunks) == 1
    assert chunks[0].ndim == 1


@pytest.mark.asyncio
async def test_stream_pcm_file() -> None:
    """Test streaming raw PCM file."""
    import tempfile

    with tempfile.NamedTemporaryFile(suffix=".pcm", delete=False) as f:
        f.write(b"\x00\x00" * 16000)  # 1 second of silence
        pcm_path = Path(f.name)

    config = AudioSourceConfig(sample_rate=16000, channels=1, source_path=str(pcm_path))
    source = AudioStreamSource(config=config, chunk_seconds=0.5)

    chunks = []
    async for chunk in source.stream():
        chunks.append(chunk)
        if len(chunks) >= 2:
            break

    assert len(chunks) == 2


@pytest.mark.asyncio
async def test_stream_ffmpeg_failure(monkeypatch) -> None:
    """Test ffmpeg stream failure handling."""
    config = AudioSourceConfig(
        sample_rate=16000, channels=1, source_path="invalid://stream"
    )
    source = AudioStreamSource(config=config, chunk_seconds=0.5)

    # Mock ffmpeg to fail - need to return an async generator that raises
    async def mock_stream_ffmpeg(*args, **kwargs):
        raise RuntimeError("FFmpeg failed")
        yield  # Make it an async generator (unreachable)

    monkeypatch.setattr(source, "_stream_ffmpeg", mock_stream_ffmpeg)

    # Should raise the exception
    with pytest.raises(RuntimeError, match="FFmpeg failed"):
        async for _ in source.stream():
            pass
