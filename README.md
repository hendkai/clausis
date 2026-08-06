# VoiceOS Core

VoiceOS Core is an executable Debian voice-first desktop prototype integrating
Hermes Agent without granting the agent unrestricted operating-system access.
The repository now builds a bootable Debian Live/Calamares USB image. It remains
a **technical preview, not a production-ready end-user operating system**.

## What works now

- 24 deterministic German/English offline command families.
- Strict, versioned action messages and an allowlisted action broker.
- Provenance tainting for every Hermes or external-content action.
- Short-lived, single-use, action-bound confirmation capabilities.
- Trusted-confirmation state machine with random phrases and a derived PIN.
- Shell-free fixed-argument execution, dry-run by default.
- Tamper-evident, privacy-redacted audit records.
- Audio capability degradation and secret-free installer plan validation.
- D-Bus interface definitions, hardened systemd units, Polkit and Debian
  packaging scaffolding.
- Local microphone capture, Faster-Whisper transcription and system TTS.
- Reproducible Debian Stable amd64 ISO build with GNOME, Orca and Calamares.

## Build the installation ISO

Docker Desktop with amd64 emulation and at least 25 GB free storage is needed:

```sh
./scripts/build_iso.sh
```

The hybrid BIOS/UEFI image and SHA-256 file are written to `dist/`. See
[`docs/INSTALL_USB.md`](docs/INSTALL_USB.md) before selecting or overwriting a
USB device.

## Development

No network download is required for the core test suite:

```sh
PYTHONPATH=src python3 -m unittest discover -s tests -v
PYTHONPATH=src python3 -m voiceos.cli route "Lautstärke 35 Prozent"
printf 'Netzwerkstatus\nStopp Hermes\n' | PYTHONPATH=src python3 -m voiceos.runtime --stdin
```

The source/developer runtime remains a dry-run unless `--execute` is selected.
The live-image launcher enables validated low-risk platform actions. Privileged
and medium-or-higher-risk actions without trusted confirmation fail closed.

## Trust boundaries

Hermes does not receive terminal, code-execution, file-write, skill-write or
capability-signing access.  It may only propose JSON action requests.  A
separate broker validates the action and its arguments.  A separate trusted
confirmation service owns confirmation phrases and capability issuance.

The current D-Bus PIN string is a **prototype-only transport**.  It must be
replaced by direct trusted audio verification or a protected portal/memfd
before any end-user release.  This is tracked as a release blocker in the
threat model.

## Licensing and AI notice

VoiceOS-owned code is GPL-3.0-or-later.  Hermes Agent remains a separate MIT
component; its notice must be preserved when it is redistributed.  No model,
voice or cloud credential is bundled by this repository.

AI-assisted tools contributed to architecture, implementation and review.
Human maintainers remain responsible for validation and release approval; see
[`docs/compliance/AI_CONTRIBUTION.md`](docs/compliance/AI_CONTRIBUTION.md).
