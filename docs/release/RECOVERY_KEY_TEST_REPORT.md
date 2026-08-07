# Clausis recovery-key implementation test report

Date: 2026-08-07  
Branch: `agent/clausis-recovery-key`  
Status: implementation validated; persistent installation and hardware release
gates remain open

## Verified

- 167 Python unit, policy, installer, accessibility and packaging tests passed
  both locally and during the Debian package build.
- Debian Calamares 3.3.14 compiled successfully with both public Clausis
  patches. The resulting `luksbootkeyfile` binary contains the guarded staging,
  enrollment, cleanup and success-marker paths.
- A real 32 MiB LUKS2 test container was formatted, the Clausis-format recovery
  key was added with `cryptsetup luksAddKey`, and `cryptsetup open
  --test-passphrase` accepted that key.
- A complete amd64 development ISO was rebuilt. Its SHA-256 is
  `76190948789368b782ef13c25badc4de16ab87e1f7b6b4056934c581ea2d2b2c`.
- ISO structure, checksum, BIOS and UEFI metadata, offline speech model,
  Hermes license, installer ordering, recovery module and guard timeout passed
  the image verifier.
- QEMU x86-64 emulation booted Linux 6.12.101, the live root and GDM. A second
  graphical run reached the Clausis-branded GNOME live session and setup app.

## Not yet verified

- A complete Calamares installation onto a persistent virtual disk.
- Unlock of that installed disk with the exact key spoken during installation.
- VirtualBox-specific audio and graphics behavior; VirtualBox is not installed
  on the build host, so QEMU was used for the current boot evidence.
- Physical separation of trusted confirmation audio from the desktop audio
  graph, the protected keyboard/Orca confirmation equivalent and replay or
  synthesized-voice resistance.
- TPM/FIDO2 enrollment, update rollback and supported physical hardware.

The ISO above is development evidence, not a replacement for the published
0.4.1 release asset and not a production release.
