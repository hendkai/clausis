# Clausis architecture

Status: executable core prototype, version 0.4.1.

## Data flow

```text
microphone -> local STT -> VoiceRuntime -> OfflineRouter -> ActionBroker
                               |
                               +-- unmatched -> HermesOneShot -> spoken reply

microphone -> optional OpenAI Realtime -> typed function request -> ActionBroker
     ^                    |                                      |
     +---- streamed TTS <-+                         trusted confirmation for risk
```

The unprivileged audio frontend owns local STT, activation state and TTS. Its
local gate discards background transcripts until “Hallo Clausis”, expires the
short command window automatically and recognizes stop before an agent or cloud
fallback. Recording uses adaptive energy detection. Dedicated low-power
wake-word inference, echo cancellation and a tested interruption detector for
true barge-in remain open; all current hardware therefore announces
half-duplex. `VoiceRuntime` always checks deterministic offline commands first.
Only unmatched activated utterances may be sent to Hermes, and only after cloud
consent when a remote provider is used.

GPT Live is a separate, voluntary frontend. When enabled, 24 kHz PCM microphone
audio is streamed over a TLS WebSocket to the configured OpenAI Realtime model,
and returned PCM speech is played immediately. The model sees one narrow
`clausis_action` function and a stop function. It never receives a shell,
generic computer-use tool, capability token or arbitrary executable. Function
arguments are parsed with a strict schema, and origin, minimum risk and
reversibility are replaced with canonical local policy values before broker
submission. If connection or audio startup fails, the assistant announces the
failure and returns to local STT automatically.

## Trust boundaries

1. **Voice Runtime** is unprivileged and replaceable. A compromised STT model
   can propose requests but cannot execute them.
2. **Hermes OneShot** receives only unmatched text and is launched with the
   explicit local `todo` toolset. Its plain-text reply can be spoken but cannot
   become a system action. The separately tested typed `Hermes Adapter`
   discards caller-supplied origins and capability tokens, but is not connected
   to the 0.4.1 runtime yet.
3. **GPT Live frontend** holds the user's OpenAI key and streams audio only
   after separate opt-in. Its model can propose fixed typed actions, but cannot
   execute or confirm them. A per-user local stop marker and desktop launcher
   terminate streaming without cloud cooperation.
4. **Action Broker** accepts only allowlisted verbs and validated arguments. It
   does not accept shell strings and cannot reduce an action's minimum risk.
5. **Trusted Confirm** runs as the separate `clausis-confirm` system user. Its
   public API has only `ConfirmAndSubmit(request)`: the service creates and
   speaks the canonical summary and random phrase, captures phrase and PIN
   through its direct local audio frontend, and submits the capability to the
   broker itself. Neither secrets nor the capability are returned to the
   desktop caller. Tokens bind action, target, arguments, origin and expiry and
   are single-use.
6. **Platform adapters** translate one approved action into a fixed argv vector
   or desktop API call. Missing adapters fail closed.
7. **GNOME semantic adapter** runs inside the unprivileged user session and
   reads the bounded AT-SPI tree. It uses no screen coordinates or global input
   synthesis. Read-only orientation is low risk; arbitrary numbered activation
   is medium risk and requires a capability.

Broker and confirmer receive a root-created HMAC credential through systemd
credentials; Hermes and the desktop session do not receive it. The voice PIN
is enrolled before installation, persisted only as a versioned PBKDF2 verifier
and copied into the target through bounded, no-following Calamares code. The
service remains disabled when no verifier exists. Physical microphone/seat
isolation and replay resistance are not yet proven on supported hardware.

## Public action interface

```json
{
  "action": "file.move_to_trash",
  "target": "/home/user/example.txt",
  "arguments": {},
  "origin": "hermes",
  "risk": "high",
  "reversible": true,
  "capability_token": null,
  "expires_at": null
}
```

The versioned D-Bus names are `org.clausis.ActionBroker1` and
`org.clausis.TrustedConfirm1`. Unknown fields, oversized messages, relative
paths, unsafe identifiers and understated risk are rejected.
`TrustedConfirm1` intentionally exposes no separate begin/approve/deny methods
and accepts no phrase, PIN, file descriptor or capability from a caller.
The local and GPT-Live runtimes call this endpoint only after their in-process
broker has classified a request as confirmation-required. A missing service,
invalid response or audio failure is converted into a denial without exposing
provider or secret details.

## Degradation

| Failure | Behavior |
|---|---|
| No network | Offline router continues; an attempted Hermes reply fails after its provider/network error or the 45-second hard timeout. |
| No remote model | Same as no network; no silent provider fallback. |
| GPT Live unavailable | A spoken notice is emitted and the existing local voice loop starts automatically. |
| User wants online audio stopped | “GPT Live sofort beenden” writes a local per-user stop marker; the Realtime loop checks it independently of the cloud. |
| Unknown audio hardware | Device presence is probed locally and Clausis announces safe half-duplex; no Barge-in promise is made. |
| No microphone | Setup, desktop, keyboard and Orca remain available; the current automatic voice loop cannot accept a stop phrase. |
| No audio | Keyboard, visual setup and Orca remain available. |
| Broker refusal | Canonical reason is spoken and displayed; no automatic bypass. |
| Hermes release lookup or install fails | The launcher remains on the pinned image version; status is recorded and announced at first installed login. |
| System package update fails | Health-check and snapshot scaffolding exist, but automatic rollback is not wired in 0.4.1. |

