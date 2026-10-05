from __future__ import annotations

import asyncio
from pathlib import Path

import pytest
from app.audio.stream import AudioStreamSource
from app.config import AudioSourceConfig, HomeAssistantConfig

FIXTURE_WAV = (
    Path(__file__).parent / "fixtures" / "audio" / "train" / "freight_train_01.wav"
)


def test_stream_source_wav_file() -> None:
    if not FIXTURE_WAV.exists():
        pytest.skip("Fixture WAV file not found")

    async def _run() -> None:
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
        assert len(chunks[0]) == 8000  # 16000 Hz * 0.5s = 8000 samples

    asyncio.run(_run())


def test_stream_source_ffmpeg_cmd_builder() -> None:
    config = AudioSourceConfig(
        sample_rate=16000, channels=1, source_path="rtsp://192.168.1.100/live"
    )
    source = AudioStreamSource(config=config)
    assert source.config.source_path == "rtsp://192.168.1.100/live"


def test_stream_source_ha_camera_entity() -> None:
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
