# Clausis Core

Clausis Core is an executable Debian voice-first desktop prototype integrating
Hermes Agent without granting the agent unrestricted operating-system access.
The repository now builds a bootable Debian Live/Calamares USB image. It remains
a **technical preview, not a production-ready end-user operating system**.

The current test image is published under
[`Releases`](https://github.com/hendkai/clausis/releases). Every `v*` Git tag
automatically starts a clean Debian ISO build and uploads split, checksummed
release assets through GitHub Actions.

## Test image herunterladen

Download all three files from the
[`v0.1.1` release](https://github.com/hendkai/clausis/releases/tag/v0.1.1):

- `clausis-0.1.1-amd64.iso.part-aa`
- `clausis-0.1.1-amd64.iso.part-ab`
- `clausis-0.1.1-amd64.iso.sha256`

Do **not** unpack the files. On Windows, place all three files in the same
folder, open PowerShell in that folder and run:

```powershell
cmd /c copy /b clausis-0.1.1-amd64.iso.part-aa+clausis-0.1.1-amd64.iso.part-ab clausis-0.1.1-amd64.iso
$expected = (Get-Content .\clausis-0.1.1-amd64.iso.sha256).Split()[0].ToUpper()
$actual = (Get-FileHash .\clausis-0.1.1-amd64.iso -Algorithm SHA256).Hash
if ($actual -ne $expected) { throw "Checksum mismatch - download the parts again" }
"Checksum OK: $actual"
```

Linux and Git Bash users can assemble and verify the ISO with:

```sh
cat clausis-0.1.1-amd64.iso.part-aa clausis-0.1.1-amd64.iso.part-ab > clausis-0.1.1-amd64.iso
sha256sum -c clausis-0.1.1-amd64.iso.sha256
```

On macOS, replace the verification command with:

```sh
shasum -a 256 -c clausis-0.1.1-amd64.iso.sha256
```

After verification, select `clausis-0.1.1-amd64.iso` directly as the optical
disk in VirtualBox. Do not unpack the resulting ISO.

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
PYTHONPATH=src python3 -m clausis.cli route "Lautstärke 35 Prozent"
printf 'Netzwerkstatus\nStopp Hermes\n' | PYTHONPATH=src python3 -m clausis.runtime --stdin
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

Clausis-owned code is GPL-3.0-or-later.  Hermes Agent remains a separate MIT
component; its notice must be preserved when it is redistributed.  No model,
voice or cloud credential is bundled by this repository.

AI-assisted tools contributed to architecture, implementation and review.
Human maintainers remain responsible for validation and release approval; see
[`docs/compliance/AI_CONTRIBUTION.md`](docs/compliance/AI_CONTRIBUTION.md).
