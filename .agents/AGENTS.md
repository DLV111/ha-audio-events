# AI Assistant Guide & Repository Overview: `ha-audio-events`

This document provides AI assistants with a comprehensive technical guide to the structure, architecture, data flow, configuration schemas, testing procedures, and coding guidelines for the **`ha-audio-events`** repository.

---

## 1. Executive Summary & Architecture

**`ha-audio-events`** is a Home Assistant (HA) add-on designed for real-time audio event detection using TensorFlow Lite (specifically the **Google YAMNet** model). It captures continuous audio streams (from stdin or audio file inputs), monitors activity levels to prevent redundant model calls, runs inference using `ai-edge-litert`, aggregates detection events across time windows, and notifies Home Assistant via HTTP REST APIs and/or MQTT binary sensors and event entities.

### Core Processing Pipeline Data Flow

```
[ Audio Source ] (stdin / file via stream.py)
       │
       ▼
[ Circular Audio Buffer ] (buffer.py)
       │
       ▼
[ Activity Detector ] (activity.py - RMS & Peak threshold check)
       │
       ├──── (Below threshold) ──► Skip frame
       │
       ▼ (Above threshold)
[ YAMNet Classifier ] (yamnet.py via LiteRT Interpreter)
       │
       ▼
[ Detection Filter ] (filter.py - confidence threshold, include/exclude rules)
       │
       ▼
[ Event Aggregator ] (aggregate.py - state transitions: START -> ONGOING -> ENDED)
       │
       ├──► [ Home Assistant REST API ] (client.py & entities.py)
       └──► [ Home Assistant MQTT / Discovery ] (mqtt.py & discovery.py)
```

---

## 2. Directory & File Map

```
ha-audio-events/
├── .agents/
│   └── AGENTS.md                  # (This file) AI context, architecture, & development guide
├── app/
│   └── versioning.py              # Symlink/entrypoint to package version manager script
├── ha-audio-events/               # HA Add-on root & Python package source
│   ├── app/                       # Core Python codebase
│   │   ├── __init__.py
│   │   ├── config.py              # Configuration dataclasses & YAML/JSON loaders
│   │   ├── demo.py                # CLI script for running inference on static audio files
│   │   ├── main.py                # Main async entry point (`main_sync` / `_run_pipeline`)
│   │   ├── versioning.py          # Script for updating project versions across files
│   │   ├── audio/                 # Audio stream ingest and pre-processing
│   │   │   ├── activity.py        # RMS & peak volume activity threshold detector
│   │   │   ├── buffer.py          # Circular floating-point audio buffer
│   │   │   ├── resample.py        # Sample rate conversion utilities
│   │   │   └── stream.py          # Async audio reader (stdin / subprocess / file)
│   │   ├── classifiers/           # ML Classifier implementations
│   │   │   ├── base.py            # Abstract BaseAudioClassifier & Detection dataclass
│   │   │   ├── registry.py        # Classifier factory (`build_classifier`)
│   │   │   └── yamnet.py          # YAMNet classifier using ai-edge-litert / TFLite
│   │   ├── detection/             # Event detection & temporal aggregation
│   │   │   ├── aggregate.py       # Aggregates single-frame detections into multi-second AudioEvents
│   │   │   ├── filter.py          # Confidence & class inclusion/exclusion filters
│   │   │   └── models.py          # AudioEvent dataclass (label, confidence, state, duration)
│   │   ├── homeassistant/         # HA integrations
│   │   │   ├── client.py          # Async REST client for HA event firing and state updates
│   │   │   ├── discovery.py       # MQTT Discovery payload generator
│   │   │   ├── entities.py        # Entity ID & attribute builders for HA binary sensors
│   │   │   └── mqtt.py            # MQTT client (paho-mqtt wrapper)
│   │   └── utils/
│   │       └── logging.py         # Logging configuration helper
│   ├── config.json                # Home Assistant add-on options & schema specification
│   ├── config.yaml                # Default options for container/local execution
│   ├── Dockerfile                 # Container image based on python:3.12-slim
│   ├── logo.png                   # HA Add-on icon
│   └── run.sh                     # Container start script executing `python3 -m app.main`
├── models/
│   ├── yamnet.tflite              # Pre-trained TFLite model (~4.1 MB)
│   └── yamnet_class_map.csv       # YAMNet 521 audio class label map
├── tests/                         # Pytest test suite & audio test fixtures
│   ├── fixtures/
│   │   └── audio/                 # Sample audio files (dog barking, train horn, etc.)
│   ├── test_audio_classifier_integration.py
│   ├── test_audio_fixtures.py
│   ├── test_detection.py
│   ├── test_homeassistant.py
│   ├── test_main.py
│   ├── test_versioning.py
│   └── test_yamnet_label_loading.py
├── config.yaml                    # Local testing config file
├── Makefile                       # Developer tasks (test, version bump, update model, etc.)
├── pyproject.toml                 # Packaging, dependencies, scripts (`ha-audio-events`)
├── README.md                      # General repository documentation
└── repository.json                # Home Assistant add-on repository manifest
```

