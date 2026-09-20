# Graph Report - t_82250682  (2026-09-20)

## Corpus Check
- 64 files · ~33,124 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 11 file(s) not represented in the graph (top: (none) 7, .tflite 2, .csv 2)

## Summary
- 899 nodes · 1758 edges · 70 communities (36 shown, 34 thin omitted)
- Extraction: 87% EXTRACTED · 13% INFERRED · 0% AMBIGUOUS · INFERRED: 233 edges (avg confidence: 0.94)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `b776ddf4`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- HomeAssistantConfig
- AudioStreamSource
- test_addon_options.py
- MQTTConfig
- Changelog
- manifest.json
- test_addon_mgr.py
- test_main.py
- YAMNetClassifier
- test_manifest.py
- config.py
- WebUI
- test_hardening.py
- driver.py
- AddonManager
- HA Audio Events (Home Assistant Add-on)
- EventHistory
- _run_pipeline
- test_no_audio_detection.py
- TestWebUI
- TestWebUIClassifierFilters
- pathlib
- AggregationConfig
- server.py
- Option 1 (recommended): dedicated ESP32 running streamer firmware
- test_webui.py
- CircularAudioBuffer
- logging.py
- TestWebUIAuth
- .start
- addon_manager
- TestWebUIBindNotices
- ActivityDetector
- Autonomous Development Skill for ha-audio-events
- demo.py
- load_config
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
- `3.3 Event Aggregation & Filtering (`app/detection/`)` --references--> `EventAggregator`  [INFERRED]
  agents.md → ha-audio-events/app/detection/aggregate.py

## Import Cycles
- None detected.

## Communities (70 total, 34 thin omitted)

### Community 0 - "HomeAssistantConfig"
Cohesion: 0.05
Nodes (56): ClientTimeout, HomeAssistantConfig, End every active event immediately. Called on pipeline shutdown so Home…, EventMessage, HomeAssistantClient, Any, Initialize required HA entities if they don't exist yet., Fetch entity states from Home Assistant, optionally filtered to a domain.… (+48 more)

### Community 1 - "AudioStreamSource"
Cohesion: 0.05
Nodes (51): deque, ensure_mono(), pcm_s16le_to_float32(), ndarray, AudioStreamSource, ndarray, Path, Consume ffmpeg stderr, logging each line, until EOF. (+43 more)

### Community 2 - "test_addon_options.py"
Cohesion: 0.08
Nodes (28): _iter_option_values(), _iter_schema_leaves(), _load_manifest(), _load_translations(), asyncio, parametrize, Path, Tests for add-on option usability work: - homeassistant.url normalization… (+20 more)

### Community 3 - "MQTTConfig"
Cohesion: 0.07
Nodes (42): MQTTConfig, build_entity_ids_for_labels(), build_label_state_topic(), build_mqtt_discovery_payload(), Per-label state topic, so each discovered sensor only reacts to its own label., Convert an audio label into a valid Home Assistant object_id slug. YAMNet…, slugify_label(), MQTTClient (+34 more)

### Community 4 - "Changelog"
Cohesion: 0.05
Nodes (36): [0.1.10] - 2026-08-12, [0.1.11] - 2026-08-15, [0.1.13] - 2026-08-16, [0.1.7] - 2026-08-XX, [0.1.8] - 2026-08-XX, [0.1.9] - 2026-08-XX, [0.3.0] - 2026-08-22, [0.4.0] - 2026-08-22 (+28 more)

### Community 5 - "manifest.json"
Cohesion: 0.05
Nodes (36): audiopapkin-barking-large-and-small-dog-290711.mp3, category, duration_seconds, expected_label, notes, path, dragon-studio-dog-barking-406629.mp3, category (+28 more)

### Community 6 - "test_addon_mgr.py"
Cohesion: 0.08
Nodes (36): asyncio, Tests for addon manager., Test close when no session exists., Test successful API request., Test API request with error status., A non-JSON body is surfaced as None instead of raising., Chunked responses (content_length None) must still be parsed as JSON.…, Test API request cancellation. (+28 more)

### Community 7 - "test_main.py"
Cohesion: 0.09
Nodes (19): build_classifier(), AppConfig, format_event_summary(), asyncio, Test _run_pipeline processes audio chunks., Regression: when the audio stream ends, still-active aggregated events must be…, Regression for a live incident: the Web UI used to be awaited only AFTER the…, Test format_event_summary with missing attributes. (+11 more)

### Community 8 - "YAMNetClassifier"
Cohesion: 0.07
Nodes (27): 1. Executive Summary & Architecture, 2. Directory & File Map, 3.2 Machine Learning Inference (`app/classifiers/`), 3.4 Integration & Notification (`app/homeassistant/`), 3. Subsystem Breakdown, 4. Environment & Testing Procedures, 5. Coding & Contribution Guidelines for AI Agents, AI Assistant Guide & Repository Overview: `ha-audio-events` (+19 more)

