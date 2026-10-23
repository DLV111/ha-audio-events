# Graph Report - ha-audio-events  (2026-09-27)

## Corpus Check
- 64 files · ~33,051 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 10 file(s) not represented in the graph (top: (none) 6, .tflite 2, .csv 2)

## Summary
- 899 nodes · 1758 edges · 71 communities (35 shown, 36 thin omitted)
- Extraction: 87% EXTRACTED · 13% INFERRED · 0% AMBIGUOUS · INFERRED: 233 edges (avg confidence: 0.94)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `92a22e29`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- HomeAssistantConfig
- MQTTConfig
- AudioStreamSource
- driver.py
- Changelog
- manifest.json
- test_addon_mgr.py
- YAMNetClassifier
- test_addon_options.py
- test_main.py
- test_manifest.py
- test_hardening.py
- WebUI
- test_no_audio_detection.py
- Backlog & Known Issues
- main.py
- demo.py
- test_webui.py
- AddonManager
- HA Audio Events (Home Assistant Add-on)
- EventHistory
- ActivityConfig
- TestWebUI
- TestWebUIClassifierFilters
- config.py
- pathlib
- server.py
- Option 1 (recommended): dedicated ESP32 running streamer firmware
- logging.py
- TestWebUIAuth
- CircularAudioBuffer
- addon_manager
- TestWebUIBindNotices
- .start
- test_webui_starts_while_stream_is_still_live
- Autonomous Development Skill for ha-audio-events
- test_run_pipeline_with_audio_chunks
- test_config_defaults.py
- audio/__init__.py
- classifiers/__init__.py
- detection/__init__.py
- homeassistant/__init__.py
- app/__init__.py
- utils/__init__.py
- run.sh
- train/README.md
- test_make_request_empty_response
- test_get_option_success
- test_get_option_category_exists_key_missing
- test_get_option_none_result
- test_set_option_info_fails
- test_set_option_creates_new_category
- test_get_addon_info_success
- test_get_session_creates_new
- test_get_session_reuses_existing
- test_get_session_recreates_closed
- .test_set_source_success
- .test_set_source_restarts_only_after_response_is_delivered
- .test_set_source_failure_never_restarts
- .test_set_source_missing_parameter
- .test_set_source_failure
- .test_set_source_restart_failure
- .test_get_microphones_success
- .test_get_microphones_failure
- .test_get_detections_empty_without_history
- .test_get_cameras_success
- .test_get_cameras_no_cameras
- .test_get_source_success
- .test_get_source_not_set
- ha-audio-events

## God Nodes (most connected - your core abstractions)
1. `HomeAssistantConfig` - 44 edges
2. `HomeAssistantClient` - 41 edges
3. `WebUI` - 35 edges
4. `EventMessage` - 32 edges
5. `_run_pipeline()` - 32 edges
6. `AudioStreamSource` - 31 edges
7. `AddonManager` - 28 edges
8. `TestWebUI` - 27 edges
9. `AudioSourceConfig` - 25 edges
10. `load_config()` - 25 edges

## Surprising Connections (you probably didn't know these)
- `Key Layout Note` --references--> `build_classifier()`  [INFERRED]
  agents.md → ha-audio-events/app/classifiers/registry.py
- `3.1 Ingestion & Audio Preprocessing (`app/audio/`)` --references--> `ActivityDetector`  [INFERRED]
  agents.md → ha-audio-events/app/audio/activity.py
- `3.1 Ingestion & Audio Preprocessing (`app/audio/`)` --references--> `AudioStreamSource`  [INFERRED]
  agents.md → ha-audio-events/app/audio/stream.py
- `3.2 Machine Learning Inference (`app/classifiers/`)` --references--> `YAMNetClassifier`  [INFERRED]
  agents.md → ha-audio-events/app/classifiers/yamnet.py
- `15. Scale from one pipeline to N sources and fan-out consumers` --references--> `_run_pipeline()`  [INFERRED]
  TODO.md → ha-audio-events/app/main.py

## Import Cycles
- None detected.

## Communities (71 total, 36 thin omitted)

### Community 0 - "HomeAssistantConfig"
Cohesion: 0.05
Nodes (56): ClientTimeout, HomeAssistantConfig, End every active event immediately. Called on pipeline shutdown so Home…, EventMessage, HomeAssistantClient, Any, Initialize required HA entities if they don't exist yet., Fetch entity states from Home Assistant, optionally filtered to a domain.… (+48 more)

### Community 1 - "MQTTConfig"
Cohesion: 0.07
Nodes (42): MQTTConfig, build_entity_ids_for_labels(), build_label_state_topic(), build_mqtt_discovery_payload(), Per-label state topic, so each discovered sensor only reacts to its own label., Convert an audio label into a valid Home Assistant object_id slug. YAMNet…, slugify_label(), MQTTClient (+34 more)

