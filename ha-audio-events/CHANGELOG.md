# Changelog

All notable changes to this add-on will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
