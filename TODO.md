# Backlog & Known Issues

Working list of open items from the 2026-08-22 live-debugging session.
Context: add-on v0.4.2 shipped via PRs #14–#17; live instance is
`ce06deeb_ha_audio_events` on the author's HA box.

---

## 🔴 Urgent — live install housekeeping

> ✅ RESOLVED 2026-08-23: production options restored; v0.4.3+ deployed.

### 1. Restore production options (left in test state)

The end-to-end detection test boosted sensitivity and never got reverted,
and the source was switched to a failing camera during testing.

Current (test) values on the live install:

| Option | Test value now | Production value to restore |
| :--- | :--- | :--- |
| `activity.rms_threshold` | `0.001` | `0.02` |
| `activity.peak_threshold` | `0.001` | `0.08` |
| `activity.hold_time` | `0.5` | `2.0` |
| `classifier.threshold` | `0.1` | `0.6` |
| `classifier.include` | `[]` | `[train, dog, thunder, siren, speech]` |
| `classifier.exclude` | `[]` | `[music, silence]` |
| `aggregation.start_confidence` | `0.1` | `0.85` |
| `aggregation.end_timeout` | `2.0` | `5.0` |
| `audio.source_path` | `camera.shed_fluent` (returns HTTP 5XX) | `camera.garage_camera` |

The add-on is currently in Supervisor state `error` (process dead). After
restoring options, start it and confirm `state: started`.

---

## 🐛 Bugs to investigate

### 2. ✅ FIXED (PR #19, v0.4.3) — Container died despite "webui survives pipeline failure" design

v0.4.2's `_run_pipeline` catches `_detect()` exceptions and keeps serving
the Web UI so users can fix a bad source from the panel. Despite that, the
container ended up in state `error` after ffmpeg hit the 5XX below —
something exited the whole process anyway.

Suspects to check:
- exception raised *outside* the detect task (e.g. `init_entities`, HA
  client timeout storm, aiohttp session closed mid-flight)
- interaction between the delayed-restart task (`asyncio.create_task`) and
  asyncio.run teardown
- Supervisor-side restart/stop semantics racing our own restart call

Action: reproduce with a deliberately 5XX-ing source, capture full log +
traceback, fix, add a container-level regression test.

### 3. ✅ VERIFIED NON-ISSUE — Bare ffmpeg stderr bypassed the stderr drain

Log showed `Error opening input files: Server returned 5XX Server Error
reply` **without** the `app.audio.stream: ffmpeg stderr:` prefix — i.e. it
reached container stderr directly instead of going through our
`stderr=PIPE` + drain task.

Hypotheses:
- deployed container image was built from stale/cached layers predating
  PR #14's drain change (verify the running image actually contains the
  drain code)
- a second spawn path somewhere that still inherits stderr

Action: verify image provenance; grep all `create_subprocess_exec` sites;
add a test asserting ffmpeg output always goes through `_drain_stderr`.

### 4. 🟡 FIX SHIPPED v0.4.5 (PR pending merge) — Camera proxy stream reliability / missing audio track

Neither `camera.garage_camera` nor `camera.shed_fluent` produced a single
detection even with near-zero thresholds over several minutes, and
`shed_fluent` intermittently returns 5XX from `/api/camera_proxy_stream/`.
Strong suspicion: HA's camera proxy serves MJPEG (video-only) for these
integrations, so there is literally no audio to classify.

Findings (2026-08-23 live test): garage/shed proxies deliver ZERO audio bytes
(even rms_threshold=0 produced nothing) while ffmpeg stays connected --
video-only MJPEG confirmed. First-byte-timeout guard shipped in v0.4.5.

Actions:
- probe the resolved stream for an audio track before/at start; if absent,
  fail loudly AND show it in the Web UI ("this source has no audio track")
  instead of silently classifying nothing
- document recommended setups that actually carry audio (direct RTSP URL
  from the camera, or routing through go2rtc)
- consider bounded retry with backoff on 5XX rather than one attempt then
  zombie-silence

---

## ✨ Improvements

### 5. No-detection observability

Users cannot tell "working but quiet" apart from "silently broken".
Ideas: heartbeat sensor (`sensor.audio_last_analysis` timestamp),
bytes-received indicator in the panel, activity-gate statistics at debug
log level.

### 6. ✅ FIXED (PR #20, v0.4.4) — Web UI auth warning is noisy behind ingress

`WARNING: Web UI is bound to 0.0.0.0 without an auth token...` fires on
every start even though ingress protects the port in add-on context.
Suppress when running under Supervisor (detect ingress/SUPERVISOR_TOKEN);
keep the warning for standalone deployments.

### 7. ✅ DOCUMENTED (PR #20) — Ingress retry dialog after restarts

Browser showed HA's "The app seems to not be ready" dialog repeatedly
around restarts. Mostly genuine downtime, but worth documenting
("reload the panel after changing sources") and checking whether stale
ingress tokens contribute.

### 8. Legacy url/token fields still render for existing installs

Schema keeps `homeassistant.url`/`token` (`str?`) so old saved options
validate; existing installs therefore still see those fields in the UI
(with the healed value). Once the installed base has migrated, drop them
from the schema entirely.

### 9. ⚠️ PARTIALLY REVERTED — Watchdog/boot defaults

`watchdog: true` in the manifest caused this Supervisor build to fail
manifest parsing (`expected string or buffer ... Got True`), detaching
the add-on from the store and blocking ALL updates. Reverted in
fix/watchdog-manifest-schema. Reintroduce only after verifying the
accepted schema type (possibly string "true") against the pinned
Supervisor version; meanwhile users enable Watchdog via the UI toggle.

