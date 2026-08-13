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
            squashfs-root/usr/share/pixmaps/hermes-agent.png \
            squashfs-root/opt/clausis-hermes-updater/bin/uv \
            squashfs-root/usr/share/doc/hermes-agent/LICENSE \
            squashfs-root/usr/bin/clausis-setup \
            squashfs-root/usr/bin/clausis-finalize-hermes-install \
            squashfs-root/etc/skel/.config/gnome-initial-setup-done \
            squashfs-root/etc/dconf/db/local.d/00-clausis \
            squashfs-root/etc/dconf/db/local \
            squashfs-root/etc/acpi/events/clausis-vm-power \
            squashfs-root/usr/local/sbin/clausis-vm-power \
            squashfs-root/etc/calamares/modules/shellprocess@clausis.conf \
            squashfs-root/etc/calamares/modules/shellprocess@clausis-guard.conf \
            squashfs-root/etc/calamares/modules/partition.conf \
            squashfs-root/usr/lib/x86_64-linux-gnu/calamares/modules/luksbootkeyfile/libcalamares_job_luksbootkeyfile.so \
            squashfs-root/usr/share/applications/clausis-hermes-chat.desktop \
            squashfs-root/usr/share/clausis/models/faster-whisper-base/model.bin \
            squashfs-root/opt/clausis/lib/python3.13/site-packages/faster_whisper/__init__.py \
            squashfs-root/opt/clausis/lib/python3.13/site-packages/sounddevice.py
        do
            grep -Fq "$required" /tmp/squashfs-tree
        done

        unsquashfs -f -d /tmp/model-root /tmp/filesystem.squashfs \
            usr/share/clausis/models/faster-whisper-base \
            usr/share/clausis/models/faster-whisper-base.sha256 >/dev/null
        (cd /tmp/model-root/usr/share/clausis/models/faster-whisper-base && \
            sha256sum -c ../faster-whisper-base.sha256)

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
        sed -n "/^Package: acpid$/,/^$/p" /tmp/package-status \
            | grep -Fxq "Status: install ok installed"
        sed -n "/^Package: calamares$/,/^$/p" /tmp/package-status \
            | grep -Fxq "Version: 3.3.14-1+clausis11"

        unsquashfs -cat /tmp/filesystem.squashfs \
            etc/acpi/events/clausis-vm-power >/tmp/clausis-vm-power-event
        grep -Fxq "event=button/power.*" /tmp/clausis-vm-power-event
        grep -Fxq "action=/usr/local/sbin/clausis-vm-power" /tmp/clausis-vm-power-event
        unsquashfs -cat /tmp/filesystem.squashfs \
            usr/local/sbin/clausis-vm-power >/tmp/clausis-vm-power-handler
        grep -Fq "systemd-detect-virt --vm --quiet" /tmp/clausis-vm-power-handler
        grep -Fq "exec systemctl --no-block poweroff" /tmp/clausis-vm-power-handler
        unsquashfs -f -d /tmp/calamares-module /tmp/filesystem.squashfs \
            usr/lib/x86_64-linux-gnu/calamares/modules/partition/libcalamares_viewmodule_partition.so \
            >/tmp/extract-calamares.log
        strings /tmp/calamares-module/usr/lib/x86_64-linux-gnu/calamares/modules/partition/libcalamares_viewmodule_partition.so \
            | grep -Fxq "clausisSelectedDevice"
        strings /tmp/calamares-module/usr/lib/x86_64-linux-gnu/calamares/modules/partition/libcalamares_viewmodule_partition.so \
            | grep -Fxq "clausisInstallMode"

        unsquashfs -f -d /tmp/calamares-recovery-module /tmp/filesystem.squashfs \
            usr/lib/x86_64-linux-gnu/calamares/modules/luksbootkeyfile/libcalamares_job_luksbootkeyfile.so \
            >/tmp/extract-calamares-recovery.log
        recovery_module=/tmp/calamares-recovery-module/usr/lib/x86_64-linux-gnu/calamares/modules/luksbootkeyfile/libcalamares_job_luksbootkeyfile.so
        strings "$recovery_module" | grep -Fxq "/run/clausis-installer/recovery.key"
        strings "$recovery_module" | grep -Fxq "/run/clausis-installer/recovery-installed"
        strings "$recovery_module" | grep -Fq "Clausis recovery key was installed"
        strings "$recovery_module" \
            | grep -Fq "A confirmed Clausis recovery key is required"

        unsquashfs -cat /tmp/filesystem.squashfs \
            etc/calamares/modules/shellprocess@clausis-guard.conf \
            >/tmp/clausis-guard
        grep -Fxq "timeout: 300" /tmp/clausis-guard
        grep -Fq "clausisInstallMode" /tmp/clausis-guard
        unsquashfs -cat /tmp/filesystem.squashfs \
            usr/lib/python3/dist-packages/clausis/installer.py \
            | grep -Fq "stage_recovery_key"
        grep -Fq "/usr/libexec/calamares-clausis/calamares_clausis.py" \
            /tmp/clausis-guard
        unsquashfs -cat /tmp/filesystem.squashfs \
            usr/libexec/calamares-clausis/calamares_clausis.py \
            >/tmp/calamares-clausis-bridge
        head -n 1 /tmp/calamares-clausis-bridge \
            | grep -Fxq "#!/opt/clausis/bin/python"
        grep -Fq "args.install_mode not in" /tmp/calamares-clausis-bridge
        grep -Fq "erase" /tmp/calamares-clausis-bridge
        grep -Fq "other" /tmp/calamares-clausis-bridge
        grep -Fq "invalid or missing Calamares install mode" \
            /tmp/calamares-clausis-bridge
        unsquashfs -cat /tmp/filesystem.squashfs \
            usr/lib/python3/dist-packages/clausis/speech.py \
            >/tmp/clausis-speech
        grep -Fq "except subprocess.TimeoutExpired" /tmp/clausis-speech
        grep -Fq "Never replay it through another backend" /tmp/clausis-speech

        unsquashfs -cat /tmp/filesystem.squashfs \
            opt/hermes-agent/pyproject.toml | grep -Fq '\''version = "0.20.0"'\''
        unsquashfs -cat /tmp/filesystem.squashfs \
            usr/share/applications/clausis-hermes-chat.desktop \
            | grep -Fq "hermes --toolsets todo"
        unsquashfs -cat /tmp/filesystem.squashfs \
            usr/share/applications/clausis-hermes-chat.desktop \
            | grep -Fxq "Icon=hermes-agent"
        unsquashfs -cat /tmp/filesystem.squashfs \
            etc/calamares/modules/locale.conf \
            | grep -Fxq "    style: \"none\""
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
        unsquashfs -cat /tmp/filesystem.squashfs \
            usr/lib/python3/dist-packages/clausis/gnome_adapter.py \
            >/tmp/gnome-adapter
        grep -Fq "fresh_actions = tuple" /tmp/gnome-adapter
        grep -Fq "keine erlaubte Aktivierungsaktion" /tmp/gnome-adapter
        grep -Fq "Die semantische Zurück-Aktion ist nicht eindeutig" /tmp/gnome-adapter
        grep -Fq "Das GNOME-Shell-Ziel für" /tmp/gnome-adapter
        grep -Fq "def read_notifications" /tmp/gnome-adapter
        grep -Fq "def dismiss_notification" /tmp/gnome-adapter
        grep -Fq "Der Benachrichtigungstext überschreitet die sichere Grenze" /tmp/gnome-adapter
        grep -Fq "Die sichtbare Benachrichtigungsreihenfolge hat sich geändert" /tmp/gnome-adapter
        grep -Fq "aber der exakte Nachzustand" /tmp/gnome-adapter
        grep -Fq "Die Fensteraktion {operation} ist nicht eindeutig" /tmp/gnome-adapter
        grep -Fq "never bind work to mere visibility" /tmp/gnome-adapter
        grep -Fq "Permit one unique showing window only for non-mutating orientation" /tmp/gnome-adapter
        grep -Fq "Das aktive GNOME-Fenster ist nicht eindeutig" /tmp/gnome-adapter
        grep -Fq "Der Ausgangsfokus ist nicht eindeutig" /tmp/gnome-adapter
        grep -Fq "def exactly_focused(expected: Any)" /tmp/gnome-adapter
        grep -Fq "Das benannte Element konnte nicht fokussiert werden" /tmp/gnome-adapter
        grep -Fq "Das aktive Fenster hat vor der Aktivierung gewechselt" /tmp/gnome-adapter
        grep -Fq "Das Bedienelement ist nicht mehr eindeutig an das aktive Fenster gebunden" /tmp/gnome-adapter
        grep -Fq "if rebound_window is not window" /tmp/gnome-adapter
        grep -Fq "Das aktive Fenster hat vor der nummerierten Aktivierung gewechselt" /tmp/gnome-adapter
        grep -Fq "Die Nummerierung der Bedienelemente hat sich geändert" /tmp/gnome-adapter
        grep -Fq "rebound_node is not original_node" /tmp/gnome-adapter
        grep -Fq "Der Berechtigungsdialog hat vor der Entscheidung gewechselt" /tmp/gnome-adapter
        grep -Fq "Das Erlauben-/Ablehnen-Paar hat sich vor der Entscheidung geändert" /tmp/gnome-adapter
        grep -Fq "rebound[key][0] is not matches[key][0]" /tmp/gnome-adapter
        grep -Fq "Die Fensterliste der Anwendung hat sich vor der Berechtigungsentscheidung" /tmp/gnome-adapter
        grep -Fq "Die Berechtigungsentscheidung wurde ausgelöst, aber der exakte" /tmp/gnome-adapter
        grep -Fq "Das aktive Fenster hat vor der Menüaktivierung gewechselt" /tmp/gnome-adapter
        grep -Fq "Menü oder Menüeintrag haben sich vor der Aktivierung geändert" /tmp/gnome-adapter
        grep -Fq "rebound_menu is not menu or rebound_item is not item" /tmp/gnome-adapter
        grep -Fq "def decide_file_dialog" /tmp/gnome-adapter
        grep -Fq "Der Dateidialog hat vor der Entscheidung gewechselt" /tmp/gnome-adapter
        grep -Fq "Das Bestätigen-/Abbrechen-Paar hat sich vor der Entscheidung geändert" /tmp/gnome-adapter
        grep -Fq "rebound[key][0] is not bound[key][0]" /tmp/gnome-adapter
        grep -Fq "Die Fensterliste der Anwendung hat sich vor der Dateidialogentscheidung" /tmp/gnome-adapter
        grep -Fq "Die Dateidialogentscheidung wurde ausgelöst, aber der exakte" /tmp/gnome-adapter
        grep -Fq "def decide_standard_dialog" /tmp/gnome-adapter
        grep -Fq "def read_standard_dialog" /tmp/gnome-adapter
        grep -Fq "def dismiss_standard_dialog" /tmp/gnome-adapter
        grep -Fq "Der Standarddialogtext überschreitet die sichere Grenze" /tmp/gnome-adapter
        grep -Fq "Das Schließen-Bedienelement hat sich vor der Aktivierung geändert" /tmp/gnome-adapter
        grep -Fq "aber der exakte Nachzustand" /tmp/gnome-adapter
        grep -Fq "candidate for candidate in windows if candidate is not window" /tmp/gnome-adapter
        grep -Fq "Die Fensterliste der Anwendung hat sich vor dem Schließen geändert" /tmp/gnome-adapter
        grep -Fq "Der Standarddialog hat vor der Entscheidung gewechselt" /tmp/gnome-adapter
        grep -Fq "Das Standarddialogpaar hat sich vor der Entscheidung geändert" /tmp/gnome-adapter
        grep -Fq "Die Fensterliste der Anwendung hat sich vor der Standarddialogentscheidung" /tmp/gnome-adapter
        grep -Fq "Die Standarddialogentscheidung wurde ausgelöst, aber der exakte" /tmp/gnome-adapter
        grep -Fq "(\"retry\", {\"retry\", \"wiederholen\"}" /tmp/gnome-adapter
        grep -Fq "(\"apply\", {\"apply\", \"anwenden\"}" /tmp/gnome-adapter
    '

printf '%s\n' \
    "ISO checksum, BIOS/UEFI boot, Hermes, licenses, speech model, accessibility setup, installer binding and recovery-key module verified."
