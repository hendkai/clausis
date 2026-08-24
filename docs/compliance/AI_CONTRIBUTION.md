# AI contribution record

## Document control

| Field | Value |
|---|---|
| Product | Clausis Core |
| Version | 0.5.0 development prototype |
| Date | 2026-08-07 |
| Responsible role | Open; must be assigned before release |
| Status | Draft; public prototype testing allowed, production release blocked |
| Next review | 2027-02-06 or earlier on a trigger below |

## Development provenance

AI-assisted tools were used to propose, draft, transform and review the product
concept, Python implementation, tests, Debian Live ISO configuration, local
speech integration, packaging and documentation. Known tools
in this work session included OpenAI Codex/GPT-5-family assistance and Claude
Code Opus 5 for architecture review. A Claude Fable 5 review was attempted but
did not return a usable review. Exact model-side implementation details and
training data are unknown.

Automated tests were executed after implementation. No human code, security,
accessibility, privacy or legal sign-off has yet been recorded; it would be
misleading to claim that the result is production-ready or fully compliant.
The complete 88-test suite and Debian binary-package build also passed inside
an official fresh Debian Stable container. A later Opus 5 source-review attempt
did not return output and therefore is not counted as review evidence.

On 2026-08-07 Codex added the first non-destructive voice-installer safety
foundation after 0.4.1. It implemented fixed-argument read-only block-device
inventory, conservative target exclusion, stable-ID/size/serial rebinding,
whole-disk-only plan validation, canonical destructive summaries and an
in-memory single-use expiring confirmation phrase. Calamares remains fail-safe:
erase is never preselected. Its proposal now defaults to LUKS2, a separate
unencrypted boot partition, Btrfs root and an explicitly installed cryptsetup
initramfs integration. The GTK Hermes setup footer was moved outside the
scrolling form for small VM displays.

Codex then added a minimal nine-line patch against the exact Debian Calamares
3.3.14-1 source. It exports only selected device node, mode, encryption boolean
and filesystem from the in-memory partition view; it never exports the LUKS
passphrase. The ISO builder obtains Debian's signed source package, applies the
public patch, creates the higher-versioned `3.3.14-1+clausis11` binary and
injects it into the image. A guard job runs immediately before Calamares's
partition placeholder, re-discovers the target and blocks a changed,
ineligible, unencrypted or non-Btrfs automatic erase proposal before the first
partition job. The custom amd64 package compiled successfully and its module
binary was checked for all three exported key names.

The subsequent 2026-08-07 change connects the phrase to the exact pre-write
process: after fresh target rebinding it speaks the canonical disk warning and
an in-memory challenge, records and transcribes one response locally, deletes
the temporary recording and returns no phrase or transcript through Calamares
or stdout. It adds deterministic success, mismatch, single-attempt, deletion
and summary-binding tests. The code still does not generate/export a recovery
key, enroll TPM/FIDO2, prove physical audio isolation or write a disk in tests.
Those boundaries and a complete installation test remain release blockers.
This change introduces no model, provider, biometric processing or new cloud
data flow. Local STT use and the existing direct-AI-interaction disclosure are
unchanged. Codex authored the code, tests and documentation; 163 automated
tests and the clean Debian 13 amd64 binary-package build passed. No human
security, accessibility or legal approval is recorded.

Codex subsequently implemented recovery-key enrollment at the same trusted
pre-write boundary. The guard generates twelve independent four-digit groups
(about 159 bits of entropy), speaks the key twice, stores it mode `0600` only in
the tmpfs-backed `/run` directory and deletes it on confirmation failure. A
second GPL-compatible Calamares patch validates ownership, mode, file type and
format, copies the key temporarily into the already mounted target, invokes
`cryptsetup luksAddKey` while the existing disk passphrase remains on the
module's private standard input, and overwrites and unlinks both temporary
files. Recovery material is not sent in command arguments, GlobalStorage,
stdout or audit output. The complete 167-test Python suite passed. The patched
Calamares 3.3.14 Debian amd64 package compiled successfully in the ISO builder,
and the resulting shared object was inspected for its staging, completion and
error-handling paths. An actual persistent installation and unlock with the
spoken key, trusted audio isolation and the protected keyboard/Orca equivalent
remain release blockers. No new AI model, biometric processing or cloud data
flow was introduced.

