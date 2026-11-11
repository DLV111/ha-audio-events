# syntax=docker/dockerfile:1
FROM python:3.12-slim-bookworm AS builder

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install build tooling only in the builder stage so it is not shipped in the
# final runtime image. BuildKit cache mounts keep apt caches off the layers.
# Debian's stock /etc/apt/apt.conf.d/docker-clean deletes
# /var/cache/apt/archives/*.deb after every apt invocation, which would defeat
# the archives cache mount -- remove it so warm builds reuse downloaded .debs.
# NOTE: no "rm -rf /var/lib/apt/lists/*" here on purpose: the lists live in
# the cache mount (not the layer), and deleting them would wipe the shared
# cache for later builds.
RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt/lists,sharing=locked \
    rm -f /etc/apt/apt.conf.d/docker-clean && \
    apt-get update && \
    apt-get install -y --no-install-recommends build-essential

WORKDIR /deps

# Install Python dependencies before copying source so code changes do not
# invalidate this layer. The BuildKit pip cache mount persists wheels across
# builds; --no-cache-dir (or PIP_NO_CACHE_DIR) must NOT be set here or pip
# bypasses the mount entirely and re-downloads every wheel on each build.
COPY requirements.txt .
RUN --mount=type=cache,target=/root/.cache/pip,sharing=locked \
    python -m pip install --target=/deps -r requirements.txt

# ------------------------------------------------------------------------------
FROM python:3.12-slim-bookworm

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# Runtime system packages only. Audio tooling is required for ffmpeg conversion
# and for interacting with the host's ALSA/PulseAudio devices.
# docker-clean is removed for the same reason as in the builder stage.
RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt/lists,sharing=locked \
    rm -f /etc/apt/apt.conf.d/docker-clean && \
    apt-get update && \
    apt-get install -y --no-install-recommends \
        ffmpeg \
        alsa-utils \
        pulseaudio-utils

WORKDIR /app

# Copy pre-built Python packages from the builder stage into the runtime
# interpreter's site-packages.
COPY --from=builder /deps /usr/local/lib/python3.12/site-packages

# Copy application source, models, and entrypoint last so code changes do not
# invalidate the dependency layers above.
COPY . /app

# Pre-compile application bytecode. PYTHONDONTWRITEBYTECODE=1 (below) keeps
# the runtime filesystem clean, but without shipped __pycache__ CPython would
# recompile every app module on every container start -- a measurable startup
# tax for zero benefit. Compiling at build time keeps starts fast and the
# runtime image read-only-friendly.
RUN python -m compileall -q /app/app

# NOTE: intentionally still running as root -- Home Assistant OS grants audio
# hardware via device nodes / the shared PulseAudio socket whose ownership
# doesn't suit arbitrary unprivileged UIDs, and a non-root user would silently
# break microphone capture.
# NOTE: intentionally no health check -- the only stable probe target (Web UI
# on 8099) is optional and disabled in some configurations; a failing-by-config
# probe is worse than none.

ENTRYPOINT ["/app/run.sh"]
