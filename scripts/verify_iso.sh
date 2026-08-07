#!/bin/sh
set -eu

project_dir=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
iso="$project_dir/dist/clausis-0.4.1-amd64.iso"
checksum="$iso.sha256"
builder="clausis-iso-builder:0.4.1"

test -s "$iso"
test -s "$checksum"
expected=$(awk 'NR == 1 {print $1}' "$checksum")
actual=$(shasum -a 256 "$iso" | awk '{print $1}')
test "$expected" = "$actual"

docker run --rm --platform linux/amd64 --entrypoint sh \
    -v "$project_dir/dist:/artifacts:ro" "$builder" -exc '
        xorriso -indev /artifacts/clausis-0.4.1-amd64.iso -check_media -- >/tmp/media-check 2>&1
        xorriso -indev /artifacts/clausis-0.4.1-amd64.iso -report_el_torito plain >/tmp/boot-report 2>&1
        xorriso -indev /artifacts/clausis-0.4.1-amd64.iso -find / -type f -exec echo -- >/tmp/file-list 2>&1
        grep -Eq "El Torito|BIOS" /tmp/boot-report
        grep -Eq "UEFI|EFI" /tmp/boot-report
        grep -q "/live/filesystem.squashfs" /tmp/file-list
        grep -q "/live/vmlinuz" /tmp/file-list
        grep -q "/live/initrd" /tmp/file-list

        xorriso -osirrox on -indev /artifacts/clausis-0.4.1-amd64.iso \
            -extract /live/filesystem.squashfs /tmp/filesystem.squashfs \
            >/tmp/extract.log 2>&1
        unsquashfs -ll /tmp/filesystem.squashfs >/tmp/squashfs-tree
        for required in \
            squashfs-root/usr/local/bin/hermes \
            squashfs-root/opt/hermes-agent/LICENSE \
            squashfs-root/opt/clausis-hermes-updater/bin/uv \
            squashfs-root/usr/share/doc/hermes-agent/LICENSE \
            squashfs-root/usr/bin/clausis-setup \
            squashfs-root/usr/bin/clausis-finalize-hermes-install \
            squashfs-root/etc/skel/.config/gnome-initial-setup-done \
            squashfs-root/etc/dconf/db/local.d/00-clausis \
            squashfs-root/etc/dconf/db/local \
            squashfs-root/etc/calamares/modules/shellprocess@clausis.conf \
            squashfs-root/etc/calamares/modules/shellprocess@clausis-guard.conf \
            squashfs-root/etc/calamares/modules/partition.conf \
            squashfs-root/usr/lib/x86_64-linux-gnu/calamares/modules/luksbootkeyfile/libcalamares_job_luksbootkeyfile.so \
            squashfs-root/usr/share/applications/clausis-hermes-chat.desktop \
            squashfs-root/usr/share/clausis/models/faster-whisper-base/model.bin
        do
            grep -Fq "$required" /tmp/squashfs-tree
        done

        unsquashfs -cat /tmp/filesystem.squashfs \
            usr/local/bin/clausis-live-welcome >/tmp/welcome
        grep -Fq "live_system=0" /tmp/welcome
        grep -Fq "user_id=\$(id -u)" /tmp/welcome
        ! grep -Fq '\''${UID}'\'' /tmp/welcome
        grep -Fq "Stopp Hermes" /tmp/welcome
        grep -Fq "clausis-live-assistant >/dev/null" /tmp/welcome
        ! grep -Fq "assistant.log" /tmp/welcome

        unsquashfs -cat /tmp/filesystem.squashfs \
            etc/dconf/db/local.d/00-clausis \
            | grep -Fq "welcome-dialog-last-shown-version="

        unsquashfs -cat /tmp/filesystem.squashfs \
            etc/calamares/settings.conf | sed -n "/^- exec:/,\$p" >/tmp/calamares-exec
        grep -A1 -Fx "  - users" /tmp/calamares-exec \
            | tail -n 1 | grep -Fxq "  - shellprocess@clausis"
        grep -B1 -Fx "  - partition" /tmp/calamares-exec \
            | head -n 1 | grep -Fxq "  - shellprocess@clausis-guard"

        unsquashfs -cat /tmp/filesystem.squashfs \
            etc/calamares/modules/partition.conf >/tmp/clausis-partition
        grep -Fxq "initialPartitioningChoice: none" /tmp/clausis-partition
        grep -Fxq "luksGeneration: luks2" /tmp/clausis-partition
        grep -Fxq "defaultFileSystemType: \"btrfs\"" /tmp/clausis-partition

        unsquashfs -cat /tmp/filesystem.squashfs var/lib/dpkg/status \
            >/tmp/package-status
        sed -n "/^Package: calamares$/,/^$/p" /tmp/package-status \
            | grep -Fxq "Version: 3.3.14-1+clausis11"
        unsquashfs -f -d /tmp/calamares-module /tmp/filesystem.squashfs \
            usr/lib/x86_64-linux-gnu/calamares/modules/partition/libcalamares_viewmodule_partition.so \
            >/tmp/extract-calamares.log
        strings /tmp/calamares-module/usr/lib/x86_64-linux-gnu/calamares/modules/partition/libcalamares_viewmodule_partition.so \
            | grep -Fxq "clausisSelectedDevice"

        unsquashfs -f -d /tmp/calamares-recovery-module /tmp/filesystem.squashfs \
            usr/lib/x86_64-linux-gnu/calamares/modules/luksbootkeyfile/libcalamares_job_luksbootkeyfile.so \
            >/tmp/extract-calamares-recovery.log
        recovery_module=/tmp/calamares-recovery-module/usr/lib/x86_64-linux-gnu/calamares/modules/luksbootkeyfile/libcalamares_job_luksbootkeyfile.so
        strings "$recovery_module" | grep -Fxq "/run/clausis-installer/recovery.key"
        strings "$recovery_module" | grep -Fxq "/run/clausis-installer/recovery-installed"
        strings "$recovery_module" | grep -Fq "Clausis recovery key was installed"

        unsquashfs -cat /tmp/filesystem.squashfs \
            etc/calamares/modules/shellprocess@clausis-guard.conf \
            | grep -Fxq "timeout: 300"
        unsquashfs -cat /tmp/filesystem.squashfs \
            usr/lib/python3/dist-packages/clausis/installer.py \
            | grep -Fq "stage_recovery_key"

        unsquashfs -cat /tmp/filesystem.squashfs \
            opt/hermes-agent/pyproject.toml | grep -Fq '\''version = "0.20.0"'\''
        unsquashfs -cat /tmp/filesystem.squashfs \
            usr/share/applications/clausis-hermes-chat.desktop \
            | grep -Fq "hermes --toolsets todo"
        unsquashfs -cat /tmp/filesystem.squashfs \
            usr/share/applications/clausis-setup.desktop \
            | grep -Fq "Exec=clausis-setup --installed"
        unsquashfs -cat /tmp/filesystem.squashfs \
            usr/lib/python3/dist-packages/clausis/hermes_client.py \
            | grep -Fq "Technische Fehlermeldungen werden aus Datenschutzgründen nicht vorgelesen"
        unsquashfs -cat /tmp/filesystem.squashfs \
            usr/lib/python3/dist-packages/clausis/finalize_install.py \
            | grep -Fq "os.O_NOFOLLOW"
        unsquashfs -cat /tmp/filesystem.squashfs \
            usr/lib/python3/dist-packages/clausis/hermes_update.py \
            | grep -Fq "releases/latest"
    '

printf '%s\n' \
    "ISO checksum, BIOS/UEFI boot, Hermes, licenses, speech model, accessibility setup, installer binding and recovery-key module verified."