The complete development ISO was then rebuilt and structurally verified. Its
SHA-256 was
`76190948789368b782ef13c25badc4de16ab87e1f7b6b4056934c581ea2d2b2c`.
QEMU x86-64 emulation reached Linux 6.12.101, the live root and GDM; a separate
graphical run reached the Clausis-branded GNOME session and setup application.
This is boot evidence only and does not prove a complete persistent Calamares
installation, recovery-key unlock, VirtualBox behavior or physical audio
isolation. The test evidence is recorded in
`docs/release/RECOVERY_KEY_TEST_REPORT.md`; it does not replace the published
0.4.1 release asset.

For the 0.5.0 preview, Codex replaced the previously hard-coded 0.4.1 artifact
names with one authoritative version read from `pyproject.toml`. Package,
builder, ISO, checksum, screenshot, split assets, release notes and the GitHub
tag are now checked against that value; a mismatching tag fails before any
release is created. The Debian package metadata, Python module version, legacy
setup metadata and CycloneDX SBOM were updated to 0.5.0. The two-patch Calamares
build is separately versioned `3.3.14-1+clausis12`. Windows reassembly and
checksum instructions and explicit VirtualBox limitations are included in the
0.5.0 release notes. This work was proposed and implemented with OpenAI Codex;
168 automated tests passed locally. Full ISO and persistent-install results are
recorded only after those builds actually finish.

The AI Act scope check was refreshed on 2026-08-07 against the official
consolidated Regulation (EU) 2024/1689 entry, the Commission AI Act framework
page and the final Commission Article 50 transparency guidelines published in
July 2026. Clausis directly exposes Hermes and optional GPT Live to natural
persons, so the existing accessible disclosure that the user is interacting
with an AI system remains relevant. Coding-assistant provenance is documented
separately and is not by itself treated as an Article 50 product duty. No new
model, provider, biometric inference or cloud data flow is introduced by the
versioning change. Product, security, privacy, accessibility and legal approval
remain blocked pending the release gates below.

On 2026-08-06 Codex added the first local audio frontend, the accessible live
session welcome, a Calamares-based installation image configuration and a
containerised amd64 ISO build. The ISO includes the MIT-licensed converted
`Systran/faster-whisper-base` model and pinned speech libraries. Any ISO build
and structural boot checks are recorded separately from human hardware,
accessibility, privacy and security approval.

On 2026-08-06 Codex also performed the complete product rename to Clausis. This
included source-package names, commands, system users and services, D-Bus and
Polkit identifiers, installer integration, ISO metadata, documentation, tests
and release automation. The rename was validated by the complete automated
test suite and a clean package/ISO rebuild.

On 2026-08-06 Codex clarified the release download instructions for Windows,
Linux and Git Bash, including byte-for-byte ISO reassembly and SHA-256
verification. The README, versioned release notes and published GitHub release
description were selected as the user-facing documentation surfaces. This was
a documentation-only change and did not alter the released ISO artifacts.

On 2026-08-06 OpenAI image generation created an original Clausis emblem from
a Codex-authored visual specification. Codex reviewed the result, removed the
flat chroma-key background, produced deterministic 800×600 and 640×480 boot
compositions and added structural asset tests. The generated mark combines a
rounded C, a speech waveform and audio-pulse arcs; no existing project logo or
third-party logo was supplied as a reference. Human brand and trademark review
remains open before a production release.

The same test cycle reproduced the 0.1.1 graphical live-login failure under
x86-64 QEMU. Codex traced it to the absent Debian `user-setup` package: the
upstream live-config component intentionally skips live-user creation when that
package is unavailable, leaving GDM without the configured `clausis` account.
The package and regression checks were added for the next image. This finding
does not change the AI Act scope assessment.

