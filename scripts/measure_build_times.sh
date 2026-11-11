#!/usr/bin/env bash
# Measure container build times for cold/warm scenarios.
#
# Used to validate the optimized Dockerfile against the pre-optimization
# baseline (see docs/container-build-validation.md). Each scenario builds from
# a snapshot of the build context so the working tree is never modified.
#
# Scenarios:
#   cold                  Clean environment: layer cache ignored (--no-cache)
#                         AND BuildKit cache mounts (apt/pip) cleared.
#   warm                  No change since the previous build (all layers hit).
#   warm-source-change    A source file changed (app/main.py) -> only layers
#                         after the source COPY may rebuild.
#   warm-deps-change      requirements.txt changed -> dependency layers must
#                         re-run (wheels may still come from the pip cache
#                         mount). Skipped when the context has no
#                         requirements.txt (pre-optimization baseline).
#   warm-no-layer-cache   Layer cache cleared (--no-cache) but BuildKit cache
#                         mounts kept warm. Shows how much apt/pip downloads
#                         the cache mounts save when layers must rebuild
#                         (e.g. after a base-image bump or CI cache miss).
#
# Usage:
#   ./scripts/measure_build_times.sh                       # standard set
#   ./scripts/measure_build_times.sh --scenarios cold
#   ./scripts/measure_build_times.sh --context ./ha-audio-events --json out.json
#
# Environment variables:
#   CONTAINER_ENGINE  - docker or podman (auto-detected if unset)
#   IMAGE_TAG          - tag for the built image (default: ha-audio-events-bench)
#
# The script never pushes or runs the image. Unless --keep-image is passed the
# measured image is removed again on exit.

set -euo pipefail

CONTEXT_DEFAULT="./ha-audio-events"
TAG_DEFAULT="ha-audio-events-bench"
STANDARD_SCENARIOS="cold,warm,warm-source-change,warm-deps-change"
ALL_SCENARIOS="${STANDARD_SCENARIOS},warm-no-layer-cache"

usage() {
    cat <<'EOF'
Usage: scripts/measure_build_times.sh [OPTIONS]

Options:
  -c, --context DIR      Build context to measure (default: ./ha-audio-events)
  -t, --tag NAME         Image tag to build (default: ha-audio-events-bench)
  -s, --scenarios LIST   Comma-separated scenarios, "standard" or "all"
                         (default: standard = cold,warm,warm-source-change,
                          warm-deps-change)
      --json PATH        Also write results as JSON to PATH
      --keep-image       Keep the measured image instead of removing it
      --dry-run          Print what would run without building
  -h, --help             Show this help

Scenarios:
  cold                  clean layers + cleared BuildKit cache mounts
  warm                  rebuild with no changes
  warm-source-change    rebuild after editing app/main.py
  warm-deps-change      rebuild after editing requirements.txt
  warm-no-layer-cache   --no-cache rebuild with warm BuildKit cache mounts
EOF
}

CONTEXT="${CONTEXT_DEFAULT}"
TAG="${TAG_DEFAULT}"
SCENARIOS="standard"
JSON_PATH=""
KEEP_IMAGE=false
DRY_RUN=false

while [ "$#" -gt 0 ]; do
    case "$1" in
        -c|--context) CONTEXT="${2:?--context requires a value}"; shift 2 ;;
        -t|--tag) TAG="${2:?--tag requires a value}"; shift 2 ;;
        -s|--scenarios) SCENARIOS="${2:?--scenarios requires a value}"; shift 2 ;;
        --json) JSON_PATH="${2:?--json requires a value}"; shift 2 ;;
        --keep-image) KEEP_IMAGE=true; shift ;;
        --dry-run) DRY_RUN=true; shift ;;
        -h|--help) usage; exit 0 ;;
        *) echo "ERROR: unknown option: $1" >&2; usage >&2; exit 1 ;;
    esac
done

case "$SCENARIOS" in
    standard) SCENARIOS="$STANDARD_SCENARIOS" ;;
    all) SCENARIOS="$ALL_SCENARIOS" ;;
