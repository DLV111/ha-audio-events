# Graph Report - t_654aeb1a  (2026-09-19)

## Corpus Check
- 73 files · ~43,430 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 10 file(s) not represented in the graph (top: (none) 6, .tflite 2, .csv 2)

## Summary
- 960 nodes · 1811 edges · 70 communities (45 shown, 25 thin omitted)
- Extraction: 87% EXTRACTED · 13% INFERRED · 0% AMBIGUOUS · INFERRED: 234 edges (avg confidence: 0.94)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `befe61a4`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- AudioStreamSource
- MQTTConfig
- Changelog
- TestWebUI
- HomeAssistantClient
- driver.py
- manifest.json
- test_addon_mgr.py
- test_addon_options.py
- test_main.py
- test_manifest.py
- test_hardening.py
- WebUI
- What You Must Do When Invoked
- test_no_audio_detection.py
- Backlog & Known Issues
- HomeAssistantConfig
- logging.py
- 4. Environment & Testing Procedures
- test_webui.py
- AddonManager
- HA Audio Events (Home Assistant Add-on)
- EventHistory
- EventMessage
- test_homeassistant_client.py
- ActivityConfig
- pathlib
- TestWebUIClassifierFilters
- demo.py
- config.py
- CircularAudioBuffer
- YAMNetClassifier
- Option 1 (recommended): dedicated ESP32 running streamer firmware
- TestWebUIAuth
- server.py
- graphify reference: extra exports and benchmark
- .test_get_state_filters_by_domain
- addon_manager
- TestWebUIBindNotices
- graphify reference: query, path, explain
- test_webui_starts_while_stream_is_still_live
- Autonomous Development Skill for ha-audio-events
- .update_state
- graphify reference: add a URL and watch a folder
- graphify reference: commit hook and native CLAUDE.md integration
- graphify reference: incremental update and cluster-only
- test_config_defaults.py
- graphify reference: GitHub clone and cross-repo merge
- graphify reference: transcribe video and audio
- graphify
- audio/__init__.py
- classifiers/__init__.py
- detection/__init__.py
- homeassistant/__init__.py
- app/__init__.py
- utils/__init__.py
- run.sh
- extraction-spec.md
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

## Communities (70 total, 25 thin omitted)

### Community 0 - "AudioStreamSource"
Cohesion: 0.07
Nodes (41): asyncio, collections_abc, deque, ensure_mono(), pcm_s16le_to_float32(), ndarray, AudioStreamSource, NoAudioStreamError (+33 more)

### Community 1 - "MQTTConfig"
Cohesion: 0.07
Nodes (42): MQTTConfig, build_entity_ids_for_labels(), build_label_state_topic(), build_mqtt_discovery_payload(), Per-label state topic, so each discovered sensor only reacts to its own label., Convert an audio label into a valid Home Assistant object_id slug. YAMNet…, slugify_label(), MQTTClient (+34 more)

### Community 2 - "Changelog"
Cohesion: 0.05
Nodes (40): Start the aiohttp web server and run until cancelled., Warn appropriately about an unauthenticated non-loopback bind., [0.1.10] - 2026-08-12, [0.1.11] - 2026-08-15, [0.1.13] - 2026-08-16, [0.1.7] - 2026-08-XX, [0.1.8] - 2026-08-XX, [0.1.9] - 2026-08-XX (+32 more)

### Community 3 - "TestWebUI"
Cohesion: 0.05
Nodes (21): Test successful setting of audio source., Regression: restarting the add-on used to run inline, killing the container…, A failed option write must not schedule a container restart., Test setting source with missing parameter., Test setting source when addon manager fails., Restart failures happen after the response is delivered, so they surface as a…, Test suite for WebUI server endpoints., Test that Web UI is accessible. (+13 more)

### Community 4 - "HomeAssistantClient"
Cohesion: 0.11
Nodes (22): HomeAssistantClient, make_mock_session(), asyncio, Tests for HomeAssistantClient., Test that __init__ creates an aiohttp session., Test that close closes the session., Test fire_event returns early if disabled., Test fire_event sends correct request on success. (+14 more)

