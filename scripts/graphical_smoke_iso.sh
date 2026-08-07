#!/bin/sh
set -eu

project_dir=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
iso="$project_dir/dist/clausis-0.2.0-amd64.iso"
image="clausis-boot-smoke:0.2.0"
screenshot="clausis-0.2.0-boot-screen.png"

test -s "$iso"
docker build -f "$project_dir/packaging/live-build/Dockerfile.boottest" \
    -t "$image" "$project_dir/packaging/live-build"
docker run --rm --entrypoint sh -v "$project_dir/dist:/artifacts" "$image" -ec '
    mkdir -p /tmp/boot
    : > /artifacts/clausis-0.2.0-graphical-boot.log
    : > /artifacts/clausis-0.2.0-graphical-qemu.log
    : > /artifacts/clausis-0.2.0-monitor.log
    xorriso -osirrox on -indev /artifacts/clausis-0.2.0-amd64.iso \
        -extract /live/vmlinuz /tmp/boot/vmlinuz \
        -extract /live/initrd.img /tmp/boot/initrd.img >/tmp/extract.log 2>&1
    qemu-system-x86_64 \
        -machine q35,accel=tcg \
        -cpu max -smp 2 -m 3072 \
        -kernel /tmp/boot/vmlinuz \
        -initrd /tmp/boot/initrd.img \
        -append "boot=live components username=clausis hostname=clausis console=ttyS0,115200" \
        -drive file=/artifacts/clausis-0.2.0-amd64.iso,media=cdrom,readonly=on \
        -display none -vga std \
        -serial file:/artifacts/clausis-0.2.0-graphical-boot.log \
        -monitor unix:/tmp/qemu-monitor,server=on,wait=off \
        -no-reboot >/artifacts/clausis-0.2.0-graphical-qemu.log 2>&1 &
    qemu_pid=$!
    cleanup() {
        kill "$qemu_pid" >/dev/null 2>&1 || true
        wait "$qemu_pid" >/dev/null 2>&1 || true
    }
    trap cleanup EXIT INT TERM

    ready=0
    elapsed=0
    while [ "$elapsed" -lt 360 ] && kill -0 "$qemu_pid" >/dev/null 2>&1; do
        if grep -Eq "Started .*GNOME Display Manager|Started .*gdm.service" /artifacts/clausis-0.2.0-graphical-boot.log 2>/dev/null; then
            ready=1
            break
        fi
        sleep 2
        elapsed=$((elapsed + 2))
    done
    if [ "$ready" -ne 1 ]; then
        tail -120 /artifacts/clausis-0.2.0-graphical-boot.log 2>/dev/null || true
        exit 1
    fi

    # Give GDM enough time to create the live account session and show the
    # first accessible Clausis window under slow software emulation.
    elapsed=0
    while [ "$elapsed" -lt 90 ] && kill -0 "$qemu_pid" >/dev/null 2>&1; do
        sleep 2
        elapsed=$((elapsed + 2))
    done
    test -S /tmp/qemu-monitor
    printf "screendump /tmp/boot-screen.ppm\n" \
        | socat - UNIX-CONNECT:/tmp/qemu-monitor >/artifacts/clausis-0.2.0-monitor.log 2>&1
    test -s /tmp/boot-screen.ppm
    pnmtopng /tmp/boot-screen.ppm > /artifacts/clausis-0.2.0-boot-screen.png
    test -s /artifacts/clausis-0.2.0-boot-screen.png
    grep -E "Started .*GNOME Display Manager|Started .*gdm.service" /artifacts/clausis-0.2.0-graphical-boot.log | tail -1
  '

printf '%s\n' "Graphical live-session screenshot: $project_dir/dist/$screenshot"
