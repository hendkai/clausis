#!/bin/sh
set -eu

project_dir=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
version=$("$project_dir/scripts/project_version.sh")
iso_name="clausis-$version-amd64.iso"
iso="$project_dir/dist/$iso_name"
image="clausis-boot-smoke:$version"
screenshot="clausis-$version-boot-screen.png"

test -s "$iso"
docker build -f "$project_dir/packaging/live-build/Dockerfile.boottest" \
    -t "$image" "$project_dir/packaging/live-build"
docker run --rm --entrypoint sh \
    -e CLAUSIS_ISO_NAME="$iso_name" -e CLAUSIS_VERSION="$version" \
    -v "$project_dir/dist:/artifacts" "$image" -ec '
    mkdir -p /tmp/boot
    prefix="/artifacts/clausis-$CLAUSIS_VERSION"
    boot_log="$prefix-graphical-boot.log"
    qemu_log="$prefix-graphical-qemu.log"
    monitor_log="$prefix-monitor.log"
    screenshot="$prefix-boot-screen.png"
    : > "$boot_log"
    : > "$qemu_log"
    : > "$monitor_log"
    xorriso -osirrox on -indev "/artifacts/$CLAUSIS_ISO_NAME" \
        -extract /live/vmlinuz /tmp/boot/vmlinuz \
        -extract /live/initrd.img /tmp/boot/initrd.img >/tmp/extract.log 2>&1
    qemu-system-x86_64 \
        -machine q35,accel=tcg \
        -cpu max -smp 2 -m 3072 \
        -kernel /tmp/boot/vmlinuz \
        -initrd /tmp/boot/initrd.img \
        -append "boot=live components username=clausis hostname=clausis console=ttyS0,115200" \
        -drive file="/artifacts/$CLAUSIS_ISO_NAME",media=cdrom,readonly=on \
        -display none -vga std \
        -serial "file:$boot_log" \
        -monitor unix:/tmp/qemu-monitor,server=on,wait=off \
        -no-reboot >"$qemu_log" 2>&1 &
    qemu_pid=$!
    cleanup() {
        kill "$qemu_pid" >/dev/null 2>&1 || true
        wait "$qemu_pid" >/dev/null 2>&1 || true
    }
    trap cleanup EXIT INT TERM

    ready=0
    elapsed=0
    while [ "$elapsed" -lt 360 ] && kill -0 "$qemu_pid" >/dev/null 2>&1; do
        if grep -Eq "Started .*GNOME Display Manager|Started .*gdm.service" "$boot_log" 2>/dev/null; then
            ready=1
            break
        fi
        sleep 2
        elapsed=$((elapsed + 2))
    done
    if [ "$ready" -ne 1 ]; then
        tail -120 "$boot_log" 2>/dev/null || true
        exit 1
    fi

    # GDM can start well before software-emulated graphics reaches the live
    # session. Keep sampling until the PNG is materially richer than the small
    # static SeaBIOS screen; never publish that boot screen as desktop proof.
    captured=0
    elapsed=0
    while [ "$elapsed" -lt 300 ] && kill -0 "$qemu_pid" >/dev/null 2>&1; do
        sleep 10
        elapsed=$((elapsed + 10))
        test -S /tmp/qemu-monitor
        printf "screendump /tmp/boot-screen.ppm\n" \
            | socat - UNIX-CONNECT:/tmp/qemu-monitor \
                >"$monitor_log" 2>&1
        test -s /tmp/boot-screen.ppm
        pnmtopng /tmp/boot-screen.ppm > /tmp/boot-screen.png
        png_bytes=$(wc -c < /tmp/boot-screen.png)
        if [ "$png_bytes" -ge 20000 ]; then
            # The authenticated desktop exists. Allow its accessibility and
            # Clausis autostarts to finish before taking the release evidence.
            sleep 90
            kill -0 "$qemu_pid" >/dev/null 2>&1
            printf "screendump /tmp/boot-screen.ppm\n" \
                | socat - UNIX-CONNECT:/tmp/qemu-monitor \
                    >"$monitor_log" 2>&1
            pnmtopng /tmp/boot-screen.ppm \
                > "$screenshot"
            final_png_bytes=$(wc -c < "$screenshot")
            test "$final_png_bytes" -ge 20000
            captured=1
            break
        fi
    done
    if [ "$captured" -ne 1 ]; then
        printf "%s\n" "No graphical live-session frame appeared within 300 seconds." >&2
        tail -120 "$boot_log" 2>/dev/null || true
        exit 1
    fi
    grep -E "Started .*GNOME Display Manager|Started .*gdm.service" "$boot_log" | tail -1
  '

printf '%s\n' "Graphical live-session screenshot: $project_dir/dist/$screenshot"
