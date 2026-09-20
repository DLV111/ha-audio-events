# Graph Report - t_82250682  (2026-09-20)

## Corpus Check
- 62 files · ~31,788 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 11 file(s) not represented in the graph (top: (none) 7, .tflite 2, .csv 2)

## Summary
- 866 nodes · 1683 edges · 71 communities (37 shown, 34 thin omitted)
- Extraction: 87% EXTRACTED · 13% INFERRED · 0% AMBIGUOUS · INFERRED: 225 edges (avg confidence: 0.94)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `b776ddf4`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- HomeAssistantConfig
- AudioStreamSource
- test_addon_options.py
- EventMessage
- Changelog
- manifest.json
- test_addon_mgr.py
- test_main.py
- CircularAudioBuffer
- test_manifest.py
- config.py
- WebUI
- test_hardening.py
- Backlog & Known Issues
- AddonManager
- HA Audio Events (Home Assistant Add-on)
- EventHistory
- _run_pipeline
- YAMNetClassifier
- TestWebUI
- TestWebUIClassifierFilters
- yamnet.py
- AggregationConfig
- server.py
- Option 1 (recommended): dedicated ESP32 running streamer firmware
- TestWebUIFilterMarkup
- HomeAssistantClient
- logging.py
- TestWebUIAuth
- main_sync
- addon_manager
- TestWebUIBindNotices
- ActivityDetector
- TestWebUIHtmlSafety
- ClassifierConfig
- _load_config
- test_audio_fixtures.py
- auth_middleware
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
- `3.2 Machine Learning Inference (`app/classifiers/`)` --references--> `YAMNetClassifier`  [INFERRED]
  agents.md → ha-audio-events/app/classifiers/yamnet.py
- `3.1 Ingestion & Audio Preprocessing (`app/audio/`)` --references--> `ActivityDetector`  [INFERRED]
  agents.md → ha-audio-events/app/audio/activity.py
- `3.1 Ingestion & Audio Preprocessing (`app/audio/`)` --references--> `AudioStreamSource`  [INFERRED]
  agents.md → ha-audio-events/app/audio/stream.py
- `3.3 Event Aggregation & Filtering (`app/detection/`)` --references--> `EventAggregator`  [INFERRED]
  agents.md → ha-audio-events/app/detection/aggregate.py

## Import Cycles
- None detected.

## Communities (71 total, 34 thin omitted)

### Community 0 - "HomeAssistantConfig"
Cohesion: 0.05
Nodes (51): HomeAssistantConfig, Initialize required HA entities if they don't exist yet., build_entity_ids(), build_friendly_names(), build_label_friendly_names(), build_label_sensor_entity_ids(), Regression tests for default config values that matter for correctness, not…, The Supervisor's internal proxy to Home Assistant Core's REST API is reachable… (+43 more)

### Community 1 - "AudioStreamSource"
Cohesion: 0.05
Nodes (49): deque, ensure_mono(), pcm_s16le_to_float32(), ndarray, AudioStreamSource, ndarray, Path, Consume ffmpeg stderr, logging each line, until EOF. (+41 more)

### Community 2 - "test_addon_options.py"
Cohesion: 0.06
Nodes (36): argparse, bump_version(), main(), Path, Update version references in the add-on manifests and python package metadata., re, _iter_option_values(), _iter_schema_leaves() (+28 more)

### Community 3 - "EventMessage"
Cohesion: 0.08
Nodes (36): MQTTConfig, End every active event immediately. Called on pipeline shutdown so Home…, EventMessage, build_entity_ids_for_labels(), build_label_state_topic(), build_mqtt_discovery_payload(), Per-label state topic, so each discovered sensor only reacts to its own label., Convert an audio label into a valid Home Assistant object_id slug. YAMNet… (+28 more)

### Community 4 - "Changelog"
Cohesion: 0.05
Nodes (40): Start the aiohttp web server and run until cancelled., Warn appropriately about an unauthenticated non-loopback bind., [0.1.10] - 2026-08-12, [0.1.11] - 2026-08-15, [0.1.13] - 2026-08-16, [0.1.7] - 2026-08-XX, [0.1.8] - 2026-08-XX, [0.1.9] - 2026-08-XX (+32 more)

### Community 5 - "manifest.json"
Cohesion: 0.05
Nodes (36): audiopapkin-barking-large-and-small-dog-290711.mp3, category, duration_seconds, expected_label, notes, path, dragon-studio-dog-barking-406629.mp3, category (+28 more)