### Community 9 - "test_manifest.py"
Cohesion: 0.11
Nodes (26): _invalid_map_entry(), load_manifest(), ManifestValidationError, Any, Path, Validation helpers for the Home Assistant add-on manifest (config.yaml). These…, Validate the ``map`` section of a manifest. Returns a list of error messages…, Validate an add-on manifest file, returning a list of error messages. (+18 more)

### Community 10 - "config.py"
Cohesion: 0.24
Nodes (11): asyncio, dataclasses, NoAudioStreamError, Raised when a source delivers no audio bytes at all. Typical cause: an HA…, normalize_ha_url(), Normalize legacy Home Assistant API URLs. Existing installs may still carry the…, numpy, os (+3 more)

### Community 11 - "WebUI"
Cohesion: 0.12
Nodes (16): Serve the main HTML page for the Web UI., Fetch available camera entities from Home Assistant., Fetch assist_satellite (voice-satellite / built-in microphone) entities from…, Return the most recent detection events, most recent first., Get the currently configured source path., Set the audio source path and restart the add-on. The HTTP response is sent…, Restart the add-on after the current response has been delivered., Load YAMNet class names from the class map CSV. Same lookup convention as… (+8 more)

### Community 12 - "test_hardening.py"
Cohesion: 0.10
Nodes (24): _classifier_with_frame_len(), _detection(), asyncio, Path, Regression tests for the codebase-hardening pass. Covers: YAMNet full-buffer…, Every HA request must be bounded: aiohttp's default is 5 minutes, which stalls…, _stream_wav yields chunks as it reads instead of materialising the entire file…, A 3s buffer must be classified as 3+ frames, not truncated to 0.975s. (+16 more)

### Community 13 - "driver.py"
Cohesion: 0.10
Nodes (36): argparse, _branch_name(), _bump_version(), cmd_apply(), cmd_clean(), cmd_fix(), cmd_monitor(), cmd_pr_create() (+28 more)

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
Nodes (11): build_attributes(), _run_pipeline(), _detect(), _flush_active_events(), _publish_events(), Regression test for a real bug: AddonManager() was previously called with no…, Regression: a failing audio pipeline (e.g. bad source_path) used to tear down…, test_run_pipeline_wires_up_webui_correctly() (+3 more)

### Community 18 - "test_no_audio_detection.py"
Cohesion: 0.13
Nodes (14): _FakeProc, _HangingStdout, asyncio, Tests for the no-audio-stream guard. Regression for a live incident: HA camera…, Simulates ffmpeg connected to a video-only proxy: never outputs., A source that never delivers audio bytes must fail fast and loudly., A normal stream (bytes arrive immediately) must flow untouched., Slow sources are tolerated: audio arriving just inside the window must not be… (+6 more)

### Community 19 - "TestWebUI"
Cohesion: 0.14
Nodes (8): Test suite for WebUI server endpoints., Test that Web UI is accessible., Test cameras endpoint works correctly., Create the aiohttp application for testing., assist_satellite entities aren't a supported capture source yet -- set_source…, Test that the index page is served correctly., Test camera discovery when HA API returns an error., TestWebUI

