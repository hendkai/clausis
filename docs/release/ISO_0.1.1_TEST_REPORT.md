# Clausis 0.1.1 ISO test report

Date: 2026-08-06  
Artifact: `dist/clausis-0.1.1-amd64.iso`
Size: 2,296,233,984 bytes (2.14 GiB)  
SHA-256: `42217e6d5328476e24386c2735df6158f86a1be3587a48ee394a2f71cfaff4a6`

## Passed automated evidence

- Built from an official Debian Stable (13/Trixie) amd64 container with
  live-build 20250505+deb13u1.
- The locally built `clausis-core_0.1.1-1_all.deb` installed successfully into
  the image; all 60 unit/security tests passed during that package build.
- The complete ISO media range was read by xorriso without a damaged region.
- El Torito contains a bootable BIOS image at `/isolinux/isolinux.bin` and a
  bootable UEFI image at `/boot/grub/efi.img`.
- `/live/filesystem.squashfs`, `/live/vmlinuz` and `/live/initrd.img` exist.
- A native-arm64 QEMU process emulated an x86-64 Q35 system, loaded the kernel
  and initramfs from the ISO, mounted the live system and successfully started
  `gdm.service` (GNOME Display Manager).
- The image build installed Faster-Whisper 1.2.1, sounddevice 0.5.5, the pinned
  `Systran/faster-whisper-base` model revision
  `ebe41f70d5b6dfa9166e2c581c45c9c0cfc57b66`, German/English locales,
  speech-dispatcher, eSpeak NG, Orca and Calamares.

## Not yet proven

- No physical PC has yet booted this exact checksum from USB.
- Microphone selection, speech latency, speaker output, Orca/Calamares behavior,
  Wi-Fi firmware and installation to a physical disk need hardware tests.
- The standard Calamares UI is spoken through Orca but installation fields are
  not yet controlled directly by the planned dedicated voice backend.
- Secure Boot signing, artifact signatures, Hermes provider setup, trusted
  voice PIN, TPM/LUKS integration and rollback are not complete.
- This is a technical preview and remains blocked from a production release.

## Reproduction

Run `./scripts/build_iso.sh`, `./scripts/verify_iso.sh` and
`./scripts/boot_smoke_iso.sh`. The Debian mirror can change over time; the
model revision and direct speech packages are pinned, but a complete lock of
all Debian and transitive Python packages remains future release work.