### Community 5 - "driver.py"
Cohesion: 0.11
Nodes (35): argparse, _branch_name(), _bump_version(), cmd_apply(), cmd_clean(), cmd_fix(), cmd_monitor(), cmd_pr_create() (+27 more)

### Community 6 - "manifest.json"
Cohesion: 0.05
Nodes (36): audiopapkin-barking-large-and-small-dog-290711.mp3, category, duration_seconds, expected_label, notes, path, dragon-studio-dog-barking-406629.mp3, category (+28 more)

### Community 7 - "test_addon_mgr.py"
Cohesion: 0.08
Nodes (36): asyncio, Tests for addon manager., Test close when no session exists., Test successful API request., Test API request with error status., A non-JSON body is surfaced as None instead of raising., Chunked responses (content_length None) must still be parsed as JSON.…, Test API request cancellation. (+28 more)

### Community 8 - "test_addon_options.py"
Cohesion: 0.08
Nodes (28): _iter_option_values(), _iter_schema_leaves(), _load_manifest(), _load_translations(), asyncio, parametrize, Path, Tests for add-on option usability work: - homeassistant.url normalization… (+20 more)

### Community 9 - "test_main.py"
Cohesion: 0.10
Nodes (16): build_classifier(), AppConfig, asyncio, Test _run_pipeline processes audio chunks., Regression test for a real bug: AddonManager() was previously called with no…, Regression: when the audio stream ends, still-active aggregated events must be…, Regression: a failing audio pipeline (e.g. bad source_path) used to tear down…, Test _run_pipeline handles no audio source gracefully. (+8 more)

### Community 10 - "test_manifest.py"
Cohesion: 0.12
Nodes (25): _invalid_map_entry(), load_manifest(), ManifestValidationError, Any, Path, Validation helpers for the Home Assistant add-on manifest (config.yaml). These…, Validate the ``map`` section of a manifest. Returns a list of error messages…, Validate an add-on manifest file, returning a list of error messages. (+17 more)

### Community 11 - "test_hardening.py"
Cohesion: 0.11
Nodes (23): _classifier_with_frame_len(), _detection(), asyncio, Path, Regression tests for the codebase-hardening pass. Covers: YAMNet full-buffer…, Every HA request must be bounded: aiohttp's default is 5 minutes, which stalls…, _stream_wav yields chunks as it reads instead of materialising the entire file…, A 3s buffer must be classified as 3+ frames, not truncated to 0.975s. (+15 more)

### Community 12 - "WebUI"
Cohesion: 0.14
Nodes (14): Serve the main HTML page for the Web UI., Fetch available camera entities from Home Assistant., Fetch assist_satellite (voice-satellite / built-in microphone) entities from…, Return the most recent detection events, most recent first., Get the currently configured source path., Set the audio source path and restart the add-on. The HTTP response is sent…, Restart the add-on after the current response has been delivered., Load YAMNet class names from the class map CSV. Same lookup convention as… (+6 more)

### Community 13 - "What You Must Do When Invoked"
Cohesion: 0.08
Nodes (23): For /graphify add and --watch, For /graphify query, For the commit hook and native CLAUDE.md integration, For --update and --cluster-only, /graphify, Honesty Rules, Part A - Structural extraction for code files, Part B - Semantic extraction (parallel subagents) (+15 more)

### Community 14 - "test_no_audio_detection.py"
Cohesion: 0.13
Nodes (14): _FakeProc, _HangingStdout, asyncio, Tests for the no-audio-stream guard. Regression for a live incident: HA camera…, Simulates ffmpeg connected to a video-only proxy: never outputs., A source that never delivers audio bytes must fail fast and loudly., A normal stream (bytes arrive immediately) must flow untouched., Slow sources are tolerated: audio arriving just inside the window must not be… (+6 more)

