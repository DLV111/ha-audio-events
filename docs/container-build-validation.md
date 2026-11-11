# Container build validation

Measured validation of the optimized multi-stage Dockerfile
(`ha-audio-events/Dockerfile`) against the pre-optimization baseline, plus the
smoke/content checks that guard the image contents and startup behaviour.

## How to reproduce

```bash
# Build + validate image contents (28 checks)
./scripts/build.sh && ./scripts/validate_container_contents.sh

# End-to-end smoke checks
make test-container          # dog-bark fixture -> real detection fired
make test-container-webui    # webui served HTTP on 8099

# Build-time benchmark (cold/warm scenarios, machine-readable via --json)
./scripts/measure_build_times.sh --scenarios all --json /tmp/results.json
```

## Environment

- Engine: `docker` command backed by the Podman compatibility shim
  (podman 4.9.3 / buildah 1.33.7, rootless, `--layers` layer caching).
- Runner: shared host; absolute timings include environment noise, so treat
  deltas (not raw seconds) as the result.
- Benchmark tool: `scripts/measure_build_times.sh` (builds from a context
  snapshot; the working tree is never modified).

## Measured results (2026-11-11)

### Optimized Dockerfile (multi-stage builder/runtime)

| scenario              | seconds | image size |
|-----------------------|--------:|-----------:|
| cold                  | 131.5*  | 716MiB     |
| warm (no change)      | 3.6     | 716MiB     |
| warm-source-change    | 4.4     | 716MiB     |
| warm-deps-change      | 9.0     | 716MiB     |
| warm-no-layer-cache   | 122.9*  | 716MiB     |

\* cold / warm-no-layer-cache re-measured in a dedicated run with the
buildah cache mounts handled correctly: cold 113.4 s (mounts cleared) vs
warm-no-layer-cache 102.8 s (mounts warm) — i.e. the persistent apt/pip cache
mounts save ~10 s (~9%) on layer-cache-miss rebuilds.

### Pre-optimization baseline (single stage, `python:3.12-slim`)

| scenario              | seconds | image size |
|-----------------------|--------:|-----------:|
| cold                  | 86.9    | 1010MiB    |
| warm (no change)      | 0.7     | 1010MiB    |
| warm-source-change    | 19.6    | 1010MiB    |

The baseline Dockerfile has no `requirements.txt`, so `warm-deps-change` and
`warm-no-layer-cache` are equivalent to `warm-source-change`/`cold` for the
baseline (a single stage means any change re-runs the full pip install).

## Comparison and interpretation

| metric                     | baseline | optimized | delta            |
|----------------------------|---------:|----------:|------------------|
| image size                 | 1010MiB  | 716MiB    | **−294MiB (−29%)** |
| rebuild after source change| 19.6 s   | 4.4 s     | **−78%**         |
| rebuild after deps change  | ~19.6 s  | 9.0 s     | **−55%**         |
| warm no-change rebuild     | 0.7 s    | 3.6 s     | +2.9 s (negligible) |
| fully cold build           | 86.9 s   | 113.4 s   | +30% (accepted trade-off) |

Key wins:

- **Image size −29%** (1010MiB → 716MiB): build-essential toolchain and apt
  state no longer ship in the runtime image.
- **Source-change rebuilds 4.5x faster**: dependencies live in layers before
  the `COPY . /app`, so app edits skip the pip install entirely.
- **Deps-change rebuilds still ~2x faster** than baseline because the pip
  cache mount serves the wheels instead of the network.
- **Bytecode precompiled at build time** (`python -m compileall`): container
  startup skips app-module compilation even with
  `PYTHONDONTWRITEBYTECODE=1`.

Accepted trade-offs / remaining bottlenecks:

- **Fully cold builds are ~30% slower** than the baseline single stage: the
  multi-stage build pays for two apt transactions, a `COPY --from=builder`
  site-packages copy (~200 MiB), and `compileall`. In CI this case is
  mitigated by the gha/registry cache (`BUILD_CACHE_FROM`/`BUILD_CACHE_TO`);
  locally, layer caching makes it a rare event. Revisit only if cold CI
  builds become frequent (e.g. consider merging the two apt transactions
  across stages via a shared stage).
- **Cache mounts save only ~10 s on layer-cache-miss rebuilds**: package
  unpack/configure dominates over download on this network, so the
  `docker-clean` removal and pip-cache-mount fixes matter more for
  metered/slow networks than for this host.
- **Podman note:** the persistent `RUN --mount=type=cache` storage lives at
  `<engine tmpdir>/buildah-cache-<uid>`, where the tmpdir is the engine's
  resolved `ImageCopyTmpDir` — *not* necessarily `/var/tmp`. Tools that clear
  the cache must resolve it via `podman info` (the measure script does).

## Image content / startup checks

`scripts/validate_container_contents.sh` (28 checks, all passing):

- runtime tooling present (ffmpeg, arecord, pactl), Python 3.12 + all five
  runtime deps importable, app payload (run.sh, config.yaml, YAMNet model +
  class map + group files, translations, webui assets) intact;
- hygiene: no gcc/build-essential, no pip cache, no apt lists in layers, no
  CHANGELOG shipped, app bytecode precompiled;
- startup: entrypoint forwards args, `PYTHONDONTWRITEBYTECODE` and
  `PYTHONUNBUFFERED` set.

End-to-end smoke checks (both passing):

- `make test-container`: container classified the dog-bark fixture and fired
  `Detected event: Dog`.
- `make test-container-webui`: ingress panel and `/api/detections` served
  HTTP 200 on port 8099.

Unit suite at time of validation: 308 tests passing (includes
`tests/test_dockerfile.py` and `tests/test_measure_build_times.py` guards for
the Dockerfile layering rules and the benchmark script).