---

## 3. Subsystem Breakdown

### 3.1 Ingestion & Audio Preprocessing (`app/audio/`)
- **`AudioStreamSource` (`stream.py`)**: Streams 16-bit PCM mono audio from `sys.stdin.buffer` or a specified file path. Supports reading via `ffmpeg` pipeline when needed.
- **`CircularAudioBuffer` (`buffer.py`)**: Stores raw audio samples in a fixed-size `numpy.ndarray` buffer representing a rolling window (default `buffer_seconds: 3.0`).
- **`ActivityDetector` (`activity.py`)**: Evaluates Root-Mean-Square (RMS) and peak signal amplitude. If signal level is below configured `rms_threshold` / `peak_threshold`, classifier inference is skipped, saving CPU resources.

### 3.2 Machine Learning Inference (`app/classifiers/`)
- **`YAMNetClassifier` (`yamnet.py`)**: Primary classifier using Google's YAMNet architecture. Uses `ai_edge_litert.interpreter.Interpreter` (with fallback to `tflite_runtime.interpreter.Interpreter`).
- Model input expectation: 15600 1D float32 samples (approx. 0.975 seconds at 16kHz).
- Model output: 521 class probabilities mapped to human-readable names via `yamnet_class_map.csv`.

### 3.3 Event Aggregation & Filtering (`app/detection/`)
- **`filter_detections()` (`filter.py`)**: Filters top K predictions against `threshold`, matching `include` whitelist (or all if empty) and removing `exclude` blacklist items (e.g. `music`, `silence`).
- **`EventAggregator` (`aggregate.py`)**: Solves single-frame noise by maintaining event state across frames:
  - **`started`**: Event confidence surpasses `start_confidence`.
  - **`ongoing`**: Event continues across consecutive classification frames.
  - **`ended`**: Event confidence drops or disappears for longer than `end_timeout` seconds.

### 3.4 Integration & Notification (`app/homeassistant/`)
- **REST Client (`client.py`)**: Connects to HA Supervisor API (`http://supervisor/homeassistant`) or standalone HA URL, sending `POST` requests to update entity states (`sensor.last_audio_event`, `binary_sensor.audio_active`, etc.) and fire `audio_event` events.
- **MQTT Integration (`mqtt.py` & `discovery.py`)**: Publishes discovery configs to HA topic (`homeassistant/binary_sensor/audio_*/config`) and broadcasts event payloads to `audio/events`.

---

## 4. Environment & Testing Procedures

### Python & Environment Setup
- Python Version: **>= 3.12**
- Environment Path: `.venv`

### Executing Tests
Run unit and integration tests using the virtual environment's pytest:

```bash
# Run full test suite
.venv/bin/pytest

# Run specific test file
.venv/bin/pytest tests/test_audio_classifier_integration.py

# Run tests with verbose output
.venv/bin/pytest -v
```

### Useful Makefile Commands
- **`make test-fixtures`**: Run pytest against fixture test files.
- **`make demo-file FILE=path/to/audio.wav`**: Test classifier pipeline on a single audio file.
- **`make test-container`**: Build Podman/Docker image and run container smoke test.
- **`make version VERSION=x.y.z`**: Bump version across `pyproject.toml` and `ha-audio-events/config.json`.
- **`make update-yamnet-model`**: Download latest YAMNet model assets from Kaggle.

---

## 5. Coding & Contribution Guidelines for AI Agents

1. **Virtualenv Usage**: Always invoke Python tools via `.venv/bin/python` or `.venv/bin/pytest`.
2. **Type Annotations & Modern Python**: Code uses Python 3.12+ features (`from __future__ import annotations`, type syntax `str | None`, `list[str]`).
3. **Async Architecture**: Core pipeline in `main.py` and HA HTTP calls are asynchronous (`asyncio`). CPU-heavy inference is offloaded via `asyncio.to_thread`.
4. **Configuration Consistency**: When modifying options or schemas, ensure both `app/config.py` dataclasses, `config.yaml`, and `ha-audio-events/config.json` schema definitions remain synchronized.
5. **Verification**: Always execute `.venv/bin/pytest` after making code modifications to ensure no regressions occur.
