#!/bin/sh
set -eu

project_dir=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
version=$("$project_dir/scripts/project_version.sh")
builder="clausis-iso-builder:$version"
iso_name="clausis-$version-amd64.iso"

mkdir -p "$project_dir/dist"
docker build --platform linux/amd64 -t "$builder" "$project_dir/packaging/live-build"
docker run --rm --privileged --platform linux/amd64 \
    -e CLAUSIS_VERSION="$version" \
    -v "$project_dir:/source:ro" \
    -v "$project_dir/dist:/output" \
    -v clausis-live-cache:/build/iso/cache \
    "$builder"

"$project_dir/scripts/verify_iso.sh"

printf '%s\n' "ISO: $project_dir/dist/$iso_name"
printf '%s\n' "SHA-256: $project_dir/dist/$iso_name.sha256"
