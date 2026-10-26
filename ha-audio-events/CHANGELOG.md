# Changelog

All notable changes to this add-on will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.9.0] - 2026-10-26
### Added
- A real `silence` event is emitted after 5 seconds without activity by default.
- The timeout is tunable with `activity.silence_timeout`; sound immediately ends the silence event.

## [0.8.0] - 2026-10-19
### Added
- The Audio Class Filters picker now **filters both panes as you type**: typing in the search box narrows the Available and Accepted lists by class-name substring. Previously the query was stored in state but `filterState()` was never called by the renderer, so the lists never changed.
- Search and category chips combine (AND): a query only shows matches inside the selected AudioSet category.
- A live, `aria-live` result count reports how many classes are available/selected under the current search and category filter.
- Keyboard navigation for both lists: Arrow Up/Down move between rows, Home/End jump, Space/Enter toggle the focused row.
- Phones get a segmented **Browse / Selected** view, a full-width search box, and touch targets of at least 44px for rows, category chips and buttons.
### Changed
- The picker renderer and styles were extracted from the inline code in `server.py` into `app/webui/static/picker.js` and `app/webui/static/picker.css`; the page now only fetches data and mounts the pickers.
- The byte-identical duplicate `app/webui/transfer_picker.js` was removed. `app/webui/static/transfer_picker.js` is the single source of truth, and the Node test now targets it.
- Group headers and label rows are siblings in the DOM. Labels no longer sit inside the flex group header, which previously produced a large empty gutter and a header hundreds of pixels tall.
- Both panes are bounded with their own scroll area, and the desktop layout is a three-column grid (available | transfer | accepted).
### Fixed
- Ticking a label no longer collapses its group (checkbox clicks now stop event propagation).
- The whole label row is a tap target, not just the small checkbox.
- **Select All / Remove All** act on the currently visible (search + chip filtered) labels instead of silently accepting or clearing hundreds of hidden ones.

### Upgrade note
The saved configuration format is unchanged: the panel still posts `{include, exclude}` as lowercased string arrays.

## [0.7.1] - 2026-10-17
### Fixed
- **MQTT-disabled installs keep working**: entity ownership is now config-driven and mutually exclusive. With `mqtt.enabled=false` the two scalar entities (`sensor.<prefix>_last_audio_event`, `binary_sensor.<prefix>_audio_active`) *and* the per-label sensors named in `classifier.include` are created and updated over the Home Assistant REST API again, exactly as before MQTT discovery existed — they are just not manageable from the UI (no registry `unique_id`). This restores the behaviour of the `0.7.0` release, which published entity state through MQTT only and silently left MQTT-disabled installs with entities that never updated.
- **No stale `unknown` scalar entities**: the event payload published to `mqtt.topic` — the topic both scalar entities read as their state and attributes — and the per-label state topics are now published **retained**, so the entities keep their last known value across a broker or Home Assistant restart instead of sitting at `unknown` until the next detection.
- **Discovery survives a slow broker**: MQTT discovery is (re)published from paho's `on_connect` callback using cached payloads, rather than only once at startup. A start-up publish issued before the CONNACK is not queued by paho at QoS 0 and could be dropped silently when the broker was slow or briefly unavailable.
### Changed
- The "MQTT is disabled" warning now names **both** the scalar entities and the per-label sensors that lose UI manageability, and says that `unique_id` requires MQTT. Previously it mentioned only the scalar pair, so per-label sensors looked unaffected.
- The MQTT device advertised through discovery is now named `Audio Events (<prefix>)` instead of `<prefix> audio detector` (which read as "audio audio detector" for the default `audio` prefix).
- `make generate-class-groups` now syncs `models/class_groups.json` into the container build context (`ha-audio-events/models/`) instead of relying on two hand-copied files.

### Upgrade note
Entities created by the REST state POSTs have no registry `unique_id`, so with `mqtt.enabled=false` they remain unmanageable in the Home Assistant UI — that is expected and unchanged. Enabling MQTT registers the discovered entities; if you previously ran REST-created entities and then enable MQTT, Home Assistant may briefly show both the newly registered entity and the leftover unmanaged one. The add-on never renames or deletes your entities: delete the stale unmanaged duplicates by hand once.

## [0.7.0] - 2026-10-13
### Added
- **Menu-driven, mobile-friendly audio class filters**: each Include / Exclude picker now has a horizontally scrollable bar of AudioSet category chips that narrows both panes to one top-level category at a time. Backed by a new `GET /api/class-groups` endpoint serving `models/class_groups.json` — the grouped class menu, generated from the AudioSet ontology with `make generate-class-groups` (never hand-maintained), which partitions all 521 YAMNet classes across the 7 groups of the current ontology.
- **Unique IDs for the two scalar Home Assistant entities**: `sensor.<prefix>_last_audio_event` and `binary_sensor.<prefix>_audio_active` are now created through MQTT discovery (with `unique_id`, device block, and value/attribute templates) instead of REST state POSTs, so Home Assistant no longer reports "does not have a unique ID, therefore its settings cannot be managed from the UI". Because entity ids and unique ids both derive from `homeassistant.entity_prefix`, a second audio stream simply uses its own prefix (e.g. `audio_kitchen`).
### Changed
- Entity state is no longer published over the Home Assistant REST API: `HomeAssistantClient.init_entities()` only creates entities explicitly declared by `build_rest_entity_ids()` (empty after this change), and event handling publishes to MQTT only (the REST client still fires the `audio.detected` event). Enable the `mqtt` option to get the entities; the add-on logs a warning when Home Assistant publishing is enabled without MQTT.
- Scalar entity discovery is published on every MQTT connect, including when `classifier.include` is empty (an empty include list still means "report all classes"). Per-label binary sensors are unchanged — same entity ids, published only for labels named in `classifier.include`.
- Filter pickers adapt to phones: below 700px the two panes stack vertically and the transfer arrows, group headers and label rows grow to full-width tap targets.
### Fixed
- Buttons inside the Audio Class Filters form (category chips, group Select / Clear, transfer arrows, Select All / Remove All) are now `type="button"`, so tapping one no longer submits the form — which previously re-applied the stored filters and restarted the add-on on every click.

