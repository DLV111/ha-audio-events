#!/usr/bin/env bash
# Validate the contents of the built ha-audio-events container image.
#
# Guards the multi-stage optimized image against regressions in image
# contents and startup behaviour (see docs/container-build-validation.md).
# Complements `make test-container` / `make test-container-webui`, which
# exercise end-to-end behaviour; this script checks what is (and is not)
# shipped inside the image.
#
# Usage:
#   ./scripts/validate_container_contents.sh [IMAGE]
#     IMAGE defaults to ha-audio-events-test.
#
# Exit code is non-zero if any check fails.

set -euo pipefail

IMAGE="${1:-ha-audio-events-test}"

if [ -z "${CONTAINER_ENGINE:-}" ]; then
    if command -v docker >/dev/null 2>&1; then
        CONTAINER_ENGINE="docker"
    elif command -v podman >/dev/null 2>&1; then
        CONTAINER_ENGINE="podman"
    else
        echo "ERROR: no container engine found (docker or podman required)" >&2
        exit 1
    fi
fi

pass=0
fail=0

report() {
    local status="$1" what="$2" detail="${3:-}"
    if [ "$status" = "pass" ]; then
        pass=$((pass + 1))
        printf '  PASS  %s %s\n' "$what" "$detail"
    else
        fail=$((fail + 1))
        printf '  FAIL  %s %s\n' "$what" "$detail"
    fi
}

# run_in_image CMD... -- run a command inside the image, exit code available.
run_in_image() {
    "$CONTAINER_ENGINE" run --rm --entrypoint /bin/bash "$IMAGE" -lc "$*" \
        >/dev/null 2>&1
}

check_contains() {
    local what="$1" cmd="$2"
    if run_in_image "$cmd"; then
        report pass "$what"
    else
        report fail "$what" "(command failed: $cmd)"
    fi
}

check_absent() {
    local what="$1" cmd="$2"
    if run_in_image "$cmd"; then
        report fail "$what" "(command unexpectedly succeeded: $cmd)"
    else
        report pass "$what"
    fi
}

if ! "$CONTAINER_ENGINE" image exists "$IMAGE" 2>/dev/null \
    && ! "$CONTAINER_ENGINE" image inspect "$IMAGE" >/dev/null 2>&1; then
    echo "ERROR: image not found: $IMAGE" >&2
    echo "Build it first: make build-container" >&2
    exit 1
fi

size_bytes="$("$CONTAINER_ENGINE" image inspect "$IMAGE" --format '{{.Size}}')"
size_human="$(numfmt --to=iec-i --suffix=B "$size_bytes" 2>/dev/null || echo "${size_bytes}B")"

echo "Validating image: $IMAGE ($size_human)"
echo ""

echo "== runtime tooling present =="
check_contains "ffmpeg executable" "command -v ffmpeg"
check_contains "ffmpeg runs" "ffmpeg -version"
check_contains "alsa-utils (arecord)" "command -v arecord"
check_contains "pulseaudio-utils (pactl)" "command -v pactl"

echo ""
echo "== Python runtime and dependencies =="
check_contains "python3 present" "python3 --version"
check_contains "python 3.12" "python3 -c 'import sys; sys.exit(0 if sys.version_info[:2] == (3, 12) else 1)'"
check_contains "numpy importable" "python3 -c 'import numpy'"
check_contains "aiohttp importable" "python3 -c 'import aiohttp'"
check_contains "yaml importable" "python3 -c 'import yaml'"
check_contains "paho-mqtt importable" "python3 -c 'import paho.mqtt.client'"
check_contains "ai-edge-litert importable" "python3 -c 'import ai_edge_litert.interpreter'"

echo ""
echo "== application payload =="
check_contains "app package present" "test -f /app/run.sh && test -d /app/app"
check_contains "app entrypoint runnable" "test -x /app/run.sh"
check_contains "default config.yaml present" "test -f /app/config.yaml"
check_contains "YAMNet model present" "test -s /app/models/yamnet.tflite"
check_contains "YAMNet class map present" "test -s /app/models/yamnet_class_map.csv"
check_contains "class groups present" "test -s /app/models/class_groups.json"
check_contains "yamnet groups present" "test -s /app/models/yamnet_groups.json"
check_contains "translations present" "test -d /app/translations"
check_contains "webui assets present" "test -d /app/app/webui"

echo ""
echo "== build hygiene =="
check_absent "no build-essential/gcc in runtime" "command -v gcc || command -v g++ || command -v make"
check_absent "no pip cache in image" "test -d /root/.cache/pip"
check_absent "no apt lists committed to layers" "test -d /var/lib/apt/lists && test -n \"\$(ls -A /var/lib/apt/lists)\""
check_contains "app bytecode precompiled" "test -d /app/app/__pycache__"
check_absent "no CHANGELOG.md shipped" "test -e /app/CHANGELOG.md"

echo ""
echo "== startup behaviour =="
check_contains "entrypoint forwards args" "grep -q 'exec \"\$@\"' /app/run.sh"
check_contains "PYTHONDONTWRITEBYTECODE set" "env | grep -q PYTHONDONTWRITEBYTECODE"
check_contains "PYTHONUNBUFFERED set" "env | grep -q PYTHONUNBUFFERED"

echo ""
echo "================================================"
echo "Image size: $size_human ($size_bytes bytes)"
echo "Results:    $pass passed, $fail failed"
echo "================================================"

[ "$fail" -eq 0 ]
