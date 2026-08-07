# Clausis 0.2.0 ISO test report

Date: 2026-08-06

Status: public technical preview; not approved for production use.

## Artifact

- File: `clausis-0.2.0-amd64.iso`
- Size: 2,609,577,984 bytes
- SHA-256: `b02eeccddcaa93af66abc5e7f2979c05a504b867f936b3402e254996fa920c87`
- Windows-safe parts: `part-aa` (1.9 GiB) and `part-ab` (589 MiB)
- Concatenating both parts reproduced the exact ISO SHA-256.

## Passed automated checks

- 88 Python unit and integration tests.
- Clean Debian Stable amd64 binary-package build.
- ISO checksum and media readability.
- Hybrid BIOS and UEFI boot entries.
- Pinned Hermes Agent 0.20.0, frozen dependency resolution and complete MIT
  license files in the final SquashFS.
- Bundled local Faster-Whisper model and speech runtime.
- Accessible Clausis setup, protected Hermes launcher and Calamares handoff
  configuration in the final SquashFS.
- No-follow, bounded and atomic transfer code for staged Hermes settings.
- GNOME initial-setup marker and compiled dconf default that suppress Debian's
  tour in favour of the Clausis first-run dialog.
- x86-64 QEMU boot reached kernel, initramfs, live root and GDM.
- A graphical QEMU capture confirmed an authenticated live GNOME session with
  no login prompt and no Debian tour in front. The visible foreground window
  was `Clausis einrichten`, including provider selection, protected API-key
  entry, cloud consent, voice selection and the continue-to-install action.

The retained local evidence image is `dist/clausis-0.2.0-boot-screen.png`.

## Not established by this report

- A complete Calamares install to a physical disk or a persistent VirtualBox
  disk was not performed.
- Physical microphone, speaker, Bluetooth, Wi-Fi, USB boot and diverse audio
  hardware were not tested.
- Voice-controlled partitioning is not implemented; Calamares remains
  keyboard- and Orca-operable.
- Wake word, true barge-in, echo cancellation, voice PIN, LUKS/TPM binding,
  FIDO2 and automatic snapshot rollback remain future work.
- OAuth subscription login is not present; current cloud providers use API
  keys entered by keyboard.
- No blind-user study, human security review, privacy sign-off, signed release
  chain or production support commitment has been completed.
