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
       ├─── (Below threshold) ──► Skip frame
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
├── agents.md                       # (This file) AI context, architecture, & development guide
├── app/
│   └── versioning.py              # Version bumping utility (duplicate of ha-audio-events/app/versioning.py)
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
│   │       ├── manifest.json
│   │       ├── dog-barking/
│   │       └── train/
│   ├── test_audio_classifier_integration.py
│   ├── test_audio_fixtures.py
│   ├── test_detection.py
│   ├── test_homeassistant.py
│   ├── test_main.py
│   ├── test_mqtt_discovery.py
│   ├── test_stream.py
│   ├── test_versioning.py
│   └── test_yamnet_label_loading.py
├── config.yaml                    # Local testing config file
├── Makefile                       # Developer tasks (test, version bump, update model, etc.)
├── pyproject.toml                 # Packaging, dependencies, scripts (`ha-audio-events`)
├── README.md                      # General repository documentation
└── repository.json                # Home Assistant add-on repository manifest
```

### Key Layout Note

The application code lives in `ha-audio-events/app/`, **not** the root `app/`.
The root `app/` directory only contains `versioning.py` (a duplicate of
`ha-audio-events/app/versioning.py`).

The `pyproject.toml` configures pytest with `pythonpath = ["ha-audio-events"]`,
so all imports use `from app.xxx import ...` and resolve to
`ha-audio-events/app/`.

---

## 3. Subsystem Breakdown

### 3.1 Ingestion & Audio Preprocessing (`app/audio/`)
- **`AudioStreamSource` (`stream.py`)**: Streams 16-bit PCM mono audio from `sys.stdin.buffer` or a specified file path. Supports reading via `ffmpeg` pipeline when needed. Also supports Home Assistant camera entity IDs (resolved via HA API to an M3U8/RTSP stream URL).
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

### Installing Dependencies

**Do NOT use `pip install -e ".[dev]"`** — setuptools auto-discovery will fail
because it finds multiple top-level packages (`app` at root and `models`),
causing a "Multiple top-level packages discovered in a flat-layout" error.
The project is designed to run with `PYTHONPATH=ha-audio-events` instead.

```bash
# Activate the virtual environment
source .venv/bin/activate

# Install runtime + dev dependencies directly
pip install aiohttp numpy PyYAML "paho-mqtt>=2.1,<3.0" "ai-edge-litert>=2.1.0,<3.0.0" \
    pytest pytest-asyncio ruff black mypy
```

### Executing Tests

Run unit and integration tests using the virtual environment's pytest:

```bash
# Run full test suite (pythonpath is configured in pyproject.toml)
.venv/bin/pytest -v

# Run specific test file
.venv/bin/pytest tests/test_audio_classifier_integration.py

# Run tests with verbose output
.venv/bin/pytest -v
```

### Complete Test Workflow (Use Before Pushing)

The recommended way to run all checks locally is via the Makefile, which mirrors the CI pipeline:

```bash
# Run ALL checks: unit tests + linting (ruff) + formatting (black) + coverage
make test
```

This runs three sub-targets:
- **`make test-lint`** - Runs ruff check on source and tests
- **`make test-format`** - Runs black format check with `--target-version py312`
- **`make test-with-coverage`** - Runs pytest with coverage (60% threshold)

**All three must pass (exit code 0) before pushing to GitHub.**

You can also run them individually:
```bash
make test-lint          # Just linting
make test-format        # Just format check
make test-with-coverage # Just coverage check (includes test execution)
make test-unit          # Just unit tests (no coverage)
```

### Test Results (as of last run)
- **44 tests, all passing** in ~4 seconds
- Coverage: **64%** (threshold: 60%)
- Integration tests require `models/yamnet.tflite` and `models/yamnet_class_map.csv`
  (present in the repo). If missing, those tests are skipped.
- `test_stream.py::test_stream_source_wav_file` requires
  `tests/fixtures/audio/train/freight_train_01.wav` (present).

### CI Pipeline Alignment

The GitHub Actions workflow (`.github/workflows/ci.yml`) runs the exact same commands in a single job:
1. Install dependencies (no editable install, uses `PYTHONPATH=ha-audio-events`, installs `pytest-cov`)
2. Install `ffmpeg` system package (required for MP3 fixture conversion)
3. Run `pytest --cov=ha-audio-events/app --cov-fail-under=60 --cov-report=term-missing -v`
4. Run `ruff check ha-audio-events/app/ tests/`
5. Run `black --check ha-audio-events/app/ tests/`
6. Upload coverage report as artifact

**If `make test` passes locally, CI will pass.**

The old CI had separate `test` and `coverage-check` jobs that ran tests twice. Now both CI and local run tests once with coverage.

### Running the Demo

The demo classifies an audio file and prints detected events. Requires
`PYTHONPATH=ha-audio-events` since the `app` package is in `ha-audio-events/app/`:

```bash
# WAV files don't need conversion
PYTHONPATH=ha-audio-events .venv/bin/python -m app.demo tests/fixtures/audio/train/freight_train_01.wav

