from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import numpy as np
import pytest
from app.classifiers.registry import build_classifier
from app.config import (
    ActivityConfig,
    AggregationConfig,
    AppConfig,
    AudioSourceConfig,
    ClassifierConfig,
    HomeAssistantConfig,
    MQTTConfig,
    WebUIConfig,
)
from app.demo import format_file_result
from app.detection.models import EventMessage
from app.main import _run_pipeline, format_event_summary, main_sync


def test_format_event_summary_uses_label_and_duration() -> None:
    event = EventMessage(
        event_type="audio.detected",
        label="train",
        confidence=0.95,
        duration=30.0,
        state="ended",
        model="yamnet",
    )

    assert format_event_summary(event) == "train - 30.0s"


def test_format_event_summary_handles_missing_attributes() -> None:
    """Test format_event_summary with missing attributes."""
    event = object()  # No label or duration
    assert format_event_summary(event) == "unknown - 0.0s"


def test_prepare_waveform_matches_model_input_shape() -> None:
    classifier = build_classifier(AppConfig(model="yamnet"))
    expected_len = int(classifier._input_details[0]["shape"][0])

    waveform = classifier._prepare_waveform(np.zeros(1000, dtype=np.float32))

    assert waveform.shape == (expected_len,)


def test_format_file_result() -> None:
    assert (
        format_file_result("clip.wav", "train", 30.0) == "file clip.wav - train - 30.0s"
    )


@pytest.mark.asyncio
async def test_run_pipeline_no_audio_source() -> None:
    """Test _run_pipeline handles no audio source gracefully."""
    config = AppConfig(
        model="yamnet",
        audio=AudioSourceConfig(sample_rate=16000, channels=1),
        activity=ActivityConfig(rms_threshold=0.01, peak_threshold=0.01),
        buffer_seconds=3.0,
        aggregation=AggregationConfig(start_confidence=0.5, end_timeout=2.0),
        classifier=ClassifierConfig(threshold=0.5, include=[], exclude=[]),
        homeassistant=HomeAssistantConfig(enabled=False),
        mqtt=MQTTConfig(enabled=False),
        webui=WebUIConfig(enabled=False),
        log_level="INFO",
    )

    # Mock the entire pipeline to avoid hanging on stream
    with (
        patch("app.main.AudioStreamSource") as mock_source_class,
        patch("app.main.build_classifier") as mock_classifier,
        patch("app.main.EventAggregator") as mock_aggregator,
    ):

        # Create a source that yields no audio - use a simple async iterator
        class EmptyAsyncIterator:
            def __aiter__(self):
                return self

            async def __anext__(self):
                raise StopAsyncIteration

        mock_source = MagicMock()
        mock_source.stream.return_value = EmptyAsyncIterator()
        mock_source_class.return_value = mock_source

        # Mock classifier to return no detections
        mock_classifier_instance = AsyncMock()
        mock_classifier_instance.classify = AsyncMock(return_value=[])
        mock_classifier.return_value = mock_classifier_instance

        # Mock aggregator
        mock_aggregator_instance = MagicMock()
        mock_aggregator_instance.update.return_value = []
        mock_aggregator.return_value = mock_aggregator_instance

        # Should not raise
        await _run_pipeline(config)


@pytest.mark.asyncio
async def test_run_pipeline_with_audio_chunks() -> None:
    """Test _run_pipeline processes audio chunks."""
    config = AppConfig(
        model="yamnet",
        audio=AudioSourceConfig(sample_rate=16000, channels=1),
        activity=ActivityConfig(rms_threshold=0.001, peak_threshold=0.001),
        buffer_seconds=3.0,
        aggregation=AggregationConfig(start_confidence=0.5, end_timeout=2.0),
        classifier=ClassifierConfig(threshold=0.5, include=[], exclude=[]),
        homeassistant=HomeAssistantConfig(enabled=False),
        mqtt=MQTTConfig(enabled=False),
        webui=WebUIConfig(enabled=False),
        log_level="INFO",
    )

    chunk = (
        np.ones(16000, dtype=np.float32) * 0.01
    )  # Non-zero signal to pass activity detector

    with (
        patch("app.main.AudioStreamSource") as mock_source_class,
        patch("app.main.build_classifier") as mock_classifier,
        patch("app.main.EventAggregator") as mock_aggregator,
    ):
        mock_source = MagicMock()

        class ChunkAsyncIterator:
            def __init__(self):
                self.yielded = False

            def __aiter__(self):
                return self

            async def __anext__(self):
                if not self.yielded:
                    self.yielded = True
                    return chunk
                raise StopAsyncIteration

        mock_source.stream.return_value = ChunkAsyncIterator()
        mock_source_class.return_value = mock_source

        mock_classifier_instance = AsyncMock()
        mock_classifier_instance.classify = AsyncMock(return_value=[])
        mock_classifier.return_value = mock_classifier_instance

        mock_aggregator_instance = MagicMock()
        mock_aggregator_instance.update.return_value = []
        mock_aggregator.return_value = mock_aggregator_instance

        await _run_pipeline(config)

        mock_aggregator_instance.update.assert_called()


