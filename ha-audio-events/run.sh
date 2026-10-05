#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# In normal (production/add-on) use, no arguments are passed and this just
# runs the app. But `podman run <image> <args...>` appends <args...> after
# the image's ENTRYPOINT (this script) rather than replacing it -- so test
# harnesses (see Makefile's test-container targets) rely on being able to
# pass a command like `timeout 30 bash -c '...'` through to actually run.
# Without this forwarding, those arguments were silently discarded and the
# container always ran the full production entrypoint instead -- which,
# with the webui enabled, blocks forever and never exits on its own.
if [ "$#" -gt 0 ]; then
    exec "$@"
else
    exec python3 -m app.main
fi