esac

# --------------------------------------------------------------------------
# Engine detection (mirrors scripts/build.sh).
# --------------------------------------------------------------------------
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

BUILD_CMD=("$CONTAINER_ENGINE" "build")
# A 'docker' binary backed by Podman (compat shim) cannot use BuildKit cache
# export, but layer caching and RUN --mount=type=cache still work.
ENGINE_FLAVOR="$($CONTAINER_ENGINE --version 2>/dev/null || true)"
case "$CONTAINER_ENGINE" in
    docker)
        if echo "$ENGINE_FLAVOR" | grep -qiE "podman|buildah"; then
            ENGINE_FLAVOR="docker-shim(podman)"
        fi
        ;;
    podman) ;;
    *) echo "ERROR: CONTAINER_ENGINE must be 'docker' or 'podman'" >&2; exit 1 ;;
esac

# Extra flags every build gets: podman (and the docker shim) needs --layers
# to reuse intermediate layers.
EXTRA_BUILD_FLAGS=()
if [ "$CONTAINER_ENGINE" = "podman" ] || [ "$ENGINE_FLAVOR" = "docker-shim(podman)" ]; then
    EXTRA_BUILD_FLAGS+=("--layers")
fi

image_size_bytes() {
    "$CONTAINER_ENGINE" image inspect "$TAG" --format '{{.Size}}' 2>/dev/null || echo ""
}

image_size_human() {
    local bytes
    bytes="$(image_size_bytes)"
    [ -n "$bytes" ] || { echo "unknown"; return; }
    numfmt --to=iec-i --suffix=B "$bytes" 2>/dev/null || echo "${bytes}B"
}

# --------------------------------------------------------------------------
# BuildKit cache-mount management.
#
# RUN --mount=type=cache data lives outside the layer cache:
#   * podman/buildah (rootless): <tmpdir>/buildah-cache-<uid>/ where <tmpdir>
#     is the engine's resolved image-copy tmp dir ('podman info' reports it as
#     .ImageCopyTmpDir); it honours containers.conf's image_copy_tmp_dir and
#     $TMPDIR, and defaults to /var/tmp. Clearing /var/tmp alone therefore
#     misses the cache whenever image_copy_tmp_dir is redirected.
#   * real docker/buildx: builder state, cleared via 'docker builder prune'
# --------------------------------------------------------------------------
resolve_buildah_tmpdir() {
    local tmp
    tmp="$($CONTAINER_ENGINE info --format '{{.ImageCopyTmpDir}}' 2>/dev/null | tr -d '[:space:]')"
    if [ -z "$tmp" ]; then
        tmp="${TMPDIR:-/var/tmp}"
    fi
    printf '%s' "$tmp"
}

clear_buildkit_mount_caches() {
    if [ "$ENGINE_FLAVOR" = "docker-shim(podman)" ] || [ "$CONTAINER_ENGINE" = "podman" ]; then
        local tmpdir dir
        tmpdir="$(resolve_buildah_tmpdir)"
        BUILDKIT_MOUNT_CACHE_DIRS=("$tmpdir/buildah-cache-$(id -u)")
        for dir in "${BUILDKIT_MOUNT_CACHE_DIRS[@]}"; do
            if [ "$DRY_RUN" = "true" ]; then
                echo "    would clear buildah cache mounts: $dir"
            elif [ -d "$dir" ]; then
                rm -rf "$dir"
                echo "    cleared buildah cache mounts: $dir"
            else
                echo "    no buildah cache mounts present: $dir"
            fi
        done
    else
        # Real Docker: build cache (including cache mounts) lives in the
        # buildx builder state. Prune without touching images.
        if $DRY docker builder prune --all --force >/dev/null 2>&1; then
            echo "    cleared docker buildx build cache (incl. cache mounts)"
        else
            echo "    WARNING: could not clear docker buildx cache; 'cold' may not be fully cold" >&2
        fi
    fi
}