@pytest.mark.asyncio
async def test_run_pipeline_wires_up_webui_correctly() -> None:
    """Regression test for a real bug: AddonManager() was previously called
    with no arguments (TypeError: missing required 'supervisor_token'),
    webui.start() was called with a host/port signature the method didn't
    accept (TypeError), and the webui was only started after the pipeline's
    own cleanup as an unawaited asyncio.create_task -- meaning it never
    stayed running in practice. This exercises the actual wiring inside
    _run_pipeline the way main_sync() does, instead of testing WebUI and
    AddonManager only in isolation with mocks that don't touch main.py."""
    config = AppConfig(
        model="yamnet",
        audio=AudioSourceConfig(sample_rate=16000, channels=1),
        activity=ActivityConfig(rms_threshold=0.01, peak_threshold=0.01),
        buffer_seconds=3.0,
        aggregation=AggregationConfig(start_confidence=0.5, end_timeout=2.0),
        classifier=ClassifierConfig(threshold=0.5, include=[], exclude=[]),
        homeassistant=HomeAssistantConfig(enabled=False),
        mqtt=MQTTConfig(enabled=False),
        webui=WebUIConfig(enabled=True, host="0.0.0.0", port=8123),
        log_level="INFO",
    )

    class EmptyAsyncIterator:
        def __aiter__(self):
            return self

        async def __anext__(self):
            raise StopAsyncIteration

    with (
        patch("app.main.AudioStreamSource") as mock_source_class,
        patch("app.main.build_classifier") as mock_classifier,
        patch("app.main.EventAggregator") as mock_aggregator,
        patch("app.main.AddonManager") as mock_addon_manager_class,
        patch("app.main.WebUI") as mock_webui_class,
        patch("app.main.HomeAssistantClient") as mock_ha_client_class,
        patch.dict("os.environ", {"SUPERVISOR_TOKEN": "test-supervisor-token"}),
    ):
        mock_source = MagicMock()
        mock_source.stream.return_value = EmptyAsyncIterator()
        mock_source_class.return_value = mock_source

        mock_classifier_instance = AsyncMock()
        mock_classifier_instance.classify = AsyncMock(return_value=[])
        mock_classifier.return_value = mock_classifier_instance

        mock_aggregator_instance = MagicMock()
        mock_aggregator_instance.update.return_value = []
        mock_aggregator.return_value = mock_aggregator_instance

        mock_addon_manager_instance = MagicMock()
        mock_addon_manager_instance.close = AsyncMock()
        mock_addon_manager_class.return_value = mock_addon_manager_instance

        mock_webui_instance = MagicMock()
        mock_webui_instance.start = AsyncMock(return_value=None)
        mock_webui_class.return_value = mock_webui_instance

        mock_ha_client_instance = MagicMock()
        mock_ha_client_instance.close = AsyncMock()
        mock_ha_client_class.return_value = mock_ha_client_instance

        await _run_pipeline(config)

    # AddonManager must be constructed with the real supervisor token, not
    # called with zero arguments.
    mock_addon_manager_class.assert_called_once_with("test-supervisor-token")

    # WebUI.start must be awaited with the host/port the user configured --
    # not called with a signature the method doesn't accept, and not left
    # as a dangling, never-awaited task.
    mock_webui_instance.start.assert_awaited_once_with(host="0.0.0.0", port=8123)


@patch("app.main.load_config")
@patch("app.main.configure_logging")
@patch("app.main.asyncio.run")
def test_main_sync_success(mock_run, mock_logging, mock_load_config) -> None:
    """Test main_sync runs successfully."""
    mock_config = MagicMock()
    mock_load_config.return_value = mock_config

    main_sync()

    mock_load_config.assert_called_once()
    mock_logging.assert_called_once_with(mock_config.log_level)
    mock_run.assert_called_once()


@patch("app.main.load_config")
@patch("app.main.configure_logging")
@patch("app.main.asyncio.run")
@patch("app.main._LOGGER")
def test_main_sync_keyboard_interrupt(
    mock_logger, mock_run, mock_logging, mock_load_config
) -> None:
    """Test main_sync handles KeyboardInterrupt."""
    mock_config = MagicMock()
    mock_load_config.return_value = mock_config
    mock_run.side_effect = KeyboardInterrupt()

    main_sync()

    mock_logger.info.assert_called_with("Shutting down HA Audio Events add-on")


@patch("app.main.load_config")
@patch("app.main.configure_logging")
@patch("app.main.asyncio.run")
@patch("app.main._LOGGER")
def test_main_sync_exception(
    mock_logger, mock_run, mock_logging, mock_load_config
) -> None:
    """Test main_sync handles generic exception."""
    mock_config = MagicMock()
    mock_load_config.return_value = mock_config
    mock_run.side_effect = Exception("Test error")

    main_sync()

    mock_logger.exception.assert_called_with("Unhandled error in HA Audio Events")
