from __future__ import annotations

import asyncio
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

    assert format_event_summary(event) == "train [ended] - 30.000s"


def test_format_event_summary_handles_missing_attributes() -> None:
    """Test format_event_summary with missing attributes."""
    event = object()  # No label, state, or duration
    assert format_event_summary(event) == "unknown [unknown] - 0.000s"


def test_format_event_summary_distinguishes_close_sub_second_durations() -> None:
    """Regression test: with only 1 decimal place, distinct started/active
    events with sub-100ms durations (as seen when a fixture file is
    processed far faster than real time, e.g. in the container smoke test)
    all rendered as the identical, confusing 'label - 0.0s' -- making a
    correctly-firing sequence of events look like the aggregator was
    spamming duplicate 'started' events. 3 decimal places is enough to
    show these are genuinely different, correctly-progressing events."""
    started = EventMessage(
        event_type="audio.detected",
        label="dog",
        confidence=0.89,
        duration=0.0,
        state="started",
        model="yamnet",
    )
    active = EventMessage(
        event_type="audio.detected",
        label="dog",
        confidence=0.97,
        duration=0.0142,
        state="active",
        model="yamnet",
    )

    assert format_event_summary(started) != format_event_summary(active)
    assert format_event_summary(started) == "dog [started] - 0.000s"
    assert format_event_summary(active) == "dog [active] - 0.014s"


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
        mock_aggregator_instance.flush.return_value = []
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
        mock_aggregator_instance.flush.return_value = []
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
        mock_aggregator_instance.flush.return_value = []
        mock_aggregator.return_value = mock_aggregator_instance

        mock_addon_manager_instance = MagicMock()
        mock_addon_manager_instance.close = AsyncMock()
        mock_addon_manager_class.return_value = mock_addon_manager_instance

        mock_webui_instance = MagicMock()
        _webui_ready = asyncio.Event()

        async def _webui_start(**kwargs):
            _webui_ready.set()

        mock_webui_instance.start = AsyncMock(side_effect=_webui_start)
        mock_webui_instance.started = _webui_ready
        mock_webui_class.return_value = mock_webui_instance

        mock_ha_client_instance = MagicMock()
        mock_ha_client_instance.close = AsyncMock()
        # _run_pipeline now always calls the idempotent init_entities().
        mock_ha_client_instance.init_entities = AsyncMock()
        mock_ha_client_class.return_value = mock_ha_client_instance

        await _run_pipeline(config)

    # AddonManager must be constructed with the real supervisor token, not
    # called with zero arguments.
    mock_addon_manager_class.assert_called_once_with("test-supervisor-token")

    # WebUI.start must be awaited with the host/port the user configured --
    # not called with a signature the method doesn't accept, and not left
    # as a dangling, never-awaited task.
    mock_webui_instance.start.assert_awaited_once_with(host="0.0.0.0", port=8123)


@pytest.mark.asyncio
async def test_pipeline_flushes_active_events_when_stream_ends() -> None:
    """Regression: when the audio stream ends, still-active aggregated events
    must be flushed as 'ended' so HA binary sensors don't stay stuck 'on'."""
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
    )

    ended_event = EventMessage(
        event_type="audio.detected",
        label="dog",
        confidence=0.9,
        duration=4.2,
        state="ended",
        model="yamnet",
    )

    class EmptyAsyncIterator:
        def __aiter__(self):
            return self

        async def __anext__(self):
            raise StopAsyncIteration

    with (
        patch("app.main.AudioStreamSource") as mock_source_class,
        patch("app.main.build_classifier"),
        patch("app.main.EventAggregator") as mock_aggregator,
    ):
        mock_source = MagicMock()
        mock_source.stream.return_value = EmptyAsyncIterator()
        mock_source_class.return_value = mock_source

        aggregator = MagicMock()
        aggregator.update.return_value = []
        aggregator.flush.return_value = [ended_event]
        mock_aggregator.return_value = aggregator

        await _run_pipeline(config)

        aggregator.flush.assert_called_once()