## [0.6.1] - 2026-10-05
### Fixed
- **Audio Class Filters no longer fail with "TransferPicker is not defined"**: the panel loaded its picker module from the root-absolute URL `/static/transfer_picker.js`. Under Home Assistant ingress the panel is served from `/api/hassio_ingress/<token>/`, so the browser requested the asset from Home Assistant core, the request never reached the add-on, the classic `<script>` never executed, and the first `TransferPicker.*` call threw. The reference is now relative (`static/transfer_picker.js`), so it resolves under whatever prefix the panel is mounted at, ingress included.
- **Static assets are served regardless of the process working directory**: `/static/{path}` resolved its directory relative to the current working directory, so it only worked when the add-on had started from `ha-audio-events/` (it 404'd under pytest and any other CWD). It now resolves from the module location and rejects paths that escape the static directory.

### Added
- Regression tests: a Node `node:vm` test asserting the UMD wrapper assigns a global `TransferPicker` (with its full API) in a classic-script context, plus pytest coverage for the static route, the relative asset reference, and that the served asset matches the Node-tested source.

## [0.6.0] - 2026-10-05
### Added
- **Dual-list transfer pickers for audio class filters in the Web UI panel**: Replace the two multi-select dropdowns with proper left/right transfer pickers (one for Include, one for Exclude) featuring available/accepted panes, Select All / Remove All, bidirectional transfer arrows, per-group Select / Clear, collapsible group headers, a search box filtering both panes, and a visible "N/M values accepted" counter.
- **AudioSet-ontology label grouping**: `make update-yamnet-groups` (plus an offline fixture suite) derives each of the 521 YAMNet label groupings from the [AudioSet ontology](https://raw.githubusercontent.com/audioset/ontology/master/ontology.json) into a committed `models/yamnet_groups.json` (no network needed at add-on runtime); labels are rendered grouped by their ontology ancestry (e.g. `Bark` → Animal > Domestic animals, pets > Dog).
- **JS unit tests for the picker logic**: `transfer_picker.js` is a reusable module (with Node test runner in CI, via `setup-node`) exercising accept/remove/select-all/remove-all/search/filtering/counter behaviour — 13 tests.
- New panel endpoint `GET /api/groups` exposing the grouped classes tree (consumed by the picker).

### Fixed
- **`update-yamnet-groups` now keeps the container build context in sync** by also copying `yamnet_groups.json` into `ha-audio-events/models/`, so the add-on has the groups file when it runs `models/yamnet_groups.json` relative to its working directory.

## [0.5.2] - 2026-09-28
### Changed
- Removed the standalone Audio Event Duration, Audio Model, and Last Audio Confidence sensors; these details remain available in Home Assistant event data and Last Audio Event attributes.

## [0.5.1] - 2026-09-28
### Fixed
- **Regression coverage for startup and shutdown**: tightened the async tests around `_run_pipeline()` and `main_sync()` so coroutine cleanup and interrupt handling no longer leave behind unawaited tasks or silent warnings during CI.
- **Test reliability**: corrected the mocked HA client exception paths so they mimic synchronous `aiohttp` call failures without creating spurious `RuntimeWarning` warnings during the suite.

## [0.5.0] - 2026-08-23
### Added
- **Audio class filters in the Web UI panel**: a new "Audio Class Filters" section with Include / Exclude multi-select dropdowns populated from all 521 YAMNet class names — no more free-text editing of `classifier.include`/`classifier.exclude` in the add-on options. Applying filters persists them to the add-on options and restarts the add-on, using the same response-then-restart contract as the source picker.
- New panel endpoints: `GET /api/class-map` (YAMNet class names, loaded once at startup from `yamnet_class_map.csv`) and `GET/POST /api/classifiers` (read/persist the filter lists; malformed payloads get an explicit 400).

### Fixed
- **Startup no longer stalls for minutes when Home Assistant is slow or unreachable** (reproduced on plain 0.4.5): entity initialisation POSTed default states sequentially, each waiting out its HTTP timeout, which kept the ingress panel offline during that window. Initialisation now runs as a background task; per-call failures were already logged.

## [0.4.5] - 2026-08-23
### Fixed
- **Sources with no audio track no longer hang silently** (confirmed live on HA camera MJPEG proxies): if ffmpeg produces no audio bytes within 20s of connecting, the add-on now raises a clear `no audio received -- stream is likely video-only` condition, logs it loudly, surfaces it in the panel's Recent Detections as `no-audio-source`, and keeps the Web UI available so the source can be changed. Previously the pipeline blocked forever on the first read and the install just looked "quiet".

## [0.4.4] - 2026-08-23
### Changed
- Quiet logs: per-request access lines for the panel's 3-second `/api/detections` polling are filtered out instead of flooding the add-on log
- The "bound without an auth token" warning now fires only for standalone deployments -- behind Home Assistant ingress it was noise on every start
- ~~Add-on manifest enables `watchdog: true`~~ REVERTED before release: this Supervisor build rejects a boolean `watchdog` and refuses to parse the manifest (blocking all updates); recommend enabling Watchdog via the add-on's UI toggle instead
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
