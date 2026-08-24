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
[`v0.5.0` release](https://github.com/hendkai/clausis/releases/tag/v0.5.0):

- `clausis-0.5.0-amd64.iso.part-aa`
- `clausis-0.5.0-amd64.iso.part-ab`
- `clausis-0.5.0-amd64.iso.sha256`

Do **not** unpack the files. On Windows, place all three files in the same
folder, open PowerShell in that folder and run:

```powershell
cmd /c copy /b clausis-0.5.0-amd64.iso.part-aa+clausis-0.5.0-amd64.iso.part-ab clausis-0.5.0-amd64.iso
$expected = (Get-Content .\clausis-0.5.0-amd64.iso.sha256).Split()[0].ToUpper()
$actual = (Get-FileHash .\clausis-0.5.0-amd64.iso -Algorithm SHA256).Hash
if ($actual -ne $expected) { throw "Checksum mismatch - download the parts again" }
"Checksum OK: $actual"
```

Linux and Git Bash users can assemble and verify the ISO with:

```sh
cat clausis-0.5.0-amd64.iso.part-aa clausis-0.5.0-amd64.iso.part-ab > clausis-0.5.0-amd64.iso
sha256sum -c clausis-0.5.0-amd64.iso.sha256
```

On macOS, replace the verification command with:

```sh
shasum -a 256 -c clausis-0.5.0-amd64.iso.sha256
```

A checksum only proves the download is intact, not that it came from this
project: whoever can replace the image can replace the checksum beside it. When
a release also carries `clausis-0.5.0-amd64.iso.sha256.asc` and
`clausis-release-key.asc`, verify the origin as well — and check the key
fingerprint against a second, independent source before trusting it:

```sh
gpg --import clausis-release-key.asc
gpg --verify clausis-0.5.0-amd64.iso.sha256.asc clausis-0.5.0-amd64.iso.sha256
```

Releases published without those two files are unsigned. Treat them as a
technical preview from an unverified source.

After verification, select `clausis-0.5.0-amd64.iso` directly as the optical
disk in VirtualBox. Do not unpack the resulting ISO.

## What works now

- Original Clausis boot branding for both GRUB/UEFI and Syslinux/BIOS.
- Matching GNOME identity with the Clausis listening-field wallpaper, dark
  color preference, purple speech accent, branded launchers and GDM logo,
  reduced animation and Atkinson Hyperlegible typography.
- 86 deterministic German/English offline command families. Every allowlisted
  action reaches exactly one adapter — semantic GNOME, read-only local query,
  the Polkit-gated privileged helper or a fixed argument vector — and a test
  fails the build if an action is left without one.
- Standard dialogs are classified and spoken: file open, file save, plain
  message, and permission or authentication prompts. Clausis **refuses to
  approve a permission or login prompt by voice** — that is exactly what a
  misheard or injected utterance would want approved — while cancelling stays
  available so a voice-only user is never trapped in one. Accepting any other
  dialog is medium risk and needs trusted confirmation.
- Clipboard: read it aloud, copy through the widget's own accessible copy
  action, paste with the same refusals that guard dictation. Clipboard content
  can be placed there by any process, so a hijacked clipboard cannot be pasted
  into a terminal or password field.
- Spoken switches for the on-screen keyboard, screen magnifier and Orca.
- A two-stage wake path: an energy gate that costs 0.03 % of one 80 ms frame
  rejects silence, and only frames that could contain speech reach a keyword
  model. While it is active nothing is transcribed until the wake word fires,
  so background conversation never reaches an agent at all. The model itself is
  not bundled — the weights carry their own licence and their false-accept rate
  has to be measured — so Clausis falls back to matching the wake phrase in the
  transcript, exactly as before, and says which path is active.
- Barge-in that refuses to lie: the interruption detector will not arm without
  certified echo cancellation, because otherwise Clausis hears its own speaker
  and interrupts itself forever. `AudioMode.FULL_DUPLEX` is now reachable, but
  only when certified hardware, a shared clock, echo cancellation and a
  measured interruption detector are all present. Everything else keeps the
  honest half-duplex announcement.
- Non-speech earcons for wake, confirm, error and sleep, synthesised locally
  with the standard library. They are hints, never the only carrier: every
  state they mark is also available as speech or as a notification.
- Audio at disk unlock and at the login screen. There is no synthesiser in an
  initramfs, so the prompts are pre-rendered when the package is configured and
  played by a minimal ALSA player that the initramfs hook pulls in together
  with the sound modules. The prompt says plainly that the passphrase has to be
  typed and is not read back — voice cannot unlock a disk. Every step is best
  effort: a missing card or file can never delay or block a boot. At the GDM
  greeter, where none of Clausis runs yet, Orca is enabled so the login screen
  speaks.
- A Btrfs subvolume layout built for the rollback, not for tidiness. Only `/`
  is inside the rollback boundary; `/home`, `/var/log`, `/var/lib/clausis`,
  `/.snapshots`, the caches and the swapfile are deliberately outside it.
  Undoing a failed update must never erase the tamper-evident audit chain that
  records what that update did. If the layout is missing — an older
  installation, or hand partitioning — the rollback still runs but says plainly
  that the log may have been reverted with it.
- Package and security updates run inside a snapshot guard: a `pre` snapshot,
  the update, a `post` snapshot, then the health check. A failed update — or one
  that leaves a system which can no longer speak — is undone automatically. A
  machine without snapper still receives its security updates and says plainly
  that no snapshot exists; refusing them would trade a real risk for a
  hypothetical one.
- Online Hermes releases are verified against a pinned maintainer trust anchor:
  the signed tag, or the commit behind a lightweight tag, is checked with gpg in
  an isolated keyring. There is no "unsigned is fine" path — an unconfigured
  anchor, a missing signature or an unknown key all keep the reviewed release
  bundled in the image active. The anchor ships as a placeholder, so online
  updates are currently refused entirely.
- A named recovery path for every supported failure — no microphone, no speech
  output, no network, unreachable agent, crashed broker, unavailable trusted
  confirmation, missing shell extension, unanswerable dialog, failed update.
  Each one names the equal keyboard/Orca route, and a test refuses to let a
  failure exist without one. When speech output itself dies, messages fall back
  to a desktop notification (which Orca reads) and then to the terminal, so a
  failure never ends in silence. A crash in the broker or an adapter no longer
  ends the voice session; it becomes a spoken failure, and “Stopp” still works.
- Dictation into the focused text field over AT-SPI: “Diktiere …”, “Tippe …”,
  “Schreib ins Feld …”, plus “Wort löschen”, “Feld leeren” and “Lies das Feld
  vor”. The inserted text is read back out of the accessibility tree before
  Clausis reports success, so a field that swallowed the input is not announced
  as written. Clausis refuses to dictate into a password field or a terminal —
  there a line of text would be a command. An ambiguous “Schreibe mir ein
  Gedicht” stays a request to the agent, not dictation.
- Window and shell control without screen coordinates: minimize, maximize,
  restore, switch workspace, move the window to the next or previous workspace,
  application grid, quick settings and notifications.
- Local answers for “Systemstatus”, “Suche nach Updates” and “Suche Datei …”
  without a shell: uptime, load, memory, disk and battery come from `/proc` and
  `/sys`, updates from a non-locking `apt-get --simulate` run, and file search
  from a bounded walk over the user's XDG directories that skips hidden files.
- A Polkit-gated root helper for reboot, power-off, package management and
  security updates. The typed request travels on standard input, so neither the
  capability nor the target enters an argument list; the helper re-checks
  policy and capability, keeps its own single-use replay store and executes a
  fixed argument vector from a root-side table.
- A minimal Clausis GNOME Shell extension for surfaces outside the AT-SPI tree.
  Its private session-bus interface is parameterless and exposes no evaluation,
  screen coordinates or input simulation.
- “Schließe …” closes a window through the accessible close action the
  application itself publishes, after trusted confirmation; Clausis never
  terminates a process by force.
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
- GPT Live can request only Clausis' typed allowlisted actions, and it can now
  request all of them — including restart, power-off, package management and
  security updates, which were previously missing from the offered set. The
  offered list is derived from adapter coverage, so an action can never be
  advertised to the model without an implementation behind it. Breadth changes
  nothing about authorization: GPT Live receives no shell, arbitrary program,
  plug-in, MCP or capability-token access, and every medium or higher-risk,
  irreversible or privileged action still needs the separate trusted
  confirmation — plus, for privileged actions, the Polkit prompt.
- A desktop entry named **GPT Live sofort beenden** stops online audio locally,
  without waiting for the model or an internet connection. Reopening
  **Clausis und Hermes einrichten** lets the user disable GPT Live permanently.
- Automatic offline voice-control start after installation; “Stopp Hermes”
  stops it locally without asking a cloud model.
- Reproducible Debian Stable amd64 ISO build with GNOME, Orca and Calamares.

**Testing this as a blind person?** Start with
[`docs/TESTING_FOR_BLIND_USERS.md`](docs/TESTING_FOR_BLIND_USERS.md): what to
try, what to report, and what Clausis deliberately refuses to do by voice. Say
“Fehlerbericht” or run `clausis-report` to produce a diagnostic that contains
no recordings, transcripts, filenames or credentials — Clausis reads out a
summary of what it is about to share before you send it.

What is still missing before a blind person could run this machine entirely by
voice is tracked separately in
[`docs/BLIND_USE_GAP_ANALYSIS.md`](docs/BLIND_USE_GAP_ANALYSIS.md) — including
the honest note that no blind person has yet worked on or tested Clausis, which
makes every assumption in it a guess until that changes.

The remaining technical work before Clausis can honestly be called fully
voice-operated is tracked in
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

Beyond the offline suite, a session-level smoke test runs a real GTK
application on a real accessibility bus and drives the text-editing adapter
end to end, including the password-field refusal. In CI it is the
“AT-SPI session smoke” workflow; locally:

```sh
scripts/atspi_session_smoke.sh   # needs Docker (linux/amd64)
```

## Trust boundaries

Hermes does not receive terminal, code-execution, file-write, skill-write or
capability-signing access. In version 0.5.0 Hermes is a reply-only fallback and
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
