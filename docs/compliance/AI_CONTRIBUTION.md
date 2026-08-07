# AI contribution record

## Document control

| Field | Value |
|---|---|
| Product | Clausis Core |
| Version | 0.3.1 development prototype |
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
AI Act and final Article 50 guidance were rechecked on 2026-08-07 for the
0.3.1 assessment. GNOME and XDG sources were checked on 2026-08-07 for the
voice-only architecture analysis.

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
