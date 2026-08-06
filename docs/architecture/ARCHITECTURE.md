# Clausis architecture

Status: executable core prototype, version 0.1.1.

## Data flow

```text
microphone -> audio frontend -> VoiceRuntime -> OfflineRouter ------+
                                      |                             |
                                      +-> HermesAdapter (optional) -+-> ActionBroker
                                                                       |
                           TrustedConfirm <- confirmation request -----+
                                |                                      |
                                +---- single-use capability ---------->+
                                                                       |
                                                             fixed platform adapters
```

The audio frontend owns wake-word, VAD, STT, echo handling and TTS. It emits a
final transcript but receives no system privileges. `VoiceRuntime` always
checks deterministic offline commands first. Only unmatched utterances may be
sent to Hermes, and only after cloud consent when a remote provider is used.

## Trust boundaries

1. **Voice Runtime** is unprivileged and replaceable. A compromised STT model
   can propose requests but cannot execute them.
2. **Hermes Adapter** discards caller-supplied origins and capability tokens.
   Every request is marked `hermes`, which forces confirmation.
3. **Action Broker** accepts only allowlisted verbs and validated arguments. It
   does not accept shell strings and cannot reduce an action's minimum risk.
4. **Trusted Confirm** creates the canonical summary and random phrase. Tokens
   bind action, target, arguments, origin and expiry and are single-use.
5. **Platform adapters** translate one approved action into a fixed argv vector
   or desktop API call. Missing adapters fail closed.

The HMAC capability key is a root-created systemd credential shared by broker
and confirmer. Hermes and the desktop session do not receive it. This prevents
capability forgery by the agent; whole-process isolation and D-Bus policy remain
required because in-process pattern filters are not security boundaries.

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
| No network | Offline router continues; Hermes reports unavailable within 2 seconds. |
| No remote model | Same as no network; no silent provider fallback. |
| Unknown audio hardware | Announced half-duplex; VAD can still interrupt TTS. |
| No microphone | Spoken output plus keyboard and Orca remain active. |
| No audio | Keyboard, visual UI and Orca remain active. |
| Broker refusal | Canonical reason is spoken and displayed; no automatic bypass. |
| Failed update | Health check requests bootloader rollback; `/home` is not rolled back. |

## Not implemented in 0.1.1

- Actual PipeWire capture, wake-word, STT and TTS plugins.
- GNOME Shell, AT-SPI and xdg-desktop-portal adapters.
- Trusted compositor/seat UI and secure PIN transport.
- Speaker verification, replay detection or biometric enrollment.
- Calamares backend execution, partitioning, LUKS/TPM enrollment and snapshots.
- Hermes package installation and provider OAuth.

These are explicit release blockers, not silently mocked capabilities.