# MP3 files are auto-converted via ffmpeg
PYTHONPATH=ha-audio-events .venv/bin/python -m app.demo tests/fixtures/audio/train/freesound_community-8-freight-train_126s.mp3
```

> **Note**: The demo loads `config.yaml` from the project root. The current
> `config.yaml` has `source_path: /tmp/fixture.wav` but the demo overrides this
> with the provided file path.

### Useful Makefile Commands
- **`make test`**: Run ALL checks (linting + formatting + coverage with tests)
- **`make test-unit`**: Run unit tests only (no coverage)
- **`make test-lint`**: Run ruff linting
- **`make test-format`**: Run black format check
- **`make test-with-coverage`**: Run tests with coverage (60% threshold)
- **`make test-fixtures`**: Run pytest against fixture test files.
- **`make demo-file FILE=path/to/audio.wav`**: Test classifier pipeline on a single audio file.
- **`make test-container`**: Build Podman/Docker image and run container smoke test.
- **`make version VERSION=x.y.z`**: Bump version across `pyproject.toml` and `ha-audio-events/config.json`.
- **`make update-yamnet-model`**: Download latest YAMNet model assets from Kaggle.

### Linting

```bash
# Check for issues
PYTHONPATH=ha-audio-events .venv/bin/ruff check ha-audio-events/app/ tests/

# Auto-fix what's possible
PYTHONPATH=ha-audio-events .venv/bin/ruff check --fix ha-audio-events/app/ tests/

# Check formatting
PYTHONPATH=ha-audio-events .venv/bin/black --check --target-version py312 ha-audio-events/app/ tests/

# Check coverage
PYTHONPATH=ha-audio-events .venv/bin/pytest --cov=ha-audio-events/app --cov-fail-under=60 --cov-report=term-missing
```

> **Note**: There are pre-existing linting issues (import sorting, unused imports,
> modernization suggestions). These don't affect test functionality.

---

## 5. Coding & Contribution Guidelines for AI Agents

1. **Virtualenv Usage**: Always invoke Python tools via `.venv/bin/python` or `.venv/bin/pytest`.
2. **Type Annotations & Modern Python**: Code uses Python 3.12+ features (`from __future__ import annotations`, type syntax `str | None`, `list[str]`).
3. **Async Architecture**: Core pipeline in `main.py` and HA HTTP calls are asynchronous (`asyncio`). CPU-heavy inference is offloaded via `asyncio.to_thread`.
4. **Configuration Consistency**: When modifying options or schemas, ensure both `app/config.py` dataclasses, `config.yaml`, and `ha-audio-events/config.json` schema definitions remain synchronized.
5. **Verification**: Always execute `.venv/bin/pytest` after making code modifications to ensure no regressions occur.
6. **Package Layout**: The `app` package is in `ha-audio-events/app/`. Use `PYTHONPATH=ha-audio-events` when running Python directly (not via pytest). Do not attempt `pip install -e` due to setuptools auto-discovery conflicts with root-level `app/` and `models/` directories.

# Solution on resolving common API response errors:

When fixing add-on option update failures:
1. Modify the `set_option` method in `addon_mgr.py` to:
   - Validate API responses for proper "result": "ok" structure
   - Add comprehensive logging for debug visibility
   - Handle empty responses gracefully
2. Commit changes to `fix/addon-manager-option-error` branch
3. Push to remote and create PR with issue description and context
4. Reference this branch when applying similar fixes

This ensures proper API response handling for the "Failed to set source in add-on options" error.
