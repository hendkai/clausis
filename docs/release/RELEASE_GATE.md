# Release gate

Status for 0.4.1: **blocked for production/end-user release; suitable only as
an explicitly labelled public technical test preview**.

- [x] Core unit tests pass.
- [x] Action schema and capability replay tests exist.
- [x] Threat model, AI contribution record and preliminary CRA scope exist.
- [x] Repository-level CycloneDX SBOM and license notices exist.
- [x] Hermes source and dependency resolution are pinned to reviewed upstream identifiers.
- [x] The bundled Faster-Whisper runtime files have an exact SHA-256 manifest;
  offline cache import, chroot installation and final ISO extraction all fail
  closed on a missing or changed file.
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
- [x] Confirmed notification reading is restricted to Showing AT-SPI
  `notification` roles inside exactly one GNOME Shell application, excludes
  calendar/editable/protected content, applies bounded count/text limits and
  audit-redacts the complete spoken result.
- [x] Numbered notification dismissal carries no notification title, rebinds
  the same GNOME Shell plus the complete ordered visible-notification identity
  snapshot and invokes only one exact Dismiss or Close action.
- [x] Notification dismissal verifies its post-state within two seconds as the
  same Shell and exact original order minus only the selected object; unchanged
  or foreign mutation never reports success.
- [x] Confirmed permission decisions rebind the same application, complete
  ordered top-level window list, active dialog and exact Allow/Deny pair before
  invocation, then accept only that window order minus the dialog within two
  seconds; unchanged, foreign-mutated or unreadable state fails explicitly.
- [x] Recognized file choosers keep selection/navigation separate from commit;
  confirmed accept/cancel requires one exact semantic pair and rebinds the
  same application, complete ordered top-level window list, active dialog and
  both concrete controls immediately before invocation, then accepts only that
  window order minus the chooser within two seconds. Unchanged, foreign-mutated
  or unreadable state fails explicitly.
- [x] Confirmed generic standard-dialog decisions accept only one exact
  OK/Cancel, Yes/No, Confirm/Cancel, Retry/Cancel or Apply/Cancel pair; Retry
  and Apply are distinct intents, file choosers and permission pairs are
  excluded. The same application, complete ordered top-level window list,
  dialog and both concrete controls are rebound before the single
  non-reversible high-risk action, then only that window order minus the dialog
  is accepted within two seconds. Unchanged, foreign-mutated or unreadable
  state fails explicitly.
- [x] Active regular-dialog text can be read only through one confirmed,
  audit-redacted action restricted to static labels, paragraphs and
  descriptions; editable text and file choosers are excluded and the result is
  bounded to 20 unique items and 1,000 characters.
- [x] Close-only regular dialogs have a distinct confirmed high-risk action
  requiring exactly one Close/Schließen/Dismiss control across the complete
  actionable surface, with dialog and concrete-control rebinding immediately
  before invocation. The complete application-window identity list is rebound
  at the same boundary, followed by a two-second exact same-application
  postcondition accepting only the original order minus that dialog.
- [ ] Dedicated wake-word and Barge-in latency meet the physical-hardware
  targets; the current release intentionally stays in half-duplex.
- [ ] Real security contact and HTTPS `security.txt` configured.
- [x] Public trusted-confirmation API no longer transports phrase, PIN or
  capability; the isolated service captures locally and submits directly.
- [x] Exact local spoken abort phrases fail closed at every protected phrase,
  PIN and installer recording step and delete the temporary recording.
- [ ] Physical confirmation-audio isolation and replay handling pass on every
  supported hardware profile.
- [x] GTK accessibility metadata, local voice setup path and Calamares target-copy code are present and structurally validated in the final ISO.
- [x] Read-only disk inventory rejects live/removable/mounted/read-only/undersized
  targets, plans rebind stable identity, and destructive Calamares choice is not
  preselected. LUKS2/Btrfs defaults pass structural Debian checks.
- [x] Patched Calamares exports non-secret in-memory target/profile metadata and
  the stable identity guard runs before its first partition job.
- [x] The exact pre-write process creates and speaks the expiring random phrase,
  captures one local response and never exports phrase or transcript through
  Calamares state, arguments or stdout.
- [ ] A high-entropy recovery key is generated, spoken twice and added to the
  installed LUKS volume without command-line or Calamares-state disclosure.
  The first full disposable install exposed a fail-open integration defect:
  the guard consumed the fragile nested `partitionChoices.install` expansion,
  treated Erase as a non-Erase fallback and skipped the protected recovery
  exchange. The rebuilt ISO now exports and consumes the flat
  `clausisInstallMode` value and structurally verifies it in both the compiled
  partition module and guard configuration. A new disposable VirtualBox run
  now proves that the embedded guard rejects without microphone confirmation,
  removes its staged secret, leaves no partition table and does not change the
  first four MiB of the target. Positive spoken readback, key enrollment and
  recovery-key unlock are still required.
  A subsequent stricter probe found and corrected the Debian executable path,
  requires bridge-owned `denied` JSON, and rejects missing/unknown install
  modes. Final ISO SHA-256
  `c7ad5e541f47632bd91bb4b70317517c503255db893a085db76b2c5e12061671`
  passes this real embedded-bridge negative test in VirtualBox.
  The downstream LUKS job now independently rejects an absent confirmed key;
  final ISO SHA-256
  `cae6866f1930169988a43701a6ce9ba7d013bd8cf3bb4ed0c0e116b3a78729c4`
  contains this compiled fail-closed invariant and passes the guard regression
  again in a fresh disposable VirtualBox VM.