Inspection of live-config 11.0.5 also found that its default `live` password
still uses a legacy DES hash. Codex added a compatibility component that
replaces only the ephemeral live-account hash with SHA-512 and leaves installed
user credentials untouched. A subsequent root-console boot established the
decisive remaining blocker: the package had already created a system group
named `clausis`, so `user-setup` could not create the live user and its matching
primary group. The authorization group was renamed to `clausis-control` across
package setup, D-Bus, polkit and systemd configuration. The final image then
completed a graphical QEMU boot directly into the authenticated GNOME live
session without a login prompt.

The completed artifacts were structurally verified and booted under x86-64
QEMU. Version 0.1.2 additionally reached the authenticated GNOME live session.
This evidence is documented in `docs/release/ISO_0.1.1_TEST_REPORT.md` and
`docs/release/ISO_0.1.2_TEST_REPORT.md`; it does not establish physical audio,
USB installation, accessibility user-study or production-security fitness.

On 2026-08-06 Codex added the 0.2.0 Hermes integration. Hermes Agent 0.20.0
is fetched from the pinned upstream commit
`0957277f2f468bac22bbfcfa7c43029858c9597e`, installed from its frozen
`uv.lock` with upstream's pinned uv 0.9.28, and retains its MIT license in the
image. The real install hook and CLI startup passed in a fresh Debian 13 amd64
container. The initial attempt with uv 0.12.2 failed closed because that uv
release would have re-resolved the lock; no unlocked fallback was accepted.

Codex also added a GTK3 Hermes/provider setup shown before Calamares, local
spoken provider selection and explicit spoken cloud consent, private API-key
storage, Calamares transfer into the installed user's home, and a restricted
Hermes one-shot reply adapter for Clausis voice input. API keys remain
keyboard-only and are never spoken. Hermes is forced to the local `todo`
toolset for voice/chat launchers, while terminal, file, browser, code execution,
skill mutation, delegation, computer use, project, cron and Home Assistant
toolsets are disabled in the managed configuration. The tool exclusion was
checked against the pinned upstream implementation. The GTK accessibility
smoke check passed in Debian/Xvfb with named controls and a masked secret field.
These automated checks do not replace Orca testing by blind users.

The first complete 0.2.0 ISO build passed media, checksum, BIOS/UEFI structure
and x86-64 QEMU graphical-target boot checks. A review of that image exposed
that the shared live-session autostart would reopen Calamares after installation
and that a background assistant log could retain recognized transcripts. Codex
added an explicit live-system boundary, automatic installed-system voice start
with a spoken microphone notice and local stop phrase, and removed persistent
background transcript logging. A later review rejected symlink-based source and
target redirection in the privileged Calamares configuration transfer and added
bounded, no-follow, atomic private-file copies.

The final 0.2.0 image passed checksum, media, BIOS/UEFI, embedded-component and
x86-64 QEMU graphical-target checks. A graphical capture confirmed live
autologin and the accessible `Clausis einrichten` foreground dialog. Two
intermediate captures exposed Debian's GNOME initial-setup/tour overlays; Codex
added the initial-setup marker and a compiled system dconf default, then rebuilt
and repeated the checks until neither overlay remained. Exact artifact data and
limitations are recorded in `docs/release/ISO_0.2.0_TEST_REPORT.md`.

The installed-system setup path was separated from live-installer staging so
that reopening the settings after installation does not retain a redundant
second API-key copy under the Calamares staging directory.

On 2026-08-07 Codex implemented the Clausis 0.2.1 online Hermes installation
path. It queries the official NousResearch GitHub latest-release API during the
Calamares target installation, accepts only a non-draft/non-prerelease release
with a constrained version tag, fetches that exact tag and installs the
release with its committed `uv.lock`. The Hermes launcher changes only after a
complete successful install. Network, source, lockfile, license or environment
failures preserve the reviewed image version and create a non-secret local
fallback status, which the first installed login speaks and displays.

