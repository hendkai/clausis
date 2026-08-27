#!/bin/sh
# Inner container script for the session-level AT-SPI smoke tests.
# Runs INSIDE the debian:13-slim container (see atspi_session_smoke.sh)
# with the repository mounted at /src and results written to /out.
#
# Usage: atspi_session_container.sh [gtk|browser|all]
#
#   gtk      real GTK probe app: text editing, say-all, structure list jump
#   browser  firefox-esr loads tests/fixtures/browser_probe_page.html via
#            file:// — structure navigation against browser-published
#            AT-SPI roles and ARIA xml-roles (BLIND §2/§4).  Read-only:
#            jumps move focus and announce, NEVER activate.
#   all      both sessions (default)
set -eu

mode=${1:-all}

apt-get update -qq
DEBIAN_FRONTEND=noninteractive apt-get install -y -qq \
  dbus-x11 xvfb at-spi2-core libatk-adaptor python3-pyatspi \
  python3-gi gir1.2-gtk-3.0 matchbox-window-manager procps >/dev/null
if [ "$mode" = browser ] || [ "$mode" = all ]; then
  # firefox-esr is a native Debian package; this is why the browser
  # session rides in a container instead of on the Ubuntu runner.
  DEBIAN_FRONTEND=noninteractive apt-get install -y -qq firefox-esr >/dev/null
fi

dbus-run-session -- sh -eu -c '
  mode="$1"
  # C.UTF-8: with the POSIX default locale X11 mangles the German UTF-8
  # window title ("failure in conversion from UTF8_STRING") and no name
  # comparison would ever match.  GNOME_ACCESSIBILITY=1 makes Firefox
  # enable its accessibility engine at startup (modern Firefox only
  # activates a11y when this env var or a gsettings daemon says so —
  # verified: without it Firefox never registers on the bus, with it the
  # frame appears within ~5 s).
  export LANG=C.UTF-8 LC_ALL=C.UTF-8
  Xvfb :99 -screen 0 1280x720x24 >/tmp/xvfb.log 2>&1 &
  export DISPLAY=:99 NO_AT_BRIDGE=0 GTK_MODULES=gail:atk-bridge GNOME_ACCESSIBILITY=1
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
  probe_pid=
  if [ "$mode" = gtk ] || [ "$mode" = all ]; then
    PYTHONPATH=/src/src python3 /src/tests/fixtures/atspi_session_probe_app.py /out/app-marker.txt >/tmp/app.log 2>&1 &
    probe_pid=$!
    sleep 3
    PYTHONPATH=/src/src python3 /src/tests/fixtures/atspi_session_client.py /out/session-result.txt
  fi
  if [ "$mode" = browser ] || [ "$mode" = all ]; then
    # In "all" mode the GTK probe window still owns the active state; take
    # it off the bus so the Firefox window becomes the active window the
    # adapter walks.  Kill by recorded PID, NEVER pkill -f: the session
    # shell executes the whole script text as one command line, and that
    # text contains the probe-app filename — pkill -f matched the carrier
    # shell itself and SIGTERMed the whole session (verified: container
    # died rc=143 exactly at this line before the client ever started).
    if [ -n "$probe_pid" ]; then
      kill "$probe_pid" >/dev/null 2>&1 || true
      sleep 1
    fi
    # Pre-seeded profile (tests/fixtures/firefox_user.js): no default-browser
    # prompt, no welcome page, no update pings — the one window must show
    # the probe page and nothing else, locally, without network navigation.
    mkdir -p /tmp/ffprofile
    cp /src/tests/fixtures/firefox_user.js /tmp/ffprofile/user.js
    # MOZ_DISABLE_CONTENT_SANDBOX: in minimal containers the content
    # sandbox regularly freezes first paint; harmless here (the session
    # only READS the a11y tree) and the second-most common freeze cause.
    MOZ_DISABLE_CONTENT_SANDBOX=1 MOZ_ALLOW_RUN_AS_ROOT=1 \
      firefox-esr --profile /tmp/ffprofile --no-remote \
      --new-window file:///src/tests/fixtures/browser_probe_page.html \
      >/tmp/firefox.log 2>&1 &
    # PYTHONPATH: the client imports clausis.gnome_adapter from /src/src.
    # timeout 120: a wedged bus must never eat the whole CI budget; the
    # client flushes after every step, so partial results still land in
    # /out/browser-result.txt.  A nonzero client exit propagates out of
    # the container (after copying the logs) so CI fails on real errors.
    set +e
    PYTHONPATH=/src/src timeout 120 python3 \
      /src/tests/fixtures/atspi_browser_session_client.py /out/browser-result.txt
    client_rc=$?
    set -e
    if [ "$client_rc" -ne 0 ]; then
      cp /tmp/firefox.log /tmp/atspi.log /out/ 2>/dev/null || true
      exit "$client_rc"
    fi
  fi
' inner-sh "$mode"
