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
[`v0.4.1` release](https://github.com/hendkai/clausis/releases/tag/v0.4.1):

- `clausis-0.4.1-amd64.iso.part-aa`
- `clausis-0.4.1-amd64.iso.part-ab`
- `clausis-0.4.1-amd64.iso.sha256`

Do **not** unpack the files. On Windows, place all three files in the same
folder, open PowerShell in that folder and run:

```powershell
cmd /c copy /b clausis-0.4.1-amd64.iso.part-aa+clausis-0.4.1-amd64.iso.part-ab clausis-0.4.1-amd64.iso
$expected = (Get-Content .\clausis-0.4.1-amd64.iso.sha256).Split()[0].ToUpper()
$actual = (Get-FileHash .\clausis-0.4.1-amd64.iso -Algorithm SHA256).Hash
if ($actual -ne $expected) { throw "Checksum mismatch - download the parts again" }
"Checksum OK: $actual"
```

Linux and Git Bash users can assemble and verify the ISO with:

```sh
cat clausis-0.4.1-amd64.iso.part-aa clausis-0.4.1-amd64.iso.part-ab > clausis-0.4.1-amd64.iso
sha256sum -c clausis-0.4.1-amd64.iso.sha256
```

On macOS, replace the verification command with:

```sh
shasum -a 256 -c clausis-0.4.1-amd64.iso.sha256
```

After verification, select `clausis-0.4.1-amd64.iso` directly as the optical
disk in VirtualBox. Do not unpack the resulting ISO.

## What works now

- Original Clausis boot branding for both GRUB/UEFI and Syslinux/BIOS.
- Matching GNOME identity with the Clausis listening-field wallpaper, dark
  color preference, purple speech accent, branded launchers and GDM logo,
  reduced animation and Atkinson Hyperlegible typography.
- 32 deterministic German/English offline command families.
- A persistent local wake gate: background transcripts are discarded until
  “Hallo Clausis”, the activation window closes automatically, and “Stopp
  Clausis” is handled before Hermes or any cloud fallback.
- Semantic GNOME orientation through AT-SPI without screen coordinates:
  describe the active window/focus, enumerate numbered controls, navigate back
  and move between accessible windows. Arbitrary control activation remains
  confirmation-gated.
- Strict, versioned action messages and an allowlisted action broker.
- Provenance tainting for every Hermes or external-content action.
- Short-lived, single-use, action-bound confirmation capabilities.
- Trusted-confirmation state machine with random phrases and a derived PIN.
- Shell-free fixed-argument execution, dry-run by default.
- Tamper-evident, privacy-redacted audit records.
- Audio capability degradation and secret-free installer plan validation.
- Conservative read-only disk discovery that excludes the live medium,
  removable, mounted, read-only, undersized and unstably identified devices;
  plans are rebound to stable ID, exact size and serial suffix before hand-off.
- Calamares defaults to no destructive selection, preselected LUKS2 encryption,
  a separate boot partition and Btrfs root; keyboard and Orca manual mode remain.
- D-Bus interface definitions, hardened systemd units, Polkit and Debian
  packaging scaffolding.
- Local microphone capture, Faster-Whisper transcription and system TTS.
- Hermes Agent 0.20.0 preinstalled from a pinned upstream commit as the offline
  fallback. During installation Clausis checks the official upstream for the
  latest stable release, installs its frozen dependency lock and switches over
  only after a successful installation.
- Accessible Hermes provider setup before Calamares with local spoken provider
  choice, explicit cloud consent, masked keyboard-only API-key entry and Orca.
- The local offline assistant now starts before Calamares even when GPT Live is
  not selected, so window orientation, control lists, back and stop remain
  spoken without a network connection.
- Optional GPT Live mode for low-latency online speech during installation and
  on the installed desktop. It is off by default, needs a separate explicit
  audio-transmission consent and a keyboard-only OpenAI API key, and falls back
  to local voice control when unavailable.
- GPT Live can request only Clausis' typed allowlisted actions. It receives no
  shell, arbitrary program, plug-in, MCP or capability-token access; medium and
  higher-risk actions still require the separate trusted confirmation path.
- A desktop entry named **GPT Live sofort beenden** stops online audio locally,
  without waiting for the model or an internet connection. Reopening
  **Clausis und Hermes einrichten** lets the user disable GPT Live permanently.
- Automatic offline voice-control start after installation; “Stopp Hermes”
  stops it locally without asking a cloud model.
- Reproducible Debian Stable amd64 ISO build with GNOME, Orca and Calamares.

The remaining work before Clausis can honestly be called fully voice-operated
is tracked in
[`docs/VOICE_ONLY_GAP_ANALYSIS.md`](docs/VOICE_ONLY_GAP_ANALYSIS.md). The main
missing pieces are a dedicated low-latency wake-word/barge-in detector, broader
GNOME/portal coverage, physical confirmation-audio isolation, enforced
voice-native installation, a protected keyboard/Orca confirmation path and
boot/login/recovery audio. The installer now creates a high-entropy spoken
recovery key and adds it directly to the encrypted LUKS2 system without placing
the key or disk passphrase in process arguments or Calamares state; the complete
install-and-unlock path still needs persistent-VM and hardware validation.

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
capability-signing access. In version 0.4.1 Hermes is a reply-only fallback and
is launched with only its local `todo` toolset; it cannot send system actions to
the broker. The optional OpenAI Realtime frontend can propose only the fixed
action names published by Clausis; every proposal is reconstructed and checked
locally by the same typed broker. A separate trusted-confirmation service owns
confirmation phrases and capability issuance.

GPT Live sends microphone audio to OpenAI while it is active. The OpenAI API is
billed separately; a ChatGPT subscription does not automatically provide API
credit. Clausis stores the supplied API key in the selected user's private
configuration file (mode `0600`), never in the public installer plan, and does
not bundle a key. This technical preview does not yet provide a backend for
short-lived client tokens, so other malicious processes already running as the
same desktop user remain a credential-theft risk.

During the live installation GPT Live is a spoken companion and can control the
currently supported Clausis desktop actions. Calamares disk partition fields
are not yet controlled directly by GPT Live; those remain available through
the graphical, keyboard and Orca paths. A small source-built Calamares patch
exports only the non-secret selected target, mode, encryption state and
filesystem. Clausis rebinds those values immediately before the first
partition job and blocks a changed or weakened whole-disk proposal. The
protected phrase is now generated, spoken and checked inside that exact
pre-write process without entering Calamares state or stdout. Recovery-key
export, physical trusted-audio isolation and persistent-install validation are
still missing, so fully voice-native partitioning remains release-blocked.

Trusted confirmation no longer exposes `Begin`, `Approve`, a challenge phrase,
a PIN or a capability through the public D-Bus interface. The isolated
`clausis-confirm` system service speaks its own canonical summary, captures the
random phrase and PIN directly with the pinned local speech runtime, submits
the resulting action-bound capability to ActionBroker itself, and returns only
the final action result. The installer stages only a PBKDF2 verifier; plaintext
PIN and raw confirmation recordings are not persisted. Physical isolation from
the desktop PipeWire graph, replay detection and hardware validation remain
production release blockers.

## Licensing and AI notice

Clausis-owned code is GPL-3.0-or-later. Hermes Agent remains a separate MIT
component; its notice is preserved in the image. The MIT-licensed converted
`Systran/faster-whisper-base` model is bundled for offline speech recognition.
No cloud credential or proprietary model weight is bundled.

The online installer accepts only the latest non-draft, non-prerelease tag from
the official `NousResearch/hermes-agent` GitHub repository. It records the tag
and commit in `/var/lib/clausis/hermes-install.json`. If lookup, download or the
frozen install fails, the pinned image version remains active and the first
installed login reports the fallback by speech and notification.

AI-assisted tools contributed to architecture, implementation and review.
Human maintainers remain responsible for validation and release approval; see
[`docs/compliance/AI_CONTRIBUTION.md`](docs/compliance/AI_CONTRIBUTION.md).
