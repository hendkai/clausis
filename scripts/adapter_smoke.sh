#!/bin/sh
# Exercise the platform adapters against a real Debian system.
#
# The unit tests drive these adapters with fakes.  This smoke test proves the
# parts that only a real Debian container can show: that the update adapter's
# argument vector is accepted by the installed apt, that the status adapter
# reads a real /proc and /sys, and that the shipped Polkit helper fails closed
# when it cannot read the capability key.
set -eu

project_dir=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)

docker run --rm --platform linux/amd64 \
    -v "$project_dir:/source:ro" \
    debian:13-slim sh -euxc '
apt-get update >/dev/null
DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends python3 >/dev/null
export PYTHONPATH=/source/src

python3 - <<"PY"
from clausis.models import ActionRequest
from clausis.policy import ACTION_POLICIES
from clausis.system_actions import LocalQueryExecutor

executor = LocalQueryExecutor()

# The real apt-get must accept the fixed simulation vector.
updates = executor.execute(ActionRequest("update.check"), ACTION_POLICIES["update.check"])
assert updates.status == "completed", updates
assert isinstance(updates.details["total"], int), updates
print("update.check:", updates.message)

# The real /proc and /sys must produce a spoken status.
status = executor.execute(ActionRequest("system.status"), ACTION_POLICIES["system.status"])
assert status.status == "completed", status
assert status.details["uptime_seconds"] is not None, status
assert "System" in status.message, status
print("system.status:", status.message)
PY

# The shipped helper must refuse without the root-only capability key.
reply=$(echo "{\"action\":\"system.reboot\",\"risk\":\"critical\",\"reversible\":false}" \
    | python3 /source/packaging/libexec/clausis-system-action || true)
echo "$reply"
echo "$reply" | python3 -c "import json,sys; r=json.load(sys.stdin); assert r[\"status\"]==\"denied\", r"

# An unauthorised caller must not be able to name a command.
reply=$(echo "{\"action\":\"package.install\",\"target\":\"--reinstall\",\"risk\":\"high\"}" \
    | python3 /source/packaging/libexec/clausis-system-action || true)
echo "$reply" | python3 -c "import json,sys; r=json.load(sys.stdin); assert r[\"status\"]==\"denied\", r"
echo "adapter smoke passed"
'