### Community 15 - "Backlog & Known Issues"
Cohesion: 0.09
Nodes (21): 10. ✅ FIXED (PR #20) — Log noise from panel polling, 11. ⚠️ BLOCKED ON SOURCE — End-to-end detection never confirmed on live install, 12. MQTT integration never tested against a broker, 13. CI gap: no container test for the camera-entity path, 14. Support custom ESP32 hardware as a detection source, 1. Restore production options (left in test state), 3. ✅ VERIFIED NON-ISSUE — Bare ffmpeg stderr bypassed the stderr drain, 4. 🟡 FIX SHIPPED v0.4.5 (PR pending merge) — Camera proxy stream reliability / missing audio track (+13 more)

### Community 16 - "HomeAssistantConfig"
Cohesion: 0.22
Nodes (15): ClientTimeout, HomeAssistantConfig, Initialize required HA entities if they don't exist yet., build_attributes(), build_entity_ids(), build_friendly_names(), build_label_friendly_names(), build_label_sensor_entity_ids() (+7 more)

### Community 17 - "logging.py"
Cohesion: 0.12
Nodes (17): Addon Manager for HA Audio Events add-on. Handles communication with Supervisor…, main_sync(), configure_logging(), _QuietPollAccessFilter, Silence per-request access lines for high-frequency panel polling. The ingress…, LogRecord, patch, Tests for logging behaviour: quiet panel-polling access logs and the… (+9 more)

### Community 18 - "4. Environment & Testing Procedures"
Cohesion: 0.11
Nodes (18): 1. Executive Summary & Architecture, 2. Directory & File Map, 4. Environment & Testing Procedures, 5. Coding & Contribution Guidelines for AI Agents, AI Assistant Guide & Repository Overview: `ha-audio-events`, 🤖 Automated Skill: Audio Config Boolean Handling, CI Pipeline Alignment, Complete Test Workflow (Use Before Pushing) (+10 more)

### Community 19 - "test_webui.py"
Cohesion: 0.12
Nodes (10): aiohttp_test_utils, AioHTTPTestCase, Tests for the Web UI server implementation in HA Audio Events add-on. Tests the…, Without an auth token configured (the HA-ingress default), API access stays…, Regression guards for the XSS fix in the detections panel., Regression: the panel used to call .json() directly on every response; when the…, The index page must contain the filter controls wired up by JS., TestWebUIFilterMarkup (+2 more)

### Community 20 - "AddonManager"
Cohesion: 0.18
Nodes (10): ClientSession, AddonManager, Any, Get an option value from add-on configuration. Uses the /addons/self/info…, Get information about the current add-on., Get or create aiohttp session., Close the aiohttp session., Make a request to Supervisor API. (+2 more)

### Community 21 - "HA Audio Events (Home Assistant Add-on)"
Cohesion: 0.11
Nodes (17): Audio Source Configuration, Full Configuration Reference, HA Audio Events (Home Assistant Add-on), Home Assistant Entities & Events, Home Assistant Event Automation Example, Ingress Web UI Source Picker, Installation in Home Assistant, Key Features (+9 more)

### Community 22 - "EventHistory"
Cohesion: 0.15
Nodes (11): collections, DetectionRecord, EventHistory, In-memory recent-detections buffer shared between the detection loop and the…, Ring buffer of the most recent detection events., Interpreter guard for subcommands, test_empty_history_returns_empty_list(), test_recent_includes_expected_fields() (+3 more)

### Community 23 - "EventMessage"
Cohesion: 0.19
Nodes (12): EventAggregator, datetime, End every active event immediately. Called on pipeline shutdown so Home…, AggregatedEvent, EventMessage, format_event_summary(), Test format_event_summary with missing attributes., Regression test: with only 1 decimal place, distinct started/active events with… (+4 more)

### Community 24 - "test_homeassistant_client.py"
Cohesion: 0.17
Nodes (15): aiohttp, ha_config(), ha_config_disabled(), mock_event(), mock_response_200(), mock_response_400(), mock_response_500(), fixture (+7 more)

### Community 25 - "ActivityConfig"
Cohesion: 0.24
Nodes (9): dataclasses, ActivityDetector, datetime, ndarray, ActivityConfig, numpy, test_activity_detector_thresholds(), test_circular_buffer_append_and_window() (+1 more)

### Community 26 - "pathlib"
Cohesion: 0.22
Nodes (9): ABC, ai_edge_litert_interpreter, datetime, AudioClassifier, ndarray, pathlib, Path, test_loads_display_names_from_yamnet_class_map_csv() (+1 more)

### Community 27 - "TestWebUIClassifierFilters"
Cohesion: 0.14
Nodes (7): Tests for the classification filter endpoints (/api/class-map, GET/POST…, The class map endpoint serves the names loaded from yamnet_class_map.csv at…, Stored options are normalised to lowercase, matching how the pipeline compares…, Both option writes happen and a delayed restart follows., A malformed payload gets an explicit 400 and never touches the Supervisor…, If the second option write fails, no restart is scheduled., TestWebUIClassifierFilters

### Community 28 - "demo.py"
Cohesion: 0.31
Nodes (10): Detection, AggregationConfig, ClassifierConfig, format_file_result(), main(), _prepare_audio_for_demo(), run_demo(), filter_detections() (+2 more)

### Community 29 - "config.py"
Cohesion: 0.32
Nodes (12): _clean_str(), load_config(), _load_config(), _load_json(), _load_yaml(), normalize_ha_url(), Any, Path (+4 more)

### Community 30 - "CircularAudioBuffer"
Cohesion: 0.20
Nodes (7): 3.1 Ingestion & Audio Preprocessing (`app/audio/`), 3.2 Machine Learning Inference (`app/classifiers/`), 3.3 Event Aggregation & Filtering (`app/detection/`), 3.4 Integration & Notification (`app/homeassistant/`), 3. Subsystem Breakdown, CircularAudioBuffer, ndarray

### Community 31 - "YAMNetClassifier"
Cohesion: 0.32
Nodes (4): ndarray, Mono-float waveform trimmed/padded to exactly one model frame., Split the buffer into model-sized frames covering the whole window. The YAMNet…, YAMNetClassifier

### Community 32 - "Option 1 (recommended): dedicated ESP32 running streamer firmware"
Cohesion: 0.18
Nodes (10): Flash & find the streams, Hardware, Option 1 (recommended): dedicated ESP32 running streamer firmware, Option 1 vs Option 2 — remaining trade-offs, Option 2: stream from an existing ESPHome device, Point the add-on at it, Sharing the mic with Assist (supported), Troubleshooting (+2 more)

### Community 33 - "TestWebUIAuth"
Cohesion: 0.20
Nodes (3): The optional shared token must lock every /api endpoint while keeping the index…, The page itself must load so the user can be prompted for the token; only /api…, TestWebUIAuth

### Community 34 - "server.py"
Cohesion: 0.22
Nodes (7): csv, auth_middleware(), Web UI server for HA Audio Events add-on. Provides ingress panel for selecting…, Require a shared token on /api routes when one is configured. Behind Home…, hmac, middleware, StreamResponse

### Community 35 - "graphify reference: extra exports and benchmark"
Cohesion: 0.22
Nodes (8): graphify reference: extra exports and benchmark, Step 6b - Wiki (only if --wiki flag), Step 7 - Neo4j export (only if --neo4j or --neo4j-push flag), Step 7a - FalkorDB export (only if --falkordb or --falkordb-push flag), Step 7b - SVG export (only if --svg flag), Step 7c - GraphML export (only if --graphml flag), Step 7d - MCP server (only if --mcp flag), Step 8 - Token reduction benchmark (only if total_words > 5000)

### Community 36 - ".test_get_state_filters_by_domain"
Cohesion: 0.25
Nodes (5): make_mock_get_session(), get_state("camera") should call GET /api/states and filter to camera.* entities., get_state should return None (not raise) on a non-2xx response., Unlike fire_event/update_state, get_state must not be gated on config.enabled…, Create a mock session whose .get() returns the given response.

### Community 37 - "addon_manager"
Cohesion: 0.29
Nodes (7): addon_manager(), mock_response(), mock_session(), fixture, Create a mock aiohttp response., Create a mock aiohttp session., Create an AddonManager with mocked session.

### Community 39 - "graphify reference: query, path, explain"
Cohesion: 0.33
Nodes (5): For /graphify explain, For /graphify path, graphify reference: query, path, explain, Step 0 — Constrained query expansion (REQUIRED before traversal), Step 1 — Traversal

### Community 41 - "Autonomous Development Skill for ha-audio-events"
Cohesion: 0.40
Nodes (4): Autonomous Development Skill for ha-audio-events, Driver, How to Invoke, Prerequisites

### Community 42 - ".update_state"
Cohesion: 0.40
Nodes (3): Any, Fetch entity states from Home Assistant, optionally filtered to a domain.…, Fixed

### Community 43 - "graphify reference: add a URL and watch a folder"
Cohesion: 0.50
Nodes (3): For /graphify add, For --watch, graphify reference: add a URL and watch a folder

### Community 44 - "graphify reference: commit hook and native CLAUDE.md integration"
Cohesion: 0.50
Nodes (3): For git commit hook, For native CLAUDE.md integration, graphify reference: commit hook and native CLAUDE.md integration

### Community 45 - "graphify reference: incremental update and cluster-only"
Cohesion: 0.50
Nodes (3): For --cluster-only, For --update (incremental re-extraction), graphify reference: incremental update and cluster-only

### Community 46 - "test_config_defaults.py"
Cohesion: 0.50
Nodes (3): Regression tests for default config values that matter for correctness, not…, The Supervisor's internal proxy to Home Assistant Core's REST API is reachable…, test_homeassistant_default_url_uses_correct_supervisor_proxy_path()

## Knowledge Gaps
- **140 isolated node(s):** `run.sh script`, `ha-audio-events`, `category`, `expected_label`, `duration_seconds` (+135 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 447 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **25 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `WebUI` connect `WebUI` to `TestWebUIAuth`, `server.py`, `Changelog`, `HomeAssistantClient`, `TestWebUI`, `TestWebUIBindNotices`, `HomeAssistantConfig`, `test_webui.py`, `AddonManager`, `EventHistory`, `TestWebUIClassifierFilters`?**
  _High betweenness centrality (0.087) - this node is a cross-community bridge._
- **Why does `AddonManager` connect `AddonManager` to `TestWebUIAuth`, `server.py`, `test_get_session_creates_new`, `test_get_session_recreates_closed`, `addon_manager`, `test_get_session_reuses_existing`, `test_addon_mgr.py`, `TestWebUI`, `TestWebUIBindNotices`, `WebUI`, `HomeAssistantConfig`, `logging.py`, `test_webui.py`, `TestWebUIClassifierFilters`?**
  _High betweenness centrality (0.087) - this node is a cross-community bridge._
- **Why does `HomeAssistantClient` connect `HomeAssistantClient` to `TestWebUIAuth`, `server.py`, `TestWebUI`, `.test_get_state_filters_by_domain`, `TestWebUIBindNotices`, `.update_state`, `test_hardening.py`, `WebUI`, `HomeAssistantConfig`, `test_webui.py`, `EventMessage`, `TestWebUIClassifierFilters`?**
  _High betweenness centrality (0.087) - this node is a cross-community bridge._
- **Are the 20 inferred relationships involving `HomeAssistantConfig` (e.g. with `AudioStreamSource` and `HomeAssistantClient`) actually correct?**
  _`HomeAssistantConfig` has 20 INFERRED edges - model-reasoned connections that need verification._
- **Are the 12 inferred relationships involving `HomeAssistantClient` (e.g. with `HomeAssistantConfig` and `EventMessage`) actually correct?**
  _`HomeAssistantClient` has 12 INFERRED edges - model-reasoned connections that need verification._
- **Are the 10 inferred relationships involving `WebUI` (e.g. with `AddonManager` and `EventHistory`) actually correct?**
  _`WebUI` has 10 INFERRED edges - model-reasoned connections that need verification._
- **Are the 15 inferred relationships involving `EventMessage` (e.g. with `run_demo()` and `EventAggregator`) actually correct?**
  _`EventMessage` has 15 INFERRED edges - model-reasoned connections that need verification._