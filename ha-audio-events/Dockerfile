FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1

# Deps are pinned here to match pyproject.toml so container builds don't drift
# from what's tested locally/CI.
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    ffmpeg \
    alsa-utils \
    pulseaudio-utils \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY . /app
RUN pip install --no-cache-dir \
    "aiohttp>=3.9" \
    "numpy>=1.26" \
    "PyYAML>=6.0" \
    "paho-mqtt>=2.1,<3.0" \
    "ai-edge-litert>=2.1.0,<3.0.0"
# LiteRT is the new runtime for TensorFlow Lite and is API-compatible with
# the TensorFlow Lite Interpreter API used by YAMNetClassifier.

# NOTE: intentionally still running as root -- Home Assistant OS grants audio
# hardware via device nodes / the shared PulseAudio socket whose ownership
# doesn't suit arbitrary unprivileged UIDs, and a non-root user would silently
# break microphone capture.
# NOTE: no HEALTHCHECK -- the only stable probe target (Web UI on 8099) is
# optional and disabled in some configurations; a failing-by-config health
# check is worse than none.

ENTRYPOINT ["/app/run.sh"]
