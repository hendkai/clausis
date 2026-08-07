#!/bin/sh
set -eu

project_dir=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)

docker run --rm --platform linux/amd64 \
    -v "$project_dir:/source:ro" \
    debian:13-slim sh -euxc '
apt-get update >/dev/null
DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends dbus python3-dbus-next >/dev/null
mkdir -p /tmp/clausis-credentials /var/log/clausis
printf "%s\n" \
  "<!DOCTYPE busconfig PUBLIC \"-//freedesktop//DTD D-Bus Bus Configuration 1.0//EN\" \"http://www.freedesktop.org/standards/dbus/1.0/busconfig.dtd\">" \
  "<busconfig>" \
  "<type>system</type>" \
  "<listen>unix:path=/tmp/clausis-system-bus</listen>" \
  "<policy context=\"default\">" \
  "<allow own=\"*\"/>" \
  "<allow send_destination=\"*\"/>" \
  "<allow receive_sender=\"*\"/>" \
  "</policy>" \
  "</busconfig>" > /tmp/clausis-system.conf
PYTHONPATH=/source/src python3 -c "import json, os; from pathlib import Path; from clausis.confirmation import PinVerifier; p=Path(\"/tmp/clausis-credentials\"); (p/\"capability.key\").write_bytes(os.urandom(32)); (p/\"audit.key\").write_bytes(os.urandom(32)); (p/\"voice-pin.json\").write_text(json.dumps(PinVerifier.enroll(\"123456\").export()))"
dbus-daemon --config-file=/tmp/clausis-system.conf --nofork --nopidfile &
bus_pid=$!
cleanup() {
  kill "$confirm_pid" "$broker_pid" "$bus_pid" 2>/dev/null || true
}
confirm_pid=
broker_pid=
trap cleanup EXIT INT TERM
export DBUS_SYSTEM_BUS_ADDRESS=unix:path=/tmp/clausis-system-bus
export CREDENTIALS_DIRECTORY=/tmp/clausis-credentials
export PYTHONPATH=/source/src
python3 -c "from clausis.services import broker_main; broker_main()" &
broker_pid=$!
python3 -c "from clausis.services import confirm_main; confirm_main()" &
confirm_pid=$!
python3 /source/tests/fixtures/dbus_smoke_client.py
'
