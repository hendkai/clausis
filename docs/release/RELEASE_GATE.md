# Release gate

Status for 0.1.0: **blocked for end-user release; suitable for source prototype
review only**.

- [x] Core unit tests pass.
- [x] Action schema and capability replay tests exist.
- [x] Threat model, AI contribution record and preliminary CRA scope exist.
- [x] Repository-level CycloneDX SBOM and license notices exist.
- [x] Debian Stable amd64 package builds and its 60 tests pass in a clean container.
- [x] Hybrid ISO builds; media, BIOS/UEFI entries and emulated live-to-GDM boot pass.
- [ ] Real security contact and HTTPS `security.txt` configured.
- [ ] Trusted PIN/audio path replaces prototype D-Bus string.
- [ ] PipeWire/STT/TTS, GNOME and Calamares adapters implemented and tested.
- [ ] ISO, package repository and update metadata signed.
- [ ] Exact ISO checksum boots, speaks and installs successfully on supported physical hardware.
- [ ] Snapshot rollback and speech health recovery verified on hardware.
- [ ] Prompt-injection and voice-spoof corpus gates pass.
- [ ] Orca, keyboard and voice user studies meet acceptance criteria.
- [ ] Model/voice licenses and cloud data flows approved.
- [ ] Biometric DPIA and legal review completed if voiceprint is enabled.
- [ ] Human product owner and security lead sign the release evidence.
