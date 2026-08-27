from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class LiveImageConfigurationTests(unittest.TestCase):
    def test_release_artifacts_share_one_authoritative_project_version(self) -> None:
        pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
        self.assertIn('version = "0.6.0"', pyproject)
        self.assertIn(
            '__version__ = "0.6.0"',
            (ROOT / "src/clausis/__init__.py").read_text(encoding="utf-8"),
        )
        self.assertIn(
            'version="0.6.0"',
            (ROOT / "setup.py").read_text(encoding="utf-8"),
        )
        self.assertIn(
            '"version": "0.6.0"',
            (ROOT / "sbom.cdx.json").read_text(encoding="utf-8"),
        )
        self.assertTrue(
            (ROOT / "debian/changelog")
            .read_text(encoding="utf-8")
            .startswith("clausis-core (0.6.0-1)")
        )
        for relative in (
            "scripts/build_iso.sh",
            "scripts/verify_iso.sh",
            "scripts/boot_smoke_iso.sh",
            "scripts/graphical_smoke_iso.sh",
            "scripts/reassemble_iso.sh",
        ):
            script = (ROOT / relative).read_text(encoding="utf-8")
            self.assertIn("project_version.sh", script)
            self.assertNotIn("clausis-0.4.1-amd64.iso", script)

        workflow = (ROOT / ".github/workflows/release.yml").read_text(
            encoding="utf-8"
        )
        self.assertIn('test "$RELEASE_TAG" = "v$version"', workflow)
        self.assertIn("$CLAUSIS_ISO", workflow)
        self.assertNotIn("clausis-0.4.1-amd64.iso", workflow)

    def test_debian_initial_setup_is_suppressed_for_new_users(self) -> None:
        marker = (
            ROOT
            / "packaging/live-build/config/includes.chroot/etc/skel/.config"
            / "gnome-initial-setup-done"
        )

        self.assertTrue(marker.is_file())

        dconf_defaults = (
            ROOT
            / "packaging/live-build/config/includes.chroot/etc/dconf/db/local.d"
            / "00-clausis"
        ).read_text(encoding="utf-8")
        dconf_profile = (
            ROOT
            / "packaging/live-build/config/includes.chroot/etc/dconf/profile/user"
        ).read_text(encoding="utf-8")
        desktop_hook = (
            ROOT
            / "packaging/live-build/config/hooks/normal/030-clausis-desktop.hook.chroot"
        ).read_text(encoding="utf-8")

        self.assertIn("welcome-dialog-last-shown-version='999'", dconf_defaults)
        self.assertIn("system-db:local", dconf_profile)
        self.assertIn("dconf update", desktop_hook)

    def test_graphical_live_autologin_dependencies_are_present(self) -> None:
        package_list = (
            ROOT
            / "packaging/live-build/config/package-lists/clausis.list.chroot"
        ).read_text(encoding="utf-8").splitlines()

        self.assertIn("gdm3", package_list)
        self.assertIn("live-config-systemd", package_list)
        self.assertIn("user-setup", package_list)
        self.assertIn("python3-pyatspi", package_list)

    def test_user_runtime_executes_only_validated_session_actions(self) -> None:
        service = (
            ROOT / "packaging/systemd/clausis-runtime.service"
        ).read_text(encoding="utf-8")

        self.assertIn("ExecStart=/usr/bin/clausis-session-runtime", service)
        self.assertIn("RestartSec=30", service)
        self.assertIn("NoNewPrivileges=yes", service)
        self.assertIn("RestrictAddressFamilies=AF_UNIX", service)

        release_workflow = (ROOT / ".github/workflows/release.yml").read_text(
            encoding="utf-8"
        )
        self.assertIn("./scripts/atspi_smoke.sh", release_workflow)
        self.assertIn("./scripts/dbus_smoke.sh", release_workflow)

    def test_live_user_is_selected_on_the_kernel_command_line(self) -> None:
        config = (ROOT / "packaging/live-build/auto/config").read_text(
            encoding="utf-8"
        )
        self.assertIn("boot=live", config)
        self.assertIn("username=clausis", config)

    def test_debian_13_live_password_compatibility_hook_is_installed(self) -> None:
        hook = (
            ROOT
            / "packaging/live-build/config/includes.chroot/usr/lib/live/config"
            / "0035-clausis-live-user"
        ).read_text(encoding="utf-8")

        self.assertIn("usermod --password", hook)
        self.assertIn("usermod --append --groups clausis-control", hook)
        self.assertIn("chage --expiredate -1", hook)
        self.assertNotIn("clausis:live", hook)

    def test_service_group_does_not_collide_with_live_username(self) -> None:
        postinst = (ROOT / "debian/clausis-core.postinst").read_text(encoding="utf-8")

        self.assertIn("group clausis-control", postinst)
        self.assertNotIn("group clausis >/dev/null", postinst)

    def test_trusted_confirmation_has_no_automatable_approve_api(self) -> None:
        from clausis.dbus_api import TRUSTED_CONFIRM_XML

        self.assertIn("ConfirmAndSubmit", TRUSTED_CONFIRM_XML)
        self.assertNotIn("Approve", TRUSTED_CONFIRM_XML)
        self.assertNotIn("phrase", TRUSTED_CONFIRM_XML)
        self.assertNotIn("pin", TRUSTED_CONFIRM_XML.casefold())
        self.assertNotIn("capability", TRUSTED_CONFIRM_XML)

        unit = (
            ROOT / "packaging/systemd/clausis-trusted-confirm.service"
        ).read_text(encoding="utf-8")
        self.assertIn("ConditionPathExists=/etc/clausis/voice-pin.json", unit)
        self.assertIn("SupplementaryGroups=clausis-control", unit)
        self.assertIn("ProtectProc=invisible", unit)
        self.assertIn("ExecStart=/usr/bin/clausis-trusted-confirm-runtime", unit)

        launcher = (
            ROOT / "packaging/bin/clausis-trusted-confirm-runtime"
        ).read_text(encoding="utf-8")
        self.assertIn("/opt/clausis/bin/python", launcher)
        self.assertIn("faster_whisper, sounddevice, clausis", launcher)
        activation = (
            ROOT / "packaging/dbus/org.clausis.TrustedConfirm1.service"
        ).read_text(encoding="utf-8")
        self.assertIn("Exec=/usr/bin/clausis-trusted-confirm-runtime", activation)

    def test_hermes_agent_is_pinned_and_preinstalled(self) -> None:
        hook = (
            ROOT
            / "packaging/live-build/config/hooks/normal/025-hermes-agent.hook.chroot"
        ).read_text(encoding="utf-8")

        self.assertIn("0957277f2f468bac22bbfcfa7c43029858c9597e", hook)
        self.assertIn("uv sync", hook)
        self.assertIn("uv_version='0.9.28'", hook)
        self.assertIn("/opt/clausis-hermes-updater/bin/uv", hook)
        self.assertIn("--frozen", hook)
        self.assertIn("--extra anthropic", hook)
        self.assertIn("/usr/local/bin/hermes", hook)
        self.assertIn("/usr/share/doc/hermes-agent/LICENSE", hook)

        audio_hook = (
            ROOT
            / "packaging/live-build/config/hooks/normal/020-clausis-audio.hook.chroot"
        ).read_text(encoding="utf-8")
        self.assertIn("websocket-client==1.9.0", audio_hook)

    def test_accessibility_setup_runs_before_calamares(self) -> None:
        welcome = (
            ROOT
            / "packaging/live-build/config/includes.chroot/usr/local/bin"
            / "clausis-live-welcome"
        ).read_text(encoding="utf-8")

        self.assertLess(welcome.index("orca --replace"), welcome.index("clausis-setup"))
        self.assertLess(welcome.index("clausis-setup"), welcome.index("calamares-install-debian"))
        self.assertIn("QT_ACCESSIBILITY=1", welcome)
        self.assertIn("realtime_enabled", welcome)
        self.assertIn("GPT Live begleitet", welcome)
        self.assertIn("lokale Clausis Sprachsteuerung begleitet", welcome)
        self.assertLess(
            welcome.index("clausis-live-assistant >/dev/null"),
            welcome.index("calamares-install-debian"),
        )

        setup_source = (ROOT / "src/clausis/setup_app.py").read_text(
            encoding="utf-8"
        )
        self.assertIn("Gtk.ScrolledWindow()", setup_source)
        self.assertIn("Gtk.InputPurpose.PIN", setup_source)

    def test_installed_autostart_never_reopens_installer(self) -> None:
        welcome = (
            ROOT
            / "packaging/live-build/config/includes.chroot/usr/local/bin"
            / "clausis-live-welcome"
        ).read_text(encoding="utf-8")

        self.assertIn("live_system=0", welcome)
        self.assertIn('if [ "$live_system" -eq 1 ]', welcome)
        live_branch = welcome.index('if [ "$live_system" -eq 1 ]')
        installed_branch = welcome.index("# The same autostart file")
        self.assertLess(
            welcome.index("calamares-install-debian", live_branch),
            welcome.index("exit 0", live_branch),
        )
        self.assertLess(welcome.index("exit 0", live_branch), installed_branch)
        self.assertIn("clausis-live-assistant", welcome)
        self.assertIn("clausis-setup --installed", welcome)
        self.assertIn("Stopp Hermes", welcome)
        self.assertNotIn("assistant.log", welcome)
        self.assertIn("chmod 0700", welcome)
        self.assertIn("user_id=$(id -u)", welcome)
        self.assertNotIn("${UID}", welcome)

        session_launcher = (
            ROOT / "packaging/bin/clausis-session-runtime"
        ).read_text(encoding="utf-8")
        self.assertIn("/opt/clausis/bin/python", session_launcher)
        self.assertIn("clausis.assistant --execute", session_launcher)
        self.assertIn("clausis-session-runtime", (
            ROOT
            / "packaging/live-build/config/includes.chroot/usr/local/bin"
            / "clausis-live-assistant"
        ).read_text(encoding="utf-8"))

        stop_launcher = (
            ROOT
            / "packaging/live-build/config/includes.chroot/usr/share/applications"
            / "clausis-gpt-live-stop.desktop"
        ).read_text(encoding="utf-8")
        self.assertIn("GPT Live sofort beenden", stop_launcher)
        self.assertIn("--stop-live", stop_launcher)

        launcher = (
            ROOT
            / "packaging/live-build/config/includes.chroot/usr/share/applications"
            / "clausis-setup.desktop"
        ).read_text(encoding="utf-8")
        self.assertIn("Exec=clausis-setup --installed", launcher)

    def test_desktop_hermes_chat_forces_the_minimal_toolset(self) -> None:
        launcher = (
            ROOT
            / "packaging/live-build/config/includes.chroot/usr/share/applications"
            / "clausis-hermes-chat.desktop"
        ).read_text(encoding="utf-8")

        self.assertIn("hermes --toolsets todo", launcher)

    def test_calamares_copies_staged_hermes_config_after_user_creation(self) -> None:
        hook = (
            ROOT
            / "packaging/live-build/config/hooks/normal/035-clausis-calamares.hook.chroot"
        ).read_text(encoding="utf-8")
        module = (
            ROOT / "packaging/calamares/shellprocess@clausis.conf"
        ).read_text(encoding="utf-8")

        self.assertIn("/^  - users$/a", hook)
        self.assertIn("shellprocess@clausis", hook)
        self.assertIn("id: clausis", hook)
        self.assertIn("config: shellprocess@clausis.conf", hook)
        self.assertIn("clausis-finalize-hermes-install", module)
        self.assertIn("${ROOT}", module)
        self.assertIn("${USER}", module)
        self.assertIn("timeout: 1800", module)

        welcome = (
            ROOT
            / "packaging/live-build/config/includes.chroot/usr/local/bin"
            / "clausis-live-welcome"
        ).read_text(encoding="utf-8")
        self.assertIn("neuesten offiziellen stabilen Version", welcome)
        self.assertIn("bundled-fallback", welcome)

    def test_calamares_target_guard_runs_before_first_partition_job(self) -> None:
        hook = (
            ROOT
            / "packaging/live-build/config/hooks/normal/035-clausis-calamares.hook.chroot"
        ).read_text(encoding="utf-8")
        module = (
            ROOT / "packaging/calamares/shellprocess@clausis-guard.conf"
        ).read_text(encoding="utf-8")
        dockerfile = (ROOT / "packaging/live-build/Dockerfile").read_text(
            encoding="utf-8"
        )
        patch_source = (
            ROOT
            / "packaging/live-build/patches/calamares/0001-export-selected-device-metadata.patch"
        ).read_text(encoding="utf-8")
        recovery_patch = (
            ROOT
            / "packaging/live-build/patches/calamares/0002-install-clausis-recovery-key.patch"
        ).read_text(encoding="utf-8")

        self.assertIn('/^  - partition$/i\\  - shellprocess@clausis-guard', hook)
        self.assertIn("id: clausis-guard", hook)
        self.assertIn("config: shellprocess@clausis-guard.conf", hook)
        self.assertIn("--guard-transaction", module)
        self.assertIn("${gs[clausisSelectedDevice]}", module)
        self.assertIn("${gs[partitionChoices.install]}", module)
        self.assertIn("${gs[clausisEncryptionEnabled]}", module)
        self.assertIn("apt-get source calamares=3.3.14-1", dockerfile)
        self.assertIn("0002-install-clausis-recovery-key.patch", dockerfile)
        self.assertIn("timeout: 300", module)
        self.assertIn('gs->insert( "clausisSelectedDevice"', patch_source)
        self.assertIn("/run/clausis-installer/recovery.key", recovery_patch)
        self.assertIn("/run/clausis-installer/recovery-installed", recovery_patch)
        self.assertIn("luksAddKey", recovery_patch)
        self.assertIn("removeStagedRecoveryKey", recovery_patch)
        self.assertNotIn("luksPassphrase", module)
        bridge = (ROOT / "scripts/calamares_clausis.py").read_text(encoding="utf-8")
        self.assertIn("DirectInstallConfirmation", bridge)
        self.assertIn("calamares_prewrite_summary", bridge)
        self.assertIn("stage_recovery_key", bridge)
        self.assertIn("discard_staged_recovery_key", bridge)
        self.assertNotIn("--phrase", module)

    def test_calamares_defaults_are_encrypted_btrfs_but_never_preselect_erase(self) -> None:
        partition = (ROOT / "packaging/calamares/partition.conf").read_text(
            encoding="utf-8"
        )
        packages = (
            ROOT / "packaging/live-build/config/package-lists/clausis.list.chroot"
        ).read_text(encoding="utf-8").splitlines()

        self.assertIn("initialPartitioningChoice: none", partition)
        self.assertIn("luksGeneration: luks2", partition)
        self.assertIn("preCheckEncryption: true", partition)
        self.assertIn('defaultFileSystemType: "btrfs"', partition)
        self.assertIn('mountPoint: "/boot"', partition)
        self.assertIn("noEncrypt: true", partition)
        self.assertIn("cryptsetup-initramfs", packages)