### Community 20 - "TestWebUIClassifierFilters"
Cohesion: 0.14
Nodes (7): Tests for the classification filter endpoints (/api/class-map, GET/POST…, The class map endpoint serves the names loaded from yamnet_class_map.csv at…, Stored options are normalised to lowercase, matching how the pipeline compares…, Both option writes happen and a delayed restart follows., A malformed payload gets an explicit 400 and never touches the Supervisor…, If the second option write fails, no restart is scheduled., TestWebUIClassifierFilters

### Community 21 - "pathlib"
Cohesion: 0.27
Nodes (7): ABC, ai_edge_litert_interpreter, datetime, AudioClassifier, ndarray, pathlib, tflite_runtime_interpreter

### Community 22 - "AggregationConfig"
Cohesion: 0.36
Nodes (7): collections_abc, Detection, AggregationConfig, EventAggregator, datetime, AggregatedEvent, test_event_aggregator_starts_and_ends()

### Community 23 - "server.py"
Cohesion: 0.18
Nodes (9): aiohttp, csv, Addon Manager for HA Audio Events add-on. Handles communication with Supervisor…, auth_middleware(), Web UI server for HA Audio Events add-on. Provides ingress panel for selecting…, Require a shared token on /api routes when one is configured. Behind Home…, hmac, middleware (+1 more)

### Community 24 - "Option 1 (recommended): dedicated ESP32 running streamer firmware"
Cohesion: 0.18
Nodes (10): Flash & find the streams, Hardware, Option 1 (recommended): dedicated ESP32 running streamer firmware, Option 1 vs Option 2 — remaining trade-offs, Option 2: stream from an existing ESPHome device, Point the add-on at it, Sharing the mic with Assist (supported), Troubleshooting (+2 more)

### Community 25 - "test_webui.py"
Cohesion: 0.12
Nodes (10): aiohttp_test_utils, AioHTTPTestCase, Tests for the Web UI server implementation in HA Audio Events add-on. Tests the…, Without an auth token configured (the HA-ingress default), API access stays…, Regression guards for the XSS fix in the detections panel., Regression: the panel used to call .json() directly on every response; when the…, The index page must contain the filter controls wired up by JS., TestWebUIFilterMarkup (+2 more)

### Community 26 - "CircularAudioBuffer"
Cohesion: 0.28
Nodes (4): 3.1 Ingestion & Audio Preprocessing (`app/audio/`), CircularAudioBuffer, ndarray, test_circular_buffer_append_and_window()

### Community 27 - "logging.py"
Cohesion: 0.14
Nodes (15): main_sync(), configure_logging(), _QuietPollAccessFilter, Silence per-request access lines for high-frequency panel polling. The ingress…, LogRecord, patch, Tests for logging behaviour: quiet panel-polling access logs and the…, test_configure_logging_installs_poll_filter() (+7 more)

### Community 28 - "TestWebUIAuth"
Cohesion: 0.20
Nodes (3): The optional shared token must lock every /api endpoint while keeping the index…, The page itself must load so the user can be prompted for the token; only /api…, TestWebUIAuth

### Community 29 - ".start"
Cohesion: 0.33
Nodes (4): Start the aiohttp web server and run until cancelled., Warn appropriately about an unauthenticated non-loopback bind., [0.4.3] - 2026-08-23, Fixed

### Community 30 - "addon_manager"
Cohesion: 0.29
Nodes (7): addon_manager(), mock_response(), mock_session(), fixture, Create a mock aiohttp response., Create a mock aiohttp session., Create an AddonManager with mocked session.

### Community 32 - "ActivityDetector"
Cohesion: 0.60
Nodes (3): ActivityDetector, datetime, ndarray

### Community 33 - "Autonomous Development Skill for ha-audio-events"
Cohesion: 0.40
Nodes (4): Autonomous Development Skill for ha-audio-events, Driver, How to Invoke, Prerequisites

### Community 34 - "demo.py"
Cohesion: 0.32
Nodes (10): 3.3 Event Aggregation & Filtering (`app/detection/`), ActivityConfig, ClassifierConfig, format_file_result(), main(), _prepare_audio_for_demo(), run_demo(), filter_detections() (+2 more)

### Community 35 - "load_config"
Cohesion: 0.36
Nodes (10): _clean_str(), load_config(), _load_config(), _load_json(), _load_yaml(), Any, Path, Treat blank strings as unset. Add-on option defaults use "" rather than null… (+2 more)

### Community 36 - "test_config_defaults.py"
Cohesion: 0.50
Nodes (3): Regression tests for default config values that matter for correctness, not…, The Supervisor's internal proxy to Home Assistant Core's REST API is reachable…, test_homeassistant_default_url_uses_correct_supervisor_proxy_path()

## Knowledge Gaps
- **99 isolated node(s):** `run.sh script`, `ha-audio-events`, `category`, `expected_label`, `duration_seconds` (+94 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 397 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **34 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `AddonManager` connect `AddonManager` to `test_addon_mgr.py`, `config.py`, `WebUI`, `_run_pipeline`, `TestWebUI`, `TestWebUIClassifierFilters`, `test_get_session_creates_new`, `test_get_session_recreates_closed`, `server.py`, `test_get_session_reuses_existing`, `test_webui.py`, `TestWebUIAuth`, `addon_manager`, `TestWebUIBindNotices`?**
  _High betweenness centrality (0.097) - this node is a cross-community bridge._
- **Why does `HomeAssistantClient` connect `HomeAssistantConfig` to `config.py`, `WebUI`, `test_hardening.py`, `_run_pipeline`, `TestWebUI`, `TestWebUIClassifierFilters`, `server.py`, `test_webui.py`, `TestWebUIAuth`, `TestWebUIBindNotices`?**
  _High betweenness centrality (0.095) - this node is a cross-community bridge._
- **Why does `WebUI` connect `WebUI` to `HomeAssistantConfig`, `config.py`, `AddonManager`, `EventHistory`, `_run_pipeline`, `TestWebUI`, `TestWebUIClassifierFilters`, `server.py`, `test_webui.py`, `TestWebUIAuth`, `.start`, `TestWebUIBindNotices`?**
  _High betweenness centrality (0.093) - this node is a cross-community bridge._
- **Are the 20 inferred relationships involving `HomeAssistantConfig` (e.g. with `AudioStreamSource` and `HomeAssistantClient`) actually correct?**
  _`HomeAssistantConfig` has 20 INFERRED edges - model-reasoned connections that need verification._
- **Are the 12 inferred relationships involving `HomeAssistantClient` (e.g. with `HomeAssistantConfig` and `EventMessage`) actually correct?**
  _`HomeAssistantClient` has 12 INFERRED edges - model-reasoned connections that need verification._
- **Are the 10 inferred relationships involving `WebUI` (e.g. with `AddonManager` and `EventHistory`) actually correct?**
  _`WebUI` has 10 INFERRED edges - model-reasoned connections that need verification._
- **Are the 15 inferred relationships involving `EventMessage` (e.g. with `run_demo()` and `EventAggregator`) actually correct?**
  _`EventMessage` has 15 INFERRED edges - model-reasoned connections that need verification._