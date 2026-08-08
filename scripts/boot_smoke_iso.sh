#!/bin/sh
set -eu

project_dir=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
version=$("$project_dir/scripts/project_version.sh")
iso_name="clausis-$version-amd64.iso"
iso="$project_dir/dist/$iso_name"
image="clausis-boot-smoke:$version"

test -s "$iso"
docker build -f "$project_dir/packaging/live-build/Dockerfile.boottest" -t "$image" "$project_dir/packaging/live-build"
docker run --rm --entrypoint sh -e CLAUSIS_ISO_NAME="$iso_name" \
    -v "$project_dir/dist:/artifacts:ro" "$image" -ec '
    mkdir -p /tmp/boot
    xorriso -osirrox on -indev "/artifacts/$CLAUSIS_ISO_NAME" \
        -extract /live/vmlinuz /tmp/boot/vmlinuz \
        -extract /live/initrd.img /tmp/boot/initrd.img >/tmp/extract.log 2>&1
    set +e
    timeout 240 qemu-system-x86_64 \
        -machine q35,accel=tcg \
        -cpu max -smp 2 -m 3072 \
        -kernel /tmp/boot/vmlinuz \
        -initrd /tmp/boot/initrd.img \
        -append "boot=live components username=clausis hostname=clausis console=ttyS0,115200" \
        -drive file="/artifacts/$CLAUSIS_ISO_NAME",media=cdrom,readonly=on \
        -display none -serial stdio -monitor none -no-reboot > /tmp/boot.log 2>&1
    status=$?
    set -e
    if ! grep -Eq "Reached target (graphical|Graphical Interface)|Started .*Display Manager|Starting .*Display Manager" /tmp/boot.log; then
        tail -120 /tmp/boot.log
        exit "$status"
    fi
    grep -E "Linux version|Reached target (graphical|Graphical Interface)|Display Manager" /tmp/boot.log | tail -20
  '

printf '%s\n' "Kernel, initramfs and live root reached the graphical boot target in x86-64 emulation."