### Community 6 - "test_addon_mgr.py"
Cohesion: 0.08
Nodes (36): asyncio, Tests for addon manager., Test close when no session exists., Test successful API request., Test API request with error status., A non-JSON body is surfaced as None instead of raising., Chunked responses (content_length None) must still be parsed as JSON.…, Test API request cancellation. (+28 more)

### Community 7 - "test_main.py"
Cohesion: 0.09
Nodes (18): ActivityConfig, WebUIConfig, test_activity_detector_thresholds(), test_load_config_parses_webui_auth_token(), asyncio, Test _run_pipeline processes audio chunks., Regression test for a real bug: AddonManager() was previously called with no…, Regression: when the audio stream ends, still-active aggregated events must be… (+10 more)

### Community 8 - "CircularAudioBuffer"
Cohesion: 0.07
Nodes (25): 1. Executive Summary & Architecture, 2. Directory & File Map, 3.1 Ingestion & Audio Preprocessing (`app/audio/`), 3.2 Machine Learning Inference (`app/classifiers/`), 3.4 Integration & Notification (`app/homeassistant/`), 3. Subsystem Breakdown, 4. Environment & Testing Procedures, 5. Coding & Contribution Guidelines for AI Agents (+17 more)

### Community 9 - "test_manifest.py"
Cohesion: 0.11
Nodes (26): _invalid_map_entry(), load_manifest(), ManifestValidationError, Any, Path, Validation helpers for the Home Assistant add-on manifest (config.yaml). These…, Validate the ``map`` section of a manifest. Returns a list of error messages…, Validate an add-on manifest file, returning a list of error messages. (+18 more)

### Community 10 - "config.py"
Cohesion: 0.17
Nodes (22): asyncio, build_classifier(), AppConfig, _clean_str(), load_config(), normalize_ha_url(), Normalize legacy Home Assistant API URLs. Existing installs may still carry the…, Treat blank strings as unset. Add-on option defaults use "" rather than null… (+14 more)

### Community 11 - "WebUI"
Cohesion: 0.14
Nodes (14): Serve the main HTML page for the Web UI., Fetch available camera entities from Home Assistant., Fetch assist_satellite (voice-satellite / built-in microphone) entities from…, Return the most recent detection events, most recent first., Get the currently configured source path., Set the audio source path and restart the add-on. The HTTP response is sent…, Restart the add-on after the current response has been delivered., Load YAMNet class names from the class map CSV. Same lookup convention as… (+6 more)

### Community 12 - "test_hardening.py"
Cohesion: 0.11
Nodes (22): _classifier_with_frame_len(), _detection(), asyncio, Path, Regression tests for the codebase-hardening pass. Covers: YAMNet full-buffer…, Every HA request must be bounded: aiohttp's default is 5 minutes, which stalls…, A 3s buffer must be classified as 3+ frames, not truncated to 0.975s., Very large buffers must not explode inference cost. (+14 more)

