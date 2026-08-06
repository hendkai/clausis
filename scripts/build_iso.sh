#!/bin/sh
set -eu

project_dir=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
builder="voiceos-iso-builder:0.1.0"

mkdir -p "$project_dir/dist"
docker build --platform linux/amd64 -t "$builder" "$project_dir/packaging/live-build"
docker run --rm --privileged --platform linux/amd64 \
    -v "$project_dir:/source:ro" \
    -v "$project_dir/dist:/output" \
    -v voiceos-live-cache:/build/iso/cache \
    "$builder"

"$project_dir/scripts/verify_iso.sh"

printf '%s\n' "ISO: $project_dir/dist/voiceos-0.1.0-amd64.iso"
printf '%s\n' "SHA-256: $project_dir/dist/voiceos-0.1.0-amd64.iso.sha256"
