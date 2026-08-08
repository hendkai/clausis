# Threat model

Status: living pre-release assessment for Clausis Core 0.5.0.

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
| Audit tampering | HMAC chain and privacy redaction; `/var/log` and `/var/lib/clausis` sit outside the Btrfs rollback boundary, so undoing a failed update cannot erase the record of what it did | Local root can still replace log and key; remote/WORM export is future work. On a system installed without the layout the rollback does revert the log, which is why the guard says so explicitly. |
| Session process widens a privileged action | The session may name only an action and one validated Debian package name; the argument vector comes from a root-side table in the Polkit-gated helper, which re-parses the request, re-evaluates the policy and re-verifies the action-bound capability | A user who passes the Polkit admin prompt still authorizes the action; the helper cannot tell a coerced user from a deliberate one. |
| Capability replayed at the privileged helper | The helper keeps its own root-only single-use store in `/run`, because the broker consumes tokens in a different process | A reboot clears `/run`, so a capability could be replayed across a reboot inside its 30 s lifetime. |
| Capability signing key is read by the desktop user | `/etc/clausis` is mode `0700 root:root` and the key is `0600 root:root`; both services receive it through systemd `LoadCredential`, which reads it as root before dropping privileges | Local root still holds the key; a future relaxation of the directory mode would silently reintroduce the exposure. |
| Dictation writes attacker-influenced text into a sensitive field | The adapter refuses a password role, the `PROTECTED` state, a terminal widget and any terminal ancestor before writing; the request schema rejects control characters, so no newline can submit a form or a command line | A normal document or chat field still receives whatever was understood; misrecognition and nearby speech are corrected by the user, not prevented. |
| Agent or cloud model dictates text on the user's behalf | Dictation carries the caller's origin, so Hermes and external content stay tainted and need trusted confirmation; GPT Live may dictate at low risk, which is the same trade-off as its other low-risk actions | A model that misunderstands can still write a wrong sentence into an open document; the text is spoken back but not undone automatically. |
| Overheard or injected speech approves a permission prompt | The dialog adapter classifies permission and authentication dialogs by wording in both languages and by any protected/password widget in the tree, and refuses to press the affirmative button at all; cancelling stays available | Classification is heuristic: an unusually worded prompt could be treated as an ordinary dialog, where accepting still needs trusted confirmation. Keyboard and Orca remain the intended path for these prompts. |
| Hijacked clipboard is pasted into a shell | Pasting reuses the dictation refusals, so a terminal widget, a terminal ancestor, a password role and the `PROTECTED` state all block the paste; only the widget's own accessible paste action is used | Pasting into an ordinary editor still inserts whatever another process placed on the clipboard; the result is spoken back but not inspected. |
| Voice closes a window and loses unsaved work | `app.close` is medium risk and requires trusted confirmation; Clausis invokes only the accessible close action the application publishes and never kills a process | An application that closes without prompting can still discard unsaved state. |
| Shell bridge is abused by a compromised session process | Every extension method is parameterless and maps to one fixed shell surface; no evaluation, coordinate handling or input synthesis is exported | A process that can already talk to the session bus can open the overview; the surfaces themselves carry no privilege. |
| Malicious update | Signed Debian packages, SBOM, and a snapshot guard that runs package and security updates between a `pre` and `post` snapshot and undoes the change when the update fails or the health check reports a system that can no longer speak | Release signing tooling exists but no release key is configured yet, so published images remain unsigned. A machine without a working snapper still receives updates, deliberately, and then has nothing to roll back to. |
| Malicious online Hermes release | Official GitHub API/repository only, strict stable-tag grammar, exact-tag fetch, frozen lockfile, license check, switch-after-success, and OpenPGP verification of the signed tag or commit against a pinned maintainer trust anchor in an isolated keyring | The trust anchor ships as a placeholder, so every online release is currently refused and the bundled version stays active. Once real keys are added, a compromised maintainer key or a malicious dependency inside a correctly signed release remains outside this control. |
| GPT Live model proposes an unsafe action | Only an enumerated function is exposed; action, risk, origin and reversibility are canonicalized locally; medium-or-higher risk requires trusted confirmation, and privileged actions additionally pass Polkit | A model may misunderstand a spoken request or socially pressure the user; low-risk reversible actions can execute immediately for responsiveness. The enumeration now covers the whole allowlist, so the model can also propose restart, power-off and package changes — each still blocked behind confirmation, but the social-engineering surface for those prompts is larger. |
| Prompt or audio injection reaches GPT Live | No general computer-use, shell, MCP, plug-in or capability token is exposed; strict size/schema limits and broker policy apply | Nearby speech can still trigger a low-risk reversible allowlisted action. A dedicated wake-word stage is implemented but ships without a model, so the transcript gate is what is active; speaker verification is not implemented. |
| OpenAI API key is stolen by a local process | Key is keyboard-only, excluded from public installer state and stored mode `0600`; never sent as a tool argument | A malicious process running as the same desktop user can read it. Short-lived backend-issued client tokens are not implemented. |
| Cloud remains active after user wants to stop | Local desktop stop action uses a per-user runtime marker and does not require a model response or network | Spoken stop still depends on the active Realtime session recognizing/calling the stop tool; use the local launcher or Ctrl+C if it does not. |
| Cloud audio disclosure | GPT Live is off by default and requires a separate explicit consent directly beside the notice | While active, microphone audio is sent to OpenAI; surrounding speech may be captured. Provider retention/account settings require user review. |
| Live user redirects privileged installer copy | Hermes files and the versioned PIN verifier are bounded, reject symlinks, open with `O_NOFOLLOW` and atomically replace target names; plaintext PIN is never staged | A compromised root process or Calamares itself remains outside this control. |
| Installer erases the live medium or wrong disk | A patched Calamares exports its in-memory target without secrets; a guard re-runs strict inventory immediately before the partition placeholder and blocks changed/live/removable/mounted/read-only/undersized/unstable targets before the first write | Hot-unplug after the guard and a compromised root/Calamares remain outside this control. |
| Recovery key leaks during installation | The trusted guard generates and speaks it locally, stages it mode 0600 in tmpfs, and the patched LUKS module adds it without command-line arguments before overwriting and unlinking temporary copies | Root, a compromised installer, room audio recording or unproven desktop-audio isolation can still expose it; persistent-VM verification is pending. |
| Prompt injection says “confirm installation” | After exact target rebinding, the pre-write process itself speaks the destructive summary and expiring single-use phrase, records one local answer, deletes the recording and exports neither phrase nor transcript | Physical separation from desktop audio and a protected keyboard/Orca equivalent still require implementation and hardware proof. |
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
- Verify the spoken recovery key against an installed LUKS volume, prove
  trusted-audio and protected keyboard isolation, then exercise power-loss and
  device-swap cases on disposable persistent VM disks.

## Security acceptance gates

- Zero irreversible actions from the injection corpus without a matching,
  unexpired capability.
- Zero successful mutation/replay of an already consumed capability.
- All core flows remain available by keyboard and Orca when audio is disabled.
- No secret or raw voice data in action or audit logs.
- Any missing dependency, adapter or authorization fails closed.
