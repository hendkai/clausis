#!/bin/sh
set -eu

project_dir=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
version=$("$project_dir/scripts/project_version.sh")
base="clausis-$version-amd64.iso"
parts_dir=${1:-.}
output=${2:-$base}

part_a="$parts_dir/$base.part-aa"
part_b="$parts_dir/$base.part-ab"
checksum="$parts_dir/$base.sha256"

test -f "$part_a"
test -f "$part_b"
test -f "$checksum"
cat "$part_a" "$part_b" > "$output"

expected=$(awk 'NR == 1 {print $1}' "$checksum")
if command -v sha256sum >/dev/null 2>&1; then
    actual=$(sha256sum "$output" | awk '{print $1}')
else
    actual=$(shasum -a 256 "$output" | awk '{print $1}')
fi
test "$expected" = "$actual"
printf '%s\n' "ISO erfolgreich zusammengesetzt und geprüft: $output"