Codex added deterministic tests for stable-release parsing, prerelease and
command-injection tag rejection, success ordering, frozen installation,
provenance recording and preservation of the existing launcher on failure.
The full suite passed with 93 tests. The official upstream release endpoint and
tag metadata were checked on 2026-08-07; the then-current stable release was
`v2026.8.3`, resolving to commit
`3c27eb6234bf91b8ceee9e9071591b31e9b148cb`. Remaining risk: the installer does
not yet verify the release tag against a Clausis-owned allowlist of trusted
Hermes maintainer signing keys. A compromised official upstream account or
dependency artifact therefore remains in the supply-chain threat model.
Codex additionally ran the real `v2026.8.3` checkout and frozen installation in
a clean Debian 13 amd64 container with the shipped uv 0.9.28, then executed the
resulting Hermes CLI successfully. A separate clean Debian package build ran
all 93 tests and confirmed that version 0.2.1 contains both the updater module
and privileged Calamares finalizer entry point. A complete 0.2.1 ISO install to
a persistent disk remains a release test still to be performed.

Evidence:

- `tests/` and the latest local test output;
- `docs/security/THREAT_MODEL.md`;
- `docs/release/RELEASE_GATE.md`;
- `docs/compliance/CRA_SCOPE.md`;
- `sbom.cdx.json` and `THIRD_PARTY_NOTICES.md`.

On 2026-08-07 Codex implemented the optional OpenAI Realtime frontend for the
0.3.0 technical preview. The user must separately enable GPT Live, consent to
continuous microphone-audio transmission and enter an OpenAI API key through a
masked keyboard field. The key is stored only in the selected user's dedicated
private `.gpt-live.env` file and is excluded from Hermes' environment, the
public config and installer
marker. The setup explicitly states that API billing is separate from ChatGPT.

The implementation uses the documented `gpt-realtime-2.1` WebSocket speech-to-
speech flow with semantic VAD and a privacy-preserving safety identifier. The
model receives only an enumerated `clausis_action` function and a stop function;
it receives no shell, generic computer-use tool, plug-in/MCP access or
capability token. Tool arguments, origin, minimum risk and reversibility are
canonicalized locally before the existing broker sees them. Low-risk reversible
actions may run for responsiveness, while medium-or-higher risk still requires
the separate trusted confirmation. A local per-user stop marker and desktop
launcher stop streaming without model or network cooperation, and connection
failure falls back to local voice control.

Codex checked the current official OpenAI Realtime conversation, WebSocket,
function-tool and `gpt-realtime-2.1` model documentation on 2026-08-07. The
OpenAI developer-documentation MCP was registered locally but requires a Codex
restart, so this turn used the official OpenAI web documentation fallback. The
102-test suite and a Debian 13 amd64 binary-package build passed. The expanded
GTK accessibility smoke check also passed under Debian/Xvfb: all
GPT Live controls had accessible names and both API-key fields remained masked.
No real API key was available, so a paid end-to-end Realtime call, physical
audio behavior, the documented one-hour session limit
and reconnection remain unverified release gates. The data-flow change was
added to the threat model, DPIA draft, release gate, SBOM and license notice.

## AI functions in the product

On 2026-08-07 Codex implemented the second voice-only security stage for the
0.4.1 technical preview. The public `TrustedConfirm1` D-Bus contract no longer
contains separate begin/approve methods or accepts a challenge phrase, PIN,
file descriptor or capability. The isolated system service creates and speaks
its canonical action summary and random challenge, records phrase and PIN
locally with the already-pinned Faster-Whisper stack, issues an action-bound
single-use capability and submits it directly to ActionBroker. Only the final
action result returns to the desktop caller. Requests crossing the public bus
cannot claim local voice/UI provenance or supply their own capability.

The accessible installer setup can capture the security PIN twice by local
speech or through masked keyboard fields. Only a versioned PBKDF2-HMAC-SHA-256
verifier is staged; Calamares validates its exact fields, algorithm, work
factor, size and regular-file status before a private atomic target copy. Raw
confirmation recordings are temporary and deleted after local transcription.
The service does not start without an enrolled verifier and selects the same
pinned native speech environment used by the live runtime.

