# Release gate

Status for 0.2.1: **blocked for production/end-user release; suitable only as
an explicitly labelled public technical test preview**.

- [x] Core unit tests pass.
- [x] Action schema and capability replay tests exist.
- [x] Threat model, AI contribution record and preliminary CRA scope exist.
- [x] Repository-level CycloneDX SBOM and license notices exist.
- [x] Hermes source and dependency resolution are pinned to reviewed upstream identifiers.
- [x] Online Hermes installation accepts only an exact official stable tag,
  uses its frozen lock and retains the bundled fallback until success.
- [x] Provider secrets are excluded from spoken summaries, logs and public installer state.
- [x] Debian Stable amd64 package and complete automated suite pass in a clean container.
- [x] Hybrid ISO builds; media, BIOS/UEFI entries and emulated live-to-GDM boot pass.
- [x] Final ISO graphical capture shows live autologin and the accessible Clausis/Hermes setup without Debian's tour.
- [ ] Real security contact and HTTPS `security.txt` configured.
- [ ] Trusted PIN/audio path replaces prototype D-Bus string.
- [x] GTK accessibility metadata, local voice setup path and Calamares target-copy code are present and structurally validated in the final ISO.
- [ ] Complete Calamares install and target-copy behavior validated on a persistent virtual or physical disk.
- [ ] ISO, package repository and update metadata signed.
- [ ] Online Hermes releases verified against trusted maintainer signing keys.
- [ ] Exact ISO checksum boots, speaks and installs successfully on supported physical hardware.
- [ ] Snapshot rollback and speech health recovery verified on hardware.
- [ ] Prompt-injection and voice-spoof corpus gates pass.
- [ ] Orca, keyboard and voice user studies meet acceptance criteria.
- [ ] Model/voice licenses and cloud data flows approved.
- [ ] Biometric DPIA and legal review completed if voiceprint is enabled.
- [ ] Human product owner and security lead sign the release evidence.
