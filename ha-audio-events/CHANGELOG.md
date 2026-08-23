# Changelog

All notable changes to this add-on will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.4.5] - 2026-08-23
### Fixed
- **Sources with no audio track no longer hang silently** (confirmed live on HA camera MJPEG proxies): if ffmpeg produces no audio bytes within 20s of connecting, the add-on now raises a clear `no audio received -- stream is likely video-only` condition, logs it loudly, surfaces it in the panel's Recent Detections as `no-audio-source`, and keeps the Web UI available so the source can be changed. Previously the pipeline blocked forever on the first read and the install just looked "quiet".

## [0.4.4] - 2026-08-23
### Changed
- Quiet logs: per-request access lines for the panel's 3-second `/api/detections` polling are filtered out instead of flooding the add-on log
- The "bound without an auth token" warning now fires only for standalone deployments -- behind Home Assistant ingress it was noise on every start
- Add-on manifest enables `watchdog: true` by default so a crashed container auto-restarts instead of sitting down silently
- README troubleshooting gains an entry for the panel's "app seems not ready" retry dialog

## [0.4.3] - 2026-08-23
### Fixed
- **Web UI never came up while a stream was running** (regression since 0.3.0): `webui.start()` was awaited only *after* the detection task finished, but a healthy live stream never finishes -- so the ingress panel showed "app not ready" forever while detection quietly worked. The server now binds immediately and detection runs concurrently; a pipeline failure still leaves the panel up, and bind failures fail loudly within 10s.

## [0.4.2] - 2026-08-22
### Fixed
- Web UI panel no longer breaks with cryptic JSON errors ("Unexpected non-whitespace character after JSON") when the add-on is stopped or restarting: responses are now parsed defensively and the panel explains what actually happened (add-on unreachable vs connection lost during restart)
- Applying a source no longer kills its own HTTP response: the add-on restart is scheduled ~1s after the confirmation reply is delivered, instead of destroying the container mid-request

## [0.4.1] - 2026-08-22
### Fixed
- Add-on option defaults no longer use `null` for optional string fields (`mqtt.username`/`password`, `webui.auth_token`, `audio.source_path`). The Supervisor's validator rejects null for nullable schema fields with "Missing required option", which could block add-on start/update on real installs (observed live). Blank strings are now the defaults, and `load_config` coerces blanks back to proper `None` values so app behaviour is unchanged.

## [0.4.0] - 2026-08-22
### Fixed
- Self-healing for legacy saved options: `homeassistant.url` values like `http://supervisor/homeassistant` (the broken pre-0.1.11 default) are normalised to `http://supervisor/core` at startup — camera streaming and entity updates work again without manually editing options
- Dead audio sources no longer fail silently: when ffmpeg exits non-zero (unreachable RTSP camera, stream with no audio track), the add-on now logs a loud error naming the exit code plus recent ffmpeg output

### Added
- Inline documentation for every add-on option via `translations/en.yaml` — names and descriptions now render directly in the Home Assistant configuration panel, with links to full docs
- Dropdown selection for options fixed by the pipeline (`model`, `sample_rate`, `channels`, `format`) so invalid values can't be entered, plus a new `log_level` dropdown
- Removed `homeassistant.url`/`token` from fresh-install defaults: inside the add-on these are provided by the Supervisor automatically; existing saved values stay valid and legacy URLs self-heal (see above)
- Per-option reference table added to the README

### Changed
- Version bump to 0.4.0

## [0.3.0] - 2026-08-22
### Fixed
- **Security**: GitHub Actions PR-title validation interpolated the attacker-controlled PR title directly into a shell script (script injection). It now goes through an env var; the version-bump workflow's inputs are likewise isolated
- **CI**: version-bump workflow staged a non-existent `ha-audio-events/config.json`, so every bump run failed before committing. It now stages `config.yaml` and no longer relies on a fragile editable install
- **Deadlock**: ffmpeg was spawned with `stderr=PIPE` that nobody drained -- long-running RTSP/Pulse streams could block forever once the pipe buffer filled. stderr is now drained concurrently and logged
- **Latency**: only the first 0.975 s of each 3 s buffer was ever classified (YAMNet frame truncation). The buffer is now tiled into consecutive model frames reduced by element-wise max (peak confidence preserved), capped at 10 frames
- Sensors stuck "on": active detections are now flushed as `ended` when the stream stops or fails, so Home Assistant binary sensors never hang in the on state
- Web UI now genuinely survives audio-pipeline failures so a bad source can be fixed from the ingress panel (previously the process exited despite comments claiming otherwise)
- MQTT: blocking `connect()` crashed the add-on at startup whenever the broker wasn't up yet (boot-order race); it now connects asynchronously with automatic retry/backoff
- Invalid Home Assistant entity IDs / MQTT topics for YAMNet labels containing commas or other punctuation ("Child speech, kid speaking") -- labels are properly slugified now
- Supervisor API responses with chunked encoding (`content_length: None`) were silently discarded as empty; bodies are read before parsing
- `load_config()` silently fell back to defaults when an explicitly passed path didn't exist; it now raises `FileNotFoundError`
- WAV files were fully loaded into memory before streaming; reads are now incremental
- README documented the wrong default HA URL (`http://supervisor/homeassistant` vs actual `http://supervisor/core`) and had duplicate section numbering