This stage adds no AI provider, model, biometric template or cloud data flow.
It changes how the existing local STT is used for a security confirmation.
Codex authored and transformed code, tests, packaging and documentation. All
The local offline runtime and optional GPT Live now invoke this service only
after the in-process broker returns `confirmation_required`; service, audio or
response-validation failures become a generic denial. All 144 automated tests
passed locally and in a fresh Debian 13 amd64 container
under Python 3.13. That container built `clausis-core_0.4.1-1_all.deb`; package
inspection confirmed the executable trusted-runtime launcher and the new
confirmation, enrollment, service and audio modules. All four installed
systemd units passed Debian 13 `systemd-analyze verify`. A real private
system-bus smoke test started both dbus-next services, confirmed that
`TrustedConfirm1` exposes only `ConfirmAndSubmit`, rejected malformed input
without returning secrets and proved that a public client cannot claim local
provenance. ISO checks remain separate. There is no human security,
accessibility or legal approval. In
particular, the tests do not prove physical isolation
from the desktop PipeWire graph, replay/synthetic-voice resistance, microphone
behavior or complete privileged execution on supported hardware, so the
production release gate remains blocked.

The consolidated AI Act entry, Commission AI Act overview and final Article 50
guidance were rechecked on 2026-08-07. The product's existing direct-AI-
interaction disclosure remains applicable; this local security-path change
does not create a new Article 50 content category. This is a technical scope
assessment, not legal advice.

On 2026-08-07 Codex implemented the first functional Voice-only roadmap stage
for Clausis 0.4.0. It added a deterministic local activation gate, expiry,
sleep and emergency-stop handling before any Hermes or cloud fallback; an
honest hardware-degradation decision that makes no Barge-in claim; and a
bounded GNOME AT-SPI adapter for current-window orientation, numbered controls,
semantic back navigation and accessible window cycling. Deterministic repeat,
correction and cancellation commands were added. Arbitrary numbered control
activation is classified as medium risk and remains capability-gated.

This stage adds no AI provider, model, biometric processing or cloud data flow.
Wake gating operates on the already-local Faster-Whisper transcript and the
GNOME adapter reads only the local accessibility tree. Raw recordings retain
the existing temporary-file deletion behavior. The current approach is not a
dedicated wake-word model and is not claimed to provide replay resistance,
low-power wake inference, echo cancellation or true Barge-in. Codex authored
and transformed the implementation, tests, packaging and documentation; human
accessibility, security and physical-audio review remain open. All 121 tests
passed locally and inside the Debian 13 amd64 package build. The resulting
0.4.0 package contains the executable session launcher and AT-SPI adapter,
declares Debian's `python3-pyatspi` dependency, and all four systemd units pass
Debian 13 `systemd-analyze verify`. A separate Debian 13 DBus/Xvfb/GTK3 smoke
test started the real AT-SPI registry; Clausis identified the live test window
and its actionable button as a numbered semantic control. These checks do not
prove real microphone, GNOME Shell, screen-reader or physical-user behavior.

The consolidated AI Act entry and the Commission's final Article 50 guidance
were rechecked on 2026-08-07. The direct-interaction disclosure remains
applicable because the product still includes Hermes, Faster-Whisper and
optional GPT Live; this local feature stage does not create a new disclosure
category. This is a technical assessment, not legal advice.

On 2026-08-07 Codex designed and implemented the Clausis 0.3.1 GNOME identity
from the existing project-specific logo: a rendered 2560×1440 listening-field
wallpaper, matching application and GDM branding, supported dark/purple GNOME
preferences, reduced animation, larger cursor, visible accessibility status and
Atkinson Hyperlegible typography. Codex also produced a source-backed gap
analysis for genuinely voice-operated GNOME, distinguishing implemented
features from the missing local audio daemon, AT-SPI/portal adapters, trusted
confirmation, installer and recovery work. The wallpaper was rendered and
visually reviewed. All 103 tests and the Debian 13 amd64 binary-package build
passed; both GNOME dconf databases compiled and the used GNOME/GDM schema keys
and enum values were verified against Debian 13. The font's Debian copyright
record identifies OFL-1.1.

This visual and documentation change adds no AI model, provider, biometric
processing or new product data flow. The existing direct-interaction disclosure
therefore remains applicable and unchanged. The consolidated AI Act entry and
the European Commission's final Article 50 transparency guidelines were
rechecked on 2026-08-07. GNOME's official AT-SPI accessibility guidance and
the official XDG Desktop Portal FileChooser interface were also checked for the
technical architecture. This remains a technical assessment, not legal advice.

