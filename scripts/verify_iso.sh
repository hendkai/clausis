#!/bin/sh
set -eu

project_dir=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
iso="$project_dir/dist/voiceos-0.1.0-amd64.iso"
checksum="$iso.sha256"
builder="voiceos-iso-builder:0.1.0"

test -s "$iso"
test -s "$checksum"
expected=$(awk 'NR == 1 {print $1}' "$checksum")
actual=$(shasum -a 256 "$iso" | awk '{print $1}')
test "$expected" = "$actual"

docker run --rm --platform linux/amd64 --entrypoint sh \
    -v "$project_dir/dist:/artifacts:ro" "$builder" -ec '
        xorriso -indev /artifacts/voiceos-0.1.0-amd64.iso -check_media -- >/tmp/media-check 2>&1
        xorriso -indev /artifacts/voiceos-0.1.0-amd64.iso -report_el_torito plain >/tmp/boot-report 2>&1
        xorriso -indev /artifacts/voiceos-0.1.0-amd64.iso -find / -type f -exec echo -- >/tmp/file-list 2>&1
        grep -Eq "El Torito|BIOS" /tmp/boot-report
        grep -Eq "UEFI|EFI" /tmp/boot-report
        grep -q "/live/filesystem.squashfs" /tmp/file-list
        grep -q "/live/vmlinuz" /tmp/file-list
        grep -q "/live/initrd" /tmp/file-list
    '

printf '%s\n' "ISO checksum, media structure, live filesystem, BIOS and UEFI boot entries verified."