Live install has `boot: manual` + `watchdog: false`, so any crash leaves
the add-on down silently until noticed. Recommend `watchdog: true` in
README/docs (and consider manifest default).

### 10. ✅ FIXED (PR #20) — Log noise from panel polling

`aiohttp.access` INFO lines every ~3 s flood the add-on log while the
panel is open. Filter access logs for `/api/detections` or raise their
level.

---

---

## 🧪 Verification gaps

### 11. ⚠️ BLOCKED ON SOURCE — End-to-end detection never confirmed on live install

Entities get created and REST calls work, but an actual
detection → `audio.detected` event → `sensor.audio_last_audio_event`
state change has never been observed live. Re-run the sensitivity-boost
test once a source with a real audio track is configured, then revert.

### 12. MQTT integration never tested against a broker

Discovery + state publishing paths are unit-tested only. Do one manual
verification with Mosquitto.

### 13. CI gap: no container test for the camera-entity path

Container smoke tests exercise WAV files only. The failure modes seen
live (proxy 5XX, no-audio-track, restart races) have zero automated
coverage. Mock the Supervisor camera proxy in a container test.

---

## 🚀 Feature: ESPHome / assist_satellite microphone support

### 14. Support custom ESP32 hardware as a detection source

Goal: use the DIY **shed sensor** (ESP32 + I2S microphone, exposed in HA
as `assist_satellite.backyard_shed_sensor_assist_satellite`) as an audio
source. The panel currently lists it under "Voice Satellites (not yet
supported)" and `set_source` rejects `assist_satellite.*` with an
explanation — HA doesn't expose a pull-able stream for Assist satellites
because their audio is pushed into the Assist pipeline over ESPHome's
native protocol.

Two realistic implementation paths:

**Path A — near-term (dedicated streamer device):**
- [`jpmurray/esp32-audio-streamer`](https://github.com/jpmurray/esp32-audio-streamer)
  already does this: I2S mic → `http://<ip>:81/stream.wav` /
  `rtsp://<ip>:8554/audio/`, both consumable by the add-on's ffmpeg
  ingestion today with zero code changes
- Full write-up now in `docs/esphome-audio-source.md` (hardware,
  flashing, addon config, verification, troubleshooting)
- Remaining work: user builds/flashes the device; optionally add an
  "ESP32 device URL" source-type hint to the panel picker

**Path B — long-term (same-device ESPHome component):**
- Stock ESPHome has no HTTP/RTSP *server* for mic audio; requires a
  custom external component (~100 lines C++, sketch included in
  `docs/esphome-audio-source.md`)
- Mic sharing with Assist is acceptable per user decision
  (2026-08-22): the device was never meant for the Assist pipeline, and
  pausing classification during wake-word capture is fine — the
  component just needs to pause/resume gracefully

---

## 🧭 Phase 2: multi-source / multi-consumer architecture

### 15. Scale from one pipeline to N sources and fan-out consumers

Today exactly one audio source feeds one detection chain
(`_run_pipeline` in `app/main.py` builds a single
`AudioStreamSource → CircularAudioBuffer → ActivityDetector →
YAMNetClassifier → EventAggregator` sequence). Phase 2 generalises this.

**Multi-source (N capture pipelines):**
- Config becomes `sources: [...]`, each entry with its own
  `name`/`source_path` and optional per-source overrides for activity /
  classifier thresholds; keep the existing singular `audio:` block as
  sugar for a single unnamed source (back-compat)
- One asyncio task per source, each with its own buffer/detector/
  aggregator and **its own TFLite interpreter instance** (interpreters
  are not thread-safe); N is small (≤ ~8), so RAM/CPU stays sane on HAOS
  hardware — add a config cap plus sequential-inference scheduling if
  measurements show contention
- The ESP32 streamer firmware is single-client, which fits perfectly:
  one connection per device, one device per source

**Entity & event model changes:**
- Every event gains a `source` field (`EventMessage`, `audio.detected`
  payload, MQTT JSON, webui rows)
- Entities become per-source: `binary_sensor.audio_<source>_<label>`;
  when only one (unnamed) source exists, keep today's un-suffixed IDs so
  existing installs see no change
- MQTT discovery payloads register per-source entities; webui groups
  Recent Detections by source

**Multi-consumer event fan-out:**
- REST `fire_event` already reaches every HA automation listening to
  `audio.detected`; MQTT already fans out via broker subscriptions — so
  "consumers" mostly means *more output channels*, e.g. optional webhook
  targets list (`webhooks: [url,...]`) posted on every event, and the
  panel's `/api/detections` gaining a source filter param

**Suggested milestones:**
1. Thread `source` through EventMessage + publishers (single source,
   value `"default"` — no behaviour change, schema ready)
2. `sources:` config + N-pipeline runner behind the existing single-
   source path when length ≤ 1
3. Per-source entities/discovery/webui grouping
4. Webhook consumer option + docs

Open questions: CPU budget per extra interpreter on low-end boxes;
whether per-source classifiers need independent include/exclude lists or
share one; how the source picker UI edits a list cleanly.

---

## Session context (for whoever picks this up)

- Merged: #14 (v0.3.0 hardening), #15 (v0.4.0 usability/self-heal),
  #16 (v0.4.1 null-defaults), #17 (v0.4.2 webui resilience).
- Live diagnosis done via HA MCP tools (`ha_get_app`,
  `ha_get_logs source=supervisor slug=...`, `ha_manage_app`).
- Local repo: `develop` synced through #17; feature branches deleted;
  this file intentionally left uncommitted for review.