The 0.3.1 development image integrates Hermes Agent for direct
natural-language replies after the user selects a local or cloud provider. The
deterministic offline router is rule-based, runs before Hermes and is not
treated as AI. System actions continue through the typed Clausis broker rather
than Hermes' general tools. The image uses a
local Faster-Whisper base model for STT and eSpeak NG/speech-dispatcher for
synthetic speech. Wake-word and speaker-verification models remain unselected
and unbundled.

The voluntary GPT Live mode additionally uses OpenAI Realtime for direct
speech-to-speech interaction and typed function requests. It is an AI system
that directly interacts with the user, so the existing spoken first-interaction
AI notice remains mandatory. Cloud microphone audio is a separate data flow
from Hermes text prompts and has its own opt-in and withdrawal path.

Target users are private individuals in the EU, including people relying on
accessibility functions. The present prototype does not implement medical,
employment, education, credit, law-enforcement or public-authority decisions.

On 2026-08-07 Codex also built and inspected the complete 0.4.1 amd64 ISO after
adding the Calamares pre-write guard. The final image passed its SHA-256,
BIOS/UEFI, SquashFS-content, custom-Calamares-version, non-secret metadata
patch, Hermes 0.20.0, license, offline-model, dconf-branding and installer-order
checks. A first QEMU TCG run reached GDM from the exact ISO; a second graphical
run produced a reviewed screenshot of the authenticated live GNOME session
with the Clausis wallpaper, branded launchers, AI notice and accessible
Clausis/Hermes setup. The first verification run exposed a shell-quoting defect
in the test itself; Codex corrected that diagnostic and reran the complete ISO
verification successfully. This evidence does not cover a persistent disk
installation, real microphone/speaker behavior, VirtualBox-specific behavior
or physical hardware.

## EU AI Act assessment

| Question | Current assessment |
|---|---|
| AI system remains in product | Yes. Hermes and local Faster-Whisper are installed; cloud chat activates only after user setup. |
| Direct interaction with people | Yes; first interaction must disclose that Hermes is AI. |
| Synthetic audio | Planned TTS; saved/exported audio marking must be assessed when a provider is selected. |
| Emotion recognition or biometric categorisation | No; prohibited by product requirements. |
| Biometric verification | Planned optional speaker verification; separate privacy/legal review required. |
| High-risk or prohibited use | Not identified for intended household accessibility use; reassess on any use expansion. |
| Visible notice | Final-image QEMU verification confirms the visual live-session notice and Clausis setup; spoken output and installed-system behavior still require physical hardware verification. |
| Machine-readable marking | Not implemented; applicability depends on selected TTS/export behavior and current standards. |

Article 50 transparency obligations apply from 2 August 2026. The Commission's
final guidelines were published on 20 July 2026 and were checked for this
assessment. The current spoken and visual first-interaction notice addresses
the direct-interaction disclosure at a technical level; legal and human
accessibility review are still open. This is a technical scope assessment, not
legal advice.

## Official sources checked

The legal sources below were initially checked on 2026-08-06. The consolidated
AI Act, Commission overview and final Article 50 guidance were rechecked on
2026-08-07 for the 0.4.1 assessment. GNOME and XDG sources were checked on
2026-08-07 for the voice-only architecture analysis.

- Consolidated Regulation (EU) 2024/1689:
  <https://eur-lex.europa.eu/legal-content/DE/TXT/?uri=CELEX:32024R1689>
- European Commission Article 50 guidelines, published 20 July 2026:
  <https://digital-strategy.ec.europa.eu/en/library/guidelines-transparency-obligations-providers-and-deployers-ai-systems>
- European Commission Article 50 transparency overview:
  <https://digital-strategy.ec.europa.eu/en/policies/guidelines-transparency-ai-generated-content>
- European Commission CRA open-source guidance:
  <https://digital-strategy.ec.europa.eu/en/policies/cra-open-source>
- European Commission CRA implementation FAQ:
  <https://digital-strategy.ec.europa.eu/en/library/cyber-resilience-act-implementation-frequently-asked-questions>
