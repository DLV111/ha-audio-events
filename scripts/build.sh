#!/usr/bin/env bash
# Build the HA Audio Events container image with BuildKit caching.
#
# This script keeps local and CI builds consistent: it auto-detects Docker or
# Podman, enables BuildKit (Docker), and applies the same cache-from/cache-to
# settings everywhere. Cache behaviour is controlled through environment
# variables documented below.
#
# Environment variables:
#   CONTAINER_ENGINE    - "docker" or "podman" (auto-detected if unset)
#   IMAGE_NAME          - image name/tag (default: ha-audio-events-test)
#   BUILD_CONTEXT       - path passed to the build command (default: ./ha-audio-events)
#   BUILD_CACHE_FROM    - BuildKit cache-from value(s). Multiple sources can be
#                         separated with ';', e.g.
#                         "type=gha" or "type=registry,ref=ghcr.io/...:cache"
#   BUILD_CACHE_TO      - BuildKit cache-to value, e.g.
#                         "type=gha,mode=max" or "type=registry,ref=...,mode=max"
#   BUILDKIT_INLINE_CACHE - set to "1" to embed cache metadata in the image
#   BUILDKIT_PROGRESS   - BuildKit progress output (default: plain)
#   PUSH_IMAGE          - set to "true" to push the image after build
#   DRY_RUN             - set to "true" to print the build command instead of running it
#
# Examples:
#   # Default local build with layer caching
#   ./scripts/build.sh
#
#   # CI build using GitHub Actions cache
#   BUILD_CACHE_FROM=type=gha BUILD_CACHE_TO=type=gha,mode=max ./scripts/build.sh
#
#   # CI build using a registry cache image
#   BUILD_CACHE_FROM=type=registry,ref=ghcr.io/dlv111/ha-audio-events:cache \
#   BUILD_CACHE_TO="type=registry,ref=ghcr.io/dlv111/ha-audio-events:cache,mode=max" \
#     ./scripts/build.sh

set -euo pipefail

IMAGE_NAME="${IMAGE_NAME:-ha-audio-events-test}"
BUILD_CONTEXT="${BUILD_CONTEXT:-./ha-audio-events}"
BUILDKIT_PROGRESS="${BUILDKIT_PROGRESS:-plain}"
PUSH_IMAGE="${PUSH_IMAGE:-false}"
DRY_RUN="${DRY_RUN:-false}"

# Auto-detect container engine if not explicitly set.
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

if [ "$CONTAINER_ENGINE" != "docker" ] && [ "$CONTAINER_ENGINE" != "podman" ]; then
    echo "ERROR: CONTAINER_ENGINE must be 'docker' or 'podman' (got '$CONTAINER_ENGINE')" >&2
    exit 1
fi

echo "Building with $CONTAINER_ENGINE: $IMAGE_NAME"

build_cmd=()
skip_cache_export=false
use_buildx=false

if [ "$CONTAINER_ENGINE" = "docker" ]; then
    export DOCKER_BUILDKIT=1
    export BUILDKIT_PROGRESS="$BUILDKIT_PROGRESS"

    # Some systems ship a 'docker' binary that is really a Podman compatibility
    # shim. BuildKit-specific cache export/import (e.g. type=gha) won't work
    # there, so detect the real backend and fall back to plain layer caching.
    docker_backend=$(docker --version 2>/dev/null || true)
    buildx_backend=$(docker buildx version 2>/dev/null || true)
    if echo "$docker_backend $buildx_backend" | grep -qiE "podman|buildah"; then
        echo "INFO: docker command is backed by Podman; using layer caching only" >&2
        build_cmd=(docker build)
        skip_cache_export=true
    elif docker buildx version >/dev/null 2>&1; then
        build_cmd=(docker buildx build)
        use_buildx=true
    else
        echo "WARNING: docker buildx unavailable; falling back to 'docker build'" >&2
        build_cmd=(docker build)
        skip_cache_export=true
    fi
else
    build_cmd=(podman build)
    skip_cache_export=true
fi

build_cmd+=("-t" "$IMAGE_NAME")

# Inline cache metadata lets a pulled image serve as a cache source for
# subsequent builds without needing a separate cache registry.
if [ "${BUILDKIT_INLINE_CACHE:-}" = "1" ]; then
    build_cmd+=("--build-arg" "BUILDKIT_INLINE_CACHE=1")
fi

# Add cache-from sources. Multiple sources can be separated with ';'.
if [ "$skip_cache_export" != "true" ] && [ -n "${BUILD_CACHE_FROM:-}" ]; then
    IFS=';' read -ra cache_from_list <<< "$BUILD_CACHE_FROM"
    for cache_from in "${cache_from_list[@]}"; do
        # Trim whitespace
        cache_from=$(echo "$cache_from" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')
        [ -n "$cache_from" ] || continue
        build_cmd+=("--cache-from" "$cache_from")
    done
fi

# Add cache-to destination (Docker buildx / recent Podman).
if [ "$skip_cache_export" != "true" ] && [ -n "${BUILD_CACHE_TO:-}" ]; then
    build_cmd+=("--cache-to" "$BUILD_CACHE_TO")
fi

# Podman needs --layers to ensure layer caching is used.
if [ "$CONTAINER_ENGINE" = "podman" ]; then
    build_cmd+=("--layers")
fi

# Load the built image into the local engine unless we are pushing it.
if [ "$PUSH_IMAGE" != "true" ] && [ "$use_buildx" = "true" ]; then
    build_cmd+=("--load")
fi

build_cmd+=("$BUILD_CONTEXT")

if [ "$PUSH_IMAGE" = "true" ]; then
    if [ "$use_buildx" = "true" ]; then
        build_cmd+=("--push")
    else
        echo "ERROR: PUSH_IMAGE=true is only supported with docker buildx" >&2
        exit 1
    fi
fi

if [ "$DRY_RUN" = "true" ]; then
    echo "DRY_RUN: ${build_cmd[*]}"
    exit 0
fi

exec "${build_cmd[@]}"