## Implemented for the 0.4.1 image

- Hermes Agent 0.20.0 is installed from pinned upstream commit
  `0957277f2f468bac22bbfcfa7c43029858c9597e` with its frozen dependency set
  and upstream's pinned uv 0.9.28.
- After Calamares creates the target account, Clausis queries only the official
  GitHub latest-release endpoint, rejects drafts, prereleases and unexpected
  tag formats, fetches that exact tag and installs it with its `uv.lock`.
  `/usr/local/bin/hermes` is atomically switched only after the new executable
  exists; the image copy stays available as a fallback. The release tag,
  resolved commit and publication time are recorded locally.
- The live-session setup is labelled for assistive technology, starts Orca
  before the installer, supports local provider-name and cloud-consent speech
  recognition and never accepts API keys through speech.
- A Calamares shell-process job copies the private staged Hermes configuration
  into the newly-created target account after the user job completes.
- Unmatched voice questions use Hermes one-shot replies after provider setup;
  only the `todo` toolset is exposed and the reply is spoken.
- Optional GPT Live setup uses a separate consent and masked key field. The
  assistant streams speech only when both are present and offers only fixed
  broker actions. The setup can be reopened to withdraw consent and erase the
  GPT Live key from Clausis' dedicated managed `.gpt-live.env` file.
- GNOME uses a Clausis listening-field wallpaper, the same emblem for Clausis
  launchers and GDM, supported dark/purple appearance preferences, reduced
  motion, a larger cursor, persistent accessibility status and Atkinson
  Hyperlegible type. These are system defaults, not an invasive GTK fork, so
  application accessibility and future GNOME updates retain their standard
  behavior.
- Local wake gating, activation timeout, always-available stop/sleep phrases and
  hardware capability degradation run before Hermes or GPT fallback.
- The AT-SPI adapter describes the active application/window/focus, lists up to
  30 current semantic controls, navigates back and cycles accessible windows.
- Orientation, repeat, correction and cancel commands are deterministic and
  offline. Numbered control activation is re-read immediately before execution
  and remains confirmation-gated.

## Installer safety foundation after 0.4.1

- A fixed-argument, read-only `lsblk --json` inventory rejects the live medium,
  removable, read-only, mounted, undersized and non-stably identified devices.
- The immutable public plan can carry the stable by-id path, exact byte size,
  model and serial suffix. It is rebound to freshly discovered hardware before
  hand-off; missing, duplicated, changed or newly mounted targets fail closed.
- Whole-disk erase is the only mode the voice-plan validator accepts. Coexist
  and manual partitioning remain keyboard/Orca fallback paths and are not
  falsely presented as voice-native.
- A single-use exact confirmation phrase exists only in process memory and
  expires after 120 seconds. This is not yet connected to a destructive job.
- Calamares never preselects erase. Its default proposal is LUKS2 with a
  separate unencrypted `/boot`, Btrfs root and swap file. The separate boot
  volume avoids relying on GRUB to unlock Argon2-backed LUKS2.
- The setup window now keeps status and primary buttons outside the scrollable
  form so they stay visible at small virtual-machine resolutions.
- A nine-line GPL-compatible patch is built against Debian's exact Calamares
  3.3.14-1 source. On leaving the partition page it publishes only selected
  device node, mode, encryption boolean and filesystem to GlobalStorage; the
  LUKS passphrase is never exported.
- `shellprocess@clausis-guard` is inserted immediately before the partition
  placeholder in Calamares' execution sequence. For whole-disk mode it re-runs
  discovery and denies a missing, changed, mounted, removable, unstable,
  unencrypted or non-Btrfs target before any Calamares partition job starts.

The target/profile enforcement boundary is now tied to Calamares' execution
queue. The missing boundary is protected user authorisation: the random phrase
and recovery-key export are not yet consumed by that pre-write guard. Until
those and a persistent-disk VM test pass, the phrase is test-only and
Calamares's own summary remains authoritative.

## Not implemented after 0.4.1

- Dedicated low-power wake-word inference, certified echo cancellation and
  true Barge-in.
- Complete GNOME Shell and xdg-desktop-portal coverage beyond the first AT-SPI
  adapter.
- Hermes-to-broker system-action wiring; 0.4.1 Hermes output is reply-only.
- Physical proof of trusted microphone/seat isolation and replay detection;
  the former string-based D-Bus PIN transport has been removed.
- Speaker verification, replay detection or biometric enrollment.
- Protected-phrase authorisation of the guarded Calamares transaction,
  recovery-key export, TPM enrollment, Btrfs subvolume snapshots and rollback.
- Short-lived OpenAI client credentials from a trusted backend; 0.4.1 stores
  the voluntarily supplied standard API key in the user's private `0600` file.
- Cryptographic verification of the upstream Hermes release tag against a
  Clausis-owned allowlist of maintainer keys; the current updater relies on TLS
  and the official GitHub repository boundary.
- Provider OAuth inside the Clausis dialog; OAuth providers currently hand off
  to the upstream Hermes flow.

These are explicit release blockers, not silently mocked capabilities.
The staged implementation sequence is documented in
`docs/VOICE_ONLY_GAP_ANALYSIS.md`.
