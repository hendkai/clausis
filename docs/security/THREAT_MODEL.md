# Threat model

Status: living pre-release assessment for Clausis Core 0.4.1.

## Intended use and boundary

Clausis targets a private household. Voice login is a convenience barrier, not
a defense against theft, a targeted attacker or modern voice cloning. The
security objective is to prevent untrusted content, Hermes, background speech
or an accidental utterance from silently performing sensitive system actions.

## Assets

- User files, credentials, cloud tokens and Hermes memory.
- Capability and audit keys.
- Voice PIN derivative and future speaker template.
- Update signing keys, package repository and recovery snapshots.
- Integrity and availability of spoken accessibility paths.

## Attackers

- A web page, email or document attempting prompt injection.
- Nearby audio, television, recording or generated/cloned speech.
- A malicious or compromised Hermes plug-in, model provider or model output.
- A local unprivileged process in the desktop session.
- A supply-chain attacker modifying packages, models or voices.
- Accidental misrecognition and hardware/audio failure.

## High-risk paths and controls

| Threat | Control | Residual risk |
|---|---|---|
| Prompt injection proposes an action | Origin taint, strict verb/argument schema, trusted confirmation | User may still approve a misleading but accurately summarized action. |
| Hermes sends a shell command | No shell action exists; unknown fields and actions are denied | A vulnerable platform adapter could reintroduce injection. |
| Capability replay or broadening | HMAC, exact request digest, 30 s TTL, one-time JTI | Key compromise defeats the scheme. |
| Agent automates confirmation | Public D-Bus exposes only `ConfirmAndSubmit`; phrase, PIN and capability stay inside the isolated system service, which speaks and records directly and submits to Broker itself | Physical isolation from the desktop PipeWire graph is not yet proven on supported hardware. |
| Recorded or cloned voice | Random phrase, PIN, lockout; future anti-replay | Not sufficient against a targeted attacker; documented home-use limit. |
| Audit tampering | HMAC chain and privacy redaction | Local root can still replace log and key; remote/WORM export is future work. |
| Malicious update | Signed Debian packages, SBOM, snapshot/health rollback plan | ISO signing and rollback integration are not implemented yet. |
| Malicious online Hermes release | Official GitHub API/repository only, strict stable-tag grammar, exact-tag fetch, frozen lockfile, license check and switch-after-success | A compromised upstream repository/GitHub account or dependency artifact can still publish a malicious stable release; maintainer-key verification is not implemented. |
| GPT Live model proposes an unsafe action | Only an enumerated function is exposed; action, risk, origin and reversibility are canonicalized locally; medium-or-higher risk requires trusted confirmation | A model may misunderstand a spoken request or socially pressure the user; low-risk reversible actions can execute immediately for responsiveness. |
| Prompt or audio injection reaches GPT Live | No general computer-use, shell, MCP, plug-in or capability token is exposed; strict size/schema limits and broker policy apply | Nearby speech can still trigger a low-risk reversible allowlisted action. Wake-word and speaker verification are not implemented. |
| OpenAI API key is stolen by a local process | Key is keyboard-only, excluded from public installer state and stored mode `0600`; never sent as a tool argument | A malicious process running as the same desktop user can read it. Short-lived backend-issued client tokens are not implemented. |
| Cloud remains active after user wants to stop | Local desktop stop action uses a per-user runtime marker and does not require a model response or network | Spoken stop still depends on the active Realtime session recognizing/calling the stop tool; use the local launcher or Ctrl+C if it does not. |
| Cloud audio disclosure | GPT Live is off by default and requires a separate explicit consent directly beside the notice | While active, microphone audio is sent to OpenAI; surrounding speech may be captured. Provider retention/account settings require user review. |
| Live user redirects privileged installer copy | Hermes files and the versioned PIN verifier are bounded, reject symlinks, open with `O_NOFOLLOW` and atomically replace target names; plaintext PIN is never staged | A compromised root process or Calamares itself remains outside this control. |
| Installer erases the live medium or wrong disk | Read-only inventory excludes live/removable/mounted/read-only/undersized disks; execution plans use stable by-id, exact byte size and serial suffix and must rebind immediately before hand-off | The validated plan is not yet enforced by Calamares partition jobs; protected voice authorisation is therefore not enabled for real erasure. |
| Prompt injection says “confirm installation” | Whole-disk plans require a canonical destructive summary and an exact expiring single-use random phrase; ambiguity, timeout and reuse deny | Challenge logic is not yet wired to a privileged installation transaction and provides no production authorisation today. |
| Audio loss locks out user | Equal keyboard/Orca path and recovery boot requirement | Requires end-to-end hardware testing. |
| Background speech reaches the local agent | A local wake gate discards transcripts until an exact activation phrase and expires after 25 seconds; stop works in every state | STT-based wake detection is heavier and less resistant to replay than a dedicated verified wake-word model. |
| Malicious accessible widget is activated by number | AT-SPI targets are re-read from the active window and arbitrary activation is medium risk | A misleading accessible name may still influence the user; trusted confirmation is not yet production-ready. |

## Release blockers

- Prove Hermes cannot access the confirmation microphone stream, random phrase,
  PIN input or capability credential.
- Prove direct ALSA/PipeWire capture isolation and add tested replay/synthetic-
  voice handling on every supported audio profile.
- Implement and fuzz every privileged adapter; never invoke arbitrary programs.
- Add real OS-level Hermes sandboxing and verify no terminal/code/file-write
  bypass remains through MCP, skills, hooks or plug-ins.
- Complete biometric DPIA and qualified legal review before voiceprint storage.
- Test at least 50 prompt-injection payloads and the audio spoofing matrix.
- Ship signed ISO/package repositories and validate automatic rollback.
- Pin trusted Hermes maintainer signing keys and verify release signatures
  before accepting an online installer update.
- Bind the validated stable target identity to Calamares's actual partition job
  before any write and exercise power-loss and device-swap cases on disposable
  persistent VM disks.

## Security acceptance gates

- Zero irreversible actions from the injection corpus without a matching,
  unexpired capability.
- Zero successful mutation/replay of an already consumed capability.
- All core flows remain available by keyboard and Orca when audio is disabled.
- No secret or raw voice data in action or audit logs.
- Any missing dependency, adapter or authorization fails closed.