- GNOME accessibility development guidance (GTK and AT-SPI):
  <https://developer.gnome.org/documentation/guidelines/accessibility.html>
- XDG Desktop Portal FileChooser interface:
  <https://flatpak.github.io/xdg-desktop-portal/docs/doc-org.freedesktop.portal.FileChooser.html>
- Calamares whole-disk partitioning documentation:
  <https://calamares.io/docs/partitions/>
- Debian encrypted-volume boot documentation:
  <https://www.debian.org/releases/trixie/arm64/ch07s02.en.html>

## Open actions and triggers

High priority: assign responsible reviewers; verify first-run disclosure on
hardware; complete model dependency/license inventory; complete DPIA; close every release blocker;
and obtain human security/accessibility review.

Reassess immediately on a release, model/provider/data-flow change, biometric
feature implementation, commercialisation, target-market/use expansion,
security/privacy incident or change in applicable law/guidance. Otherwise
reassess no later than the date above.

This record distinguishes voluntary development provenance from product-law
obligations. It is not a legal opinion or a guarantee of compliance.

## Clausis 0.5.0 build and release-tooling record — 2026-08-07

Codex consolidated build, verification, Windows reassembly and GitHub release
asset names around project version 0.5.0, prepared the matching technical
preview notes, and built the complete amd64 ISO. The exact artifact has SHA-256
`23dff45848f3b9905fb8f0bface19cc56855215f8fe0cf242f09a7e8d5cd3277`.
Static media and SquashFS inspection passed, including BIOS/UEFI entries,
Hermes and its MIT notice, the offline speech model, branded GNOME defaults,
Calamares `3.3.14-1+clausis12`, the pre-write guard and the LUKS recovery-key
module. QEMU/TCG reached GDM from the exact ISO. A second graphical run reached
the authenticated live session, and Codex visually reviewed its captured
Clausis setup, AI notice, optional GPT Live control, voice button and branded
desktop.

The official Hermes release API was checked on 2026-08-07 and reported stable
release `v2026.8.3`, published 2026-08-03. Clausis resolves that endpoint again
during an online installation, accepts only an exact stable tag and installs
with the upstream frozen lockfile; otherwise the reviewed bundled fallback
remains selected. Upstream `main` was newer than that stable tag, so it was not
treated as a stable installer release.

No new model category, biometric processing or cloud data flow was introduced
by this release-tooling work. The consolidated AI Act, Commission overview and
final Article 50 guidance were rechecked on 2026-08-07. The direct-interaction
AI disclosure remains applicable to Hermes, Faster-Whisper and voluntary GPT
Live. Persistent installation, spoken LUKS unlock, real audio hardware,
VirtualBox-specific behavior and paid OpenAI Realtime use remain explicitly
untested. This is a technical assessment, not legal advice.

## Clausis 0.5.0 rejected-candidate correction — 2026-08-07

Codex performed the first persistent-disk, virtual-audio installation test of
the 0.5.0 candidate. The test showed that Calamares queued the trusted guard
but loaded no commands because custom `shellprocess` instances were not mapped
to their configuration files in `settings.conf`. The run was stopped, the
candidate checksum was marked rejected, and publication remained blocked.

Codex added explicit mappings for the guard and Hermes finalizer, changed the
pre-write bridge to deny missing or non-erase modes, strengthened the ISO
verifier and regression tests, and started a clean rebuild. This correction
does not add an AI model, biometric use or cloud data flow. It materially
improves the enforcement of the existing trusted-confirmation boundary. A new
persistent-VM installation must still demonstrate that the guard executes;
static validation does not by itself close the release gate.

The clean rebuild subsequently completed with SHA-256
`12475ee98859552ea6ab6917f69d4001cf1d569013218ad9aa07527cd0135cbd`.
The strengthened final-image verifier found both explicit instance mappings,
and QEMU/TCG booted that exact artifact through live root to GDM. Publication
remains blocked until the corrected persistent installation and recovery path
pass at runtime.

## Clausis voice-editing stage 2 — 2026-08-24

