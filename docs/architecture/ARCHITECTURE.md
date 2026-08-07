# Clausis architecture

Status: executable core prototype, version 0.3.0.

## Data flow

```text
microphone -> local STT -> VoiceRuntime -> OfflineRouter -> ActionBroker
                               |
                               +-- unmatched -> HermesOneShot -> spoken reply

microphone -> optional OpenAI Realtime -> typed function request -> ActionBroker
     ^                    |                                      |
     +---- streamed TTS <-+                         trusted confirmation for risk
```

The target audio frontend owns wake-word, VAD, STT, echo handling and TTS and
receives no system privileges. The 0.3.0 prototype implements local STT and TTS
with sequential, fixed recording windows; wake-word, VAD, echo cancellation and
barge-in are not yet present. `VoiceRuntime` always checks deterministic offline
commands first. Only unmatched utterances may be sent to Hermes, and only after
cloud consent when a remote provider is used.

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
   to the 0.3.0 runtime yet.
3. **GPT Live frontend** holds the user's OpenAI key and streams audio only
   after separate opt-in. Its model can propose fixed typed actions, but cannot
   execute or confirm them. A per-user local stop marker and desktop launcher
   terminate streaming without cloud cooperation.
4. **Action Broker** accepts only allowlisted verbs and validated arguments. It
   does not accept shell strings and cannot reduce an action's minimum risk.
5. **Trusted Confirm** creates the canonical summary and random phrase. Tokens
   bind action, target, arguments, origin and expiry and are single-use.
6. **Platform adapters** translate one approved action into a fixed argv vector
   or desktop API call. Missing adapters fail closed.

The target design gives broker and confirmer a root-created HMAC credential;
Hermes and the desktop session do not receive it. The prototype service units
and D-Bus policy exist, but production credential provisioning and the trusted
confirmation UI are not enabled in 0.3.0.

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

## Degradation

| Failure | Behavior |
|---|---|
| No network | Offline router continues; an attempted Hermes reply fails after its provider/network error or the 45-second hard timeout. |
| No remote model | Same as no network; no silent provider fallback. |
| GPT Live unavailable | A spoken notice is emitted and the existing local voice loop starts automatically. |
| User wants online audio stopped | “GPT Live sofort beenden” writes a local per-user stop marker; the Realtime loop checks it independently of the cloud. |
| Unknown audio hardware | 0.3.0 reports capture/output failure; automatic half-duplex selection is not implemented. |
| No microphone | Setup, desktop, keyboard and Orca remain available; the current automatic voice loop cannot accept a stop phrase. |
| No audio | Keyboard, visual setup and Orca remain available. |
| Broker refusal | Canonical reason is spoken and displayed; no automatic bypass. |
| Hermes release lookup or install fails | The launcher remains on the pinned image version; status is recorded and announced at first installed login. |
| System package update fails | Health-check and snapshot scaffolding exist, but automatic rollback is not wired in 0.3.0. |

## Implemented for the 0.3.0 image

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

## Not implemented in 0.3.0

- Wake-word activation and certified echo cancellation.
- GNOME Shell, AT-SPI and xdg-desktop-portal adapters.
- Hermes-to-broker system-action wiring; 0.3.0 Hermes output is reply-only.
- Trusted compositor/seat UI and secure PIN transport.
- Speaker verification, replay detection or biometric enrollment.
- Fully voice-native Calamares partitioning, LUKS/TPM enrollment and snapshots.
- Short-lived OpenAI client credentials from a trusted backend; 0.3.0 stores
  the voluntarily supplied standard API key in the user's private `0600` file.
- Cryptographic verification of the upstream Hermes release tag against a
  Clausis-owned allowlist of maintainer keys; the current updater relies on TLS
  and the official GitHub repository boundary.
- Provider OAuth inside the Clausis dialog; OAuth providers currently hand off
  to the upstream Hermes flow.

These are explicit release blockers, not silently mocked capabilities.
