# HA Audio Events (Home Assistant Add-on)

A Home Assistant add-on and standalone application for real-time audio event detection and sound classification using TensorFlow Lite (specifically **Google YAMNet** via LiteRT).

`ha-audio-events` continuously monitors audio streams—from a host microphone, PulseAudio, RTSP IP camera streams, or audio files—and classifies sounds across 521 audio event categories (such as dog barking, sirens, speech, glass breaking, or trains). When audio events occur, it updates Home Assistant entities and fires events via REST API or MQTT.

---

## Key Features

- **TensorFlow Lite / LiteRT Inference**: High-accuracy sound classification powered by Google's YAMNet 521-class model.
- **Low CPU Activity Filtering**: Built-in Root-Mean-Square (RMS) and peak signal amplitude detection skips inference on quiet audio frames to save CPU resources.
- **Flexible Audio Ingestion**:
  - **Host Microphone / PulseAudio**: Stream live audio directly from local microphone inputs.
  - **RTSP IP Camera Streams**: Decode live camera audio streams (`rtsp://...`) directly using ffmpeg.
  - **Audio Files**: Test and process `.wav`, `.mp3`, `.aac`, `.flac`, or `.mkv` files.
- **Home Assistant REST & MQTT Integrations**:
  - Auto-creates HA binary sensors (`binary_sensor.audio_active`, `binary_sensor.audio_<label>`).
  - Updates sensors (`sensor.last_audio_event`, `sensor.last_audio_confidence`, etc.).
  - Fires `audio_event` events in Home Assistant for automation triggers.
  - Full MQTT Discovery support (`homeassistant/binary_sensor/...`).

---

## Installation in Home Assistant

1. In Home Assistant, navigate to **Settings** -> **Add-ons** -> **Add-on Store**.
2. Click the top-right menu (three dots) -> **Repositories**.
3. Add the repository URL: `https://github.com/DLV111/ha-audio-events`
4. Find **HA Audio Events** in the list and click **Install**.
5. Go to the **Configuration** tab to adjust your audio source and sound detection preferences.
6. Click **Start** and enable **Watchdog** or **Start on boot**.

---

## Audio Source Configuration

`ha-audio-events` supports three primary audio ingestion modes:

### Mode 1: Host Microphone / PulseAudio (Default)
To capture continuous audio from the Home Assistant server's USB microphone or soundcard:
- Leave `audio.source_path: null` (or leave it blank in the UI).
- Ensure **Audio input** permission is toggled on in the Add-on Configuration tab.

### Mode 2: Home Assistant Camera Entity (Recommended for Cameras)
To stream audio directly from any Home Assistant camera entity without entering camera IP addresses or RTSP passwords:
- Set `audio.source_path` to the camera entity ID:
  ```yaml
  audio:
    source_path: "camera.shed_fluent"
  ```
  *(or `camera.shed_clear`)*

### Mode 3: Network RTSP IP Camera Stream
To analyze live audio from a raw RTSP camera stream:
- Set `audio.source_path` to your camera's RTSP stream URL:
  ```yaml
  audio:
    source_path: "rtsp://admin:password@192.168.1.50:554/h264Preview_01_main"
  ```

### Mode 3: Local Audio File (Testing / Demonstration)
To classify audio from a test audio file placed inside `/config`:
- Set `audio.source_path` to the file path:
  ```yaml
  audio:
    source_path: "/config/dog_barking.wav"
  ```

---

## Full Configuration Reference

```yaml
model: yamnet
buffer_seconds: 3.0

audio:
  sample_rate: 16000
  channels: 1
  format: pcm_s16le
  source_path: null     # null = default microphone; or "rtsp://..." or "/config/audio.wav"

activity:
  rms_threshold: 0.04   # Minimum RMS signal strength to trigger model analysis
  peak_threshold: 0.1   # Minimum peak amplitude to trigger model analysis
  hold_time: 2.0        # Seconds to hold activity active after sound drops

classifier:
  threshold: 0.8        # Minimum confidence threshold (0.0 to 1.0)
  max_results: 5        # Top K predictions per frame
  include:              # Whitelist of labels to track (empty = all labels)
    - train
    - dog
    - siren
    - speech
    - thunder
    - glass
  exclude:              # Blacklist of labels to ignore
    - music
    - silence

aggregation:
  start_confidence: 0.85 # Confidence threshold required to start an event
  end_timeout: 5.0      # Seconds of low confidence before ending an event

homeassistant:
  enabled: true
  url: "http://supervisor/homeassistant"
  token: null           # Automatically uses SUPERVISOR_TOKEN inside HA OS add-on
  entity_prefix: "audio"

mqtt:
  enabled: false
  host: "localhost"
  port: 1883
  topic: "audio/events"
  discovery_prefix: "homeassistant"
```

---

## Home Assistant Entities & Events

When `homeassistant.enabled` is `true`, the add-on manages the following entities:

| Entity ID | Type | Description |
| :--- | :--- | :--- |
| `sensor.last_audio_event` | Sensor | Name of the most recently detected sound label (e.g. `dog`, `siren`). |
| `sensor.last_audio_confidence` | Sensor | Confidence score of the last detection (e.g., `0.92`). |
| `binary_sensor.audio_active` | Binary Sensor | `on` when any target sound is actively being detected. |
| `binary_sensor.audio_<label>` | Binary Sensor | `on` when specific tracked label (e.g. `binary_sensor.audio_dog`) is active. |

### Home Assistant Event Automation Example

```yaml
alias: "Notify when dog barks"
trigger:
  - platform: event
    event_type: audio_event
    event_data:
      label: "dog"
condition: []
action:
  - service: notify.notify
    data:
      title: "Audio Event Detected"
      message: "Detected {{ trigger.event.data.label }} with {{ (trigger.event.data.confidence * 100) | round(1) }}% confidence."
```

---

## Local Development & Testing

Run unit & integration tests using Python 3.12+ and `pytest`:

```bash
# Clone the repository
git clone https://github.com/DLV111/ha-audio-events.git
cd ha-audio-events

# Create virtual environment & install dependencies
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

# Run full test suite
pytest -v

# Run classification demo on an audio file
python3 -m app.demo tests/fixtures/audio/train/freight_train_01.wav
```

---

## Troubleshooting

1. **Add-on stops immediately upon start**:
   - Check the **Log** tab in the add-on page.
   - If using host microphone, ensure `Audio input` hardware access is enabled in add-on settings.
   - If using RTSP, check that `source_path` URL is valid and accessible from your Home Assistant network.

2. **No sounds detected**:
   - Check if your sound label is listed under `classifier.include`.
   - Try lowering `activity.rms_threshold` (e.g., to `0.01`) if input signal level is low.
   - Try lowering `classifier.threshold` (e.g., to `0.6`).

3. **Entities not showing up in Home Assistant**:
   - Verify `homeassistant.enabled` is `true`.
   - If using MQTT, ensure `mqtt.enabled` is `true` and broker credentials match.