- [ ] The user-noted recovery key is verified by an accessible unlock test on a
  disposable persistent installation before installation can finish.
- [ ] Complete Calamares install and target-copy behavior validated on a
  persistent virtual or physical disk. The host preflight now proves that a
  separately registered EFI VM boots the exact ISO with only a newly created
  project-local disposable VDI and that VM/VDI cleanup is bounded; Calamares
  execution, installed-system boot and unlock remain unverified. A 45-second
  non-mutating foreground capture confirms that the accessible Clausis setup
  dialog is the expected synchronous gate before Calamares. A disposable-only
  follow-up filled both matching PIN fields, but the attempted save mnemonic
  did not activate the visible button; the dialog remained open and Calamares
  received no input. A subsequent readiness-gated run closed this sub-gate: it
  waited for the actual setup window, focused Save through GTK's tab order,
  activated it with Enter and proved the visible Calamares 13 welcome page.
  No Calamares control was activated; partitioning and installation remain
  unverified. A later disposable-only preflight safely reached the Partitions
  page through Location and Keyboard. It showed only the fresh 64-GiB VBOX
  disk, neither Erase nor Manual was selected and Next was disabled. No
  partition choice or disk write occurred. Later keyboard-only Erase-selection
  probes were rejected because the radio state was not visually observed;
  their disposable VMs/VDIs were removed and this gate remains open.
  A subsequent GUI-mode probe remained on Welcome; it led to an additional
  visual Partitions-page gate so sent navigation input alone cannot pass.
  Calamares now receives the explicit AT-SPI bus address across its privilege
  boundary, but the exact Erase radio is still not exposed/selected reliably;
  the independent radio-pixel gate continues to reject the flow.
  A separately bound visible VBox window has now proven the non-writing Erase
  selection and encrypted proposed layout. Passphrases, Next and all write
  stages were intentionally untouched; those remain open gates.
  A later disposable run validated matching temporary LUKS passphrases and
  reached Users. Users data, Summary, Install and all write stages remain open.
  A follow-up filled valid disposable Users data and reached Summary with
  automatic login off. Install and all write/confirmation stages remain open.
  The subsequent explicitly approved disposable run confirmed Install Now,
  completed installation, booted without the ISO, unlocked LUKS, reached GDM
  and logged into the installed Clausis desktop. Recovery-key and physical-
  hardware validation remain open.
- [ ] ISO, package repository and update metadata signed.
- [ ] Online Hermes releases verified against trusted maintainer signing keys.
- [ ] Exact ISO checksum boots, speaks and installs successfully on supported physical hardware.
- [ ] Snapshot rollback and speech health recovery verified on hardware.
- [ ] VirtualBox/GNOME live-session ACPI shutdown reliably reaches poweroff
  after one request. The VM-only independent `acpid` fallback is verified in
  the final SquashFS and queues `systemctl --no-block poweroff`. The fail-closed
  soak harness binds every run to one ISO hash and records partial failures.
  The latest final-ISO series passed 5/5 fresh boots in 9.4 to 13.7 seconds;
  its host-side state reader catches and retries VirtualBox's transient
  direct-session console-object failure. Earlier diagnostics
  also reproduced host-accepted requests which produced no guest power-key
  event at logind or active acpid. Longer endurance and hardware coverage stay
  open.
- [ ] Prompt-injection and voice-spoof corpus gates pass.
- [ ] Spoken Recovery-key ceremony passes end to end. The final ISO exposes a
  PipeWire input/output pair plus `pw-record`, `pw-play` and `pw-loopback` in a
  disposable VirtualBox guest. TTS-to-local-capture and embedded
  Faster-Whisper recognition now pass on the final ISO, but the full 48-digit
  readback, random confirmation phrase, LUKS enrollment and recovery unlock
  are not yet validated.
- [ ] Orca, keyboard and voice user studies meet acceptance criteria.
- [ ] Model/voice licenses and cloud data flows approved.
- [ ] Real OpenAI Realtime session, one-hour reconnect behavior, billing notice
  and consent withdrawal validated with a dedicated test account on hardware.
- [ ] Biometric DPIA and legal review completed if voiceprint is enabled.
- [ ] Human product owner and security lead sign the release evidence.
