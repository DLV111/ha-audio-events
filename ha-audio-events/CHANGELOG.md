# Changelog

All notable changes to this add-on will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.6.0] - 2026-11-03
### Changed
- Secure RTSP credentials: passwords masked in logs, stored via Supervisor options (audio.streams map), multi-stream support
- Branch protection guard: enforces PR base=develop, blocks main→develop pushes
- CI job renamed to `Test Suite (3.12)`
- .gitignore hardening: config.yaml secrets exposure blocked
### Fixed
- RTSP log line no longer exposes passwords in clear text
- Web UI source path display masks password portion
- Backward-compatible: inline source_path URLs with username:password@ still supported

## [0.9.0] - 2026-10-26
### Added
- A real `silence` event is emitted after 5 seconds without activity by default.
- The timeout is tunable with `activity.silence_timeout`; sound immediately ends the silence event.

## [0.8.0] - 2026-10-19
### Added
- The Audio Class Filters picker now **filters both panes as you type**: typing in the search box narrows the Available and Accepted lists by class-name substring. Previously the query was stored in state but `filterState()` was never called by the renderer, so the lists never change.
- Search and category chips combine (AND): a query only shows matches inside the selected AudioSet category.
- A live, `aria-live` result count reports how many classes are available/selected under the current search and category filter.
- Keyboard navigation for both lists: Arrow Up/Down move between rows, Home/End jump, Space/Enter toggle the focused row.
- Phones get a segmented **Browse / Selected** view, a full-width search box, and touch targets of at least 44px for rows, category chips and buttons.

### Changed
- The picker renderer and styles were extracted from the inline code in `server.py` into `app/webui/static/picker.js` and `app/webui/static/picker.css`; the page now only fetches data and mounts the pickers.
- The byte-identical duplicate `app/webui/transfer_picker.js` was removed. `app/webui/static/transfer_picker.js` is the single source of truth, and the Node test now targets it.
- Group headers and label rows are siblings in the DOM. Labels no longer sit inside the flex group header, which previously produced a large empty gutter and a header hundreds of pixels tall.

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



## [0.10.0] - 2026-11-03
### Changed
- Version bump (0.9.0 → 0.10.0)