@pytest.mark.asyncio
async def test_webui_starts_while_stream_is_still_live() -> None:
    """Regression for a live incident: the Web UI used to be awaited only
    AFTER the detection task finished, but a healthy live stream never ends
    -- so the ingress panel never became reachable ('app not ready' forever)
    while detection quietly worked. The server must bind while the stream is
    still flowing, and a later pipeline failure must neither crash the run
    nor stop the already-started server."""
    import asyncio as aio

    config = AppConfig(
        model="yamnet",
        audio=AudioSourceConfig(sample_rate=16000, channels=1),
        activity=ActivityConfig(rms_threshold=0.001, peak_threshold=0.001),
        buffer_seconds=3.0,
        aggregation=AggregationConfig(start_confidence=0.5, end_timeout=2.0),
        classifier=ClassifierConfig(threshold=0.5, include=[], exclude=[]),
        homeassistant=HomeAssistantConfig(enabled=False),
        mqtt=MQTTConfig(enabled=False),
        webui=WebUIConfig(enabled=True, host="127.0.0.1", port=8123),
    )

    started = aio.Event()

    class SlowLiveStream:
        """First chunk flows immediately; the 'live' stream then hangs until
        poked, proving the panel comes up while detection is still running."""

        def __init__(self):
            self.n = 0

        def __aiter__(self):
            return self

        async def __anext__(self):
            self.n += 1
            if self.n == 1:
                return np.zeros(8000, dtype=np.float32)
            # Simulate the stream hanging/never ending until we poke it.
            await started.wait()
            raise RuntimeError("stream exploded mid-run")

    stream = SlowLiveStream()

    with (
        patch("app.main.AudioStreamSource") as mock_source_class,
        patch("app.main.build_classifier"),
        patch("app.main.EventAggregator") as mock_aggregator,
        patch("app.main.AddonManager") as mock_addon_manager_class,
        patch("app.main.WebUI") as mock_webui_class,
        patch("app.main.HomeAssistantClient") as mock_ha_client_class,
        patch.dict("os.environ", {"SUPERVISOR_TOKEN": "t"}),
    ):
        mock_source = MagicMock()
        mock_source.stream.return_value = stream
        mock_source_class.return_value = mock_source

        aggregator = MagicMock()
        aggregator.update.return_value = []
        aggregator.flush.return_value = []
        mock_aggregator.return_value = aggregator

        addon_mgr = MagicMock()
        addon_mgr.close = AsyncMock()
        mock_addon_manager_class.return_value = addon_mgr

        webui = MagicMock()
        ready = aio.Event()

        async def _start(**kwargs):
            ready.set()

        webui.start = AsyncMock(side_effect=_start)
        webui.started = ready
        mock_webui_class.return_value = webui

        ha_client = MagicMock()
        ha_client.close = AsyncMock()
        ha_client.init_entities = AsyncMock()
        mock_ha_client_class.return_value = ha_client

        pipeline_task = aio.create_task(_run_pipeline(config))

        # The panel must come up while the stream is still live: the second
        # chunk blocks on `started`, so at bind time the pipeline must be
        # running (not finished) -- server and detection are concurrent.
        await aio.wait_for(ready.wait(), timeout=2)
        assert not pipeline_task.done()

        # Now break the stream; the pipeline must survive it.
        started.set()
        await aio.wait_for(pipeline_task, timeout=5)

        webui.start.assert_awaited_once()
        aggregator.flush.assert_called_once()


@pytest.mark.asyncio
async def test_webui_survives_pipeline_failure() -> None:
    """Regression: a failing audio pipeline (e.g. bad source_path) used to
    tear down the whole process via asyncio.gather, making it impossible to
    fix the source from the ingress panel. The Web UI must stay up."""
    config = AppConfig(
        model="yamnet",
        audio=AudioSourceConfig(sample_rate=16000, channels=1),
        activity=ActivityConfig(rms_threshold=0.001, peak_threshold=0.001),
        buffer_seconds=3.0,
        aggregation=AggregationConfig(start_confidence=0.5, end_timeout=2.0),
        classifier=ClassifierConfig(threshold=0.5, include=[], exclude=[]),
        homeassistant=HomeAssistantConfig(enabled=False),
        mqtt=MQTTConfig(enabled=False),
        webui=WebUIConfig(enabled=True, host="127.0.0.1", port=8123),
    )

    class FailingAsyncIterator:
        def __aiter__(self):
            return self

        async def __anext__(self):
            raise RuntimeError("ffmpeg not found for source_path")

    with (
        patch("app.main.AudioStreamSource") as mock_source_class,
        patch("app.main.build_classifier"),
        patch("app.main.EventAggregator") as mock_aggregator,
        patch("app.main.AddonManager") as mock_addon_manager_class,
        patch("app.main.WebUI") as mock_webui_class,
        patch("app.main.HomeAssistantClient") as mock_ha_client_class,
        patch.dict("os.environ", {"SUPERVISOR_TOKEN": "test-supervisor-token"}),
    ):
        mock_source = MagicMock()
        mock_source.stream.return_value = FailingAsyncIterator()
        mock_source_class.return_value = mock_source

        aggregator = MagicMock()
        aggregator.update.return_value = []
        aggregator.flush.return_value = []
        mock_aggregator.return_value = aggregator

        mock_addon_manager_instance = MagicMock()
        mock_addon_manager_instance.close = AsyncMock()
        mock_addon_manager_class.return_value = mock_addon_manager_instance

        mock_webui_instance = MagicMock()
        _webui_ready = asyncio.Event()

        async def _webui_start(**kwargs):
            _webui_ready.set()

        mock_webui_instance.start = AsyncMock(side_effect=_webui_start)
        mock_webui_instance.started = _webui_ready
        mock_webui_class.return_value = mock_webui_instance

        mock_ha_client_instance = MagicMock()
        mock_ha_client_instance.close = AsyncMock()
        mock_ha_client_instance.init_entities = AsyncMock()
        mock_ha_client_class.return_value = mock_ha_client_instance

        # Must not raise even though the stream source exploded.
        await _run_pipeline(config)

        # The web server was started (and thus awaited) despite the failure.
        mock_webui_instance.start.assert_awaited_once_with(host="127.0.0.1", port=8123)


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
    """Test main_sync handles generic exception by logging it and exiting
    non-zero. Previously this only logged and returned normally (exit 0),
    which meant neither Supervisor nor a container-based CI smoke test
    could tell a real crash apart from a clean run."""
    mock_config = MagicMock()
    mock_load_config.return_value = mock_config
    mock_run.side_effect = Exception("Test error")

    with pytest.raises(SystemExit) as exc_info:
        main_sync()

    assert exc_info.value.code == 1
    mock_logger.exception.assert_called_with("Unhandled error in HA Audio Events")
