from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class LiveImageConfigurationTests(unittest.TestCase):
    def test_linux_build_entrypoints_are_lf_only_and_attributes_preserve_them(self) -> None:
        attributes = (ROOT / ".gitattributes").read_text(encoding="utf-8")
        for rule in (
            "*.sh text eol=lf",
            "*.hook.chroot text eol=lf",
            "debian/rules text eol=lf",
            "packaging/bin/* text eol=lf",
            "packaging/live-build/auto/* text eol=lf",
            "packaging/live-build/build-in-container text eol=lf",
        ):
            self.assertIn(rule, attributes)

        entrypoints = (
            "debian/rules",
            "scripts/build_iso.sh",
            "scripts/verify_iso.sh",
            "packaging/live-build/build-in-container",
            "packaging/live-build/auto/config",
            "packaging/live-build/config/hooks/normal/020-clausis-audio.hook.chroot",
        )
        for relative in entrypoints:
            payload = (ROOT / relative).read_bytes()
            self.assertNotIn(b"\r\n", payload, relative)
            self.assertTrue(payload.startswith(b"#!"), relative)

        builder = (ROOT / "packaging/live-build/build-in-container").read_text(
            encoding="utf-8"
        )
        self.assertIn("find /build/clausis -type f -exec chmod 0644", builder)
        self.assertIn("xargs -0 grep -Il .", builder)
        self.assertIn("xargs -r sed -i 's/\\r$//'", builder)
        self.assertIn('chmod 0755 "/build/clausis/$executable"', builder)
        self.assertIn("debian/clausis-core.postinst debian/rules", builder)

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

    def test_virtual_machines_have_an_independent_acpi_power_fallback(self) -> None:
        package_list = (
            ROOT
            / "packaging/live-build/config/package-lists/clausis.list.chroot"
        ).read_text(encoding="utf-8").splitlines()
        event = (
            ROOT
            / "packaging/live-build/config/includes.chroot/etc/acpi/events"
            / "clausis-vm-power"
        ).read_text(encoding="utf-8")
        handler = (
            ROOT
            / "packaging/live-build/config/includes.chroot/usr/local/sbin"
            / "clausis-vm-power"
        ).read_text(encoding="utf-8")
        builder = (
            ROOT / "packaging/live-build/build-in-container"
        ).read_text(encoding="utf-8")

        self.assertIn("acpid", package_list)
        self.assertIn("event=button/power.*", event)
        self.assertIn("action=/usr/local/sbin/clausis-vm-power", event)
        self.assertIn("systemd-detect-virt --vm --quiet", handler)
        self.assertIn("exec systemctl --no-block poweroff", handler)
        self.assertNotIn("\n    systemctl poweroff", handler)
        self.assertIn(
            "includes.chroot/usr/local/sbin/clausis-vm-power", builder
        )

    def test_virtualbox_acpi_smoke_waits_for_real_guest_readiness(self) -> None:
        smoke = (ROOT / "scripts" / "vbox_acpi_smoke.ps1").read_text(encoding="utf-8")
        self.assertIn("GRUB readiness was not observed", smoke)
        self.assertIn("function Test-ClausisBranding", smoke)
        self.assertIn("$bitmap.GetPixel", smoke)
        self.assertIn("$purplePixels -gt 100", smoke)
        self.assertIn("Live desktop readiness was not observed", smoke)
        self.assertIn("keyboardputscancode 1c 9c", smoke)
        self.assertEqual(smoke.count("acpipowerbutton"), 1)
        self.assertIn('if ($info.uart1 -ne "off")', smoke)
        self.assertIn('if ($info["IDE-0-0"] -ne $iso)', smoke)
        self.assertIn('if ($info["SATA-0-0"] -ne $vdi)', smoke)
        self.assertIn("screenshotpng \"$EvidencePrefix-timeout.png\"", smoke)
        self.assertIn("controlvm $VmName poweroff", smoke)
        self.assertIn("[switch]$CaptureForeground", smoke)
        self.assertIn("keyboardputscancode 01 81", smoke)
        self.assertIn("[int]$ForegroundDelaySeconds = 3", smoke)
        self.assertIn("Start-Sleep -Seconds $ForegroundDelaySeconds", smoke)
        self.assertIn('screenshotpng "$EvidencePrefix-foreground.png"', smoke)
        self.assertIn("[switch]$CompleteOfflineSetupForDisposableInstaller", smoke)
        self.assertIn("Offline setup automation is restricted to a disposable installer VDI", smoke)
        self.assertIn("function Test-SetupWindow", smoke)
        self.assertIn("function Test-CalamaresWindow", smoke)
        self.assertIn("Clausis setup window readiness was not observed", smoke)
        self.assertIn("$setupReady = Test-SetupWindow", smoke)
        self.assertIn("SetupReadySeconds", smoke)
        self.assertIn("Clausis setup window did not close after save activation", smoke)
        self.assertIn("Calamares window readiness was not observed", smoke)
        self.assertIn("CalamaresReady", smoke)
        self.assertIn("[switch]$AdvanceCalamaresToPartitions", smoke)
        self.assertIn("Calamares navigation requires disposable offline setup completion", smoke)
        self.assertIn('"$EvidencePrefix-calamares-welcome-ready.png"', smoke)
        self.assertIn("keyboardputscancode 38 31 b1 b8", smoke)
        self.assertIn('@("location", "keyboard", "partitions")', smoke)
        self.assertIn("Start-Sleep -Seconds 15", smoke)
        self.assertIn('"$EvidencePrefix-calamares-$page.png"', smoke)
        self.assertIn("CalamaresNavigationInputSent", smoke)
        self.assertIn("function Test-CalamaresPartitionsPage", smoke)
        self.assertIn("$partitionsY = if ($darkTheme) { 383 } else { 363 }", smoke)
        self.assertIn("Calamares Partitions page was not visually observed", smoke)
        self.assertIn("function Test-TtyCommandProducedOutput", smoke)
        self.assertIn("Calamares log command produced no visible TTY output", smoke)
        self.assertIn("[switch]$SelectDisposableEraseDisk", smoke)
        self.assertIn("Erase selection requires navigation to disposable Partitions", smoke)
        self.assertIn('"$EvidencePrefix-calamares-erase-selected.png"', smoke)
        self.assertIn("function Test-EraseDiskSelected", smoke)
        self.assertIn("desktop.select_named_radio", smoke)
        self.assertIn("[Convert]::ToBase64String", smoke)
        self.assertIn("|base64 -d|env", smoke)
        self.assertIn("DBUS_SESSION_BUS_ADDRESS=", smoke)
        self.assertIn("XDG_RUNTIME_DIR=/run/user/1000", smoke)
        self.assertIn(".mutter-Xwaylandauth.*", smoke)
        self.assertIn("/tmp/clausis-atspi-erase.log", smoke)
        self.assertIn('"$EvidencePrefix-calamares-erase-atspi-error.png"', smoke)
        self.assertIn("keyboardputscancode 1d 38 3c bc b8 9d", smoke)
        self.assertIn("Disposable Erase disk selection was not visually observed", smoke)
        self.assertIn("DisposableEraseSelectionInputSent", smoke)
        self.assertIn("[switch]$InteractiveGui", smoke)
        self.assertIn("Interaction hold requires GUI navigation", smoke)
        self.assertIn('if ($InteractiveGui) { "gui" } else { "headless" }', smoke)
        self.assertIn('"$EvidencePrefix-calamares-after-interaction.png"', smoke)
        self.assertIn("[switch]$CaptureCalamaresLog", smoke)
        self.assertIn("Calamares log capture and navigation must run separately", smoke)
        self.assertIn("keyboardputscancode 1d 38 3d bd b8 9d", smoke)
        self.assertIn("sudo tail -120 /root/.cache/calamares/session.log", smoke)
        self.assertIn("Start-Sleep -Seconds 60", smoke)
        self.assertIn('"$EvidencePrefix-calamares-log.png"', smoke)
        self.assertIn("$grayPixels -gt 3000", smoke)
        self.assertIn("$lightPixels -gt 3000", smoke)
        self.assertIn('"$EvidencePrefix-before-save.png"', smoke)
        self.assertIn("keyboardputscancode 0f 8f 0f 8f", smoke)
        self.assertIn("keyboardputscancode 1c 9c", smoke)
        self.assertIn("OfflineSetupInputSent", smoke)
        self.assertNotIn("OfflineSetupActivated", smoke)
        self.assertIn("keyboardputscancode 38 19 99 b8", smoke)
        self.assertIn("keyboardputscancode 38 11 91 b8", smoke)
        self.assertIn('screenshotpng "$EvidencePrefix-after-setup.png"', smoke)
        self.assertIn("TestDisposableRecoveryGuardFailClosed", smoke)
        self.assertIn("Recovery guard probe is restricted to a disposable installer VDI", smoke)
        self.assertIn("function Test-RecoveryGuardFailClosed", smoke)
        self.assertIn("RECOVERY_GUARD_FAIL_CLOSED_OK", smoke)
        self.assertIn("dd if=/dev/sda bs=1M count=4", smoke)
        self.assertIn("! sudo sfdisk -d /dev/sda", smoke)
        self.assertIn("echo $out|grep -q denied", smoke)
        self.assertIn("TTY3 auto-login prints its banner asynchronously", smoke)
        self.assertIn("keyboardputscancode 1d 2e ae 9d", smoke)
        self.assertIn("Do not race Enter against its final bytes", smoke)
        self.assertIn("Start-Sleep -Seconds 180", smoke)
        self.assertIn('RecoveryGuardFailClosed = [bool]$recoveryGuardFailClosed', smoke)
        self.assertIn('ForcedDisposableCleanup = [bool]$forcedDisposableCleanup', smoke)
        self.assertIn("independent from the separate ACPI release gate", smoke)

    def test_virtualbox_acpi_soak_repeats_one_shot_readiness_gate_fail_closed(self) -> None:
        soak = (ROOT / "scripts" / "vbox_acpi_soak.ps1").read_text(encoding="utf-8")
        self.assertIn("[ValidateRange(2, 20)]", soak)
        self.assertIn("[int]$Runs = 5", soak)
        self.assertIn('Join-Path $PSScriptRoot "vbox_acpi_smoke.ps1"', soak)
        self.assertIn("for ($run = 1; $run -le $Runs; $run++)", soak)
        self.assertIn("$resultItems = @($result)", soak)
        self.assertIn("$resultItems.Count -ne 1", soak)
        self.assertIn("$result.IsoSha256 -ne $expectedHash", soak)
        self.assertIn('$result.FinalState -ne "poweroff"', soak)
        self.assertIn("CompletedRuns = $results.Count", soak)
        self.assertIn("Passed = $completed -and $results.Count -eq $Runs", soak)
        self.assertIn("ConvertTo-Json -Depth 4", soak)

    def test_virtualbox_install_sandbox_never_uses_an_existing_disk(self) -> None:
        sandbox = (ROOT / "scripts" / "vbox_install_sandbox.ps1").read_text(
            encoding="utf-8"
        )
        self.assertIn("clausis-install-sandbox-{0}", sandbox)
        self.assertIn("Disposable sandbox path escaped the project dist directory", sandbox)
        self.assertIn("createmedium disk --filename $vdi", sandbox)
        self.assertIn("Disposable VDI escaped its sandbox directory", sandbox)
        self.assertIn("$existingVmExitCode = 1", sandbox)
        self.assertIn('$ErrorActionPreference = "Continue"', sandbox)
        self.assertIn("$vboxExitCode = $LASTEXITCODE", sandbox)
        self.assertIn("--type hdd --medium $resolvedVdi", sandbox)
        self.assertIn("--audio-enabled on --audio-out on", sandbox)
        self.assertIn('[switch]$InventoryDisposableAudio', sandbox)
        self.assertIn(
            '--audio-in $(if ($InventoryDisposableAudio -or '
            '$TestDisposablePipeWireLoopback -or',
            sandbox,
        )
        self.assertIn("Audio inventory must run as a separate disposable probe", sandbox)
        self.assertIn('[switch]$TestDisposablePipeWireLoopback', sandbox)
        self.assertIn("PipeWire loopback must run as a separate disposable probe", sandbox)
        self.assertIn('[switch]$TestDisposableRecoveryReadback', sandbox)
        self.assertIn("Recovery readback must run as a separate disposable probe", sandbox)

        self.assertIn("-ExpectedVdi $resolvedVdi", sandbox)
        self.assertIn("-CaptureForeground", sandbox)
        self.assertIn("[int]$ForegroundDelaySeconds = 45", sandbox)
        self.assertIn("-ForegroundDelaySeconds $ForegroundDelaySeconds", sandbox)
        self.assertIn("[switch]$AdvanceOfflineSetup", sandbox)
        self.assertIn("[switch]$AdvanceCalamaresToPartitions", sandbox)
        self.assertIn("Calamares navigation requires -AdvanceOfflineSetup", sandbox)
        self.assertIn("-CompleteOfflineSetupForDisposableInstaller:$AdvanceOfflineSetup", sandbox)
        self.assertIn("-AdvanceCalamaresToPartitions:$AdvanceCalamaresToPartitions", sandbox)
        self.assertIn("OfflineSetupInputSent", sandbox)
        self.assertIn("$smokeResult.CalamaresReady", sandbox)
        self.assertIn("CalamaresNavigationInputSent", sandbox)
        self.assertIn("[switch]$SelectDisposableEraseDisk", sandbox)
        self.assertIn("Erase selection requires -AdvanceCalamaresToPartitions", sandbox)
        self.assertIn("-SelectDisposableEraseDisk:$SelectDisposableEraseDisk", sandbox)
        self.assertIn("DisposableEraseSelectionInputSent", sandbox)
        self.assertIn("-InteractiveGui:$InteractiveGui", sandbox)
        self.assertIn("-InteractionHoldSeconds $InteractionHoldSeconds", sandbox)
        self.assertIn("[switch]$CaptureCalamaresLog", sandbox)
        self.assertIn("-CaptureCalamaresLog:$CaptureCalamaresLog", sandbox)
        self.assertIn("CalamaresLogCaptured", sandbox)
        self.assertIn("TestDisposableRecoveryGuardFailClosed", sandbox)
        self.assertIn("Disposable VM did not complete the recovery guard gate", sandbox)
        self.assertIn("Recovery guard probe did not record forced disposable cleanup", sandbox)
        self.assertIn("-not $smokeResult.ForegroundCaptured", sandbox)
        self.assertIn("$cleanupAttempt -lt 20", sandbox)
        self.assertIn("Start-Sleep -Milliseconds 250", sandbox)
        self.assertIn("unregistervm $vmName --delete", sandbox)
        self.assertIn("Remove-Item -LiteralPath $sandboxRoot -Recurse -Force", sandbox)
        self.assertIn("SandboxRemoved = $removed", sandbox)

    def test_installer_bridge_uses_pinned_voice_runtime(self) -> None:
        bridge = (ROOT / "scripts" / "calamares_clausis.py").read_text(
            encoding="utf-8"
        )
        self.assertTrue(bridge.startswith("#!/opt/clausis/bin/python\n"))

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
        self.assertIn('"${install_dir}/apps/desktop/assets/icon.png"', hook)
        self.assertIn("/usr/share/pixmaps/hermes-agent.png", hook)

        audio_hook = (
            ROOT
            / "packaging/live-build/config/hooks/normal/020-clausis-audio.hook.chroot"
        ).read_text(encoding="utf-8")
        self.assertIn("websocket-client==1.9.0", audio_hook)

    def test_faster_whisper_download_is_pinned_and_retried_without_xet(self) -> None:
        hook = (
            ROOT
            / "packaging/live-build/config/hooks/normal/020-clausis-audio.hook.chroot"
        ).read_text(encoding="utf-8")
        self.assertIn("HF_HUB_DISABLE_XET=1", hook)
        self.assertIn("HF_HUB_DISABLE_TELEMETRY=1", hook)
        self.assertIn('revision="ebe41f70d5b6dfa9166e2c581c45c9c0cfc57b66"', hook)
        self.assertIn('if [ "$attempt" -ge 3 ]', hook)
        self.assertIn("sleep $((attempt * 5))", hook)

    def test_faster_whisper_offline_cache_requires_exact_manifest(self) -> None:
        hook = (
            ROOT
            / "packaging/live-build/config/hooks/normal/020-clausis-audio.hook.chroot"
        ).read_text(encoding="utf-8")
        builder = (ROOT / "packaging/live-build/build-in-container").read_text(
            encoding="utf-8"
        )
        manifest = (
            ROOT
            / "packaging/live-build/config/includes.chroot/usr/share/clausis/models"
            / "faster-whisper-base.sha256"
        ).read_text(encoding="utf-8").splitlines()

        self.assertEqual(len(manifest), 4)
        self.assertEqual(
            {line.split()[-1] for line in manifest},
            {"config.json", "model.bin", "tokenizer.json", "vocabulary.txt"},
        )
        self.assertTrue(all(len(line.split()[0]) == 64 for line in manifest))
        self.assertIn("sha256sum -c \"$model_manifest\"", hook)
        self.assertIn("sha256sum -c \"$model_manifest\"", builder)
        self.assertIn("/output/faster-whisper-base-cache", builder)
        self.assertIn('install -m 0644 "$model_cache/$model_file"', builder)

    def test_accessibility_setup_runs_before_calamares(self) -> None:
        welcome = (
            ROOT
            / "packaging/live-build/config/includes.chroot/usr/local/bin"
            / "clausis-live-welcome"
        ).read_text(encoding="utf-8")

        self.assertLess(welcome.index("orca --replace"), welcome.index("clausis-setup"))
        self.assertLess(welcome.index("clausis-setup"), welcome.index("sudo --preserve-env"))
        live_branch = welcome[
            welcome.index('if [ "$live_system" -eq 1 ]') :
            welcome.index("# The same autostart file")
        ]
        self.assertIn('spd-say -l de "$notice"', live_branch)
        self.assertNotIn('spd-say -w -l de "$notice"', live_branch)
        self.assertIn("QT_ACCESSIBILITY=1", welcome)
        self.assertIn("QT_LINUX_ACCESSIBILITY_ALWAYS_ON=1", welcome)
        self.assertIn("NO_AT_BRIDGE=0", welcome)
        self.assertIn("sudo --preserve-env=DISPLAY,XAUTHORITY", welcome)
        self.assertIn("org.a11y.Bus.GetAddress", welcome)
        self.assertIn("AT_SPI_BUS_ADDRESS", welcome)
        self.assertNotIn("calamares-install-debian", welcome)
        self.assertIn("realtime_enabled", welcome)
        self.assertIn("GPT Live begleitet", welcome)
        self.assertIn("lokale Clausis Sprachsteuerung begleitet", welcome)
        self.assertLess(
            welcome.index("clausis-live-assistant >/dev/null"),
            welcome.index("sudo --preserve-env"),
        )

        setup_source = (ROOT / "src/clausis/setup_app.py").read_text(
            encoding="utf-8"
        )
        self.assertIn("Gtk.ScrolledWindow()", setup_source)
        self.assertIn("Gtk.InputPurpose.PIN", setup_source)

        welcome_module = (
            ROOT
            / "packaging/live-build/config/includes.chroot/etc/calamares/modules"
            / "welcome.conf"
        ).read_text(encoding="utf-8")
        self.assertIn("requiredStorage: 15", welcome_module)
        self.assertIn("requiredRam: 1.0", welcome_module)
        self.assertIn("- storage", welcome_module)
        self.assertIn("- ram", welcome_module)
        self.assertIn("- root", welcome_module)
        self.assertNotIn("- power", welcome_module)

        locale_module = (
            ROOT
            / "packaging/live-build/config/includes.chroot/etc/calamares/modules"
            / "locale.conf"
        ).read_text(encoding="utf-8")
        self.assertIn('region: "Europe"', locale_module)
        self.assertIn('zone: "Berlin"', locale_module)
        self.assertIn('style: "none"', locale_module)

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
            welcome.index("sudo --preserve-env", live_branch),
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
        self.assertIn("Icon=hermes-agent", launcher)
        self.assertNotIn("Icon=clausis-logo", launcher)

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
        self.assertIn("--guard-transaction", module)
        self.assertIn("${gs[clausisSelectedDevice]}", module)
        self.assertIn("${gs[clausisInstallMode]}", module)
        self.assertIn("/usr/libexec/calamares-clausis/calamares_clausis.py", module)
        self.assertIn("${gs[clausisEncryptionEnabled]}", module)
        self.assertIn("apt-get source calamares=3.3.14-1", dockerfile)
        self.assertIn("0002-install-clausis-recovery-key.patch", dockerfile)
        self.assertIn("0003-bound-os-prober-timeout.patch", dockerfile)
        os_prober_patch = (
            ROOT
            / "packaging/live-build/patches/calamares/0003-bound-os-prober-timeout.patch"
        ).read_text(encoding="utf-8")
        self.assertIn("waitForFinished( 15000 )", os_prober_patch)
        self.assertIn("osprober.kill()", os_prober_patch)
        self.assertIn("waitForFinished( 2000 )", os_prober_patch)
        self.assertIn("timeout: 300", module)
        self.assertIn('gs->insert( "clausisSelectedDevice"', patch_source)
        self.assertIn('gs->insert( "clausisInstallMode"', patch_source)
        self.assertIn("InstallChoice::Erase", patch_source)
        verifier = (ROOT / "scripts/verify_iso.sh").read_text(encoding="utf-8")
        self.assertIn('grep -Fxq "clausisInstallMode"', verifier)
        self.assertIn('grep -Fq "clausisInstallMode"', verifier)
        self.assertIn("calamares-clausis-bridge", verifier)
        self.assertIn('grep -Fq "args.install_mode not in"', verifier)
        self.assertIn("invalid or missing Calamares install mode", verifier)
        self.assertIn("except subprocess.TimeoutExpired", verifier)
        self.assertIn("Never replay it through another backend", verifier)
        self.assertIn("/run/clausis-installer/recovery.key", recovery_patch)
        self.assertIn("/run/clausis-installer/recovery-installed", recovery_patch)
        self.assertIn("luksAddKey", recovery_patch)
        self.assertIn("removeStagedRecoveryKey", recovery_patch)
        self.assertIn("recoveryState == RecoveryKeyState::Absent", recovery_patch)
        self.assertIn("A confirmed Clausis recovery key is required", recovery_patch)
        self.assertNotIn("luksPassphrase", module)
        bridge = (ROOT / "scripts/calamares_clausis.py").read_text(encoding="utf-8")
        self.assertIn("DirectInstallConfirmation", bridge)
        self.assertIn("calamares_prewrite_summary", bridge)
        self.assertIn("stage_recovery_key", bridge)
        self.assertIn("discard_staged_recovery_key", bridge)
        self.assertIn('args.install_mode not in {"erase", "other"}', bridge)
        self.assertIn("invalid or missing Calamares install mode", bridge)
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
        self.assertIn("wl-clipboard", packages)