# --------------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------------
now_seconds() { date +%s.%N; }

elapsed_seconds() {
    awk -v start="$1" -v end="$2" 'BEGIN { printf "%.1f", end - start }'
}

# Shell-word prefix prepended to commands. Empty in normal runs; set to
# 'echo DRY-RUN:' when --dry-run is requested so commands are printed
# instead of executed.
DRY=""
if [ "$DRY_RUN" = "true" ]; then
    DRY="echo DRY-RUN:"
fi

# Results accumulator (scenario|seconds|image_bytes|image_size_human)
RESULTS=()
record_result() {
    local scenario="$1" seconds="$2" bytes="$3" human="$4"
    RESULTS+=("${scenario}|${seconds}|${bytes}|${human}")
    if [ "$seconds" = "skipped" ]; then
        printf '  %-22s     skipped\n' "$scenario"
    else
        printf '  %-22s %8s s   image: %s\n' "$scenario" "$seconds" "$human"
    fi
}

json_escape() {
    # Minimal JSON string escaping for the fixed strings we emit.
    printf '%s' "$1" | sed 's/\\/\\\\/g; s/"/\\"/g'
}

# Copy the context so scenario file edits never touch the working tree.
snapshot_context() {
    local dest="$1"
    if [ "$DRY_RUN" = "true" ]; then
        echo "DRY-RUN: cp -a $CONTEXT -> $dest"
        mkdir -p "$dest"
        return
    fi
    cp -a "$CONTEXT" "$dest"
}

# Append a marker line to a file inside the snapshot context.
append_marker() {
    local file="$1" line="$2"
    if [ "$DRY_RUN" = "true" ]; then
        echo "DRY-RUN: appending marker line to $file"
        return
    fi
    printf '%s\n' "$line" >> "$file"
}

# Build once (unmeasured) so layers/mounts are warm.
prime() {
    local ctx="$1" label="$2"
    echo "  [$label] priming build (unmeasured)..."
    if [ "$DRY_RUN" = "true" ]; then
        $DRY "${BUILD_CMD[@]}" "${EXTRA_BUILD_FLAGS[@]}" -t "$TAG" "$ctx"
    else
        "${BUILD_CMD[@]}" "${EXTRA_BUILD_FLAGS[@]}" -t "$TAG" "$ctx" >/dev/null
    fi
}

timed_build() {
    local ctx="$1" label="$2" scenario="$3"
    shift 3
    local start end seconds
    start="$(now_seconds)"
    if [ "$DRY_RUN" = "true" ]; then
        $DRY "${BUILD_CMD[@]}" "${EXTRA_BUILD_FLAGS[@]}" "$@" -t "$TAG" "$ctx"
    else
        "${BUILD_CMD[@]}" "${EXTRA_BUILD_FLAGS[@]}" "$@" -t "$TAG" "$ctx" >/dev/null
    fi
    end="$(now_seconds)"
    seconds="$(elapsed_seconds "$start" "$end")"
    local bytes human
    bytes="$(image_size_bytes)"
    human="$(image_size_human)"
    record_result "$scenario" "$seconds" "$bytes" "$human"
}

# --------------------------------------------------------------------------
# Scenarios
# --------------------------------------------------------------------------
WORKDIR="$(mktemp -d "${TMPDIR:-/tmp}/measure-build-times.XXXXXX")"
cleanup() {
    if [ "$KEEP_IMAGE" != "true" ] && [ "$DRY_RUN" != "true" ]; then
        "$CONTAINER_ENGINE" rmi -f "$TAG" >/dev/null 2>&1 || true
    fi
    rm -rf "$WORKDIR"
}
trap cleanup EXIT

echo "Engine:      $CONTAINER_ENGINE (${ENGINE_FLAVOR:-unknown flavor})"
echo "Context:     $CONTEXT"
echo "Image tag:   $TAG"
echo "Scenarios:   $SCENARIOS"
echo "Build cmd:   ${BUILD_CMD[*]} ${EXTRA_BUILD_FLAGS[*]:-} -t $TAG <context>"
echo ""

