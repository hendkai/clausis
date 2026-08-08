# Release gate

Status for 0.5.0: **blocked for production/end-user release; suitable only as
an explicitly labelled public technical test preview**.

- [x] Core unit tests pass.
- [x] Action schema and capability replay tests exist.
- [x] Threat model, AI contribution record and preliminary CRA scope exist.
- [x] Repository-level CycloneDX SBOM and license notices exist.
- [x] Hermes source and dependency resolution are pinned to reviewed upstream identifiers.
- [x] Online Hermes installation accepts only an exact official stable tag,
  uses its frozen lock and retains the bundled fallback until success.
- [x] Provider secrets are excluded from spoken summaries, logs and public installer state.
- [x] Optional GPT Live is off by default, has separate audio consent and a local
  non-cloud stop path, and exposes only typed broker actions.
- [x] Debian Stable amd64 package and complete automated suite pass in a clean container.
- [x] Hybrid ISO builds; media, BIOS/UEFI entries and emulated live-to-GDM boot pass.
- [x] Final ISO graphical capture shows live autologin and the accessible Clausis/Hermes setup without Debian's tour.
- [x] Clausis GNOME wallpaper, icon, GDM branding, supported appearance keys,
  reduced motion and legibility font have structural and rendered-image tests.
- [x] Local wake/timeout/stop gating and semantic GNOME orientation have
  deterministic tests; a real Debian GTK/AT-SPI smoke test found a live
  actionable widget; numbered mutation remains confirmation-gated.
- [ ] Dedicated wake-word and Barge-in latency meet the physical-hardware
  targets; the current release intentionally stays in half-duplex. The
  two-stage wake path, the interruption detector, the echo-cancel
  configuration and the earcons are implemented and unit tested, and
  `scripts/wake_latency.py` measures the software path (energy gate at 0.03 %
  duty cycle). No keyword model ships and no hardware measurement has been
  made, so `interrupt_detector` must stay unset.
- [ ] Real security contact and HTTPS `security.txt` configured.
- [x] Public trusted-confirmation API no longer transports phrase, PIN or
  capability; the isolated service captures locally and submits directly.
- [ ] Physical confirmation-audio isolation, replay handling and spoken abort
  pass on every supported hardware profile.
- [x] GTK accessibility metadata, local voice setup path and Calamares target-copy code are present and structurally validated in the final ISO.
- [x] Read-only disk inventory rejects live/removable/mounted/read-only/undersized
  targets, plans rebind stable identity, and destructive Calamares choice is not
  preselected. LUKS2/Btrfs defaults pass structural Debian checks.
- [ ] Patched Calamares exports non-secret in-memory target/profile metadata.
  The first 0.5.0 persistent-VM run exposed a missing custom-instance mapping:
  Calamares queued the guard but loaded no command. The configuration now binds
  both custom `shellprocess` instances explicitly and fails closed for missing
  or non-erase mode, but a fresh persistent-VM run must prove the guard executes
  before this gate can be checked again.
- [x] The exact pre-write process creates and speaks the expiring random phrase,
  captures one local response and never exports phrase or transcript through
  Calamares state, arguments or stdout.
- [x] A high-entropy recovery key is generated, spoken twice and added to the
  installed LUKS volume without command-line or Calamares-state disclosure.
- [ ] The user-noted recovery key is verified by an accessible unlock test on a
  disposable persistent installation before installation can finish.
- [ ] Complete Calamares install and target-copy behavior validated on a persistent virtual or physical disk.
- [ ] ISO, package repository and update metadata signed. Signing tooling and
  CI wiring exist (`scripts/sign_release.sh`); no release key is configured, so
  releases are still published unsigned.
- [ ] Online Hermes releases verified against trusted maintainer signing keys.
  Verification is implemented and fails closed; `packaging/trust/hermes-maintainers.asc`
  is still the placeholder, so online updates are refused entirely.
- [ ] Exact ISO checksum boots, speaks and installs successfully on supported physical hardware.
- [ ] Snapshot rollback and speech health recovery verified on hardware. The
  guard and the health check are implemented and unit tested; no run on real
  Btrfs/snapper has happened. Initramfs unlock audio and the speaking GDM
  greeter are implemented and structurally tested, never booted.
- [ ] Prompt-injection and voice-spoof corpus gates pass. Corpora now cover
  dictation, the clipboard, disguised permission prompts and the privileged
  helper in addition to the broker and the Hermes parser; a corpus against
  recorded and synthesised speech still requires audio hardware.
- [ ] Orca, keyboard and voice user studies meet acceptance criteria.
- [ ] Model/voice licenses and cloud data flows approved.
- [ ] Real OpenAI Realtime session, one-hour reconnect behavior, billing notice
  and consent withdrawal validated with a dedicated test account on hardware.
- [ ] Biometric DPIA and legal review completed if voiceprint is enabled.
- [ ] Human product owner and security lead sign the release evidence.
