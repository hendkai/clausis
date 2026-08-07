# Release gate

Status for 0.4.1: **blocked for production/end-user release; suitable only as
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
  targets; the current release intentionally stays in half-duplex.
- [ ] Real security contact and HTTPS `security.txt` configured.
- [x] Public trusted-confirmation API no longer transports phrase, PIN or
  capability; the isolated service captures locally and submits directly.
- [ ] Physical confirmation-audio isolation, replay handling and spoken abort
  pass on every supported hardware profile.
- [x] GTK accessibility metadata, local voice setup path and Calamares target-copy code are present and structurally validated in the final ISO.
- [x] Read-only disk inventory rejects live/removable/mounted/read-only/undersized
  targets, plans rebind stable identity, and destructive Calamares choice is not
  preselected. LUKS2/Btrfs defaults pass structural Debian checks.
- [ ] Validated target identity and protected random phrase are enforced by the
  exact Calamares partition transaction before its first block-device write.
- [ ] Complete Calamares install and target-copy behavior validated on a persistent virtual or physical disk.
- [ ] ISO, package repository and update metadata signed.
- [ ] Online Hermes releases verified against trusted maintainer signing keys.
- [ ] Exact ISO checksum boots, speaks and installs successfully on supported physical hardware.
- [ ] Snapshot rollback and speech health recovery verified on hardware.
- [ ] Prompt-injection and voice-spoof corpus gates pass.
- [ ] Orca, keyboard and voice user studies meet acceptance criteria.
- [ ] Model/voice licenses and cloud data flows approved.
- [ ] Real OpenAI Realtime session, one-hour reconnect behavior, billing notice
  and consent withdrawal validated with a dedicated test account on hardware.
- [ ] Biometric DPIA and legal review completed if voiceprint is enabled.
- [ ] Human product owner and security lead sign the release evidence.