IFS=',' read -ra SCENARIO_LIST <<< "$SCENARIOS"

for scenario in "${SCENARIO_LIST[@]}"; do
    case "$scenario" in
        cold|warm|warm-source-change|warm-deps-change|warm-no-layer-cache) ;;
        *) echo "ERROR: unknown scenario: $scenario" >&2; exit 1 ;;
    esac

    echo "==> scenario: $scenario"
    ctx="$WORKDIR/$scenario/ctx"
    mkdir -p "$WORKDIR/$scenario"
    snapshot_context "$ctx"

    case "$scenario" in
        cold)
            echo "  clearing caches for a clean cold build..."
            clear_buildkit_mount_caches
            timed_build "$ctx" "$scenario" "$scenario" "--no-cache"
            ;;
        warm)
            prime "$ctx" "$scenario"
            timed_build "$ctx" "$scenario" "$scenario"
            ;;
        warm-source-change)
            prime "$ctx" "$scenario"
            main_py="$ctx/app/main.py"
            if [ "$DRY_RUN" != "true" ] && [ ! -f "$main_py" ]; then
                echo "  skipped: $main_py not found in context" >&2
                record_result "$scenario" "skipped" "" "skipped"
                continue
            fi
            append_marker "$main_py" "# measure_build_times: source-change marker"
            timed_build "$ctx" "$scenario" "$scenario"
            ;;
        warm-deps-change)
            requirements="$ctx/requirements.txt"
            if [ "$DRY_RUN" != "true" ] && [ ! -f "$requirements" ]; then
                echo "  skipped: no requirements.txt in context (pre-optimization baseline)"
                record_result "$scenario" "skipped" "" "skipped"
                continue
            fi
            prime "$ctx" "$scenario"
            append_marker "$requirements" "# measure_build_times: deps-change marker"
            timed_build "$ctx" "$scenario" "$scenario"
            ;;
        warm-no-layer-cache)
            prime "$ctx" "$scenario"
            # Layer cache must be bypassed, but cache mounts stay warm.
            timed_build "$ctx" "$scenario" "$scenario" "--no-cache"
            ;;
    esac
    echo ""
done

# --------------------------------------------------------------------------
# Report
# --------------------------------------------------------------------------
echo "==================== build time summary ===================="
printf '  %-22s %8s   %s\n' "scenario" "seconds" "image size"
for row in "${RESULTS[@]}"; do
    IFS='|' read -r scenario seconds bytes human <<< "$row"
    if [ "$seconds" = "skipped" ]; then
        printf '  %-22s %8s\n' "$scenario" "skipped"
    else
        printf '  %-22s %8s   %s\n' "$scenario" "$seconds" "$human"
    fi
done
echo "============================================================"

if [ -n "$JSON_PATH" ]; then
    {
        echo "{"
        echo "  \"engine\": \"$(json_escape "$CONTAINER_ENGINE")\","
        echo "  \"engine_flavor\": \"$(json_escape "${ENGINE_FLAVOR:-}")\","
        echo "  \"context\": \"$(json_escape "$CONTEXT")\","
        echo "  \"tag\": \"$(json_escape "$TAG")\","
        echo "  \"results\": ["
        first=true
        for row in "${RESULTS[@]}"; do
            IFS='|' read -r scenario seconds bytes human <<< "$row"
            if [ "$first" = "true" ]; then first=false; else echo ","; fi
            if [ "$seconds" = "skipped" ]; then
                echo "    {\"scenario\": \"$(json_escape "$scenario")\", \"seconds\": null, \"image_bytes\": null}"
            else
                echo "    {\"scenario\": \"$(json_escape "$scenario")\", \"seconds\": $seconds, \"image_bytes\": ${bytes:-null}}"
            fi
        done
        echo "  ]"
        echo "}"
    } > "$JSON_PATH"
    echo "JSON results written to $JSON_PATH"
fi
