# Clausis 0.4.1 ISO test report

Date: 2026-08-07
Status: development evidence; not a production release approval

## Artifact

- File: `clausis-0.4.1-amd64.iso`
- Size: 2,643,034,112 bytes
- SHA-256: `a998cfa905e8545bc821c3ad7d635d57a8d2af9bb0004bc58c479d71405496c6`
- Base: Debian 13 stable, amd64, GNOME 48

## Passed checks

- The hybrid image has both BIOS and UEFI boot entries and its media check and
  SHA-256 verification pass.
- The final SquashFS contains Clausis Core, Hermes Agent 0.20.0, its MIT
  license, the pinned offline Faster-Whisper model, Orca, the setup application,
  the Clausis GNOME/GDM identity and Calamares configuration.
- The image contains the Clausis Calamares build
  `3.3.14-1+clausis11`. Its partition module exports only the selected device,
  encryption state and filesystem; it does not export the LUKS passphrase.
- The Calamares execution queue runs `shellprocess@clausis-guard` immediately
  before the first `partition` job and retains LUKS2/Btrfs whole-disk defaults
  without preselecting erase.
- A QEMU TCG boot from the exact ISO reached Debian kernel
  `6.12.101+deb13-amd64` and the running GNOME Display Manager.
- A separate graphical QEMU run reached the automatically authenticated live
  GNOME session. Visual review confirmed the Clausis wallpaper, matching
  purple/cyan identity, branded launchers, visible AI notice and the accessible
  Clausis/Hermes setup without a login prompt or Debian tour.

## Still not proven

- A complete persistent Calamares installation onto a virtual or physical disk.
- VirtualBox-specific firmware, graphics, audio and installation behavior.
- Real microphone, speaker, echo cancellation, Barge-in and trusted-audio
  isolation on supported hardware.
- The ISO documented here predates the protected-phrase integration. A newer
  image must be built after that code change. Recovery-key export is still not
  connected to the exact pre-write transaction, so production release remains
  blocked.
