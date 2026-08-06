#!/bin/sh
set -eu

parts_dir=${1:-.}
output=${2:-voiceos-0.1.0-amd64.iso}

part_a="$parts_dir/voiceos-0.1.0-amd64.iso.part-aa"
part_b="$parts_dir/voiceos-0.1.0-amd64.iso.part-ab"
checksum="$parts_dir/voiceos-0.1.0-amd64.iso.sha256"

test -f "$part_a"
test -f "$part_b"
test -f "$checksum"
cat "$part_a" "$part_b" > "$output"

expected=$(awk 'NR == 1 {print $1}' "$checksum")
actual=$(sha256sum "$output" | awk '{print $1}')
test "$expected" = "$actual"
printf '%s\n' "ISO erfolgreich zusammengesetzt und geprüft: $output"