### Community 13 - "Backlog & Known Issues"
Cohesion: 0.09
Nodes (22): 10. ✅ FIXED (PR #20) — Log noise from panel polling, 11. ⚠️ BLOCKED ON SOURCE — End-to-end detection never confirmed on live install, 12. MQTT integration never tested against a broker, 13. CI gap: no container test for the camera-entity path, 14. Support custom ESP32 hardware as a detection source, 15. Scale from one pipeline to N sources and fan-out consumers, 1. Restore production options (left in test state), 3. ✅ VERIFIED NON-ISSUE — Bare ffmpeg stderr bypassed the stderr drain (+14 more)

### Community 14 - "AddonManager"
Cohesion: 0.18
Nodes (10): ClientSession, AddonManager, Any, Get an option value from add-on configuration. Uses the /addons/self/info…, Get information about the current add-on., Get or create aiohttp session., Close the aiohttp session., Make a request to Supervisor API. (+2 more)

### Community 15 - "HA Audio Events (Home Assistant Add-on)"
Cohesion: 0.11
Nodes (17): Audio Source Configuration, Full Configuration Reference, HA Audio Events (Home Assistant Add-on), Home Assistant Entities & Events, Home Assistant Event Automation Example, Ingress Web UI Source Picker, Installation in Home Assistant, Key Features (+9 more)

### Community 16 - "EventHistory"
Cohesion: 0.17
Nodes (10): collections, DetectionRecord, EventHistory, In-memory recent-detections buffer shared between the detection loop and the…, Ring buffer of the most recent detection events., test_empty_history_returns_empty_list(), test_recent_includes_expected_fields(), test_recent_returns_most_recent_first() (+2 more)

### Community 17 - "_run_pipeline"
Cohesion: 0.17
Nodes (15): NoAudioStreamError, Raised when a source delivers no audio bytes at all. Typical cause: an HA…, build_attributes(), format_event_summary(), _run_pipeline(), _detect(), _flush_active_events(), _publish_events() (+7 more)

### Community 18 - "YAMNetClassifier"
Cohesion: 0.25
Nodes (6): ndarray, Mono-float waveform trimmed/padded to exactly one model frame., Split the buffer into model-sized frames covering the whole window. The YAMNet…, YAMNetClassifier, Path, test_loads_display_names_from_yamnet_class_map_csv()

### Community 19 - "TestWebUI"
Cohesion: 0.14
Nodes (8): Test suite for WebUI server endpoints., Test that Web UI is accessible., Test cameras endpoint works correctly., Create the aiohttp application for testing., assist_satellite entities aren't a supported capture source yet -- set_source…, Test that the index page is served correctly., Test camera discovery when HA API returns an error., TestWebUI

### Community 20 - "TestWebUIClassifierFilters"
Cohesion: 0.14
Nodes (7): Tests for the classification filter endpoints (/api/class-map, GET/POST…, The class map endpoint serves the names loaded from yamnet_class_map.csv at…, Stored options are normalised to lowercase, matching how the pipeline compares…, Both option writes happen and a delayed restart follows., A malformed payload gets an explicit 400 and never touches the Supervisor…, If the second option write fails, no restart is scheduled., TestWebUIClassifierFilters

### Community 21 - "yamnet.py"
Cohesion: 0.28
Nodes (7): ABC, ai_edge_litert_interpreter, dataclasses, datetime, AudioClassifier, numpy, tflite_runtime_interpreter

### Community 22 - "AggregationConfig"
Cohesion: 0.28
Nodes (8): collections_abc, Detection, ndarray, AggregationConfig, EventAggregator, datetime, AggregatedEvent, test_event_aggregator_starts_and_ends()

### Community 23 - "server.py"
Cohesion: 0.22
Nodes (7): aiohttp, aiohttp_test_utils, csv, Addon Manager for HA Audio Events add-on. Handles communication with Supervisor…, Web UI server for HA Audio Events add-on. Provides ingress panel for selecting…, hmac, Tests for the Web UI server implementation in HA Audio Events add-on. Tests the…

### Community 24 - "Option 1 (recommended): dedicated ESP32 running streamer firmware"
Cohesion: 0.18
Nodes (10): Flash & find the streams, Hardware, Option 1 (recommended): dedicated ESP32 running streamer firmware, Option 1 vs Option 2 — remaining trade-offs, Option 2: stream from an existing ESPHome device, Point the add-on at it, Sharing the mic with Assist (supported), Troubleshooting (+2 more)

### Community 25 - "TestWebUIFilterMarkup"
Cohesion: 0.20
Nodes (5): AioHTTPTestCase, Without an auth token configured (the HA-ingress default), API access stays…, The index page must contain the filter controls wired up by JS., TestWebUIFilterMarkup, TestWebUINoAuthByDefault

### Community 26 - "HomeAssistantClient"
Cohesion: 0.24
Nodes (5): ClientTimeout, HomeAssistantClient, Any, Fetch entity states from Home Assistant, optionally filtered to a domain.…, Fixed

### Community 27 - "logging.py"
Cohesion: 0.27
Nodes (7): configure_logging(), _QuietPollAccessFilter, Silence per-request access lines for high-frequency panel polling. The ingress…, LogRecord, Tests for logging behaviour: quiet panel-polling access logs and the…, test_configure_logging_installs_poll_filter(), test_detections_polling_access_lines_are_filtered()

### Community 28 - "TestWebUIAuth"
Cohesion: 0.20
Nodes (3): The optional shared token must lock every /api endpoint while keeping the index…, The page itself must load so the user can be prompted for the token; only /api…, TestWebUIAuth

### Community 29 - "main_sync"
Cohesion: 0.32
Nodes (8): main_sync(), patch, Test main_sync runs successfully., Test main_sync handles KeyboardInterrupt., Test main_sync handles generic exception by logging it and exiting non-zero.…, test_main_sync_exception(), test_main_sync_keyboard_interrupt(), test_main_sync_success()

### Community 30 - "addon_manager"
Cohesion: 0.29
Nodes (7): addon_manager(), mock_response(), mock_session(), fixture, Create a mock aiohttp response., Create a mock aiohttp session., Create an AddonManager with mocked session.

### Community 32 - "ActivityDetector"
Cohesion: 0.60
Nodes (3): ActivityDetector, datetime, ndarray

### Community 33 - "TestWebUIHtmlSafety"
Cohesion: 0.33
Nodes (3): Regression guards for the XSS fix in the detections panel., Regression: the panel used to call .json() directly on every response; when the…, TestWebUIHtmlSafety

### Community 34 - "ClassifierConfig"
Cohesion: 0.60
Nodes (4): 3.3 Event Aggregation & Filtering (`app/detection/`), ClassifierConfig, filter_detections(), test_filter_detections_respects_include_exclude()

### Community 35 - "_load_config"
Cohesion: 0.80
Nodes (5): _load_config(), _load_json(), _load_yaml(), Any, Path

### Community 36 - "test_audio_fixtures.py"
Cohesion: 0.60
Nodes (4): _load_manifest(), parametrize, test_fixture_file_exists(), test_fixture_manifest_contains_expected_entry()

### Community 37 - "auth_middleware"
Cohesion: 0.50
Nodes (4): auth_middleware(), Require a shared token on /api routes when one is configured. Behind Home…, middleware, StreamResponse

## Knowledge Gaps
- **96 isolated node(s):** `run.sh script`, `ha-audio-events`, `category`, `expected_label`, `duration_seconds` (+91 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 383 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **34 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `AddonManager` connect `AddonManager` to `TestWebUIHtmlSafety`, `test_addon_mgr.py`, `config.py`, `WebUI`, `_run_pipeline`, `TestWebUI`, `TestWebUIClassifierFilters`, `test_get_session_creates_new`, `test_get_session_recreates_closed`, `server.py`, `test_get_session_reuses_existing`, `TestWebUIFilterMarkup`, `TestWebUIAuth`, `addon_manager`, `TestWebUIBindNotices`?**
  _High betweenness centrality (0.103) - this node is a cross-community bridge._
- **Why does `HomeAssistantClient` connect `HomeAssistantClient` to `HomeAssistantConfig`, `TestWebUIHtmlSafety`, `EventMessage`, `config.py`, `WebUI`, `test_hardening.py`, `_run_pipeline`, `TestWebUI`, `TestWebUIClassifierFilters`, `server.py`, `TestWebUIFilterMarkup`, `TestWebUIAuth`, `TestWebUIBindNotices`?**
  _High betweenness centrality (0.101) - this node is a cross-community bridge._
- **Why does `WebUI` connect `WebUI` to `TestWebUIHtmlSafety`, `Changelog`, `config.py`, `AddonManager`, `EventHistory`, `_run_pipeline`, `TestWebUI`, `TestWebUIClassifierFilters`, `server.py`, `TestWebUIFilterMarkup`, `HomeAssistantClient`, `TestWebUIAuth`, `TestWebUIBindNotices`?**
  _High betweenness centrality (0.098) - this node is a cross-community bridge._
- **Are the 20 inferred relationships involving `HomeAssistantConfig` (e.g. with `AudioStreamSource` and `HomeAssistantClient`) actually correct?**
  _`HomeAssistantConfig` has 20 INFERRED edges - model-reasoned connections that need verification._
- **Are the 12 inferred relationships involving `HomeAssistantClient` (e.g. with `HomeAssistantConfig` and `EventMessage`) actually correct?**
  _`HomeAssistantClient` has 12 INFERRED edges - model-reasoned connections that need verification._
- **Are the 10 inferred relationships involving `WebUI` (e.g. with `AddonManager` and `EventHistory`) actually correct?**
  _`WebUI` has 10 INFERRED edges - model-reasoned connections that need verification._
- **Are the 15 inferred relationships involving `EventMessage` (e.g. with `run_demo()` and `EventAggregator`) actually correct?**
  _`EventMessage` has 15 INFERRED edges - model-reasoned connections that need verification._