# Threat model

Status: living pre-release assessment for Clausis Core 0.2.1.

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
| Agent automates confirmation | Confirmer separated from AT-SPI path and owns phrase | Prototype D-Bus/PIN transport is not yet a trusted compositor path. |
| Recorded or cloned voice | Random phrase, PIN, lockout; future anti-replay | Not sufficient against a targeted attacker; documented home-use limit. |
| Audit tampering | HMAC chain and privacy redaction | Local root can still replace log and key; remote/WORM export is future work. |
| Malicious update | Signed Debian packages, SBOM, snapshot/health rollback plan | ISO signing and rollback integration are not implemented yet. |
| Malicious online Hermes release | Official GitHub API/repository only, strict stable-tag grammar, exact-tag fetch, frozen lockfile, license check and switch-after-success | A compromised upstream repository/GitHub account or dependency artifact can still publish a malicious stable release; maintainer-key verification is not implemented. |
| Live user redirects privileged installer copy | Calamares transfer accepts only bounded regular files, opens with `O_NOFOLLOW` and atomically replaces target names | A compromised root process or Calamares itself remains outside this control. |
| Audio loss locks out user | Equal keyboard/Orca path and recovery boot requirement | Requires end-to-end hardware testing. |

## Release blockers

- Replace the prototype string PIN D-Bus argument with direct trusted audio
  verification or a protected memfd/portal transport.
- Prove Hermes cannot access the confirmation microphone stream, random phrase,
  PIN input or capability credential.
- Implement and fuzz every privileged adapter; never invoke arbitrary programs.
- Add real OS-level Hermes sandboxing and verify no terminal/code/file-write
  bypass remains through MCP, skills, hooks or plug-ins.
- Complete biometric DPIA and qualified legal review before voiceprint storage.
- Test at least 50 prompt-injection payloads and the audio spoofing matrix.
- Ship signed ISO/package repositories and validate automatic rollback.
- Pin trusted Hermes maintainer signing keys and verify release signatures
  before accepting an online installer update.

## Security acceptance gates

- Zero irreversible actions from the injection corpus without a matching,
  unexpired capability.
- Zero successful mutation/replay of an already consumed capability.
- All core flows remain available by keyboard and Orca when audio is disabled.
- No secret or raw voice data in action or audit logs.
- Any missing dependency, adapter or authorization fails closed.
