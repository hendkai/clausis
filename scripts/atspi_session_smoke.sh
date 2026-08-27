#!/bin/sh
# Session-level AT-SPI smoke test driver (host side).
#
# Runs the real-session accessibility tests inside a Debian container so
# the exact Debian packages of the target OS are exercised (firefox-esr is
# a native Debian package and the reason the browser session does not run
# directly on the Ubuntu CI runner):
#
#   gtk      real GTK probe app: text editing, say-all, structure list jump
#   browser  firefox-esr loads tests/fixtures/browser_probe_page.html via
#            file:// — structure navigation against browser-published
#            AT-SPI roles and ARIA xml-roles (BLIND §2 "Webinhalte",
#            §4 "Anwendungsabdeckung").  Read-only, never activates.
#   all      both sessions (default)
#
# Usage: scripts/atspi_session_smoke.sh [gtk|browser|all]
set -eu

mode=${1:-all}
case "$mode" in
  gtk|browser|all) ;;
  *) echo "usage: $0 [gtk|browser|all]" >&2; exit 2 ;;
esac

repo_dir=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)

mkdir -p /tmp/clausis-session

# --shm-size: firefox freezes or crashes its content process with the
# docker default of 64 MB shared memory — the a11y tree then never
# populates and the whole session appears to hang.
docker run --rm --platform linux/amd64 --shm-size 1g \
  -v "${repo_dir}:/src:ro" -v /tmp/clausis-session:/out \
  debian:13-slim sh /src/scripts/atspi_session_container.sh "$mode" || rc=$?

# The result files are flushed after every step, so emit whatever was
# produced even when the container failed or hit the client timeout —
# a hung session must never swallow its own diagnostics.
if [ "$mode" = gtk ] || [ "$mode" = all ]; then
  echo "--- session result ---"
  cat /tmp/clausis-session/session-result.txt 2>/dev/null || echo "(missing)"
fi
if [ "$mode" = browser ] || [ "$mode" = all ]; then
  echo "--- browser session result ---"
  cat /tmp/clausis-session/browser-result.txt 2>/dev/null || echo "(missing)"
  for logname in firefox atspi app; do
    if [ -f "/tmp/clausis-session/${logname}.log" ]; then
      echo "--- ${logname}.log (tail) ---"
      tail -40 "/tmp/clausis-session/${logname}.log"
    fi
  done
fi
exit "${rc:-0}"
