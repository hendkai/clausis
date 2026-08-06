# Clausis 0.1.2 ISO test report

Date: 2026-08-06

Artifact: `clausis-0.1.2-amd64.iso`

- Size: 2,296,233,984 bytes
- SHA-256: `0352d62e51682c4e4e7dca13b718050928b28a67b1211d521bf441d034f637ce`
- Target: x86-64, Debian 13 stable, GNOME

## Automated checks

- 67 unit, security, injection, branding and live-configuration tests passed.
- The ISO checksum, ISO9660 media structure, live filesystem, BIOS boot entry
  and UEFI boot entry were verified by `scripts/verify_iso.sh`.
- `user-setup` 1.107 and `live-config-systemd` 11.0.5 are present in the live
  filesystem.
- The Clausis GRUB splash is an 800×600 RGB PNG; the Syslinux splash is a
  640×480 RGB PNG.

## Graphical boot validation

The final artifact was booted with its kernel, initramfs and ISO filesystem in
x86-64 QEMU 10.0.11 using a Q35 machine, two emulated CPUs and 4 GiB RAM.
The `clausis` live account was created successfully and GDM entered its GNOME
session automatically. No username or password prompt appeared. The normal
one-time GNOME tour dialog was shown inside the authenticated desktop.

This validation specifically covers the login regression found in 0.1.1. The
root cause was a collision between the package's former `clausis` service group
and the requested live username. Version 0.1.2 uses the distinct authorization
group `clausis-control`.

## Limits

This evidence does not establish physical audio quality, microphone support on
all hardware, a complete USB installation, accessibility user-study results or
production-security fitness. The Hermes provider setup wizard, fully spoken
partitioning, Voice PIN, TPM/LUKS integration and rollback remain unfinished.