GLM 5.3 via Hermes implemented the second voice-only gap-analysis stage:
deterministic spoken punctuation expansion for dictation (`punctuation.py`,
router-side, before policy validation), caret navigation inside the focused
field via the AT-SPI text interface with an explicit read-back check, line and
paragraph breaks as adapter-side actions, and file-chooser navigation that
lists entries read-only, focuses an entry without committing, and opens only
provable sidebar tree-item folders — file grid rows are never activated. All
paths are structural, tested against simulated accessibility trees only; no
real GNOME session was involved.

No new model category, biometric processing or cloud data flow was introduced.
The work is deterministic local code; the existing direct-interaction AI
disclosure remains applicable. A run in a real GNOME session is still
outstanding.

## Clausis text-editing, spelling and speech-control stage — 2026-08-24

GLM 5.3 (via Hermes Agent) implemented the remaining software-only items from
the blind-use gap analysis: voice text editing (select all/word/sentence,
replace and delete the selection, undo/redo through the widget's own action,
granular reading by character/word/line/sentence/paragraph), the spelling mode
("A wie Anton" becomes A; German and English alphabets plus digits, applied
before the request schema validates anything), and speech-output control
(rate faster/slower/normal, language German/English) as fixed spd-say
argument vectors with no caller-supplied value. The security contact was
pointed at GitHub Private Vulnerability Reporting, which is now enabled on
the repository and verified. All work is deterministic local code tested
against fake AT-SPI trees; a run in a real GNOME session remains outstanding.
No new model category, biometric processing or cloud data flow was introduced.

## Clausis real-session AT-SPI verification — 2026-08-24

GLM 5.3 (via Hermes Agent) closed the four-documented-times gap "no run in a
real GNOME session" for the text-editing adapters: a session-level smoke test
runs a real GTK application (editable entry plus a hidden-visibility password
entry) on a real accessibility bus (dbus-run-session, Xvfb, at-spi-bus-launcher,
GTK_MODULES=gail:atk-bridge, matchbox window manager for the focus handshake),
both locally via scripts/atspi_session_smoke.sh (Docker) and in the
GitHub workflow "AT-SPI session smoke". The client drives the real
PyAtSpiDesktop surface end to end — context, reading, caret navigation,
selection, replacement, undo/redo, insertion, granular reading — and verifies
the password-field refusal on the real bus; every step records OK/REFUSED/ERROR
and any ERROR fails CI. The run surfaced and fixed a genuine adapter bug the
fake-tree suite could never catch: pyatspi (AT-SPI2) defines no STATE_PROTECTED
attribute, so every text command crashed with AttributeError once focus worked;
password fields are now recognised solely by the "password text" role, and the
test fakes no longer invent the nonexistent state. Xvfb plus a real bus and
real widget is still not a full GNOME desktop, so widget coverage beyond GTK
remains open. No new model category, biometric processing or cloud data flow
was introduced.

## Clausis dictation modes — 2026-08-24

GLM 5.3 (via Hermes Agent) implemented the first three dictation modes from
the blind-use gap analysis §1: e-mail addresses ("diktiere e-mail hendrik at
kaiser-mail punkt de" → hendrik@kaiser-mail.de), URLs and file paths
("diktiere url …", scheme-guarded colon conversion) and numbers ("diktiere
zahl drei Komma eins vier" → 3,14; German compound number words 0–99). The
modes are deterministic, purely functional token transforms in a new module
(dictation_modes.py) that fire only on their explicit trigger phrase — never
mid-utterance, consistent with the sentence-end punctuation rule — and unparseable
number payloads are honestly refused (the router declines the utterance, the
agent can explain) instead of guessed. The output keeps every schema guarantee:
printable-only, ≤ 512 characters, TARGET_RE-valid; the injection corpus gained
a regression test that runs mode-specific payloads (carriers like "punkt",
"at", URL separators, escapes) through all three modes and the router. Honest
gaps documented in BLIND_USE_GAP_ANALYSIS §1: date/time modes absent, number
words only 0–99, URL colons only after a scheme, file paths lose word spacing.
No new model category, biometric processing or cloud data flow was introduced.