### Community 2 - "AudioStreamSource"
Cohesion: 0.09
Nodes (32): deque, ensure_mono(), pcm_s16le_to_float32(), ndarray, AudioStreamSource, ndarray, Path, Consume ffmpeg stderr, logging each line, until EOF. (+24 more)

### Community 3 - "driver.py"
Cohesion: 0.10
Nodes (36): argparse, _branch_name(), _bump_version(), cmd_apply(), cmd_clean(), cmd_fix(), cmd_monitor(), cmd_pr_create() (+28 more)

### Community 4 - "Changelog"
Cohesion: 0.05
Nodes (36): [0.1.10] - 2026-08-12, [0.1.11] - 2026-08-15, [0.1.13] - 2026-08-16, [0.1.7] - 2026-08-XX, [0.1.8] - 2026-08-XX, [0.1.9] - 2026-08-XX, [0.3.0] - 2026-08-22, [0.4.0] - 2026-08-22 (+28 more)

### Community 5 - "manifest.json"
Cohesion: 0.05
Nodes (36): audiopapkin-barking-large-and-small-dog-290711.mp3, category, duration_seconds, expected_label, notes, path, dragon-studio-dog-barking-406629.mp3, category (+28 more)

### Community 6 - "test_addon_mgr.py"
Cohesion: 0.08
Nodes (36): asyncio, Tests for addon manager., Test close when no session exists., Test successful API request., Test API request with error status., A non-JSON body is surfaced as None instead of raising., Chunked responses (content_length None) must still be parsed as JSON.…, Test API request cancellation. (+28 more)

### Community 7 - "YAMNetClassifier"
Cohesion: 0.07
Nodes (27): 1. Executive Summary & Architecture, 2. Directory & File Map, 3.2 Machine Learning Inference (`app/classifiers/`), 3.4 Integration & Notification (`app/homeassistant/`), 3. Subsystem Breakdown, 4. Environment & Testing Procedures, 5. Coding & Contribution Guidelines for AI Agents, AI Assistant Guide & Repository Overview: `ha-audio-events` (+19 more)

### Community 8 - "test_addon_options.py"
Cohesion: 0.08
Nodes (28): _iter_option_values(), _iter_schema_leaves(), _load_manifest(), _load_translations(), asyncio, parametrize, Path, Tests for add-on option usability work: - homeassistant.url normalization… (+20 more)

### Community 9 - "test_main.py"
Cohesion: 0.07
Nodes (23): patch, asyncio, Regression test for a real bug: AddonManager() was previously called with no…, Regression: when the audio stream ends, still-active aggregated events must be…, Test format_event_summary with missing attributes., Regression: a failing audio pipeline (e.g. bad source_path) used to tear down…, Regression test: with only 1 decimal place, distinct started/active events with…, Test main_sync runs successfully. (+15 more)

### Community 10 - "test_manifest.py"
Cohesion: 0.11
Nodes (26): _invalid_map_entry(), load_manifest(), ManifestValidationError, Any, Path, Validation helpers for the Home Assistant add-on manifest (config.yaml). These…, Validate the ``map`` section of a manifest. Returns a list of error messages…, Validate an add-on manifest file, returning a list of error messages. (+18 more)

### Community 11 - "test_hardening.py"
Cohesion: 0.10
Nodes (24): _classifier_with_frame_len(), _detection(), asyncio, Path, Regression tests for the codebase-hardening pass. Covers: YAMNet full-buffer…, Every HA request must be bounded: aiohttp's default is 5 minutes, which stalls…, _stream_wav yields chunks as it reads instead of materialising the entire file…, A 3s buffer must be classified as 3+ frames, not truncated to 0.975s. (+16 more)

### Community 12 - "WebUI"
Cohesion: 0.14
Nodes (14): Serve the main HTML page for the Web UI., Fetch available camera entities from Home Assistant., Fetch assist_satellite (voice-satellite / built-in microphone) entities from…, Return the most recent detection events, most recent first., Get the currently configured source path., Set the audio source path and restart the add-on. The HTTP response is sent…, Restart the add-on after the current response has been delivered., Load YAMNet class names from the class map CSV. Same lookup convention as… (+6 more)

### Community 13 - "test_no_audio_detection.py"
Cohesion: 0.13
Nodes (14): _FakeProc, _HangingStdout, asyncio, Tests for the no-audio-stream guard. Regression for a live incident: HA camera…, Simulates ffmpeg connected to a video-only proxy: never outputs., A source that never delivers audio bytes must fail fast and loudly., A normal stream (bytes arrive immediately) must flow untouched., Slow sources are tolerated: audio arriving just inside the window must not be… (+6 more)

