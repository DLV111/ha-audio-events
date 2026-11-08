# syntax=docker/dockerfile:1
FROM python:3.12-slim-bookworm AS builder

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install build tooling only in the builder stage so it is not shipped in the
# final runtime image. BuildKit cache mounts keep apt caches off the layers.
RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt/lists,sharing=locked \
    apt-get update && \
    apt-get install -y --no-install-recommends build-essential && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /deps

# Install Python dependencies before copying source so code changes do not
# invalidate this layer. BuildKit pip cache mount speeds rebuilds.
COPY requirements.txt .
RUN --mount=type=cache,target=/root/.cache/pip,sharing=locked \
    python -m pip install --no-cache-dir --target=/deps -r requirements.txt

# ------------------------------------------------------------------------------
FROM python:3.12-slim-bookworm

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# Runtime system packages only. Audio tooling is required for ffmpeg conversion
# and for interacting with the host's ALSA/PulseAudio devices.
RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt/lists,sharing=locked \
    apt-get update && \
    apt-get install -y --no-install-recommends \
        ffmpeg \
        alsa-utils \
        pulseaudio-utils && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy pre-built Python packages from the builder stage into the runtime
# interpreter's site-packages.
COPY --from=builder /deps /usr/local/lib/python3.12/site-packages

# Copy application source, models, and entrypoint last so code changes do not
# invalidate the dependency layers above.
COPY . /app

# NOTE: intentionally still running as root -- Home Assistant OS grants audio
# hardware via device nodes / the shared PulseAudio socket whose ownership
# doesn't suit arbitrary unprivileged UIDs, and a non-root user would silently
# break microphone capture.
# NOTE: intentionally no health check -- the only stable probe target (Web UI
# on 8099) is optional and disabled in some configurations; a failing-by-config
# probe is worse than none.

ENTRYPOINT ["/app/run.sh"]
