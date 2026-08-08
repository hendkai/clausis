# Clausis 0.5.0 ISO test report

Date: 2026-08-07

Artifact under test:

- `dist/clausis-0.5.0-amd64.iso`
- Size: approximately 2.5 GiB
- SHA-256: `23dff45848f3b9905fb8f0bface19cc56855215f8fe0cf242f09a7e8d5cd3277`

Status: **rejected candidate; do not publish**.

During the subsequent persistent-disk test, Calamares queued
`shellprocess@clausis-guard` but reported that the instance had no commands.
The candidate therefore reached its destructive partition job without running
the trusted spoken confirmation. The same configuration error also affected
the post-install Hermes finalizer. Testing was stopped and the artifact was
withdrawn before publication.

## Checks that passed before rejection

- The live-build pipeline completed without error from a clean Debian Stable
  container.
- The media scan found a readable hybrid ISO with BIOS and UEFI boot entries.
- The SquashFS inventory contains the Clausis 0.5.0 package, offline speech
  model, Hermes Agent, license files, GNOME branding, Calamares configuration,
  pre-write guard and LUKS recovery-key module.
- The bundled Calamares package is `3.3.14-1+clausis12`.
- An x86-64 QEMU/TCG boot of the exact ISO reached the Debian 6.12.101 kernel,
  live root and GNOME Display Manager.
- A separate graphical run reached the authenticated live GNOME session and
  captured `dist/clausis-0.5.0-boot-screen.png`. Visual review confirmed the
  Clausis wallpaper, matching dark cyan/violet identity, accessible setup
  dialog, AI notice, Hermes choices, optional GPT Live choice and voice button.
- On 2026-08-07 the official Hermes release API returned stable release
  `v2026.8.3`, published 2026-08-03. The installer is implemented to resolve
  this endpoint at installation time, fetch that exact official tag and use
  its frozen lockfile. If the online step fails, it retains the reviewed
  bundled commit instead of leaving a partial installation.

## Corrective action

- Explicitly map both custom `shellprocess` instance IDs to their configuration
  files in Calamares `settings.conf`.
- Reject missing, unknown and non-erase installer modes in the pre-write bridge
  instead of returning success.
- Extend the ISO verifier to require both instance-to-configuration mappings.
- Rebuild the ISO and repeat the complete persistent installation. Static
  checks alone may not close this release gate.

## Still not covered by this report

- A complete persistent Calamares installation onto a disposable disk.
- Unlock of the installed LUKS2 volume with the spoken recovery key.
- VirtualBox-specific devices and audio; this host runs the equivalent boot
  checks in QEMU because VirtualBox is unavailable.
- A real microphone, speaker, echo cancellation, Barge-in or physical hardware.
- A live paid OpenAI Realtime request.

These remain release gates. The rejected checksum above is retained only as
traceable negative-test evidence and must not be offered as a technical preview.

## Corrected candidate

The corrected ISO was rebuilt from a clean Debian Stable container on
2026-08-07:

- SHA-256: `12475ee98859552ea6ab6917f69d4001cf1d569013218ad9aa07527cd0135cbd`
- Size: 2,643,034,112 bytes

The strengthened verifier passed checksum, BIOS and UEFI metadata, SquashFS
contents, GNOME accessibility defaults, Hermes and license files, offline
speech model, custom Calamares package, LUKS recovery module, execution order
and both explicit custom-instance configuration mappings. A QEMU/TCG boot of
this exact corrected artifact reached Debian 6.12.101, the live root and GDM.

The corrected candidate is not cleared for publication yet. A new persistent
installation must still show the guard command executing before partitioning,
finish installation, boot without the ISO and unlock the installed LUKS2
volume through the documented accessible recovery path.
