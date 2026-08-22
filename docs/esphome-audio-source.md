# Using an ESP32 + microphone as an audio source

The add-on can classify audio from **any URL ffmpeg can read** — which
makes a DIY ESP32 board with an I²S MEMS microphone (e.g. INMP441) an
excellent, cheap detection source for sheds, garages or driveways.
`16 kHz / 16-bit / mono` — the format these setups produce — is exactly
what the YAMNet model wants.

Two ways to get the audio flowing:

| | Option 1: dedicated streamer device | Option 2: same-device ESPHome component |
| :--- | :--- | :--- |
| Effort | Flash ready-made firmware, done | Write/maintain a custom external component |
| Mic contention with HA Voice/Assist | N/A (separate device) | Only if the box also runs Assist |
| Add-on code changes needed | None | None |
| Best for | Quick start / spare board | Boxes whose mic is otherwise idle |

> **Shed-sensor note:** the DIY shed sensor (dB meter + object
> detection) never uses voice features, so Option 2 has no contention
> downside there. If Assist *is* later enabled on it, both still work —
> classification simply pauses during wake-word capture (see below).
> Optionally remove the unused voice blocks (`voice_assistant`,
> `micro_wake_word`, anything creating the `assist_satellite.*` entity)
> so HA stops listing the box under Voice Satellites entirely.

---

## Option 1 (recommended): dedicated ESP32 running streamer firmware

[`jpmurray/esp32-audio-streamer`](https://github.com/jpmurray/esp32-audio-streamer)
is purpose-built for this: it captures mono I²S microphone audio and
serves it over HTTP and RTSP.

### Hardware

- Any ESP32 dev board (WROOM / WROVER / S3 all work)
- INMP441 (or similar) I²S MEMS microphone
- Wiring per the firmware README (SCK/WS/SD + VDD/GND/L/R-to-GND)

### Flash & find the streams

Flash the firmware following its README, then it exposes:

| Stream | URL |
| :--- | :--- |
| WAV over HTTP | `http://<device-ip>:81/stream.wav` |
| Raw PCM over HTTP | `http://<device-ip>:81/stream.pcm` |
| RTSP (TCP-interleaved only) | `rtsp://<device-ip>:8554/audio/` |

> The server allows **one client at a time** — that's fine: the add-on is
> the single consumer.

Verify before wiring into Home Assistant (from any machine on the LAN):

```bash
ffprobe http://192.168.1.60:81/stream.wav
# expect: Stream #0:0: Audio: pcm_s16le, 16000 Hz, mono, s16
```

Give the device a DHCP reservation (or static IP) so the URL never drifts.

### Point the add-on at it

In the add-on configuration panel set:

```yaml
audio:
  source_path: "http://192.168.1.60:81/stream.wav"
```

or, if you prefer RTSP:

```yaml
audio:
  source_path: "rtsp://192.168.1.60:8554/audio/"
```

Save → the add-on restarts → watch the ingress panel's *Recent
Detections* feed. Clap near the mic to test.

### Tuning tips

- If quiet sounds are missed, lower `activity.rms_threshold` (e.g.
  `0.01`) and `classifier.threshold` (e.g. `0.5`).
- If you get spurious events, raise them instead.
- Keep `buffer_seconds` at `3.0` initially.

---

## Option 2: stream from an existing ESPHome device

Stock ESPHome has an `i2s_audio` **microphone**, but no built-in HTTP /
RTSP *server* component — mic audio normally goes to the Assist pipeline
(`voice_assistant` / assist satellites). To serve audio out you need a
custom external component (~100 lines of C++) registering an
`esp_http_server` handler that writes a WAV header and then streams
frames captured via the microphone data-callback API.

A minimal shape of such a component:

```cpp
// components/audio_streamer/audio_streamer.h (sketch — verify APIs
// against your ESPHome version; they move between releases)
class AudioStreamer : public Component {
 public:
  void setup() override {
    id(mic_).add_data_callback([this](const std::vector<uint8_t> &frame) {
      // fan out to every connected HTTP client
      this->broadcast_(frame);
    });
    id(mic_).start();   // continuous capture
    httpd_register_uri_handler(server_, &(httpd_uri_t){
      .uri = "/stream.wav", .method = HTTP_GET,
      .handler = [](httpd_req_t *req) { /* write WAV header, then loop chunks */ },
    });
  }
};
```

```yaml
# shed-sensor.yaml additions
external_components:
  - source:
      type: git
      url: https://github.com/DLV111/ha-audio-events
      ref: main
    components: [audio_streamer]

audio_streamer:
  microphone_id: shed_mic
  port: 8080          # keep clear of web_server (:80)
```

Then in the add-on: `source_path: "http://<shed-ip>:8080/stream.wav"`.

### Sharing the mic with Assist (supported)

Both features can live on one box: Assist keeps priority, and the
streamer simply **pauses while wake-word/voice capture is active and
resumes afterwards**. Guard the broadcast path so it never fights for
the I²S port:

```cpp
void on_mic_frame(const std::vector<uint8_t> &frame) {
    if (!id(mic_).is_running()) return;  // paused: drop silently
    this->broadcast_(frame);
}
```

Clients stay connected across pauses; a few seconds of silence during
voice activity is harmless to classification. If you'd rather not share
at all, remove the voice blocks — but per design decision (2026-08-22)
coexistence with pause-during-wake-word is the intended behaviour.

### Option 1 vs Option 2 — remaining trade-offs

1. **Reliability**: streaming 24/7 from a box that also runs Wi-Fi
   provisioning, sensors, OTA etc. invites underruns; dedicated
   firmware does one thing.
2. **Maintenance**: ESPHome internals (`microphone`, `esp_http_server`
   APIs) shift between releases; standalone firmware isolates you.

If you do build Option 2, keep the current panel behaviour (rejecting
bare `assist_satellite.*` sources with an explanation) until the
component is proven — silently accepting sources that can't deliver
audio is worse than an explicit error.

---

## Troubleshooting

| Symptom | Fix |
| :--- | :--- |
| Add-on log: `Audio stream ended unexpectedly ... Connection refused` | Wrong IP/port, or device asleep. Ping it; check DHCP reservation. |
| Stream connects but zero detections ever | Play a loud sound next to the mic while watching the panel; if still nothing, `ffprobe` the URL and confirm a real PCM stream (not silence). |
| Frequent `ffmpeg stderr:` warnings then dropouts | Wi-Fi congestion or underpowered PSU on the ESP32; try 2.4 GHz channel 1/6/11 and a 500 mA+ supply. |
| `one stream client` errors | Something else (VLC, another instance) is holding the single-client slot. |
