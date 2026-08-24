#!/bin/sh
# Session-level AT-SPI smoke test: real GTK app, real accessibility bus,
# real PyAtSpiDesktop text-editing surface (caret, selection, replace,
# undo/redo, granular reading).
#
# The container script is fed via stdin (quoted heredoc) so the nested
# dbus-run-session quoting stays a single, plain single-quoted block.
set -eu

repo_dir=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)

mkdir -p /tmp/clausis-session

docker run --rm --platform linux/amd64 --interactive --entrypoint sh \
  -v "${repo_dir}:/src:ro" -v /tmp/clausis-session:/out \
  debian:13-slim -s <<'CONTAINER_SCRIPT'
set -eu
apt-get update -qq
DEBIAN_FRONTEND=noninteractive apt-get install -y -qq \
  dbus-x11 xvfb at-spi2-core libatk-adaptor python3-pyatspi \
  python3-gi gir1.2-gtk-3.0 matchbox-window-manager >/dev/null
dbus-run-session -- sh -eu -c '
  Xvfb :99 -screen 0 1280x720x24 >/tmp/xvfb.log 2>&1 &
  export DISPLAY=:99 NO_AT_BRIDGE=0 GTK_MODULES=gail:atk-bridge
  # Bare Xvfb has no window manager: without the WM focus handshake the GTK
  # entry never gains STATE_FOCUSED and every editing step is refused.  Wait
  # for the display before starting the WM and fail loudly if the WM died.
  sleep 1
  matchbox-window-manager >/tmp/wm.log 2>&1 &
  wm_pid=$!
  sleep 1
  kill -0 "${wm_pid}"
  /usr/libexec/at-spi-bus-launcher --launch-immediately >/tmp/atspi.log 2>&1 &
  sleep 2
  PYTHONPATH=/src/src python3 /src/tests/fixtures/atspi_session_probe_app.py /out/app-marker.txt >/tmp/app.log 2>&1 &
  sleep 3
  PYTHONPATH=/src/src python3 /src/tests/fixtures/atspi_session_client.py /out/session-result.txt
'
CONTAINER_SCRIPT

echo "--- session result ---"
cat /tmp/clausis-session/session-result.txt