### Community 14 - "Backlog & Known Issues"
Cohesion: 0.09
Nodes (21): 10. ✅ FIXED (PR #20) — Log noise from panel polling, 11. ⚠️ BLOCKED ON SOURCE — End-to-end detection never confirmed on live install, 12. MQTT integration never tested against a broker, 13. CI gap: no container test for the camera-entity path, 14. Support custom ESP32 hardware as a detection source, 1. Restore production options (left in test state), 3. ✅ VERIFIED NON-ISSUE — Bare ffmpeg stderr bypassed the stderr drain, 4. 🟡 FIX SHIPPED v0.4.5 (PR pending merge) — Camera proxy stream reliability / missing audio track (+13 more)

### Community 15 - "main.py"
Cohesion: 0.17
Nodes (19): asyncio, collections_abc, NoAudioStreamError, Raised when a source delivers no audio bytes at all. Typical cause: an HA…, build_classifier(), AppConfig, build_attributes(), format_event_summary() (+11 more)

### Community 16 - "demo.py"
Cohesion: 0.25
Nodes (14): 3.3 Event Aggregation & Filtering (`app/detection/`), Detection, AggregationConfig, ClassifierConfig, format_file_result(), main(), _prepare_audio_for_demo(), run_demo() (+6 more)

### Community 17 - "test_webui.py"
Cohesion: 0.12
Nodes (10): aiohttp_test_utils, AioHTTPTestCase, Tests for the Web UI server implementation in HA Audio Events add-on. Tests the…, Without an auth token configured (the HA-ingress default), API access stays…, Regression guards for the XSS fix in the detections panel., Regression: the panel used to call .json() directly on every response; when the…, The index page must contain the filter controls wired up by JS., TestWebUIFilterMarkup (+2 more)

### Community 18 - "AddonManager"
Cohesion: 0.18
Nodes (10): ClientSession, AddonManager, Any, Get an option value from add-on configuration. Uses the /addons/self/info…, Get information about the current add-on., Get or create aiohttp session., Close the aiohttp session., Make a request to Supervisor API. (+2 more)

### Community 19 - "HA Audio Events (Home Assistant Add-on)"
Cohesion: 0.11
Nodes (17): Audio Source Configuration, Full Configuration Reference, HA Audio Events (Home Assistant Add-on), Home Assistant Entities & Events, Home Assistant Event Automation Example, Ingress Web UI Source Picker, Installation in Home Assistant, Key Features (+9 more)

### Community 20 - "EventHistory"
Cohesion: 0.17
Nodes (10): collections, DetectionRecord, EventHistory, In-memory recent-detections buffer shared between the detection loop and the…, Ring buffer of the most recent detection events., test_empty_history_returns_empty_list(), test_recent_includes_expected_fields(), test_recent_returns_most_recent_first() (+2 more)

### Community 21 - "ActivityConfig"
Cohesion: 0.26
Nodes (8): dataclasses, ActivityDetector, datetime, ndarray, ActivityConfig, numpy, test_activity_detector_thresholds(), test_circular_buffer_append_and_window()

### Community 22 - "TestWebUI"
Cohesion: 0.14
Nodes (8): Test suite for WebUI server endpoints., Test that Web UI is accessible., Test cameras endpoint works correctly., Create the aiohttp application for testing., assist_satellite entities aren't a supported capture source yet -- set_source…, Test that the index page is served correctly., Test camera discovery when HA API returns an error., TestWebUI

### Community 23 - "TestWebUIClassifierFilters"
Cohesion: 0.14
Nodes (7): Tests for the classification filter endpoints (/api/class-map, GET/POST…, The class map endpoint serves the names loaded from yamnet_class_map.csv at…, Stored options are normalised to lowercase, matching how the pipeline compares…, Both option writes happen and a delayed restart follows., A malformed payload gets an explicit 400 and never touches the Supervisor…, If the second option write fails, no restart is scheduled., TestWebUIClassifierFilters

### Community 24 - "config.py"
Cohesion: 0.32
Nodes (12): _clean_str(), load_config(), _load_config(), _load_json(), _load_yaml(), normalize_ha_url(), Any, Path (+4 more)

### Community 25 - "pathlib"
Cohesion: 0.27
Nodes (7): ABC, ai_edge_litert_interpreter, datetime, AudioClassifier, ndarray, pathlib, tflite_runtime_interpreter

### Community 26 - "server.py"
Cohesion: 0.18
Nodes (9): aiohttp, csv, Addon Manager for HA Audio Events add-on. Handles communication with Supervisor…, auth_middleware(), Web UI server for HA Audio Events add-on. Provides ingress panel for selecting…, Require a shared token on /api routes when one is configured. Behind Home…, hmac, middleware (+1 more)

### Community 27 - "Option 1 (recommended): dedicated ESP32 running streamer firmware"
Cohesion: 0.18
Nodes (10): Flash & find the streams, Hardware, Option 1 (recommended): dedicated ESP32 running streamer firmware, Option 1 vs Option 2 — remaining trade-offs, Option 2: stream from an existing ESPHome device, Point the add-on at it, Sharing the mic with Assist (supported), Troubleshooting (+2 more)

### Community 28 - "logging.py"
Cohesion: 0.27
Nodes (7): configure_logging(), _QuietPollAccessFilter, Silence per-request access lines for high-frequency panel polling. The ingress…, LogRecord, Tests for logging behaviour: quiet panel-polling access logs and the…, test_configure_logging_installs_poll_filter(), test_detections_polling_access_lines_are_filtered()

### Community 29 - "TestWebUIAuth"
Cohesion: 0.20
Nodes (3): The optional shared token must lock every /api endpoint while keeping the index…, The page itself must load so the user can be prompted for the token; only /api…, TestWebUIAuth

### Community 30 - "CircularAudioBuffer"
Cohesion: 0.32
Nodes (3): 3.1 Ingestion & Audio Preprocessing (`app/audio/`), CircularAudioBuffer, ndarray

### Community 31 - "addon_manager"
Cohesion: 0.29
Nodes (7): addon_manager(), mock_response(), mock_session(), fixture, Create a mock aiohttp response., Create a mock aiohttp session., Create an AddonManager with mocked session.

### Community 33 - ".start"
Cohesion: 0.33
Nodes (4): Start the aiohttp web server and run until cancelled., Warn appropriately about an unauthenticated non-loopback bind., [0.4.3] - 2026-08-23, Fixed

### Community 35 - "Autonomous Development Skill for ha-audio-events"
Cohesion: 0.40
Nodes (4): Autonomous Development Skill for ha-audio-events, Driver, How to Invoke, Prerequisites

### Community 37 - "test_config_defaults.py"
Cohesion: 0.50
Nodes (3): Regression tests for default config values that matter for correctness, not…, The Supervisor's internal proxy to Home Assistant Core's REST API is reachable…, test_homeassistant_default_url_uses_correct_supervisor_proxy_path()

## Knowledge Gaps
- **99 isolated node(s):** `run.sh script`, `ha-audio-events`, `category`, `expected_label`, `duration_seconds` (+94 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 397 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **36 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `AddonManager` connect `AddonManager` to `TestWebUIBindNotices`, `test_addon_mgr.py`, `WebUI`, `main.py`, `test_webui.py`, `TestWebUIClassifierFilters`, `test_get_session_creates_new`, `test_get_session_reuses_existing`, `test_get_session_recreates_closed`, `TestWebUI`, `server.py`, `TestWebUIAuth`, `addon_manager`?**
  _High betweenness centrality (0.097) - this node is a cross-community bridge._
- **Why does `HomeAssistantClient` connect `HomeAssistantConfig` to `TestWebUIBindNotices`, `test_hardening.py`, `WebUI`, `main.py`, `test_webui.py`, `TestWebUI`, `TestWebUIClassifierFilters`, `server.py`, `TestWebUIAuth`?**
  _High betweenness centrality (0.095) - this node is a cross-community bridge._
- **Why does `WebUI` connect `WebUI` to `HomeAssistantConfig`, `.start`, `TestWebUIBindNotices`, `main.py`, `test_webui.py`, `AddonManager`, `EventHistory`, `TestWebUI`, `TestWebUIClassifierFilters`, `server.py`, `TestWebUIAuth`?**
  _High betweenness centrality (0.093) - this node is a cross-community bridge._
- **Are the 20 inferred relationships involving `HomeAssistantConfig` (e.g. with `AudioStreamSource` and `HomeAssistantClient`) actually correct?**
  _`HomeAssistantConfig` has 20 INFERRED edges - model-reasoned connections that need verification._
- **Are the 12 inferred relationships involving `HomeAssistantClient` (e.g. with `HomeAssistantConfig` and `EventMessage`) actually correct?**
  _`HomeAssistantClient` has 12 INFERRED edges - model-reasoned connections that need verification._
- **Are the 10 inferred relationships involving `WebUI` (e.g. with `AddonManager` and `EventHistory`) actually correct?**
  _`WebUI` has 10 INFERRED edges - model-reasoned connections that need verification._
- **Are the 15 inferred relationships involving `EventMessage` (e.g. with `run_demo()` and `EventAggregator`) actually correct?**
  _`EventMessage` has 15 INFERRED edges - model-reasoned connections that need verification._