### Security
- Web UI: optional shared auth token (`webui.auth_token`) gates all `/api` endpoints for standalone deployments outside HA ingress, with constant-time comparison; the panel prompts for it automatically. A loud warning is logged when binding to a non-loopback host without one
- XSS: the Recent Detections panel interpolated detection label/state straight into `innerHTML`; rows are now built via `textContent`

### Added
- MQTT broker credentials (`username`/`password`) and TLS support in options + schema
- `webui` section exposed in the add-on manifest schema (enabled/host/port/auth_token) -- previously configurable in code only
- mypy type checking wired into `make test` and CI (now clean: 30 source files)
- `black`/`pytest-cov` added to dev dependencies they were silently missing from
- Container smoke tests unchanged; unit suite grew from 126 to 158 tests covering all of the above

### Removed
- Stale diverged root-level `app/versioning.py` duplicate (the packaged copy under `ha-audio-events/app/` remains canonical)
- Broken zero-byte `logo.png`

## [0.1.13] - 2026-08-16
### Fixed
- Add `get_option()` method to AddonManager to retrieve add-on options via `/addons/self/info` endpoint (fixes `AttributeError: 'AddonManager' object has no attribute 'get_option'` in server.py:518)
- Modified `set_option()` to use `get_addon_info()` (GET `/addons/self/info`) instead of direct GET `/addons/self/options` which returns 405 Method Not Allowed from Supervisor API
- Removed premature `ha_client.close()` and `mqtt_client.stop()` from `_detect()` function in main.py — moved cleanup to appropriate `finally` block and non-webui path to prevent `RuntimeError: Session is closed` when webui tries to use HA client after pipeline closes it

### Changed
- Updated CI/CD pipeline test coverage threshold from 60% to 80% in `.github/workflows/ci.yml:68`
- Added comprehensive test coverage: 25 tests for addon manager (`test_addon_mgr.py`) and 7 regression tests for main pipeline wiring (`test_main.py`)

## [0.1.11] - 2026-08-15
### Fixed
- Fix Home Assistant Supervisor proxy URL: default was `http://supervisor/homeassistant`, which is not a valid Supervisor proxy path. The correct path is `http://supervisor/core/api`. This was silently breaking every call to Home Assistant — `fire_event`, `update_state`, and the web UI's camera/microphone lookups — since the failures were only logged as warnings
- Fix "Failed to load cameras" in the web UI, caused by the URL issue above
- Fix camera/microphone friendly names always falling back to the entity ID — `friendly_name` is nested under `attributes` in Home Assistant's API response, not top-level
- Fix mangled emoji bytes in the web UI panel title

### Added
- "Recent Detections" panel in the web UI ingress page, polling every 3s, so detected events are visible directly in the add-on regardless of whether Home Assistant/MQTT publishing is working
- `GET /api/detections` endpoint backed by a new in-memory event history buffer
- `GET /api/microphones` endpoint listing `assist_satellite` (voice satellite) entities in the source picker for visibility

### Known limitations
- Voice satellite (`assist_satellite`) entities are shown in the source picker but disabled — Home Assistant doesn't expose a pull-able audio stream URL for them the way it does for cameras, so they can't be used as a capture source yet. Selecting one via the API is explicitly rejected with an explanation rather than silently accepted

## [0.1.10] - 2026-08-12
### Fixed
- Fix API response validation in addon manager to properly check for `"result": "ok"`
- Resolve "Failed to set source in add-on options" error in web UI
- Fix version bump script path resolution (was looking in wrong directory)
- Remove unused `Path` import from main.py

### Changed
- Update addon manager to validate Supervisor API response structure
- Improve error logging for add-on option updates
- Update test mocks to match actual Supervisor API response format

## [0.1.9] - 2026-08-XX
### Added
- Initial release with YAMNet audio event detection using TensorFlow Lite
- Web UI ingress panel for audio source selection from Home Assistant cameras
- MQTT discovery and Home Assistant binary sensor integration
- Real-time audio stream processing with activity detection
- Event aggregation across time windows (started/ongoing/ended states)
- REST API and MQTT notifications for detected audio events
- Support for RTSP/IP camera audio streams via ffmpeg

### Technical Details
- Uses Google YAMNet model (521 audio classes) via ai-edge-litert
- Circular audio buffer with configurable window size
- RMS/peak activity threshold detection to skip silent frames
- Configurable include/exclude filters for audio event classes
- Home Assistant Supervisor API integration for add-on management

## [0.1.8] - 2026-08-XX
### Added
- Add-on manifest validation in CI
- Docker build fixes for model files
- CI pipeline with linting, formatting, and coverage checks

## [0.1.7] - 2026-08-XX
### Added
- Initial project structure and configuration
- Version bumping utility
- Basic test infrastructure
