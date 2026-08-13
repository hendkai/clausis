# Clausis 0.4.1 ISO test report

Date: 2026-08-07
Status: development evidence; not a production release approval

## Artifact

- File: `clausis-0.4.1-amd64.iso`
- Size: 2,643,034,112 bytes
- SHA-256: `a998cfa905e8545bc821c3ad7d635d57a8d2af9bb0004bc58c479d71405496c6`
- Base: Debian 13 stable, amd64, GNOME 48

## Passed checks

- The hybrid image has both BIOS and UEFI boot entries and its media check and
  SHA-256 verification pass.
- The final SquashFS contains Clausis Core, Hermes Agent 0.20.0, its MIT
  license, the pinned offline Faster-Whisper model, Orca, the setup application,
  the Clausis GNOME/GDM identity and Calamares configuration.
- The image contains the Clausis Calamares build
  `3.3.14-1+clausis11`. Its partition module exports only the selected device,
  encryption state and filesystem; it does not export the LUKS passphrase.
- The Calamares execution queue runs `shellprocess@clausis-guard` immediately
  before the first `partition` job and retains LUKS2/Btrfs whole-disk defaults
  without preselecting erase.
- A QEMU TCG boot from the exact ISO reached Debian kernel
  `6.12.101+deb13-amd64` and the running GNOME Display Manager.
- A separate graphical QEMU run reached the automatically authenticated live
  GNOME session. Visual review confirmed the Clausis wallpaper, matching
  purple/cyan identity, branded launchers, visible AI notice and the accessible
  Clausis/Hermes setup without a login prompt or Debian tour.

## Still not proven

- A complete persistent Calamares installation onto a virtual or physical disk.
- VirtualBox-specific firmware, graphics, audio and installation behavior.
- Real microphone, speaker, echo cancellation, Barge-in and trusted-audio
  isolation on supported hardware.
- The ISO documented here predates the protected-phrase integration. A newer
  image must be built after that code change. Recovery-key export is still not
  connected to the exact pre-write transaction, so production release remains
  blocked.

## 2026-08-08 VirtualBox development validation

- The current worktree passed all 170 Python tests under Debian 13 in WSL.
- A clean source build produced a 2,643,034,112-byte hybrid ISO. Its SHA-256,
  media, BIOS/UEFI entries, SquashFS, accessibility setup, installer target
  binding and LUKS recovery-key module passed `scripts/verify_iso.sh`.
- VirtualBox 7.2.14 booted the image with EFI from a dedicated 100-GiB dynamic
  VDI. Visual evidence reached the GRUB menu, Debian kernel splash and the
  automatically authenticated GNOME live session with Clausis branding.
- The first VirtualBox run exposed a stale `Technical Preview 0.1.2` badge in
  the GRUB and Syslinux splash assets. Both source assets are now
  version-neutral. A separate boot-preserving test ISO with only those two
  corrected assets mapped in passed the same EFI-to-GNOME VirtualBox flow;
  its SHA-256 is
  `f6340a47f69d63cae55eb72f339325804b80de2c4533bb6a3ba1f73b6494c957`.
- Evidence screenshots are written to `dist/clausis-vbox-boot-version-neutral.png`
  and `dist/clausis-vbox-live-session.png` in the local development tree.

The final source tree was subsequently rebuilt without patching the ISO. The
resulting 2,643,034,112-byte artifact has SHA-256
`7f2c92a4b0a5130288e373ec1493756c9f5653706490b15ec19891b4b484c35d`.
The complete internal verification passed, and VirtualBox booted this exact
unmodified artifact through the version-neutral EFI GRUB menu, Debian kernel
and automatically authenticated GNOME live session. Evidence screenshots are
`dist/clausis-final-vbox-grub.png` and
`dist/clausis-final-vbox-live-session.png`.

A complete destructive Calamares installation and recovery-key unlock test on
the disposable VDI remains open; no host disk was exposed to the installer.

## 2026-08-08 semantic window-action build

- The AT-SPI adapter gained fail-closed minimize, maximize, restore and close
  actions. It invokes only an exact action exposed by the active accessible
  frame; no coordinates, screen scraping or Wayland input simulation are used.
- Window close is medium risk and remains capability-confirmation-gated.
- All 176 Python tests passed under Debian 13, including direct AT-SPI action
  selection, missing-action denial, router and broker policy tests.
- The clean hybrid ISO build and the full `scripts/verify_iso.sh` chain passed.
  The 2,643,034,112-byte artifact has SHA-256
  `0b12f1baa370949325e6199b0b6c4dd58969356f5208963242680eed8c24828d`.
- VirtualBox 7.2.14 booted this exact artifact through EFI GRUB and the Debian
  kernel into the automatically authenticated GNOME live session. Evidence is
  stored locally as `dist/clausis-window-actions-vbox-grub.png` and
  `dist/clausis-window-actions-vbox-live.png`.

## 2026-08-08 semantic GNOME Shell controls build

- The fail-closed AT-SPI adapter now opens the GNOME overview and applications
  grid through exact accessible controls owned by GNOME Shell. It does not use
  screen coordinates, synthetic pointer input or broad name matching.
- The German and English command router exposes 37 commands, including
  `Zeige die Anwendungen` and `Show applications`.
- All 180 Python tests passed under Debian 13, including exact GNOME Shell
  application/control selection and rejection of matching controls exposed by
  unrelated applications.
- The clean hybrid ISO build and the full `scripts/verify_iso.sh` chain passed.
  The 2,643,034,112-byte artifact has SHA-256
  `0ac94bb86ae9aea52dca0254800c28141157b0c94dffdfaa2bbabd8c8903cb7b`.
- VirtualBox 7.2.14 booted this exact artifact through its version-neutral EFI
  GRUB menu into the automatically authenticated GNOME live session. The final
  screenshot shows the active GNOME overview, application dock and Clausis
  branding. Evidence is stored locally as
  `dist/clausis-shell-actions-vbox-grub.png` and
  `dist/clausis-shell-actions-vbox-live.png`.
- The VM was powered off after the test. A complete persistent Calamares
  installation and recovery-key unlock test still requires interactive trusted
  audio with a real microphone and remains open.

## 2026-08-08 quick settings and notifications build

- The exact-control GNOME Shell adapter now also supports quick settings and
  notifications in German and English. Matching remains restricted to the
  accessible application named exactly `GNOME Shell` or `gnome-shell` and to
  `click`, `press`, `activate` or `toggle` actions; no coordinates or synthetic
  input are used.
- Overview and application-grid actions were added to `SEMANTIC_MUTATIONS`.
  This closes a regression where those actions could execute while developer
  dry-run mode was enabled. All four Shell mutations now return `dry_run`
  without calling the AT-SPI provider.
- The deterministic router now exposes 39 German/English command families.
  All 182 Python tests passed under Debian 13.
- The clean hybrid ISO build and complete `scripts/verify_iso.sh` chain passed.
  The 2,643,034,112-byte artifact has SHA-256
  `f633eec0f2b2ef8127e8d3461b9afc17954d7e07c9b49ee07eaa379c3341d697`.
- VirtualBox 7.2.14 booted this exact artifact through EFI GRUB into the
  automatically authenticated GNOME live session. Evidence is stored locally
  as `dist/clausis-quick-settings-vbox-grub.png` and
  `dist/clausis-quick-settings-vbox-live.png`. The VM was powered off after the
  test.
- The boot test proves image integration and the GNOME runtime, but not the
  exact AT-SPI names exposed by every supported GNOME locale/version. Those
  compatibility variants still need session-level accessibility-tree tests.

## 2026-08-08 semantic standard-dialog controls build

- The active-window AT-SPI adapter can move focus forward or backward among
  current visible actionable controls using `grabFocus()` only. It does not
  synthesize Tab, pointer or Wayland input.
- A caller can select one control by its exact accessible name. The adapter
  re-reads the active tree immediately before execution, rejects missing or
  duplicate names, and invokes only the current advertised semantic action.
  Named activation is medium risk and capability-confirmation-gated.
- The deterministic router now exposes 42 German/English command families.
  All 189 Python tests passed under Debian 13, including direct provider tests
  for focus movement, unique-name activation, duplicate-name denial and stale
  action failure.
- The clean hybrid ISO build and complete `scripts/verify_iso.sh` chain passed.
  The 2,643,034,112-byte artifact has SHA-256
  `dc09d81a6769b83734997a0d5666cdb403db0ada27fb504cdca17f1833956c25`.
- VirtualBox 7.2.14 booted this exact artifact through EFI GRUB into the
  automatically authenticated GNOME live session with Clausis wallpaper and
  panel. Evidence is stored locally as
  `dist/clausis-dialog-controls-vbox-grub.png` and
  `dist/clausis-dialog-controls-vbox-live.png`. The VM was powered off after
  the test.
- The VirtualBox boot proves image integration and the GNOME runtime. Spoken
  end-to-end dialog control and persistent installation still require real
  microphone interaction and remain open.

## 2026-08-08 privacy-preserving semantic text entry build

- Confirmed voice commands can replace or clear only the currently focused
  AT-SPI editable-text widget. No keyboard events, clipboard, coordinates or
  shell command are used.
- Text is bounded to 500 printable characters. Password, protected, secret,
  role-less and attribute-uninspectable fields fail closed before mutation.
- The adapter reads the previous value, writes through `EditableText`, verifies
  exact `Text` readback and attempts a verified rollback on rejection,
  exception or mismatch.
- Trusted confirmation binds the full text in the capability token but redacts
  it from the spoken canonical summary. Success and dry-run messages also do
  not echo the dictated value. The broad phrase `Schreibe ...` remains unknown;
  the deterministic command must explicitly name the text field.
- The router now exposes 44 German/English command families. All 196 Python
  tests passed under Debian 13, including privacy, sensitive-field, ambiguity,
  readback, rollback, dry-run and confirmation-redaction regressions.
- The clean hybrid ISO build and complete `scripts/verify_iso.sh` chain passed.
  The 2,643,034,112-byte artifact has SHA-256
  `dc627c97dfc09f58a97f3cf282259b2f73db6e1c47cda6a904ccea0ddc69bfc2`.
- VirtualBox 7.2.14 booted this exact artifact through EFI GRUB into the
  automatically authenticated, branded GNOME live session. Evidence is stored
  locally as `dist/clausis-text-entry-vbox-grub.png` and
  `dist/clausis-text-entry-vbox-live.png`. The VM was powered off after the
  test.
- The boot proves ISO integration and GNOME runtime availability. Spoken
  end-to-end entry in real applications still requires a microphone-driven
  session test and remains open.

## 2026-08-08 focused semantic list-selection build

- A confirmed command can select one exact direct child of the nearest AT-SPI
  `Selection` container reached by walking at most twelve ancestors from the
  focused accessible. Unrelated lists elsewhere in the window are not searched.
- The adapter rejects missing or duplicate names, captures the complete current
  direct-child selection bitmap, clears it, selects the single requested item,
  verifies the complete resulting bitmap and restores the previous bitmap on
  rejection, exception or mismatch.
- The router exposes 45 German/English command families. All 201 Python tests
  passed under Debian 13, including direct selection replacement, duplicate
  denial, rollback, broker confirmation and developer dry-run regressions.
- The clean hybrid ISO build and complete `scripts/verify_iso.sh` chain passed.
  The 2,643,034,112-byte artifact has SHA-256
  `2dcdd50f3aaa5ee87a405a06834c9389bb3e3ea73b129ee4a25870c66e4453f6`.
- VirtualBox 7.2.14 booted this exact artifact through EFI GRUB into the
  automatically authenticated, branded GNOME live session. Evidence is stored
  locally as `dist/clausis-selection-vbox-grub.png` and
  `dist/clausis-selection-vbox-live.png`.
- The guest did not finish the ACPI shutdown within the 12-second test timeout,
  so the disposable dedicated VM was powered off with the documented fallback.
  Final state was verified as `poweroff`.
- The boot proves ISO integration and GNOME runtime availability. End-to-end
  spoken selection in a real application still requires a microphone-driven
  session test and remains open.

## 2026-08-08 separated file-dialog target selection build

- A confirmed command can mark one exact visible file or folder in the active
  recognized AT-SPI file chooser. Recognition requires either a `file chooser`
  role or an exact allowlisted Open/Save/Select title, plus separate exact
  semantic accept and cancel controls.
- The target must be a single Linux file name of 1 to 255 printable characters;
  paths, `.` and `..` are denied. Exactly one selection container may expose
  the exact direct-child name.
- Target selection reuses the complete selection-bitmap verification and
  rollback path. It deliberately does not invoke Open, Save, Select or any
  other dialog commit control. Commit remains a separate confirmed semantic
  activation.
- The router exposes 46 German/English command families. All 207 Python tests
  passed under Debian 13, including file-dialog recognition, generic-dialog
  rejection, cross-list ambiguity denial, path denial, non-commit proof,
  confirmation and developer dry-run regressions.
- The clean hybrid ISO build and complete `scripts/verify_iso.sh` chain passed.
  The 2,643,034,112-byte artifact has SHA-256
  `663ac3b606363eb22780c9134c822a7ab6edc574973ab39a1794fc0f6e383294`.
- VirtualBox 7.2.14 booted this exact artifact through EFI GRUB into the
  automatically authenticated GNOME overview with Clausis branding and dock.
  Evidence is stored locally as `dist/clausis-file-dialog-vbox-grub.png` and
  `dist/clausis-file-dialog-vbox-live.png`. The VM shut down to verified
  `poweroff` state.
- The boot proves ISO integration and GNOME runtime availability. End-to-end
  spoken file selection in actual GTK and portal dialogs still requires a
  microphone-driven session test and remains open.

## 2026-08-08 bound save-dialog file-name entry build

- A confirmed command can set the file-name field in an active recognized
  AT-SPI save dialog. Recognition requires either a `file chooser` role or an
  exact allowlisted Save title, plus separate exact Save and Cancel controls.
- Only an exactly named focused Name/File Name/Filename/Dateiname field is
  accepted. The value must be a single Linux file name of 1 to 255 characters;
  paths, `.` and `..` are denied.
- Validation and mutation are bound to the same AT-SPI node, avoiding an active
  window time-of-check/time-of-use gap. EditableText writeback is verified and
  the old value is restored on rejection, exception or mismatch.
- Setting the name deliberately does not invoke Save or any other commit
  control. Saving remains a separate confirmed semantic activation.
- The router exposes 47 German/English command families. All 211 Python tests
  passed under Debian 13, including exact-field recognition, wrong-field
  rejection, non-commit proof, single-window lookup, confirmation and developer
  dry-run regressions.
- The clean hybrid ISO build and complete `scripts/verify_iso.sh` chain passed.
  The 2,643,034,112-byte artifact has SHA-256
  `dafb15206911bd640e0043ea4419536e03afbc9f1fdb303cb5d3474e901a9234`.
- VirtualBox 7.2.14 booted this exact artifact through EFI GRUB into the
  automatically authenticated, branded GNOME live session. Evidence is stored
  locally as `dist/clausis-save-name-vbox-grub.png` and
  `dist/clausis-save-name-vbox-live.png`. The VM ended in verified `poweroff`
  state.
- The boot proves ISO integration and GNOME runtime availability. End-to-end
  spoken entry in actual GTK and portal save dialogs still requires a
  microphone-driven session test and remains open.

## 2026-08-08 bound permission-dialog decision build

- Two explicit confirmed commands can allow or deny a permission only in the
  once-bound active AT-SPI dialog or alert. The adapter accepts exactly one
  complete Allow/Deny, Grant/Deny Access or Share/Don't Share pair and invokes
  only the selected node from that same tree.
- Ordinary application frames and OK/Cancel dialogs are rejected. A missing or
  duplicated side and more than one recognized decision group fail closed;
  unsupported decision values are denied by policy before the adapter runs.
- Both allow and deny are medium-risk, confirmation-gated semantic mutations
  and honor developer dry-run mode. No screen coordinates, pointer synthesis
  or generic similarly named activation is used.
- The router exposes 49 German/English command families. All 219 Python tests
  passed under Debian 13, including bound allow, German deny, generic-dialog,
  regular-window and duplicate-control rejection, broker confirmation, policy
  denial and developer dry-run regressions.
- The clean hybrid ISO build and complete `scripts/verify_iso.sh` chain passed.
  Direct SquashFS inspection also found the permission action and router entry.
  The 2,643,034,112-byte artifact has SHA-256
  `27391c7ea181a3aaed3016229ddebbd84e01f77760db5df2129b5e7234f71594`.
- VirtualBox 7.2.14 booted this exact artifact through EFI GRUB into the
  automatically authenticated, branded GNOME overview and dock. Evidence is
  stored locally as `dist/clausis-permission-vbox-grub.png` and
  `dist/clausis-permission-vbox-live.png`. Final VM state was verified as
  `poweroff` after the documented forced-poweroff fallback.
- The boot proves ISO integration and GNOME runtime availability. Triggering
  real GTK/xdg-desktop-portal permission prompts and deciding them through a
  microphone-driven session remains an open end-to-end test.

## 2026-08-08 bound file-dialog location entry build

- A confirmed command can set one absolute canonical POSIX path only in the
  focused Location/Path/Ort/Pfad field of a once-bound recognized AT-SPI file
  chooser with separate accept and cancel controls.
- Relative paths, leading or embedded duplicate separators, control characters
  and `.` or `..` components are denied. The policy rejects them before the
  adapter, and the adapter repeats validation before looking up a window.
- The already-bound field uses verified EditableText readback and rollback.
  The operation does not synthesize Enter and does not invoke Open, Save,
  Select, Choose or any other dialog commit action.
- The router exposes 50 German/English command families. All 225 Python tests
  passed under Debian 13, including confirmation, canonical-path denial,
  same-window binding, wrong-field rejection, non-commit proof and developer
  dry-run regressions.
- The clean hybrid ISO build and complete `scripts/verify_iso.sh` chain passed.
  Direct SquashFS inspection also found the location action and router entry.
  The 2,643,034,112-byte artifact has SHA-256
  `bab678f6fdc5cc4d2886eee0b3a9a6f4bda542d84617215332be9a79271c619b`.
- VirtualBox 7.2.14 booted this exact artifact through EFI GRUB into the
  automatically authenticated, branded GNOME overview and dock. Evidence is
  stored locally as `dist/clausis-location-vbox-grub.png` and
  `dist/clausis-location-vbox-live.png`. The guest shut down to verified
  `poweroff` state through ACPI.
- The boot proves ISO integration and GNOME runtime availability. Focusing a
  real GTK/xdg-desktop-portal location field and entering a path through a
  microphone-driven session remains an open end-to-end test.

## 2026-08-08 semantically proven visible-folder navigation build

- A confirmed command can navigate into one exact, uniquely named direct child
  of an AT-SPI Selection container in the once-bound recognized file chooser.
- The target must carry explicit folder evidence through a folder/directory
  role, an exact folder attribute, or a localized folder icon descendant, and
  the item itself must expose an exact Open or Activate action. File-like,
  unclassifiable, duplicated and click-only targets fail closed.
- The adapter invokes only the already-bound folder item's navigation action.
  It never invokes the file chooser's Open/Save/Select/Choose accept control,
  so navigation does not commit the dialog.
- The router exposes 51 German/English command families. All 231 Python tests
  passed under Debian 13, including confirmation, file rejection, duplicate
  denial, exact navigation-action enforcement, accept-control non-invocation,
  same-window binding and developer dry-run regressions.
- The clean hybrid ISO build and complete `scripts/verify_iso.sh` chain passed.
  Direct SquashFS inspection also found the folder action and router entry. The
  2,643,034,112-byte artifact has SHA-256
  `e3a2ca0d955f701ebf134a864f07039072baf7ba8b311ceb78f492adac351cf8`.
- VirtualBox 7.2.14 booted this exact artifact through EFI GRUB into the
  automatically authenticated, branded GNOME overview and dock. Evidence is
  stored locally as `dist/clausis-folder-vbox-grub.png` and
  `dist/clausis-folder-vbox-live.png`. The guest shut down to verified
  `poweroff` state through ACPI.
- The boot proves ISO integration and GNOME runtime availability. Triggering a
  real GTK/xdg-desktop-portal chooser, focusing a semantically exposed folder
  and navigating through a microphone-driven session remains an open
  end-to-end test.

## 2026-08-09 verified tree expand/collapse build

- A confirmed command can expand or collapse one exact uniquely named tree
  item/row in the nearest focused AT-SPI tree or tree-table container reached
  by walking at most twelve parents in the once-bound active window.
- Expansion requires explicit Expandable state; both operations check current
  Expanded state, require exactly one matching Expand or Collapse action and
  verify the resulting Expanded state. Ordinary lists, duplicate names,
  already-satisfied state, generic Click/Toggle actions, rejection and
  unchanged post-state fail closed.
- The router exposes 53 German/English command families. All 237 Python tests
  passed under Debian 13, including confirmed expand/collapse, state readback,
  duplicate denial, exact-action enforcement, ineffective-action failure and
  developer dry-run regressions.
- The first clean live-build attempt completed its binary stage but could not
  copy the ISO because four previous reproducible `/tmp` build directories had
  filled the 12-GiB temporary filesystem. Only those verified temporary trees
  were removed; a complete fresh rebuild and `scripts/verify_iso.sh` chain then
  passed. Direct SquashFS inspection found both tree actions and router entries.
- The resulting 2,643,034,112-byte artifact has SHA-256
  `20a6e2658b60e827f4f5f4d9a6e4b2035c6141973f6a2b159425293e6c34dd9b`.
- VirtualBox 7.2.14 booted this exact artifact through EFI GRUB into the
  automatically authenticated, branded GNOME overview and dock. Evidence is
  stored locally as `dist/clausis-tree-vbox-grub.png` and
  `dist/clausis-tree-vbox-live.png`. The guest shut down to verified `poweroff`
  state through ACPI.
- The boot proves ISO integration and GNOME runtime availability. Expanding and
  collapsing a real application tree through a microphone-driven session
  remains an open end-to-end test.

## 2026-08-09 verified semantic table-row selection build

- A confirmed command can select one direct row/table-row child of the nearest
  focused AT-SPI table or tree-table exposing Selection, reached by walking at
  most twelve parents in the once-bound active window.
- An exact row name or exact cell/table-cell name must identify exactly one
  row. The adapter does not treat an ordinary list as a table, and a value
  repeated across rows fails closed without changing selection.
- Selection reuses the complete direct-child bitmap verification and rollback
  path. It replaces the full row selection, checks every child and restores the
  previous bitmap on rejection, exception or mismatch.
- The router exposes 54 German/English command families. All 243 Python tests
  passed under Debian 13, including confirmation, cell-name resolution,
  duplicate denial, generic-list rejection, complete rollback and developer
  dry-run regressions.
- The clean hybrid ISO build and complete `scripts/verify_iso.sh` chain passed.
  Direct SquashFS inspection also found the table action and router entry. The
  2,643,034,112-byte artifact has SHA-256
  `686463c582c5dd38ba5fbc2cbb4bfabc0d62a4590e61774e3363c05076759b09`.
- VirtualBox 7.2.14 booted this exact artifact through EFI GRUB into the
  automatically authenticated, branded GNOME overview and dock. Evidence is
  stored locally as `dist/clausis-table-vbox-grub.png` and
  `dist/clausis-table-vbox-live.png`. The guest shut down to verified
  `poweroff` state through ACPI.
- The boot proves ISO integration and GNOME runtime availability. Selecting a
  row in a real application table through a microphone-driven session remains
  an open end-to-end test.

## 2026-08-09 verified semantic tab-selection build

- A confirmed command can select one direct page-tab child of the nearest
  focused AT-SPI page-tab-list exposing Selection, reached by walking at most
  twelve parents in the once-bound active window.
- The exact accessible tab name must identify exactly one direct child.
  Duplicate names and ordinary lists fail closed without changing selection.
- Selection reuses the complete direct-child bitmap verification and rollback
  path. It replaces the full tab selection, checks every child and restores the
  previous bitmap on rejection, exception or mismatch.
- The router exposes 55 German/English command families. All 249 Python tests
  passed under Debian 13, including confirmation, exact-name resolution,
  duplicate denial, generic-list rejection, complete rollback and developer
  dry-run regressions.
- The clean hybrid ISO build and complete `scripts/verify_iso.sh` chain passed.
  Direct SquashFS inspection also found the tab action and router entry. The
  2,643,034,112-byte artifact has SHA-256
  `9d8845709b0de6a642d2f89fc587df43ff0851ef2f72576014d3d25f4864761e`.
- VirtualBox 7.2.14 booted this exact artifact through EFI GRUB into the
  automatically authenticated, branded GNOME overview and dock. Evidence is
  stored locally as `dist/clausis-tabs-vbox-grub.png` and
  `dist/clausis-tabs-vbox-live.png`. The guest ended in verified `poweroff`
  state after the shutdown request.
- The boot proves ISO integration and GNOME runtime availability. Selecting a
  tab in a real application through a microphone-driven session remains an
  open end-to-end test.

## 2026-08-09 verified semantic slider build

- A confirmed command can set one exactly and uniquely named AT-SPI slider in
  the once-bound active window to an integer percentage from 0 through 100.
- The adapter accepts only the exact `slider` role and a finite minimum/current/
  maximum Value range. It maps the percentage onto that range, rounds to the
  declared minimum increment and reads the resulting value back. Rejection or
  mismatch triggers a best-effort restoration of the previous value and a
  closed failure; duplicate names and non-slider roles are never mutated.
- The router exposes 56 German/English command families. All 257 Python tests
  passed under Debian 13, including confirmation, range mapping, discrete-step
  mapping, duplicate denial, role denial, rollback, strict policy validation
  and developer dry-run regressions.
- The clean hybrid ISO build and complete `scripts/verify_iso.sh` chain passed.
  Direct SquashFS inspection also found the slider action and router entry. The
  2,643,034,112-byte artifact has SHA-256
  `a9168f367baa1461ce3319572f00e8fe08570b8e484a2f7ef66c0b6b5e46a9fc`.
- VirtualBox 7.2.14 booted this exact artifact through EFI GRUB into the
  automatically authenticated, branded GNOME overview and dock. Evidence is
  stored locally as `dist/clausis-slider-vbox-grub.png` and
  `dist/clausis-slider-vbox-live.png`. The guest shut down to verified
  `poweroff` state through ACPI.
- The boot proves ISO integration and GNOME runtime availability. Changing a
  real application slider through a microphone-driven session remains an open
  end-to-end test.

## 2026-08-09 verified semantic check-box and radio-button build

- Confirmed commands can set one exactly and uniquely named AT-SPI check box
  on or off and can select one exactly and uniquely named radio button in the
  once-bound active window.
- Check boxes require the exact `check box` role and exactly one Toggle action.
  Radio buttons require the exact `radio button` role and exactly one Select or
  Click action. Checked state is read before and after invocation; idempotent
  requests do not invoke a control, while ambiguity or unchanged post-state
  fails closed. A failed radio selection attempts to restore the previously
  checked control in the same bound window.
- The router exposes 59 German/English command families. All 266 Python tests
  passed under Debian 13, including confirmation, on/off state setting,
  idempotence, exact-action enforcement, duplicate denial, radio-group update,
  previous-selection restoration, strict argument validation and developer
  dry-run regressions.
- The clean hybrid ISO build and complete `scripts/verify_iso.sh` chain passed.
  Direct SquashFS inspection also found both semantic actions and all three
  router entries. The 2,643,034,112-byte artifact has SHA-256
  `b544cf4684405cd5359a8c6a0d9770ebebc809622b03c8bcd9d5774c58b81243`.
- VirtualBox 7.2.14 booted this exact artifact through EFI GRUB into the
  automatically authenticated, branded GNOME overview and dock. Evidence is
  stored locally as `dist/clausis-choices-vbox-grub.png` and
  `dist/clausis-choices-vbox-live.png`. The guest shut down to verified
  `poweroff` state through ACPI.
- The boot proves ISO integration and GNOME runtime availability. Manipulating
  real application check boxes and radio buttons through a microphone-driven
  session remains an open end-to-end test.

## 2026-08-09 verified semantic combo-box selection build

- A confirmed command can select one exact direct item in one exactly and
  uniquely named AT-SPI combo box in the once-bound active window.
- The container must have the exact `combo box` role and expose Selection. Only
  a direct `menu item`, `list item` or `option` child with an exact unique name
  is eligible. Selection uses the complete direct-child bitmap verifier and
  rollback path; generic lists, nested guesses, duplicate names, unrelated
  child roles and uninspectable state fail closed.
- The router exposes 60 German/English command families. All 273 Python tests
  passed under Debian 13, including confirmation, exact container and item
  binding, duplicate denial, role denial, complete rollback, strict argument
  validation and developer dry-run regressions.
- The clean hybrid ISO build and complete `scripts/verify_iso.sh` chain passed.
  Direct SquashFS inspection also found the combo action and router entry. The
  2,643,034,112-byte artifact has SHA-256
  `bdc0bd0d808d53a67f0972cceecd58717920d5eae9ba5a9cb89f2886d65e1181`.
- VirtualBox 7.2.14 booted this exact artifact through EFI GRUB into the
  automatically authenticated, branded GNOME session. The live Clausis setup
  dialog and its provider combo box were visibly present. Evidence is stored
  locally as `dist/clausis-combo-vbox-grub.png` and
  `dist/clausis-combo-vbox-live.png`. The guest shut down to verified
  `poweroff` state through ACPI.
- The boot proves ISO integration, GNOME runtime availability and presence of a
  real combo box. Selecting that combo through a microphone-driven semantic
  session remains an open end-to-end test.

## 2026-08-09 verified semantic numeric spin-button build

- A confirmed command can set one exactly and uniquely named AT-SPI spin button
  in the once-bound active window to a finite numeric value.
- The adapter requires the exact `spin button` role and a finite Value range.
  The requested number must lie within the declared minimum and maximum and
  align with a declared positive minimum increment; it is never silently
  rounded. The value is read back and rejection or mismatch triggers a
  best-effort restoration of the previous value. Sliders, duplicate names,
  invalid ranges and incompatible increments fail closed without mutation.
- The router exposes 61 German/English command families. All 280 Python tests
  passed under Debian 13, including confirmation, decimal-comma parsing,
  bounded range enforcement, exact-step enforcement, role and duplicate denial,
  rollback, strict argument validation and developer dry-run regressions.
- The clean hybrid ISO build and complete `scripts/verify_iso.sh` chain passed.
  Direct SquashFS inspection also found the spin-button action and router entry.
  The 2,643,034,112-byte artifact has SHA-256
  `33749be729da76c67966fd0787792dbf6b1bca3963125c883f7dff78b3129c68`.
- VirtualBox 7.2.14 booted this exact artifact through EFI GRUB into the
  automatically authenticated, branded GNOME overview and dock. Evidence is
  stored locally as `dist/clausis-spin-vbox-grub.png` and
  `dist/clausis-spin-vbox-live.png`. The guest shut down to verified `poweroff`
  state through ACPI.
- The boot proves ISO integration and GNOME runtime availability. Changing a
  real spin button through a microphone-driven semantic session remains an open
  end-to-end test.

## 2026-08-09 verified semantic switch build

- Confirmed commands can set one exactly and uniquely named AT-SPI switch in
  the once-bound active window on or off.
- The adapter requires the exact `switch` role and exactly one Toggle action.
  Checked state is read before and after invocation; an already satisfied state
  does not invoke the control. Check boxes, duplicate names, ambiguous actions
  and unchanged post-state fail closed. The implementation shares only the
  verified state-transition helper with check boxes and does not blur the roles.
- The router exposes 63 German/English command families. All 285 Python tests
  passed under Debian 13, including confirmation, on/off transitions,
  idempotence, exact-role separation, duplicate and post-state denial, strict
  boolean argument validation and developer dry-run regressions.
- The clean hybrid ISO build and complete `scripts/verify_iso.sh` chain passed.
  Direct SquashFS inspection also found the switch action and both router
  entries. The 2,643,034,112-byte artifact has SHA-256
  `571e16d2ec9ef567bcf008fe0ba6a68e1d80be4a9306eac9e69f15c03158eba0`.
- VirtualBox 7.2.14 booted this exact artifact through EFI GRUB into the
  automatically authenticated, branded GNOME overview and dock. Evidence is
  stored locally as `dist/clausis-switch-vbox-grub.png` and
  `dist/clausis-switch-vbox-live.png`. The guest shut down to verified
  `poweroff` state through ACPI.
- The boot proves ISO integration and GNOME runtime availability. Changing a
  real GNOME switch through a microphone-driven semantic session remains an
  open end-to-end test.

## 2026-08-09 verified bound semantic menu-item build

- A confirmed command can invoke one exact direct item in the nearest focused
  AT-SPI menu or menu bar, reached by walking at most twelve parents in the
  once-bound active window.
- Only direct `menu item`, `check menu item` and `radio menu item` roles are
  eligible. The exact accessible name must be unique and exactly one Activate,
  Click or Press action must exist. Ordinary lists, unrelated menus, duplicate
  names, role mismatches, ambiguous actions and rejected invocation fail closed.
- The router exposes 64 German/English command families. All 290 Python tests
  passed under Debian 13, including confirmation, focused-menu binding, exact
  direct-child activation, duplicate and generic-list denial, ambiguous-action
  denial and developer dry-run regressions.
- The clean hybrid ISO build and complete `scripts/verify_iso.sh` chain passed.
  Direct SquashFS inspection also found the menu action and router entry. The
  2,643,034,112-byte artifact has SHA-256
  `851757736a7febbe6148d5889b6990fdf85d1524a5dbf7b9de209b7f893244fd`.
- VirtualBox 7.2.14 booted this exact artifact through EFI GRUB into the
  automatically authenticated, branded GNOME overview and dock. Evidence is
  stored locally as `dist/clausis-menu-vbox-grub.png` and
  `dist/clausis-menu-vbox-live.png`. The guest shut down to verified `poweroff`
  state through ACPI.
- The boot proves ISO integration and GNOME runtime availability. Invoking a
  real application menu through a microphone-driven semantic session remains
  an open end-to-end test.

## 2026-08-09 verified named semantic focus build

- A low-risk offline command can focus one exactly and uniquely named visible
  focusable AT-SPI accessible in the once-bound active window, including an
  element that exposes no executable action.
- The target must explicitly expose Showing and Focusable state. Clausis uses
  Component `grabFocus()` without key synthesis, verifies Focused state and
  treats an already focused target idempotently. If the transition is not
  confirmed, the adapter attempts to restore the previously focused accessible;
  ambiguity, hidden or non-focusable targets and failed restoration fail closed.
- The router exposes 65 German/English command families. All 295 Python tests
  passed under Debian 13, including unique focus movement, idempotence, hidden/
  non-focusable and duplicate denial, previous-focus restoration, strict name
  validation and developer dry-run regressions.
- The clean hybrid ISO build and complete `scripts/verify_iso.sh` chain passed.
  Direct SquashFS inspection also found the named-focus action and router entry.
  The 2,643,034,112-byte artifact has SHA-256
  `8964b3d780499324caeb61a8401eddae6cf58a83c667940ad41d4cfad350247e`.
- VirtualBox 7.2.14 booted this exact artifact through EFI GRUB into the
  automatically authenticated, branded GNOME overview and dock. Evidence is
  stored locally as `dist/clausis-focus-vbox-grub.png` and
  `dist/clausis-focus-vbox-live.png`. The guest shut down to verified `poweroff`
  state through ACPI.
- The boot proves ISO integration and GNOME runtime availability. Moving focus
  in a real application through a microphone-driven semantic session remains
  an open end-to-end test.

## 2026-08-09 privacy-bounded focused-text reading build

- A low-risk offline command can read the currently focused AT-SPI `entry`,
  `text` or `document text` field without clipboard or synthesized input.
  Reading is bounded to 1,000 characters and whitespace is normalized for
  speech. Password, protected, secret, wrong-role and uninspectable fields fail
  closed before text access.
- Because the spoken result necessarily contains the requested text, the audit
  layer replaces the complete result message and details for
  `desktop.text.read_focused`; a regression test proves the private text is not
  persisted while the HMAC audit chain still verifies.
- The router exposes 66 German/English command families. All 301 Python tests
  passed under Debian 13. The focused Windows run also passed; a full Windows
  run was not treated as authoritative because existing POSIX-only security
  tests require `geteuid`, `O_NOFOLLOW`, `fchmod` and Unix symlink semantics.
- A fresh full ISO build and the repository verification script passed. Direct
  SquashFS inspection found the focused-text action, `read-focused-text` router
  entry and `[REDACTED: focused text]` audit marker in the installed Python
  package.
- The exact tested ISO is 2,643,034,112 bytes with SHA-256
  `d42d984eb6fd2ba932c4ac3d1fbded0aceae4ae128dc970c53ec5a814961f92e`.
- VirtualBox VM `Clausis` booted that exact ISO through the branded UEFI GRUB
  menu to the branded GNOME live desktop. Evidence is stored as
  `dist/clausis-readtext-vbox-grub.png` and
  `dist/clausis-readtext-vbox-live.png`; the guest then shut down through ACPI
  to verified `VMState="poweroff"`.
- The boot proves ISO integration and GNOME runtime availability. Reading a
  real application text field through a microphone-driven semantic session
  remains an open end-to-end test.

## 2026-08-09 verified semantic workspace-window movement build

- Two confirmation-gated offline commands move the active window toward the
  previous/left or next/right workspace only when the once-bound active AT-SPI
  frame exposes the corresponding exact directional action. Generic `move`
  actions, inferred keyboard shortcuts and Wayland input synthesis are rejected.
- Each direction has a distinct trusted confirmation summary so the spoken
  approval identifies both the active-window target and destination direction.
- The router exposes 68 German/English command families. All 305 Python tests
  passed under Debian 13, including confirmation gating and direction wording,
  exact AT-SPI action selection, generic-action denial, routing and policy.
- A fresh full ISO build and the repository verification script passed. Direct
  SquashFS inspection found both workspace actions, both router entries and the
  direction-specific trusted-confirmation text in the installed Python package.
- The exact tested ISO is 2,643,034,112 bytes with SHA-256
  `35e3f04c96934d18306a1f9155f635d448a5e6491e8521d5c56e585fd24848c6`.
- VirtualBox VM `Clausis` booted that exact ISO through the branded UEFI GRUB
  menu to the branded GNOME live desktop. Evidence is stored as
  `dist/clausis-workspace-vbox-grub.png` and
  `dist/clausis-workspace-vbox-live.png`; the guest then shut down through ACPI
  to verified `VMState="poweroff"`.
- The boot proves ISO integration and GNOME runtime availability. Moving an
  actual application window through a microphone-driven semantic session still
  depends on the GNOME version exposing the directional frame action and
  remains an open end-to-end test.

## 2026-08-09 verified named progress-reading build

- A low-risk offline command reads one exactly and uniquely named AT-SPI
  `progress bar` in the once-bound active window and reports its normalized
  percentage. The adapter requires finite minimum, maximum and current values,
  an ordered non-empty range, and a current value inside that range.
- The action is explicitly present in `SEMANTIC_ACTIONS` and absent from
  `SEMANTIC_MUTATIONS`; it never calls `setCurrentValue`. Duplicate names,
  slider-role confusion, out-of-range values and invalid ranges fail closed.
- The router exposes 69 German/English command families. All 309 Python tests
  passed under Debian 13, including percentage mapping, zero mutation, negative
  role/range cases, routing and low-risk policy.
- A fresh full ISO build and the repository verification script passed. Direct
  SquashFS inspection found the installed action and router entry, and an AST
  check against the installed adapter verified its read-only classification.
- The exact tested ISO is 2,643,034,112 bytes with SHA-256
  `84b64613a821936e91ae475d8d67f29cf0f458ebf5cebe93f9424457654bc32b`.
- VirtualBox VM `Clausis` booted that exact ISO through the branded UEFI GRUB
  menu to GNOME with the accessible Clausis setup dialog and visible KI notice.
  Evidence is stored as `dist/clausis-progress-vbox-grub.png` and
  `dist/clausis-progress-vbox-live.png`; the guest then shut down through ACPI
  to verified `VMState="poweroff"`.
- The boot proves ISO integration and GNOME runtime availability. Reading a
  real changing application progress bar through a microphone-driven semantic
  session remains an open end-to-end test.

## 2026-08-09 verified accessibility-rescue enablement build

- Two trusted-confirmation commands enable GNOME's built-in on-screen keyboard
  or Orca screen reader. Each policy contains one fully fixed `gsettings set`
  argument vector, rejects every target and argument, and has a tool-specific
  trusted confirmation summary.
- Voice actions to disable either rescue path are intentionally absent, so the
  new feature cannot be used to remove keyboard or screen-reader access.
- The router exposes 71 German/English command families. All 313 Python tests
  passed under Debian 13, including exact argv checks, confirmation gating,
  parameter rejection, routing and canonical summary wording.
- A fresh full ISO build and the repository verification script passed. Direct
  SquashFS inspection found both installed policy vectors, the actual
  `screen-keyboard-enabled` and `screen-reader-enabled` keys in
  `org.gnome.desktop.a11y.applications.gschema.xml`, and executable
  `usr/bin/orca`.
- The exact tested ISO is 2,643,034,112 bytes with SHA-256
  `cfeff225ce5d3f55bcbddc0405a25b9423b6a4711e0916810fc4cb9fb8c1fa04`.
- VirtualBox VM `Clausis` booted that exact ISO through the branded UEFI GRUB
  menu to the branded GNOME live desktop. Evidence is stored as
  `dist/clausis-a11y-vbox-grub.png` and `dist/clausis-a11y-vbox-live.png`; the
  guest then shut down through ACPI to verified `VMState="poweroff"`.
- The boot and SquashFS checks prove integration and runtime prerequisites.
  Triggering each preference through a microphone-driven trusted-confirmation
  session and observing the on-screen keyboard/Orca transition remains an open
  end-to-end test.

## 2026-08-09 verified screen-magnifier rescue enablement build

- A third trusted-confirmation command enables GNOME's built-in screen
  magnifier. Its policy contains one fixed `gsettings set` vector for
  `screen-magnifier-enabled`, rejects every target and argument, and has a
  magnifier-specific trusted confirmation summary.
- No voice action disables the magnifier, matching the existing on-screen
  keyboard and Orca rescue-path rule.
- The router exposes 72 German/English command families. All 313 Python tests
  passed under Debian 13; the existing parameterized accessibility tests now
  also cover exact magnifier argv, confirmation gating, parameter rejection,
  routing and canonical summary wording.
- A fresh full ISO build and the repository verification script passed. Direct
  SquashFS inspection found the installed magnifier policy vector, router
  pattern, confirmation wording and the actual `screen-magnifier-enabled` key
  in `org.gnome.desktop.a11y.applications.gschema.xml`.
- The exact tested ISO is 2,643,034,112 bytes with SHA-256
  `5aeb04fc4a31e610a08415c4383a6d65b0244bbfe034db7c31410c1bcd4689a3`.
- VirtualBox VM `Clausis` booted that exact ISO through the branded UEFI GRUB
  menu to the branded GNOME live desktop. Evidence is stored as
  `dist/clausis-magnifier-vbox-grub.png` and
  `dist/clausis-magnifier-vbox-live.png`; the guest then shut down through ACPI
  to verified `VMState="poweroff"`.
- The boot and SquashFS checks prove integration and runtime prerequisites.
  Triggering the magnifier through a microphone-driven trusted-confirmation
  session and visually observing magnification remains an open end-to-end test.

## 2026-08-09 verified bounded magnifier-zoom build

- A separate trusted-confirmation command sets GNOME's magnifier to an exact
  integer percentage from 100 through 3,200. Policy rejects targets, booleans,
  floats, missing/extra fields and out-of-range values before execution.
- The executor uses a fixed `gsettings set org.gnome.desktop.a11y.magnifier
  mag-factor` prefix and appends only the validated canonical two-decimal
  factor; for example 225 percent becomes `2.25`. The spoken confirmation names
  the exact requested percentage.
- The router exposes 73 German/English command families. All 317 Python tests
  passed under Debian 13, including exact argv conversion, all validator
  boundaries, typed routing and canonical confirmation wording.
- A fresh full ISO build and the repository verification script passed. Direct
  SquashFS inspection found the installed validator, fixed command prefix,
  canonical conversion, router pattern, confirmation wording and the actual
  `mag-factor` schema range of `0.1` through `32.0`.
- The exact tested ISO is 2,643,034,112 bytes with SHA-256
  `f4e267420d36dd823b371c928f278f7add7444494c836edacdd03c0060ecd8c4`.
- VirtualBox VM `Clausis` booted that exact ISO through the branded UEFI GRUB
  menu to the branded GNOME live desktop. Evidence is stored as
  `dist/clausis-zoom-vbox-grub.png` and `dist/clausis-zoom-vbox-live.png`; the
  guest then shut down through ACPI to verified `VMState="poweroff"`.
- The boot and SquashFS checks prove integration and runtime prerequisites.
  Setting and visually measuring zoom through a microphone-driven trusted-
  confirmation session remains an open end-to-end test.

## 2026-08-09 verified magnifier-lightness inversion build

- Two trusted-confirmation commands enable or disable only the GNOME
  magnifier's lightness inversion. Each action has a fixed parameterless
  `gsettings set org.gnome.desktop.a11y.magnifier invert-lightness` vector with
  a literal `true` or `false` value and a state-specific spoken summary.
- Turning inversion off does not turn off magnification, Orca or the on-screen
  keyboard; the accessibility rescue applications retain no voice disable path.
- The router exposes 75 German/English command families. All 320 Python tests
  passed under Debian 13, including exact boolean argv, no-parameter policy,
  typed routing and state-specific confirmation wording.
- A fresh full ISO build and the repository verification script passed. Direct
  SquashFS inspection found both policy vectors, both router patterns, both
  confirmation summaries and the actual boolean `invert-lightness` schema key.
- The exact tested ISO is 2,643,034,112 bytes with SHA-256
  `bb116b4e167c5df97928eafe6c4d6ef40d26abd0f40e2d3ec6dc800cb752a49a`.
- VirtualBox VM `Clausis` booted that exact ISO through the branded UEFI GRUB
  menu to the branded GNOME live desktop. Evidence is stored as
  `dist/clausis-inversion-vbox-grub.png` and
  `dist/clausis-inversion-vbox-live.png`; the guest then shut down through ACPI
  to verified `VMState="poweroff"`.
- The boot and SquashFS checks prove integration and runtime prerequisites.
  Toggling inversion through a microphone-driven trusted-confirmation session
  and visually measuring the transition remains an open end-to-end test.

## 2026-08-09 verified magnifier-color-saturation build

- A trusted-confirmation command sets the GNOME magnifier's color saturation
  to an exact integer percentage from 0 through 100; zero selects grayscale.
  Policy rejects targets, booleans, floats, missing/extra fields and
  out-of-range values before execution.
- The executor uses the fixed `gsettings set
  org.gnome.desktop.a11y.magnifier color-saturation` prefix and appends only
  the validated canonical two-decimal factor; for example 35 percent becomes
  `0.35`. The spoken confirmation names the exact requested percentage.
- The router exposes 76 German/English command families. All 324 Python tests
  passed under Debian 13, including exact argv conversion, validator
  boundaries, typed routing and canonical confirmation wording.
- A fresh full ISO build and the repository verification script passed. Direct
  SquashFS inspection found the installed validator, broker conversion, router
  pattern, confirmation wording and the actual `color-saturation` schema range
  of `0.0` through `1.0`.
- The exact tested ISO is 2,643,034,112 bytes with SHA-256
  `321328db53ee38ce6fc4e8e74ed7727837e537cbc6cbbb765edfcb2819dec4ab`.
- VirtualBox VM `Clausis` booted that exact ISO through the branded UEFI GRUB
  menu to the branded GNOME live desktop. Evidence is stored as
  `dist/clausis-saturation-vbox-grub.png` and
  `dist/clausis-saturation-vbox-live.png`; the guest then shut down through
  ACPI to verified `VMState="poweroff"`.
- The boot and SquashFS checks prove integration and runtime prerequisites.
  Setting and visually measuring saturation through a microphone-driven
  trusted-confirmation session remains an open end-to-end test.

## 2026-08-09 verified magnifier-screen-position build

- A trusted-confirmation command restricts the GNOME magnified view to exactly
  full screen or the top, bottom, left or right half. German and English voice
  phrases map to the five installed `screen-position` enum values; policy
  rejects targets, missing or extra fields, booleans and unknown values.
- The executor uses the fixed `gsettings set
  org.gnome.desktop.a11y.magnifier screen-position` prefix and appends only the
  policy-validated enum. The spoken confirmation names the exact requested
  screen region.
- The router exposes 77 German/English command families. All 328 Python tests
  passed under Debian 13, including all five enum mappings, exact argv,
  validator rejection cases and canonical confirmation wording.
- A fresh full ISO build and the complete repository verification chain passed.
  Direct SquashFS inspection found the installed policy, fixed command key,
  broker branch, bounded router pattern, confirmation wording and the actual
  GNOME `screen-position` enum schema.
- The exact tested ISO is 2,643,034,112 bytes with SHA-256
  `1f8b5a0e9e81c1df07c53f5fa8e682e0e2fb5f9d1c117869797188f639097590`.
- VirtualBox VM `Clausis` booted that exact ISO through the branded UEFI GRUB
  menu to the branded GNOME live desktop. Evidence is stored as
  `dist/clausis-position-vbox-grub.png` and
  `dist/clausis-position-vbox-live.png`; the guest then shut down through ACPI
  to verified `VMState="poweroff"`.
- The boot and SquashFS checks prove integration and runtime prerequisites.
  Changing and visually measuring the region through a microphone-driven
  trusted-confirmation session remains an open end-to-end test.

## 2026-08-09 verified magnifier-crosshairs build

- Two trusted-confirmation commands show or hide only the GNOME magnifier
  crosshairs. Each action is parameterless and has a fixed `gsettings set
  org.gnome.desktop.a11y.magnifier show-cross-hairs` vector with a literal
  `true` or `false` value and a state-specific spoken summary.
- Hiding the crosshairs does not disable magnification, Orca or the on-screen
  keyboard; the accessibility rescue applications retain no voice disable path.
- The router exposes 79 German/English command families. All 331 Python tests
  passed under Debian 13, including exact boolean argv, parameter rejection,
  typed routing and state-specific confirmation wording.
- A fresh full ISO build and the complete repository verification chain passed.
  Direct SquashFS inspection found both policy vectors, both router patterns,
  both confirmation summaries and the actual boolean `show-cross-hairs`
  schema key.
- The exact tested ISO is 2,643,034,112 bytes with SHA-256
  `dc350995927ec7da7324c7495d792ccb7913699ca5fd24f6c106ee1f02f8ed97`.
- VirtualBox VM `Clausis` booted that exact ISO through the branded UEFI GRUB
  menu to the branded GNOME live desktop. Evidence is stored as
  `dist/clausis-crosshairs-vbox-grub.png` and
  `dist/clausis-crosshairs-vbox-live.png`; the guest then shut down through
  ACPI to verified `VMState="poweroff"`.
- The boot and SquashFS checks prove integration and runtime prerequisites.
  Toggling and visually verifying crosshairs through a microphone-driven
  trusted-confirmation session remains an open end-to-end test.

## 2026-08-09 verified magnifier-crosshair-opacity build

- A trusted-confirmation command sets the GNOME magnifier crosshair opacity to
  an exact integer percentage from 0 through 100. Policy rejects targets,
  booleans, floats, missing/extra fields and out-of-range values before
  execution.
- The executor uses the fixed `gsettings set
  org.gnome.desktop.a11y.magnifier cross-hairs-opacity` prefix and appends only
  the validated canonical two-decimal factor; for example 42 percent becomes
  `0.42`. The spoken confirmation names the exact requested percentage.
- The router exposes 80 German/English command families. All 335 Python tests
  passed under Debian 13, including exact argv conversion, both boundaries,
  validator rejection cases, typed routing and canonical confirmation wording.
- A fresh full ISO build and the complete repository verification chain passed.
  Direct SquashFS inspection found the installed validator, fixed command key,
  broker conversion, bounded router pattern, confirmation wording and the
  actual `cross-hairs-opacity` schema range of `0.0` through `1.0`.
- The exact tested ISO is 2,643,034,112 bytes with SHA-256
  `54d4c1563eb970cc915bfb93cbdb38ee215551f53aab0ad6f87e9249b0929929`.
- VirtualBox VM `Clausis` booted that exact ISO through the branded UEFI GRUB
  menu to the branded GNOME live desktop. Evidence is stored as
  `dist/clausis-crosshair-opacity-vbox-grub.png` and
  `dist/clausis-crosshair-opacity-vbox-live.png`; the guest then shut down
  through ACPI to verified `VMState="poweroff"`.
- The boot and SquashFS checks prove integration and runtime prerequisites.
  Setting and visually measuring opacity through a microphone-driven trusted-
  confirmation session remains an open end-to-end test.

## 2026-08-09 verified magnifier-crosshair-center-clipping build

- Two trusted-confirmation commands make the GNOME magnifier crosshair lines
  stop around the magnified pointer or pass through it. Each action is
  parameterless and uses a fixed `gsettings set
  org.gnome.desktop.a11y.magnifier cross-hairs-clip` vector with a literal
  `true` or `false` value and state-specific spoken summary.
- Removing the center gap does not hide the crosshairs or disable the
  magnifier, Orca or on-screen keyboard.
- The router exposes 82 German/English command families. All 338 Python tests
  passed under Debian 13, including exact boolean argv, parameter rejection,
  typed routing and state-specific confirmation wording.
- A fresh full ISO build and the complete repository verification chain passed.
  The unusually slow build was observed through active Whisper/Hermes download,
  chroot cleanup and UEFI binary subprocesses and completed with container exit
  code zero. Direct SquashFS inspection found both policy vectors, router
  patterns, confirmation wording and the actual boolean `cross-hairs-clip`
  schema key.
- The exact tested ISO is 2,643,034,112 bytes with SHA-256
  `9fe01d88cff51b9e4449820e572cd89b9462a62f1bb086800731726aa6b50c7f`.
- VirtualBox VM `Clausis` booted that exact ISO through the branded UEFI GRUB
  menu to the branded GNOME live desktop. Evidence is stored as
  `dist/clausis-crosshair-clip-vbox-grub.png` and
  `dist/clausis-crosshair-clip-vbox-live.png`; the guest then shut down through
  ACPI to verified `VMState="poweroff"`.
- The boot and SquashFS checks prove integration and runtime prerequisites.
  Toggling and visually verifying the center gap through a microphone-driven
  trusted-confirmation session remains an open end-to-end test.

## 2026-08-09 verified magnifier-crosshair-length build

- A trusted-confirmation command sets the GNOME magnifier crosshair length to
  an exact integer from 20 through 4,096 pixels, matching the installed schema.
  Policy rejects targets, booleans, floats, missing/extra fields and values
  outside those boundaries before execution.
- The executor uses the fixed `gsettings set
  org.gnome.desktop.a11y.magnifier cross-hairs-length` prefix and appends only
  the validated canonical decimal integer. The spoken confirmation names the
  exact requested pixel count.
- The router exposes 83 German/English command families. All 342 Python tests
  passed under Debian 13, including exact argv, both schema boundaries,
  validator rejection cases, typed routing and canonical confirmation wording.
- A fresh full ISO build and the complete repository verification chain passed.
  Direct SquashFS inspection found the installed validator, fixed command key,
  broker conversion, bounded router pattern, confirmation wording and the
  actual `cross-hairs-length` schema range of `20` through `4096`.
- The exact tested ISO is 2,643,034,112 bytes with SHA-256
  `f96a47f87433cf9398edb506384a2321cb1ff7de7c99bb4770a475fd1f92b114`.
- VirtualBox VM `Clausis` booted that exact ISO through the branded UEFI GRUB
  menu to the branded GNOME live desktop. Evidence is stored as
  `dist/clausis-crosshair-length-vbox-grub.png` and
  `dist/clausis-crosshair-length-vbox-live.png`; the guest then shut down
  through ACPI to verified `VMState="poweroff"`.
- The boot and SquashFS checks prove integration and runtime prerequisites.
  Setting and visually measuring line length through a microphone-driven
  trusted-confirmation session remains an open end-to-end test.

## 2026-08-09 verified magnifier-focus-tracking build

- A trusted-confirmation command sets GNOME magnifier focus tracking to exactly
  off, centered, proportional or push mode. Policy rejects targets, missing or
  extra fields, booleans and unknown enum values before execution. Disabling
  focus tracking does not disable magnification.
- The executor uses the fixed `gsettings set
  org.gnome.desktop.a11y.magnifier focus-tracking` prefix and appends only the
  validated installed enum. English routing requires the unambiguous
  `magnifier focus tracking` prefix so it cannot collide with named focus.
- The router exposes 84 German/English command families. All 346 Python tests
  passed under Debian 13, including all four enum mappings, exact argv,
  validator rejection cases, routing disambiguation and canonical confirmation.
- The first full ISO attempt exhausted its five APT retries during a temporary
  `deb.debian.org` DNS/Fastly outage after progressing through the complete
  package list. DNS and an HTTP 200 response were verified before retrying; the
  cache-backed full rebuild and complete repository verification chain passed.
  Direct SquashFS inspection found the installed policy, fixed command key,
  broker enum append, bounded router pattern, confirmation wording and the
  actual GNOME `focus-tracking` schema with all four documented modes.
- The exact tested ISO is 2,643,034,112 bytes with SHA-256
  `777b7c86b1f6480d958413c0e9f4973a2cc2d9b8ee06d9dad57681b54236ffe0`.
- VirtualBox VM `Clausis` booted that exact ISO through the branded UEFI GRUB
  menu to the branded GNOME live desktop. Evidence is stored as
  `dist/clausis-focus-tracking-vbox-grub.png` and
  `dist/clausis-focus-tracking-vbox-live.png`; the guest then shut down through
  ACPI to verified `VMState="poweroff"`.
- The boot and SquashFS checks prove integration and runtime prerequisites.
  Switching and visually measuring focus tracking through a microphone-driven
  trusted-confirmation session remains an open end-to-end test.

## 2026-08-09 verified magnifier-caret-and-mouse-tracking build

- Two separate trusted-confirmation commands set GNOME magnifier text-caret
  tracking and mouse-pointer tracking to exactly off, centered, proportional
  or push mode. Policy rejects targets, missing or extra fields, booleans and
  unknown enum values before execution. Disabling either tracker does not
  disable magnification.
- The executor uses the fixed `gsettings set
  org.gnome.desktop.a11y.magnifier caret-tracking` and `mouse-tracking`
  prefixes and appends only the validated installed enum. English routing
  requires the explicit `magnifier caret tracking` or `magnifier mouse
  tracking` prefix so the commands remain unambiguous.
- The router exposes 86 German/English command families. All 350 Python tests
  passed under Debian 13, including every enum mapping, exact argv, validator
  rejection cases, typed routing and tracker-specific confirmation wording.
- A fresh full ISO build and the complete repository verification chain passed.
  Read-only loop-mounted SquashFS inspection found both installed policies,
  fixed command keys, broker enum handling, bounded router patterns and
  confirmation wording. The installed GNOME schema reports all four documented
  values for both `caret-tracking` and `mouse-tracking`: `none`, `centered`,
  `proportional` and `push`.
- The exact tested ISO is 2,643,034,112 bytes with SHA-256
  `abddf91515bcb4d3c2f91474e0065a05125c7ff5256789c12986f2469dc4362c`.
- VirtualBox VM `Clausis` booted that exact ISO through the branded UEFI GRUB
  menu to the branded GNOME live desktop. Evidence is stored as
  `dist/clausis-caret-mouse-tracking-vbox-grub.png` and
  `dist/clausis-caret-mouse-tracking-vbox-live.png`; the guest then shut down
  through ACPI to verified `VMState="poweroff"`.
- The boot and SquashFS checks prove integration and runtime prerequisites.
  Switching and visually observing both trackers through a microphone-driven
  trusted-confirmation session remains an open end-to-end test.

## 2026-08-09 verified magnifier-lens-and-edge-scrolling build

- Four separate trusted-confirmation commands enable or disable GNOME
  magnifier lens mode and scrolling at screen edges. Each action rejects a
  target and all arguments before execution; disabling either option does not
  disable magnification or another accessibility rescue facility.
- The executor uses complete fixed `gsettings set
  org.gnome.desktop.a11y.magnifier lens-mode true/false` and
  `scroll-at-edges true/false` vectors. No caller-controlled value is appended.
  German and English routing uses explicit feature-specific phrases.
- The router exposes 90 German/English command families. All 353 Python tests
  passed under Debian 13, including parameter rejection, all four exact argv
  vectors, typed routing and state-specific confirmation wording.
- A fresh full ISO build and the complete repository verification chain passed.
  Read-only loop-mounted SquashFS inspection found all installed policies,
  fixed command vectors, router patterns and confirmation wording. The GNOME
  schema embedded in the ISO reports boolean type for both `lens-mode` and
  `scroll-at-edges`.
- The exact tested ISO is 2,643,034,112 bytes with SHA-256
  `2f9f8c90d3ff7271de737bd9b472721d0be4659d89e3df8c9c8bfd6d728d8087`.
- VirtualBox VM `Clausis` booted that exact ISO through the branded UEFI GRUB
  menu to the branded GNOME live desktop. Evidence is stored as
  `dist/clausis-lens-edge-vbox-grub.png` and
  `dist/clausis-lens-edge-vbox-live.png`; the guest then shut down through ACPI
  to verified `VMState="poweroff"`.
- The boot and SquashFS checks prove integration and runtime prerequisites.
  Toggling and visually observing both options through a microphone-driven
  trusted-confirmation session remains an open end-to-end test.

## 2026-08-09 verified magnifier-crosshair-thickness build

- A trusted-confirmation command sets GNOME magnifier crosshair thickness to
  an exact integer from 1 through 100 pixels. Policy rejects targets, missing
  or extra fields, booleans, floats and values outside those boundaries before
  execution.
- The boundaries come from the `GtkAdjustment` embedded in the installed GNOME
  Control Center zoom page: lower `1`, upper `100`, integer step `1`. The
  executor uses the fixed `gsettings set org.gnome.desktop.a11y.magnifier
  cross-hairs-thickness` prefix and appends only the validated canonical
  decimal integer. The spoken confirmation names the exact pixel count.
- The router exposes 91 German/English command families. All 357 Python tests
  passed under Debian 13, including both UI boundaries, validator rejection
  cases, exact argv, typed routing and canonical confirmation wording.
- A fresh full ISO build and the complete repository verification chain passed.
  Read-only SquashFS inspection found the installed validator, fixed command
  key, broker integer conversion, bounded router pattern and confirmation text.
  The embedded GNOME schema reports integer type, while the embedded Control
  Center resource independently confirms the 1–100 adjustment.
- The exact tested ISO is 2,643,034,112 bytes with SHA-256
  `da9c630680b66a48b03beaa939b73603069cd2da54953f68ac7f02a0f5b4223c`.
- VirtualBox VM `Clausis` booted that exact ISO through the branded UEFI GRUB
  menu to the branded GNOME live desktop. Evidence is stored as
  `dist/clausis-crosshair-thickness-vbox-grub.png` and
  `dist/clausis-crosshair-thickness-vbox-live.png`; the guest then shut down
  through ACPI to verified `VMState="poweroff"`.
- The boot and SquashFS checks prove integration and runtime prerequisites.
  Setting and visually measuring line thickness through a microphone-driven
  trusted-confirmation session remains an open end-to-end test.

## 2026-08-09 verified magnifier-crosshair-color build

- A trusted-confirmation action sets GNOME magnifier crosshair color across the
  complete RGB color space. Its policy accepts exactly the integer fields
  `red`, `green` and `blue`, each from 0 through 255, and rejects targets,
  missing or extra fields, booleans, floats and out-of-range channels.
- Two bounded German/English command families accept eight common color names
  or exact spoken RGB channels. Both create the same typed request. Only the
  executor formats canonical lowercase `#rrggbb` and appends it to the fixed
  `gsettings set org.gnome.desktop.a11y.magnifier cross-hairs-color` prefix;
  no caller-controlled string reaches the command vector.
- The router exposes 93 German/English command families. All 361 Python tests
  passed under Debian 13, including both RGB extrema, validator rejection,
  named and numeric routing, exact `#0c22ff` argv and RGB confirmation wording.
- A fresh full ISO build and the complete repository verification chain passed.
  Read-only SquashFS inspection found the installed typed policy, fixed key,
  canonical formatter, both router builders and exact confirmation text. The
  GNOME schema embedded in the ISO reports string type for `cross-hairs-color`.
- The exact tested ISO is 2,643,034,112 bytes with SHA-256
  `6f28fd0cb08bfde66de74e4adb1a8562539707bdaea979577931faebd38c4477`.
- VirtualBox VM `Clausis` booted that exact ISO through the branded UEFI GRUB
  menu to the branded GNOME live desktop. Evidence is stored as
  `dist/clausis-crosshair-color-vbox-grub.png` and
  `dist/clausis-crosshair-color-vbox-live.png`; the guest then shut down through
  ACPI to verified `VMState="poweroff"`.
- The boot and SquashFS checks prove integration and runtime prerequisites.
  Setting and visually checking the color through a microphone-driven
  trusted-confirmation session remains an open end-to-end test.

## 2026-08-09 verified magnifier-brightness-and-contrast build

- Two trusted-confirmation actions set magnifier brightness or contrast to an
  exact signed integer from -75 through +75 percent, matching the adjustments
  embedded in the installed GNOME Control Center. Policy rejects targets,
  missing or extra fields, booleans, floats and out-of-range values.
- The executor converts the integer to a canonical two-decimal fraction and
  calls the fixed packaged `clausis-magnifier-filter brightness|contrast`
  adapter. The adapter accepts no other mode or number syntax, reads and sets
  only the fixed red, green and blue schema keys with shell-free argv, and
  restores already changed channels if a later channel fails.
- The router exposes 95 German/English command families. All 370 Python tests
  passed under Debian 13, including signed routing, both UI boundaries, exact
  adapter argv, invalid adapter syntax, three-channel writes, partial-failure
  rollback and signed confirmation wording.
- A fresh full ISO build and the complete repository verification chain passed.
  Read-only SquashFS inspection found the executable installed entrypoint,
  adapter allowlist and rollback, both policies, canonical broker conversion,
  router patterns and confirmation text. The embedded schema reports -1.0 to
  +1.0, while the embedded Control Center independently confirms the deliberately
  narrower user-facing range -0.75 to +0.75. The installed adapter directly
  rejected noncanonical input `0.2` with exit code 2.
- The exact tested ISO is 2,643,034,112 bytes with SHA-256
  `d52aaf67a99e12da3d33562af39b844747eb7d68cd2863a1f46f6e9a07a8e50c`.
- The first VirtualBox live attempt reached a graphical Debian background but
  GNOME Shell did not appear after an additional 90 seconds and the guest did
  not react to a 90-second ACPI shutdown request. The failed disposable-VM
  state was preserved as
  `dist/clausis-magnifier-filters-vbox-live-attempt1-incomplete.png`, then only
  VM `Clausis` was forcibly powered off.
- A clean second boot of the same ISO hash reached the branded UEFI GRUB menu
  and the complete branded GNOME live desktop. Primary evidence is stored as
  `dist/clausis-magnifier-filters-vbox-grub.png` and
  `dist/clausis-magnifier-filters-vbox-live.png`; attempt-two evidence remains
  separately named. The successful guest then shut down through ACPI to
  verified `VMState="poweroff"`.
- The VirtualBox host log for the failed attempt contains no VMSVGA FIFO error,
  Guru Meditation, reset or hypervisor failure. It records the guest switching
  to 1280x800 at 68 seconds and remaining there until the forced poweroff, but
  supplies no guest journal and therefore does not prove a root cause.
- Two further controlled boots of the same ISO hash and unchanged VM reached
  the complete branded GNOME desktop at the fixed three-minute checkpoint.
  Evidence is stored as `dist/clausis-magnifier-filters-vbox-live-attempt3.png`
  and `dist/clausis-magnifier-filters-vbox-live-attempt4.png`. Both intervening
  and final guests shut down through ACPI to verified poweroff. The result is
  one incomplete attempt followed by three consecutive successful attempts.
- These repeats reduce but do not erase the first transient reliability signal;
  without a guest journal its cause remains unproven. Applying and visually
  measuring both filters through a microphone-driven trusted confirmation
  session remains an open end-to-end test.

## 2026-08-09 verified Orca-speech-recovery build

- A trusted-confirmation recovery action restarts Orca with explicitly enabled
  speech. It invokes only the packaged `clausis-orca-control restart` adapter;
  arbitrary Orca settings and any missing or additional parameters are rejected.
- The adapter launches the fixed `orca --replace --enable speech` argv without a
  shell, detached from the broker with closed file descriptors, and reports an
  immediate child-process exit as a failure.
- The router exposes 96 German/English command families. All 377 Python tests
  passed under Debian 13, including exact routing and confirmation wording,
  parameter rejection, fixed broker argv, detached launch flags and immediate
  exit and spawn-failure handling.
- A fresh full ISO build and the complete repository verification chain passed.
  Read-only SquashFS inspection found the executable installed entrypoint plus
  the embedded policy, router and confirmation text. The installed adapter
  directly rejected the unsupported arguments `enable mouse-review` with exit
  code 2.
- The exact tested ISO is 2,643,034,112 bytes with SHA-256
  `9a7e052efed25e83693a9b5744dd720b7efa843ee83ae9c701f49a394bd82d3e`.
- VirtualBox VM `Clausis` booted that exact ISO through the branded UEFI GRUB
  menu to the complete branded GNOME live desktop. Evidence is stored as
  `dist/clausis-orca-recovery-vbox-grub.png` and
  `dist/clausis-orca-recovery-vbox-live.png`; the guest then shut down through
  ACPI to verified `VMState="poweroff"`.
- The boot and SquashFS checks prove packaging and live-system integration.
  Invoking the recovery through a microphone-driven trusted-confirmation session
  and audibly verifying the restarted Orca speech remain open end-to-end tests.

## 2026-08-09 verified magnifier-disable build

- A separate trusted-confirmation action disables only the GNOME screen
  magnifier. It accepts no target or arguments and uses the fully fixed
  `gsettings set org.gnome.desktop.a11y.applications screen-magnifier-enabled
  false` vector.
- The canonical spoken summary explicitly states that Orca and the on-screen
  keyboard remain enabled. Clausis still exposes no voice command that disables
  either of those two rescue facilities.
- The router exposes 97 German/English command families. All 377 Python tests
  passed under Debian 13, including both language routes, parameter rejection,
  the exact fixed `false` argv and the rescue-state confirmation wording.
- A fresh full ISO build and the complete repository verification chain passed.
  Read-only SquashFS inspection found the installed policy, router and canonical
  confirmation text, verified the fixed `false` command and imported the
  installed router to independently count all 97 command families.
- The exact tested ISO is 2,643,034,112 bytes with SHA-256
  `62a7175bb8edb7c7095fba621e57060250516b9dd5b6df8662c77848f5919ad2`.
- VirtualBox VM `Clausis` booted that exact ISO through the branded UEFI GRUB
  menu to the complete branded GNOME live desktop. Evidence is stored as
  `dist/clausis-magnifier-disable-vbox-grub.png` and
  `dist/clausis-magnifier-disable-vbox-live.png`; the guest then shut down
  through ACPI to verified `VMState="poweroff"`.
- The boot and SquashFS checks prove packaging and live-system integration.
  Disabling an already-active magnifier through a microphone-driven trusted
  confirmation while independently observing Orca and the on-screen keyboard
  remain available is still an open end-to-end session test.

## 2026-08-09 verified Wayland-clipboard-clear build

- A separate trusted-confirmation action permanently clears only the regular
  Wayland clipboard. It accepts no target or arguments and invokes exactly
  `wl-copy --clear`; it neither reads nor returns clipboard content and leaves
  the independent PRIMARY selection unchanged.
- Policy marks the operation irreversible, so callers cannot claim it is
  reversible. The canonical confirmation names the permanent deletion and its
  exact scope before a capability can be issued.
- The router exposes 98 German/English command families. All 381 Python tests
  passed under Debian 13, including both language routes, parameter and
  reversibility rejection, exact fixed argv, confirmation wording and the
  required live-image package declaration.
- A fresh full ISO build and the complete repository verification chain passed.
  Read-only SquashFS inspection found executable `/usr/bin/wl-copy`, confirmed
  `wl-clipboard` as installed in dpkg status, found the installed policy, router
  and canonical summary, and imported the installed router to count all 98
  command families.
- The exact tested ISO is 2,643,034,112 bytes with SHA-256
  `1bd4bb397f7d5bac249fb341978988dfa8b59c6e49618cb071ca62dbc403c6a7`.
- VirtualBox VM `Clausis` booted that exact ISO through the branded UEFI GRUB
  menu to the complete branded GNOME live desktop. Evidence is stored as
  `dist/clausis-clipboard-clear-vbox-grub.png` and
  `dist/clausis-clipboard-clear-vbox-live.png`; the guest then shut down through
  ACPI to verified `VMState="poweroff"`.
- The boot and SquashFS checks prove packaging and live-system integration.
  Clearing a deliberately populated clipboard through a microphone-driven
  trusted-confirmation session and verifying both clipboard and PRIMARY state
  remains an open end-to-end session test.

## 2026-08-09 verified focused-text-to-Wayland-clipboard build

- A separate trusted-confirmation action copies the exact content of the
  currently focused AT-SPI entry, text or document-text field to the regular
  Wayland clipboard. It accepts no caller-controlled target or arguments and is
  correctly marked irreversible because the previous clipboard is overwritten.
- Password/protected fields, uninspectable protection attributes, empty text,
  NULs, incomplete reads and content above 100,000 characters fail closed. The
  exact text is carried only on stdin to fixed `wl-copy --type
  text/plain;charset=utf-8`; it is absent from argv, confirmation, result
  messages and the tamper-evident audit log.
- The router exposes 99 German/English command families. All 391 Python tests
  passed under Debian 13, including exact multiline preservation, protected and
  oversized-field rejection, fixed shell-free writer flags, provider-error
  redaction, confirmation wording and an end-to-end broker audit assertion.
- A fresh full ISO build and the complete repository verification chain passed.
  Read-only SquashFS inspection found executable `wl-copy`, the installed
  clipboard writer and its stdin-only call, the AT-SPI copy path, policy, router
  and canonical summary, and imported the installed router to count all 99
  command families.
- The exact tested ISO is 2,643,034,112 bytes with SHA-256
  `4a9e555da98d361fac974de41157bccb66c7c736c80f229d3e53e02896e297c3`.
- VirtualBox VM `Clausis` booted that exact ISO through the branded UEFI GRUB
  menu to the complete branded GNOME live desktop. Evidence is stored as
  `dist/clausis-copy-focused-vbox-grub.png` and
  `dist/clausis-copy-focused-vbox-live.png`; the guest then shut down through
  ACPI to verified `VMState="poweroff"`.
- The boot and SquashFS checks prove packaging and live-system integration.
  Copying a real focused multiline field through a microphone-driven trusted
  confirmation and independently reading back the Wayland clipboard while
  observing that no content enters logs remains an open end-to-end session test.

## 2026-08-10 verified Wayland-clipboard-to-focused-text build

- A separate trusted-confirmation action replaces the currently focused safe
  editable AT-SPI field with text from the regular Wayland clipboard. It accepts
  no caller-controlled target or arguments and is marked irreversible because a
  successful operation overwrites the previous field value.
- The fixed `wl-paste --type text` process is read through a nonblocking pipe
  capped before UTF-8 decoding at 400,000 bytes and five seconds. Empty, invalid
  UTF-8, NUL-containing, over-100,000-character and disallowed-control content
  fails closed; tabs and newlines retain exact formatting.
- Password/protected or uninspectable fields are rejected. The bound AT-SPI
  mutation requires exact readback and restores the previous field content on
  exception, rejection or mismatch. Clipboard content is absent from request,
  confirmation, result, speech and the tamper-evident audit log.
- The router exposes 100 German/English command families. All 401 Python tests
  passed under Debian 13, including bounded streaming, timeout/error privacy,
  UTF-8 and control-character rejection, exact multiline mutation, rollback,
  confirmation gating and broker-level audit non-disclosure.
- A fresh full ISO build and the complete repository verification chain passed.
  Read-only SquashFS inspection found executable `wl-paste`, the installed
  byte-capped selector reader, AT-SPI paste and rollback paths, policy and
  router, and imported the installed router to count all 100 command families.
- The exact tested ISO is 2,643,034,112 bytes with SHA-256
  `2f137a8db671f198e5f83b81a298f4a44fa0a9022eae451657823b099f39fd2b`.
- VirtualBox VM `Clausis` booted that exact ISO through the branded UEFI GRUB
  menu to the complete branded GNOME live desktop. Evidence is stored as
  `dist/clausis-paste-focused-vbox-grub.png` and
  `dist/clausis-paste-focused-vbox-live.png`; the guest then shut down through
  ACPI to verified `VMState="poweroff"`.
- The boot and SquashFS checks prove packaging and live-system integration.
  Pasting a real multiline clipboard into a real focused field through a
  microphone-driven trusted confirmation and deliberately exercising rollback
  remains an open end-to-end session test.

## 2026-08-10 verified spoken-Wayland-clipboard build

- A separate trusted-confirmation action speaks text from the regular Wayland
  clipboard only after warning that the output may disclose its contents. The
  canonical confirmation itself contains no clipboard data and the action
  accepts no target or arguments.
- The action reuses the fixed, byte- and time-capped `wl-paste --type text`
  reader. Whitespace is normalized for speech; at most 1,000 characters are
  included in the result, followed by an explicit truncation notice when more
  content exists.
- Before the tamper-evident audit entry is signed, both result message and
  details are replaced with the fixed `[REDACTED: clipboard text]` marker. A
  broker-level test proves that spoken clipboard content is absent while the
  resulting HMAC chain still verifies.
- The router exposes 101 German/English command families. All 406 Python tests
  passed under Debian 13, including both routes, parameter rejection,
  confirmation disclosure wording, speech bounds and direct plus broker-level
  audit redaction.
- The first full ISO attempt passed source and Debian package tests but failed
  during the pinned speech-model download because the external Hugging Face CAS
  reconstruction endpoint returned a client/network error. No source changed;
  a full retry using the persistent cache completed successfully, including the
  repository's complete ISO verification chain.
- Read-only SquashFS inspection of the successful image found executable
  `wl-paste`, the installed action, fixed audit redaction, truncation wording and
  router, and imported the installed router to count all 101 command families.
- The exact tested ISO is 2,643,034,112 bytes with SHA-256
  `e2ef8d94bbd742e1ba85a3f1a08e105fed724e6cf8d65515ba854e59ab3b6a8c`.
- VirtualBox VM `Clausis` booted that exact ISO through the branded UEFI GRUB
  menu to the complete branded GNOME live desktop. Evidence is stored as
  `dist/clausis-read-clipboard-vbox-grub.png` and
  `dist/clausis-read-clipboard-vbox-live.png`; the guest then shut down through
  ACPI to verified `VMState="poweroff"`.
- The boot and SquashFS checks prove packaging and live-system integration.
  Speaking a deliberately populated clipboard through a microphone-driven
  trusted confirmation while monitoring both audible truncation and persistent
  logs remains an open end-to-end session test.

## 2026-08-10 verified dictated-Wayland-clipboard-write build

- A separate trusted-confirmation action writes one nonempty printable dictated
  string of at most 500 characters to the regular Wayland clipboard. It accepts
  no argument object, is marked irreversible because existing clipboard state
  is overwritten, and sends content only through stdin to the previously
  verified fixed `wl-copy --type text/plain;charset=utf-8` writer.
- The canonical confirmation and result never repeat the dictation. Before the
  audit chain HMAC is computed, the request target is replaced with the fixed
  `[REDACTED: clipboard write text]` marker.
- Review of that boundary uncovered an older privacy flaw: `desktop.text.set`
  also suppressed dictation from confirmation and result but retained its
  request target in audit. The same change now replaces that target with
  `[REDACTED: dictated text]`; its validator also rejects all extra arguments
  and DEL/non-printable input.
- The router exposes 102 German/English command families. All 412 Python tests
  passed under Debian 13, including both write routes, exact target preservation,
  size/printability/argument/reversibility rejection, stdin-only execution,
  both audit markers and valid HMAC chains after redaction.
- A fresh full ISO build and the complete repository verification chain passed.
  Read-only SquashFS inspection found executable `wl-copy`, the installed
  write policy and semantic stdin route, both audit redaction labels and router,
  and imported the installed router to count all 102 command families.
- The exact tested ISO is 2,643,034,112 bytes with SHA-256
  `bfb4b89ae92c3710130659c95708f3e77bb17873a4fe8334bbc690c811c20122`.
- VirtualBox VM `Clausis` booted that exact ISO through the branded UEFI GRUB
  menu to the complete branded GNOME live desktop, including the Clausis setup
  dialog and visible KI notice. Evidence is stored as
  `dist/clausis-write-clipboard-vbox-grub.png` and
  `dist/clausis-write-clipboard-vbox-live.png`; the guest then shut down through
  ACPI to verified `VMState="poweroff"`.
- The boot and SquashFS checks prove packaging and live-system integration.
  Writing a dictated value through a microphone-driven trusted confirmation and
  independently reading it back while inspecting persistent audit output remains
  an open end-to-end session test.

## 2026-08-10 verified AT-SPI-text-selection-to-clipboard build

- A separate trusted-confirmation action copies exactly one AT-SPI selection
  from the focused, non-protected text object to the regular Wayland clipboard.
  It requires one ordered, in-bounds selection, rejects empty, multiple,
  protected, NUL-containing, or over-100,000-character selections, and passes
  the content only through stdin to the fixed `wl-copy` writer.
- Confirmation and results describe the selected-text scope without repeating
  its content. The action is irreversible because it overwrites existing
  clipboard state and accepts no argument object.
- The router exposes 103 German/English command families. All 419 Python tests
  passed under Debian 13, including selection boundaries, protected objects,
  exact clipboard transfer, routing, policy, and confirmation behavior.
- The first full build reached the pinned Faster Whisper download but failed at
  the external Xet CAS reconstruction service. The hook now disables Xet and
  telemetry and retries the same pinned model revision at most three times with
  bounded backoff; no moving revision or fallback source was introduced. A
  fresh full ISO build then passed the complete repository verification chain.
- Read-only SquashFS inspection found the installed `nSelections` and
  `getSelection(0)` AT-SPI implementation, action, policy, confirmation, and
  router, and imported the installed router to count all 103 command families.
- The exact tested ISO is 2,643,034,112 bytes with SHA-256
  `0ab736bd541bd545b18899814046f6a6071a85693ef40d05638a9dd29390f426`.
- VirtualBox VM `Clausis` booted that exact ISO through the branded UEFI GRUB
  menu to the complete branded GNOME live desktop. Evidence is stored as
  `dist/clausis-copy-selection-vbox-grub.png` and
  `dist/clausis-copy-selection-vbox-live.png`; the guest then shut down through
  ACPI to verified `VMState="poweroff"`.
- The boot and SquashFS checks prove packaging and live-system integration.
  Copying a real application selection through a microphone-driven trusted
  confirmation and independently reading it back remains an open end-to-end
  session test.

## 2026-08-10 verified focused-text-select-all build

- The local low-risk command selects all text in the once-bound focused safe
  AT-SPI entry, text, or document-text object without synthesizing keyboard or
  pointer input. It accepts no target or arguments and never reads or reports
  the text content.
- The adapter accepts 1 through 100,000 characters and at most 64 valid prior
  selection spans. It removes those spans, adds exactly `(0, characterCount)`,
  and verifies both `nSelections == 1` and the exact returned offsets.
  Rejection or mismatch restores and verifies the previous spans; protected,
  malformed, empty, oversized, or uninspectable objects fail closed.
- The router exposes 104 German/English command families. All 425 Python tests
  passed under Debian 13, including exact selection replacement, protected and
  bounded rejection, mismatch rollback, semantic execution, routing, and
  parameterless policy enforcement.
- A fresh full ISO build passed the complete repository verification chain.
  Read-only SquashFS inspection found the installed `removeSelection`,
  `addSelection`, exact readback, action, policy, and router implementation,
  and imported the installed router to count all 104 command families.
- The exact tested ISO is 2,643,034,112 bytes with SHA-256
  `0e729837242e020c41ae2b6f9590eb84115417e9fa59efcfa51cf5dc6ffe6f3c`.
- VirtualBox VM `Clausis` booted that exact ISO through the branded UEFI GRUB
  menu to the complete branded GNOME live desktop. Evidence is stored as
  `dist/clausis-select-all-vbox-grub.png` and
  `dist/clausis-select-all-vbox-live.png`; the guest then shut down through
  ACPI to verified `VMState="poweroff"`.
- The boot and SquashFS checks prove packaging and live-system integration.
  Selecting all text in a real application through the microphone-driven
  session and then copying the exact span remains an open end-to-end test.

## 2026-08-10 verified spoken-AT-SPI-text-selection build

- A separate confirmation-gated action speaks exactly one bounded selection
  from the focused, non-protected AT-SPI text object without changing either
  the selection or the Wayland clipboard. It reuses the verified single-span,
  ordered-offset, 100,000-character source boundary.
- Spoken whitespace is normalized and output is capped at 1,000 characters
  with an explicit truncation notice. The canonical confirmation contains no
  selected content. Before HMAC chain signing, the audit result message and
  details are replaced with the fixed `[REDACTED: selected text]` marker.
- The router exposes 105 German/English command families. All 430 Python tests
  passed under Debian 13, including confirmation gating, content-free summary,
  truncation, exact speech source, audit non-disclosure and valid audit chain,
  routing, and parameterless policy enforcement.
- A fresh full ISO build passed the complete repository verification chain.
  Read-only SquashFS inspection found the installed action, confirmation,
  policy, router, 1,000-character truncation and selected-text audit marker,
  and imported the installed router to count all 105 command families.
- The exact tested ISO is 2,643,034,112 bytes with SHA-256
  `bc2edc57bc4d32e40ada332df83448d60a67736ac01f069724f5a7e87879192b`.
- VirtualBox VM `Clausis` booted that exact ISO through the branded UEFI GRUB
  menu to the complete branded GNOME live desktop. Evidence is stored as
  `dist/clausis-read-selection-vbox-grub.png` and
  `dist/clausis-read-selection-vbox-live.png`; the guest then shut down through
  ACPI to verified `VMState="poweroff"`.
- The boot and SquashFS checks prove packaging and live-system integration.
  Speaking a real application selection through a microphone-driven trusted
  confirmation while monitoring the audible truncation remains an open
  end-to-end session test.

## 2026-08-10 verified AT-SPI-text-selection-clear build

- A local low-risk correction action removes all selections from the once-bound
  focused, non-protected AT-SPI text object without keyboard or pointer input.
  It accepts no target or arguments and does not read, speak, copy, or audit any
  text content.
- The adapter snapshots at most 64 valid nonempty spans inside a bounded
  100,000-character object, removes them in descending index order, and
  requires `nSelections == 0`; an already empty selection is idempotent.
  Partial rejection or mismatch clears residual spans, restores every original
  span in order, verifies the full snapshot, and fails closed if rollback cannot
  itself be proven.
- The router exposes 106 German/English command families. All 436 Python tests
  passed under Debian 13, including multiple-span removal, empty idempotence,
  partial-failure rollback, protected/malformed/oversized rejection, semantic
  execution, routing, and parameterless policy enforcement.
- A fresh full ISO build passed the complete repository verification chain.
  Read-only SquashFS inspection found the installed removal, zero-selection
  readback, rollback, semantic action, policy, and router implementation, and
  imported the installed router to count all 106 command families.
- The exact tested ISO is 2,643,034,112 bytes with SHA-256
  `55875ad30d2bd48f9a23fb40602dfc03cb8dd6efc736e645e1e1d10e84a1bec4`.
- VirtualBox VM `Clausis` booted that exact ISO through the branded UEFI GRUB
  menu to the complete branded GNOME live desktop. Evidence is stored as
  `dist/clausis-clear-selection-vbox-grub.png` and
  `dist/clausis-clear-selection-vbox-live.png`. ACPI shutdown entered the
  visible Debian shutdown screen, exceeded the initial 60-second poll, and then
  completed normally without forced poweroff; final state was verified as
  `VMState="poweroff"`.
- The boot and SquashFS checks prove packaging and live-system integration.
  Clearing and restoring selections in a real application through a
  microphone-driven session remains an open end-to-end test.

## 2026-08-10 verified AT-SPI-caret-boundary build

- Two separate local low-risk commands move the caret of the once-bound,
  focused, non-protected AT-SPI text object to exactly offset zero or its
  reported `characterCount`. They accept no targets or arguments and do not
  read, speak, copy, or audit text content.
- Character count and the prior `caretOffset` must describe a valid
  0-through-100,000-character object. An already reached boundary is
  idempotent. Otherwise `setCaretOffset` must accept the fixed target and exact
  readback must match; rejection, exception, or mismatch restores and verifies
  the previous offset, failing closed if rollback cannot be proven.
- The router exposes 108 German/English command families. All 442 Python tests
  passed under Debian 13, including exact start/end offsets, idempotence,
  mismatch rollback, invalid/protected/oversized rejection, semantic execution,
  routing, and parameterless policy enforcement.
- A fresh full ISO build passed the complete repository verification chain.
  Read-only SquashFS inspection found both installed actions, `caretOffset`,
  `setCaretOffset`, exact readback, rollback, policies and routes, and imported
  the installed router to count all 108 command families.
- The exact tested ISO is 2,643,034,112 bytes with SHA-256
  `5ffdbcdcc69bd65acd726f1062a7cbb0286f2070ef15db26157a71c4f5a32851`.
- VirtualBox VM `Clausis` booted that exact ISO through the branded UEFI GRUB
  menu to the complete branded GNOME live desktop. Evidence is stored as
  `dist/clausis-caret-boundaries-vbox-grub.png` and
  `dist/clausis-caret-boundaries-vbox-live.png`; ACPI shutdown completed within
  55 seconds to verified `VMState="poweroff"`.
- The boot and SquashFS checks prove packaging and live-system integration.
  Moving the caret in a real application through a microphone-driven session
  remains an open end-to-end test.

## 2026-08-10 verified AT-SPI-single-character-caret build

- Two additional local low-risk commands move the caret exactly one AT-SPI
  character backward or forward in the once-bound focused safe text object.
  They accept no targets, numeric offsets, or argument objects and do not read,
  speak, copy, or audit text content.
- Targets are derived only as `max(0, caretOffset - 1)` and
  `min(characterCount, caretOffset + 1)`, so non-ASCII text remains semantic
  character navigation and each boundary is idempotent. The existing bounded
  metadata, `setCaretOffset` acceptance, exact readback, protected-field denial,
  and verified rollback rules remain mandatory.
- The router exposes 110 German/English command families. All 445 Python tests
  passed under Debian 13, including exact backward/forward movement across
  Unicode text, edge clamping, mismatch rollback, semantic execution, routing,
  and parameterless policy enforcement.
- A fresh full ISO build passed the complete repository verification chain.
  Read-only SquashFS inspection found the installed derived ±1 expressions,
  both actions, policies and routes, confirmed absence of a free offset route,
  and imported the installed router to count all 110 command families.
- The exact tested ISO is 2,643,034,112 bytes with SHA-256
  `cddf41e8cd57e57e6fa8f465540030464524891dd2ee8b28746aae92832aea0c`.
- VirtualBox VM `Clausis` booted that exact ISO through the branded UEFI GRUB
  menu to the complete branded GNOME live desktop. Evidence is stored as
  `dist/clausis-caret-steps-vbox-grub.png` and
  `dist/clausis-caret-steps-vbox-live.png`; ACPI shutdown completed within
  55 seconds to verified `VMState="poweroff"`.
- The boot and SquashFS checks prove packaging and live-system integration.
  Moving across Unicode text in a real application through a microphone-driven
  session remains an open end-to-end test.

## 2026-08-10 verified content-free-AT-SPI-caret-position build

- A separate local read-only command reports the accessible field name,
  validated `caretOffset`, and bounded `characterCount` for the once-bound
  focused safe AT-SPI text object. It accepts no target or arguments and never
  reads, speaks, copies, or audits text content.
- Only entry, text, and document-text roles with inspectable non-protected
  attributes are eligible. Count must be 0 through 100,000 and offset must be
  inside 0 through count. Password/protected objects are denied before
  `queryText`, preventing even password-length disclosure; malformed metadata
  fails closed without mutation.
- The router exposes 111 German/English command families. All 450 Python tests
  passed under Debian 13, including exact metadata output, proof that `getText`
  is not called, protected/invalid/oversized/wrong-role rejection, semantic
  execution, routing, and parameterless policy enforcement.
- A fresh full ISO build passed the complete repository verification chain.
  Read-only SquashFS inspection isolated the installed implementation block,
  found `characterCount` and `caretOffset`, proved `getText` absent from that
  block, found the installed action/policy/route, and imported the installed
  router to count all 111 command families.
- The exact tested ISO is 2,643,034,112 bytes with SHA-256
  `2026578898fef4b45f711cb82d5f4c3c6f07171f35c3fbe21609f0049f458bc2`.
- VirtualBox VM `Clausis` booted that exact ISO through the branded UEFI GRUB
  menu to the complete branded GNOME live desktop. Evidence is stored as
  `dist/clausis-caret-describe-vbox-grub.png` and
  `dist/clausis-caret-describe-vbox-live.png`; ACPI shutdown completed within
  55 seconds to verified `VMState="poweroff"`.
- The boot and SquashFS checks prove packaging and live-system integration.
Reading caret metadata in a real application through a microphone-driven
  session remains an open end-to-end test.

## 2026-08-10 verified AT-SPI text-selection deletion build

- A separate confirmed command deletes exactly one nonempty selection from the
  once-bound focused, non-protected editable AT-SPI text object. The command
  accepts no target or arguments and never repeats selected content in its
  confirmation or result.
- Before mutation the adapter validates entry/text/document-text role,
  inspectable privacy attributes, exactly one ordered selection, a valid caret,
  and complete NUL-free content bounded to 100,000 characters. It invokes only
  `EditableText.deleteText(start, end)` and requires the exact expected full
  content plus zero remaining selections.
- Rejection, exception, partial deletion, wrong readback, or a residual
  selection triggers verified restoration of the complete prior content,
  caret offset, and exact selection span. Protected, ambiguous, empty, and
  oversized inputs fail before mutation.
- The router exposes 112 German/English command families. All 457 Python tests
  passed under Debian 13, including confirmation gating, parameter rejection,
  exact deletion, deliberate partial-deletion mismatch, full rollback, and
  protected/ambiguous/oversized denial.
- A fresh full ISO build passed the complete repository verification chain.
  Direct read-only SquashFS inspection found the installed action, policy,
  canonical confirmation, `deleteText` call, exact-content readback, and
  content/caret/selection rollback calls, and counted all 112 installed command
  families.
- The exact tested ISO is 2,643,034,112 bytes with SHA-256
  `fdd241218cc1669b0b92ca031a097bea702c9249034443ed4371a4b89d3d7457`.
- VirtualBox VM `Clausis` booted that exact ISO through the branded UEFI GRUB
  menu to the complete branded GNOME live desktop. Evidence is stored as
  `dist/clausis-delete-selection-vbox-grub.png` and
  `dist/clausis-delete-selection-vbox-live.png`; ACPI shutdown completed within
  15 seconds to verified `VMState="poweroff"`.
- The boot and SquashFS checks prove packaging and live-system integration.
  Deleting a selection in a real application through a microphone-driven
  session remains an open end-to-end test.

## 2026-08-10 verified AT-SPI insert-at-caret build

- A separate confirmed command inserts one printable dictated string of 1 to
  500 characters at the validated caret of the once-bound focused,
  non-protected editable AT-SPI text object. The command requires no active
  selection and never repeats dictated content in confirmation or result.
- Before mutation the adapter validates role, inspectable privacy attributes,
  complete NUL-free prior content, zero selections, character count, and caret.
  The final content is capped at 100,000 characters. It invokes
  `EditableText.insertText`, moves the caret to the exact end of the insertion,
  and requires full expected-content, caret, and zero-selection readback.
- Rejection, exception, partial insertion, wrong readback, or caret failure
  triggers verified restoration of the complete prior content and caret.
  Protected fields, active selections, non-printable text, invalid metadata,
  and oversized results fail before mutation. The dictated target is replaced
  by `[REDACTED: inserted text]` before audit signing.
- The router exposes 113 German/English command families. All 464 Python tests
  passed under Debian 13, including confirmation gating, target validation,
  exact insertion, deliberate partial-insertion mismatch, full rollback,
  protected/selected/oversized denial, and audit redaction.
- A fresh full ISO build passed the complete repository verification chain.
  Direct read-only SquashFS inspection found the installed action, policy,
  canonical confirmation, `insertText` call, full readback, content/caret
  rollback, audit marker, and all 113 installed command families.
- The exact tested ISO is 2,643,034,112 bytes with SHA-256
  `bb80a1409fc86bc93e527c026e89f6704d90d77e61d54fa2fb64874c0cbed702`.
- VirtualBox VM `Clausis` booted that exact ISO through the branded UEFI GRUB
  menu to the complete branded GNOME live desktop and automatically opened the
  Clausis setup dialog. The visible `Clausis – KI-Hinweis` notification also
  confirms the requested AI-slop disclosure in the live session. Evidence is
  stored as `dist/clausis-insert-caret-vbox-grub.png` and
  `dist/clausis-insert-caret-vbox-live.png`; ACPI shutdown completed within
  10 seconds to verified `VMState="poweroff"`.
- The boot and SquashFS checks prove packaging and live-system integration.
  Dictating an insertion into a real application through a microphone-driven
  session remains an open end-to-end test.

## 2026-08-10 verified AT-SPI single-character deletion build

- Two separate confirmed, parameterless commands delete exactly one AT-SPI
  character immediately before or after the validated caret of the once-bound
  focused, non-protected editable text object. No keyboard or pointer event and
  no caller-controlled offset is used.
- Before mutation the adapter validates role, inspectable privacy attributes,
  complete NUL-free content up to 100,000 characters, zero selections, and a
  caret inside the reported count. It derives only `[caret-1, caret)` or
  `[caret, caret+1)`, so a Unicode character remains one semantic unit. The
  corresponding start/end boundary is successful and idempotent.
- Outside a boundary, `EditableText.deleteText` must be accepted and the exact
  complete expected content, caret, and zero-selection state must read back.
  Rejection, exception, partial deletion, wrong content, or wrong caret triggers
  verified restoration of complete prior content and caret. Protected fields,
  active selections, malformed metadata, and oversized objects fail before
  mutation.
- The router exposes 115 German/English command families. All 472 Python tests
  passed under Debian 13, including both directions, Unicode deletion,
  idempotent boundaries, confirmation gating, parameter rejection, deliberate
  partial-deletion mismatch, full rollback, and unsafe-state denial.
- A fresh full ISO build passed the complete repository verification chain.
  Direct read-only SquashFS inspection found both installed actions, policies,
  canonical confirmations, exact one-character range derivation, `deleteText`,
  complete readback, content/caret rollback, and all 115 command families.
- The exact tested ISO is 2,643,034,112 bytes with SHA-256
  `07ed6205ef7e90f7bc6f6aa1a53b578a7a060216c7290aa6787d2acdf332a92a`.
- VirtualBox VM `Clausis` booted that exact ISO through the branded UEFI GRUB
  menu to the complete branded GNOME live desktop. Evidence is stored as
  `dist/clausis-delete-character-vbox-grub.png` and
  `dist/clausis-delete-character-vbox-live.png`; ACPI shutdown completed within
  10 seconds to verified `VMState="poweroff"`.
- The boot and SquashFS checks prove packaging and live-system integration.
  Deleting characters in a real application through a microphone-driven
  session remains an open end-to-end test.

## 2026-08-10 verified AT-SPI single-character selection build

- Two separate local parameterless commands select exactly one AT-SPI character
  immediately before or after the validated caret of the once-bound focused,
  non-protected text object. They do not read character content and use no
  keyboard, pointer, caller-controlled offset, or confirmation path.
- Before mutation the adapter validates role, inspectable privacy attributes,
  zero existing selections, a character count from 0 through 100,000, and a
  caret inside that count. It derives only `[caret-1, caret)` or
  `[caret, caret+1)`, adds that exact span, moves the caret to its outer edge,
  and verifies selection count, offsets, and caret. The corresponding text
  boundary is successful and idempotent.
- Rejection, exception, wrong span, residual selection, or wrong caret removes
  all residual spans and restores the previous empty selection and caret with
  exact readback. Protected fields, existing selections, malformed metadata,
  and oversized objects fail before mutation.
- The router exposes 117 German/English command families. All 479 Python tests
  passed under Debian 13, including both directions, Unicode spans, caret-edge
  movement, idempotent boundaries, parameter rejection, deliberate span
  mismatch, full rollback, and unsafe-state denial.
- A fresh full ISO build passed the complete repository verification chain.
  Direct read-only SquashFS inspection found both installed actions and
  policies, exact one-character range derivation, selection/caret mutation,
  post-state checks, selection/caret rollback, and all 117 command families.
- The exact tested ISO is 2,643,034,112 bytes with SHA-256
  `7fa4a52603e3ce1b7e2cbb8dd7c725692cfe743dfb4d5478e482b8eb9c585d1b`.
- VirtualBox VM `Clausis` booted that exact ISO through the branded UEFI GRUB
  menu to the complete branded GNOME live desktop. Evidence is stored as
  `dist/clausis-select-character-vbox-grub.png` and
  `dist/clausis-select-character-vbox-live.png`; ACPI shutdown completed within
  10 seconds to verified `VMState="poweroff"`.
- The boot and SquashFS checks prove packaging and live-system integration.
  Selecting characters in a real application through a microphone-driven
  session remains an open end-to-end test.

## 2026-08-10 verified AT-SPI selection-replacement build

- A separate confirmed action replaces exactly one nonempty selection in the
  once-bound focused, non-protected editable AT-SPI text object with one
  printable dictated string of 1 to 500 characters. Neither selected nor
  replacement content is repeated in confirmation or result.
- Before mutation the adapter validates role, inspectable privacy attributes,
  exactly one ordered selection, a valid caret, complete NUL-free prior content,
  and a final size no greater than 100,000 characters. It constructs and writes
  the complete expected content, moves the caret directly behind the
  replacement, and requires exact full-content, caret, and zero-selection
  readback.
- Rejection, exception, partial write, wrong content, wrong caret, or residual
  selection triggers verified restoration of complete prior content, caret,
  and the exact original selection span. Protected fields, absent or ambiguous
  selections, malformed metadata, non-printable replacement text, and
  oversized results fail before mutation. The dictated target becomes
  `[REDACTED: selection replacement text]` before audit signing.
- The router exposes 118 German/English command families. All 486 Python tests
  passed under Debian 13, including exact replacement, confirmation gating,
  target validation, deliberate partial-write mismatch, complete
  content/caret/selection rollback, unsafe-state denial, and audit redaction.
- A fresh full ISO build passed the complete repository verification chain.
  Direct read-only SquashFS inspection found the installed action, policy,
  canonical confirmation, expected-content construction, complete post-state
  checks, full rollback, audit marker, and all 118 command families.
- The exact tested ISO is 2,643,034,112 bytes with SHA-256
  `a4eaa5615fa23c6eb0bc1b74bbbdd10cb1e4ff54b447d260286cbc706246ff07`.
- VirtualBox VM `Clausis` booted that exact ISO through the branded UEFI GRUB
  menu to the complete branded GNOME live desktop. Evidence is stored as
  `dist/clausis-replace-selection-vbox-grub.png` and
  `dist/clausis-replace-selection-vbox-live.png`; ACPI shutdown completed within
  10 seconds to verified `VMState="poweroff"`.
- The boot and SquashFS checks prove packaging and live-system integration.
  Replacing a selection in a real application through a microphone-driven
  session remains an open end-to-end test.

## 2026-08-10 verified content-redacted AT-SPI single-character read build

- Two separate confirmed actions read exactly one character immediately before
  or after the validated caret in a once-bound focused, non-protected AT-SPI
  entry, text, or document-text object. Space, tab, and newline are announced
  by name; other Unicode characters are spoken without reading adjacent text.
- The adapter validates inspectable privacy attributes, role, a count from 0
  through 100,000, and a caret inside that count before content access. At the
  matching text boundary it returns without calling `getText`; otherwise the
  only permitted content call is the exact one-character span beside the
  caret. Protected roles, malformed metadata, NUL, incomplete results, and
  unsupported directions fail closed without mutation.
- Confirmation summaries contain only the requested side. Spoken character
  results are replaced by `[REDACTED: previous character]` or
  `[REDACTED: next character]` before the chained audit HMAC is calculated.
- The router exposes 120 German/English command families. All 496 Python tests
  passed under Debian 13, including confirmation gating, exact Unicode spans,
  zero content access at boundaries and unsafe fields, whitespace speech, and
  side-specific audit redaction.
- A fresh full ISO build passed the complete repository verification chain.
  Direct read-only SquashFS inspection found the installed adapter, exact
  `getText(start, start + 1)` boundary, both router/policy/confirmation/audit
  paths, fixed redaction labels, and all 120 command families.
- The exact tested ISO is 2,643,034,112 bytes with SHA-256
  `a43336b8de47203468900b2aa11f604beb51bf6702758da575519923f3ad6e71`.
- VirtualBox VM `Clausis` booted that exact ISO through the branded UEFI GRUB
  menu to the complete branded GNOME live desktop. Evidence is stored as
  `dist/clausis-read-character-vbox-grub.png` and
  `dist/clausis-read-character-vbox-live.png`; ACPI shutdown completed within
  10 seconds to verified `VMState="poweroff"`.
- The boot and SquashFS checks prove packaging and live-system integration.
  Reading a character in a real application through a microphone-driven
  session remains an open end-to-end test.

## 2026-08-10 verified bounded AT-SPI adjacent-word read build

- Two separate confirmed actions announce exactly one Unicode word before or
  after the validated caret in a once-bound focused, non-protected AT-SPI
  entry, text, or document-text object. Alphanumeric characters plus
  apostrophe, hyphen, and underscore form the word; surrounding punctuation
  and whitespace are skipped.
- Every content operation is exactly one `getText(index, index + 1)` span. The
  adapter inspects at most 256 characters and accepts at most 128 word
  characters. It validates role, inspectable protection attributes, a count
  from 0 through 100,000, and an in-range caret first. The corresponding field
  boundary returns without content access; invalid metadata, protected fields,
  partial character results, excessive search distance, and excessive words
  fail closed without mutation.
- Confirmation summaries contain only the requested side and fixed limits.
  Spoken results are replaced by `[REDACTED: previous word]` or
  `[REDACTED: next word]` before the chained audit HMAC is calculated.
- The router exposes 122 German/English command families. All 506 Python tests
  passed under Debian 13, including exact Unicode word assembly, confirmation
  gating, one-character read ranges, content-free field boundaries, unsafe
  field denial, both hard limits, and side-specific audit redaction.
- A fresh full ISO build passed the complete repository verification chain.
  Direct read-only SquashFS inspection found the installed adapter, exact
  one-character content call, 256/128 limits, both
  router/policy/confirmation/audit paths, fixed redaction labels, and all 122
  command families.
- The exact tested ISO is 2,643,034,112 bytes with SHA-256
  `afddeb5d22e6ad627eac2477bc536a98022b1b8550f826e083ac259dd29929f5`.
- VirtualBox VM `Clausis` booted that exact ISO through the branded UEFI GRUB
  menu to the complete branded GNOME live desktop. Evidence is stored as
  `dist/clausis-read-word-vbox-grub.png` and
  `dist/clausis-read-word-vbox-live.png`; ACPI shutdown completed within 10
  seconds to verified `VMState="poweroff"`.
- The boot and SquashFS checks prove packaging and live-system integration.
  Reading an adjacent word in a real application through a microphone-driven
  session remains an open end-to-end test.

## 2026-08-10 verified bounded AT-SPI word-navigation build

- Two local parameterless actions move the caret to the previous or next
  Unicode word start in a once-bound focused, non-protected AT-SPI entry, text,
  or document-text object. Alphanumeric characters plus apostrophe, hyphen,
  and underscore share the same word classification as adjacent-word speech.
- The adapter requires zero active selections, valid inspectable protection
  attributes, a character count from 0 through 100,000, and an in-range caret
  before scanning. Every content operation is exactly one
  `getText(index, index + 1)` span and at most 256 characters are inspected.
  The matching field edge is content-free and idempotent.
- Mutation occurs only after the target word start is fully derived. Exact
  target caret and zero selections are read back. Rejection, exception, wrong
  offset, or selection drift triggers verified restoration of the previous
  caret; an unverified restoration fails separately.
- The router exposes 124 German/English command families. All 514 Python tests
  passed under Debian 13, including exact Unicode word starts, parameterless
  low-risk routing, content-free edges, protected/selected/invalid denial,
  one-character ranges, hard search limit, mismatch, and rollback.
- A fresh full ISO build passed the complete repository verification chain.
  Direct read-only SquashFS inspection found the installed navigation method,
  one-character content call, 256-character limit, zero-selection invariant,
  verified rollback, both router/policy/executor paths, and all 124 command
  families.
- The exact tested ISO is 2,643,034,112 bytes with SHA-256
  `7e9da3fc4e2c2f8160d91a382a84573bb70d2a2f8b4ab285f719b689402fc740`.
- VirtualBox VM `Clausis` booted that exact ISO through the branded UEFI GRUB
  menu to the complete branded GNOME live desktop. Evidence is stored as
  `dist/clausis-word-navigation-vbox-grub.png` and
  `dist/clausis-word-navigation-vbox-live.png`; ACPI shutdown completed within
  10 seconds to verified `VMState="poweroff"`.
- The boot and SquashFS checks prove packaging and live-system integration.
  Moving by word through a real microphone-driven application session remains
  an open end-to-end test.

## 2026-08-10 verified bounded AT-SPI adjacent-word selection build

- Two local parameterless actions select exactly the previous or next Unicode
  word in a once-bound focused, non-protected AT-SPI entry, text, or
  document-text object. Alphanumeric characters plus apostrophe, hyphen, and
  underscore use the same classification as word speech and navigation.
- The adapter requires zero existing selections, inspectable protection
  attributes, a character count from 0 through 100,000, and an in-range caret.
  It derives the exact nonempty span through at most 256 individual
  `getText(index, index + 1)` calls. The corresponding field edge is
  content-free and idempotent.
- The adapter adds only the calculated span, moves the caret to its outer edge,
  and verifies selection count, exact offsets, and target caret. Rejection,
  exception, span mismatch, or caret mismatch removes every residual selection
  and restores the previous caret; unverified rollback fails separately.
- The router exposes 126 German/English command families. All 522 Python tests
  passed under Debian 13, including exact Unicode spans, parameterless low-risk
  routing, content-free edges, unsafe-state denial, one-character reads, hard
  search limit, deliberate mismatch, residual-span cleanup, and caret rollback.
- A fresh full ISO build passed the complete repository verification chain.
  Direct read-only SquashFS inspection found the installed selection method,
  one-character content call, search limit, exact span verification, rollback
  removal, both router/policy/executor paths, and all 126 command families.
- The exact tested ISO is 2,643,034,112 bytes with SHA-256
  `a610eed2f3fe22b33de32a6ffbf80afa95bc1becba1d8a2cbb0f081eba3d8a77`.
- VirtualBox VM `Clausis` booted that exact ISO through the branded UEFI GRUB
  menu to the complete branded GNOME live desktop. Evidence is stored as
  `dist/clausis-word-selection-vbox-grub.png` and
  `dist/clausis-word-selection-vbox-live.png`; ACPI shutdown completed within
  10 seconds to verified `VMState="poweroff"`.
- The boot and SquashFS checks prove packaging and live-system integration.
  Selecting words in a real microphone-driven application session remains an
  open end-to-end test.

## 2026-08-10 verified bounded AT-SPI adjacent-word deletion build

- Two confirmed parameterless actions delete exactly the previous or next
  Unicode word in a once-bound focused, non-protected editable AT-SPI entry,
  text, or document-text object. The shared word class includes alphanumeric
  characters, apostrophe, hyphen, and underscore.
- The adapter requires zero selections, inspectable protection attributes, a
  character count from 0 through 100,000, and an in-range caret. It derives the
  exact span through at most 256 one-character `getText` calls. The matching
  field edge is content-free and idempotent; a field containing no reachable
  word remains unchanged.
- Before mutation the complete NUL-free field is captured. Only
  `deleteText(start, end)` is invoked, with an exact shifted caret for backward
  deletion and unchanged caret for forward deletion. Complete expected content,
  caret, and zero selections are read back. Any rejection or mismatch restores
  and verifies complete previous content and caret without repeating the word.
- The router exposes 128 German/English command families. All 531 Python tests
  passed under Debian 13, including confirmation gating, exact Unicode spans,
  both caret calculations, content-free edges, unsafe-state denial, hard search
  limit, complete expected state, deliberate mismatch, and full rollback.
- A fresh full ISO build passed the complete repository verification chain.
  Direct read-only SquashFS inspection found the installed deletion method,
  search limit, full snapshot, exact delete span, complete post-state readback,
  restore path, both router/policy/confirmation/executor paths, and all 128
  command families.
- The exact tested ISO is 2,643,034,112 bytes with SHA-256
  `65c835e021db3a639023fd9c470d56282088022dab4682a5807e348a1f78e167`.
- VirtualBox VM `Clausis` booted that exact ISO through the branded UEFI GRUB
  menu to the complete branded GNOME live desktop. Evidence is stored as
  `dist/clausis-word-deletion-vbox-grub.png` and
  `dist/clausis-word-deletion-vbox-live.png`; ACPI shutdown completed within 10
  seconds to verified `VMState="poweroff"`.
- The boot and SquashFS checks prove packaging and live-system integration.
  Deleting words in a real microphone-driven application session remains an
  open end-to-end test.

## 2026-08-10 verified redacted AT-SPI adjacent-word replacement build

- Two confirmed typed actions replace exactly the previous or next Unicode
  word in a once-bound focused, non-protected editable AT-SPI entry, text, or
  document-text object with one printable dictated string of 1 to 500
  characters.
- Zero selections, inspectable protection attributes, a character count from 0
  through 100,000, and an in-range caret are required. The exact word span is
  derived through at most 256 one-character reads. The matching field edge is
  content-free and idempotent, and the complete result may not exceed 100,000
  characters.
- The adapter snapshots the complete NUL-free field, constructs and writes the
  complete expected content atomically, places the caret directly after the
  replacement, and requires exact full-content, caret, and zero-selection
  readback. Any rejection or mismatch restores and verifies complete previous
  content and caret.
- Neither old nor replacement content appears in confirmation or result. The
  request target becomes `[REDACTED: previous word replacement text]` or
  `[REDACTED: next word replacement text]` before the chained audit HMAC.
- The router exposes 130 German/English command families. All 540 Python tests
  passed under Debian 13, including typed confirmation, target validation,
  Unicode spans, both directions, exact caret placement, content-free edges,
  search/result limits, unsafe-state denial, mismatch, rollback, and audit
  redaction.
- A fresh full ISO build passed the complete repository verification chain.
  Direct read-only SquashFS inspection found the installed replacement method,
  all hard limits, atomic expected-content write, caret target, restore path,
  both audit markers, router/policy/confirmation/executor paths, and all 130
  command families.
- The exact tested ISO is 2,643,034,112 bytes with SHA-256
  `58c3276929404c91f4fa51572f1dfe00db64777aaad7095fc367c51a4621f21a`.
- VirtualBox VM `Clausis` booted that exact ISO through the branded UEFI GRUB
  menu to the complete branded GNOME live desktop. Evidence is stored as
  `dist/clausis-word-replacement-vbox-grub.png` and
  `dist/clausis-word-replacement-vbox-live.png`; ACPI shutdown completed within
  10 seconds to verified `VMState="poweroff"`.
- The boot and SquashFS checks prove packaging and live-system integration.
  Replacing adjacent words in a real microphone-driven application session
  remains an open end-to-end test.
## 2026-08-10 verified bounded AT-SPI current-line orientation build

- Added three deterministic German/English command families: confirmed reading
  of the current line and local movement to its exact start or end. The router
  now exposes 133 command families.
- The adapter binds only a focused `entry`, `text`, or `document text` object,
  rejects protected roles/attributes before content access, validates AT-SPI
  metadata, and derives newline boundaries using exact one-character reads.
  Lines above 1,000 characters fail closed.
- Line movement requires an empty selection, verifies the requested caret
  offset and zero selections, and restores the previous caret on mismatch.
  Confirmations never contain line content and the chained audit stores
  `[REDACTED: current line]` instead of the spoken value.
- All 544 Python tests passed under Debian 13. The Windows diagnostic run had
  only known POSIX-API and Windows symlink-permission errors; the target Debian
  run completed without failures.
- `scripts/verify_iso.sh` passed for checksum, BIOS/UEFI boot structures,
  SquashFS, Hermes, licenses, accessibility, Calamares target binding and the
  recovery-key module. A separate extraction check confirmed the installed
  line helper, exact `getText(index, index + 1)` reads, the 1,000-character
  bound, selection-free movement, rollback, all router/policy/confirmation/
  audit paths, and all 133 command patterns.
- Rebuilt ISO: `dist/clausis-0.4.1-amd64.iso`, 2,643,034,112 bytes, SHA-256
  `24e4f4b1d53821549faab20fdcf217fc89bf84f9118bb2d642ce4a47475dfbb1`.
- VirtualBox VM `Clausis` used the disposable dedicated
  `G:\VM\Clausis\Clausis.vdi`, mounted that exact ISO at `IDE-0-0`, reached
  the branded EFI/GRUB menu and the branded GNOME live overview, then shut down
  cleanly to `VMState="poweroff"`. Evidence:
  `dist/clausis-line-orientation-vbox-grub.png` and
  `dist/clausis-line-orientation-vbox-live.png`.
- A microphone-driven end-to-end check of these commands in multiple real
  third-party editors remains open; the feature is still technical-preview
  functionality and the repository's KI-Slop disclosure remains applicable.
## 2026-08-10 verified bounded AT-SPI current-line selection build

- Added the local reversible `select current line` family in German and
  English. The offline router now exposes 134 deterministic command families.
- The action reuses the bounded one-character current-line scan, requires an
  initially empty selection, excludes the newline and refuses an empty line.
  Success requires the exact `[start, end)` selection and the caret at `end`.
  Rejection, exception or mismatch removes partial selections and restores the
  original cursor before returning failure.
- All 550 Python tests passed under Debian 13, including exact-span,
  empty-line, existing-selection, mismatch rollback, semantic executor, router
  and policy coverage.
- The standard ISO verifier passed checksum, BIOS/UEFI, SquashFS, Hermes,
  licensing, speech model, accessibility, installer binding and recovery-key
  checks. A separate extracted-SquashFS verifier confirmed the installed line
  selection helper, empty-selection precondition, exact selection/readback,
  cursor rollback, action registration, router, low-risk policy and all 134
  command patterns.
- Rebuilt ISO: `dist/clausis-0.4.1-amd64.iso`, 2,643,034,112 bytes, SHA-256
  `e7960a1f2de970fd9724c42a4b62ecd93a968136b04276053b4930cdbc7bded5`.
- VirtualBox VM `Clausis` mounted that exact ISO at `IDE-0-0`, retained only the
  dedicated disposable `G:\VM\Clausis\Clausis.vdi` at `SATA-0-0`, reached the
  branded EFI/GRUB menu and branded GNOME live overview, and shut down cleanly
  to `VMState="poweroff"`. Evidence:
  `dist/clausis-line-selection-vbox-grub.png` and
  `dist/clausis-line-selection-vbox-live.png`.
- Microphone-driven selection inside multiple real third-party editors remains
  an open end-to-end test. The technical-preview and KI-Slop disclosures remain
  applicable.
## 2026-08-10 verified rollback-safe AT-SPI current-line deletion build

- Added the confirmed reversible `delete current line` family in German and
  English. The offline router now exposes 135 deterministic command families.
- The adapter requires the safe bounded current-line context and no existing
  selection. It refuses empty lines, removes a middle/first line with its
  following newline, a final line with its preceding newline, or the complete
  content when it is the only line.
- Success requires exact complete-text readback, the computed caret and zero
  selections. Rejection, exception or mismatch restores and verifies the prior
  full field, original caret and empty selection. Confirmation and result text
  contain no deleted content.
- All 557 Python tests passed under Debian 13, including middle, final and only
  line deletion, empty/selected-state rejection, forced mismatch rollback,
  broker confirmation gating, router, policy and canonical-summary coverage.
- The standard ISO verifier passed checksum, BIOS/UEFI, SquashFS, Hermes,
  licensing, speech model, accessibility, installer binding and recovery-key
  checks. A separate extracted-SquashFS verifier confirmed both delimiter
  branches, exact full-text result verification, restore path, action wiring,
  medium-risk policy, content-free confirmation and all 135 command patterns.
- Rebuilt ISO: `dist/clausis-0.4.1-amd64.iso`, 2,643,034,112 bytes, SHA-256
  `3e1fb7e04e6989cf9c56025be4e5ec3ce019fc5f496a799fa4e18ff2e06ce479`.
- VirtualBox VM `Clausis` mounted that exact ISO at `IDE-0-0`, retained only the
  dedicated disposable `G:\VM\Clausis\Clausis.vdi` at `SATA-0-0`, reached the
  branded EFI/GRUB menu and branded GNOME live overview, then shut down cleanly
  to `VMState="poweroff"`. Evidence:
  `dist/clausis-line-deletion-vbox-grub.png` and
  `dist/clausis-line-deletion-vbox-live.png`.
- A microphone-driven deletion in multiple real third-party editors remains an
  open end-to-end test. Technical-preview and KI-Slop disclosures remain in
  force.
## 2026-08-10 verified redacted AT-SPI current-line replacement build

- Added the confirmed reversible `replace current line with …` family in
  German and English. The offline router now exposes 136 deterministic command
  families.
- Replacement accepts exactly 1–500 printable dictated characters, requires a
  safe bounded nonempty current line and no selection, changes only `[start,
  end)`, and preserves surrounding newlines.
- Success requires exact full-field readback, a caret directly after the
  replacement and zero selections. Rejection, exception or mismatch restores
  and verifies the prior full text, original caret and empty selection. Old and
  new content are omitted from confirmation and result; the audit request uses
  `[REDACTED: current line replacement text]`.
- All 564 Python tests passed under Debian 13, including exact replacement and
  delimiter preservation, invalid/oversized/control input rejection, protected
  and selected-state rejection, forced mismatch rollback, broker confirmation,
  router, policy, summary and chained-audit redaction coverage.
- The standard ISO verifier passed checksum, BIOS/UEFI, SquashFS, Hermes,
  licensing, speech model, accessibility, installer binding and recovery-key
  checks. A separate extracted-SquashFS verifier confirmed the installed
  bounds, exact span construction, full readback, rollback, action wiring,
  policy, confirmation, audit marker and all 136 command patterns.
- Rebuilt ISO: `dist/clausis-0.4.1-amd64.iso`, 2,643,034,112 bytes, SHA-256
  `b69e248defe8bc752105d9705ce5570f48feccf471cbf1789ba7073f63303ad0`.
- VirtualBox VM `Clausis` mounted that exact ISO at `IDE-0-0`, retained only the
  dedicated disposable `G:\VM\Clausis\Clausis.vdi` at `SATA-0-0`, reached the
  branded EFI/GRUB menu and branded GNOME live overview, and shut down cleanly
  to `VMState="poweroff"`. Evidence:
  `dist/clausis-line-replacement-vbox-grub.png` and
  `dist/clausis-line-replacement-vbox-live.png`.
- Microphone-driven replacement in multiple real third-party editors remains
  an open end-to-end test. Technical-preview and KI-Slop disclosures remain in
  force.
## 2026-08-10 verified redacted AT-SPI line insertion build

- Added confirmed reversible insertion of one new line immediately above or
  below the bounded caret line in German and English. The offline router now
  exposes 138 deterministic command families.
- Both actions accept 1–500 printable characters without a newline, require no
  existing selection, preserve all old text and delimiters, and support an
  empty field without adding an artificial newline.
- Success requires exact full-field readback, the calculated caret behind the
  new line and zero selections. Any rejection, exception or mismatch restores
  and verifies the complete previous field and cursor. Confirmation/results do
  not echo the dictation; audit targets use direction-specific fixed markers.
- All 571 Python tests passed under Debian 13, including both directions, exact
  insertion/caret state, empty-field handling, invalid input, forced mismatch
  rollback, broker confirmation, router, policy, summaries and chained-audit
  redaction.
- The standard ISO verifier passed checksum, BIOS/UEFI, SquashFS, Hermes,
  licensing, speech model, accessibility, installer binding and recovery-key
  checks. A separate extracted-SquashFS verifier confirmed both insertion
  formulas, empty-field path, full readback, rollback, action/policy/audit
  wiring and all 138 command patterns.
- Rebuilt ISO: `dist/clausis-0.4.1-amd64.iso`, 2,643,034,112 bytes, SHA-256
  `caeb51cc0d386a57f3180b465a16c404b396ef0216b203626bd6873c3ba49758`.
- VirtualBox VM `Clausis` mounted that exact ISO at `IDE-0-0`, retained only the
  dedicated disposable `G:\VM\Clausis\Clausis.vdi` at `SATA-0-0`, reached the
  branded EFI/GRUB menu and branded GNOME live overview, and shut down cleanly
  to `VMState="poweroff"`. Evidence:
  `dist/clausis-line-insertion-vbox-grub.png` and
  `dist/clausis-line-insertion-vbox-live.png`.
- Microphone-driven insertion in multiple third-party editors remains an open
  end-to-end test. Technical-preview and KI-Slop disclosures remain in force.
## 2026-08-10 verified privacy-preserving AT-SPI line duplication build

- Added confirmed reversible duplication of the bounded current line directly
  above or below itself in German and English. The offline router now exposes
  140 deterministic command families.
- Both actions require a nonempty current line and no selection. The bound line
  content stays inside the adapter and is absent from request, confirmation,
  result and audit data.
- Success requires exact full-field readback, the calculated caret at the copied
  line and zero selections. Rejection, exception or mismatch restores and
  verifies the complete previous field, original caret and empty selection.
- All 578 Python tests passed under Debian 13, covering both directions, exact
  duplicated content and caret offsets, empty/selected/invalid-direction
  rejection, forced mismatch rollback, broker confirmation, router, policy and
  privacy-specific canonical summaries.
- The standard ISO verifier passed checksum, BIOS/UEFI, SquashFS, Hermes,
  licensing, speech model, accessibility, installer binding and recovery-key
  checks. A separate extracted-SquashFS verifier confirmed both duplication
  formulas, full readback, rollback, action/policy/confirmation wiring and all
  140 command patterns.
- Rebuilt ISO: `dist/clausis-0.4.1-amd64.iso`, 2,643,034,112 bytes, SHA-256
  `78518b3de56a60ccf817747ab478b355e4a14e5d99bb32c1706086e8a5218203`.
- VirtualBox VM `Clausis` mounted that exact ISO at `IDE-0-0`, retained only the
  dedicated disposable `G:\VM\Clausis\Clausis.vdi` at `SATA-0-0`, reached the
  branded EFI/GRUB menu and branded GNOME live overview, and shut down cleanly
  to `VMState="poweroff"`. Evidence:
  `dist/clausis-line-duplication-vbox-grub.png` and
  `dist/clausis-line-duplication-vbox-live.png`.
- Microphone-driven duplication in multiple third-party editors remains an open
  end-to-end test. Technical-preview and KI-Slop disclosures remain in force.
## 2026-08-10 verified bounded AT-SPI adjacent-line move build

- Added confirmed reversible movement of the current line up or down by an
  exact swap with one adjacent line in German and English. The offline router
  now exposes 142 deterministic command families.
- Current and adjacent lines are each bounded to 1,000 characters; document
  boundaries and existing selections fail closed. Neither line content leaves
  the adapter for request, confirmation, result or audit data.
- The caret retains its relative offset within the moved line. Success requires
  exact full-field readback, that calculated caret and zero selections; failure
  restores and verifies the complete previous field and cursor.
- All 585 Python tests passed under Debian 13, covering both swap directions,
  relative caret preservation, document boundaries, selected state, oversized
  neighbors, invalid direction, forced mismatch rollback, broker confirmation,
  router, policy and privacy summaries.
- The standard ISO verifier passed checksum, BIOS/UEFI, SquashFS, Hermes,
  licensing, speech model, accessibility, installer binding and recovery-key
  checks. A separate extracted-SquashFS verifier confirmed both adjacent-line
  calculations, 1,000-character bound, caret formulas, full readback, rollback,
  action/policy/confirmation wiring and all 142 command patterns.
- Rebuilt ISO: `dist/clausis-0.4.1-amd64.iso`, 2,643,034,112 bytes, SHA-256
  `fb9979efc2d20b8ee31ba162f33f429abc74fe99f34c24065814ba1bd9835879`.
- VirtualBox VM `Clausis` mounted that exact ISO at `IDE-0-0`, retained only the
  dedicated disposable `G:\VM\Clausis\Clausis.vdi` at `SATA-0-0`, reached the
  branded EFI/GRUB menu and a complete GNOME live session showing the Clausis
  setup dialog and visible `Clausis – KI-Hinweis`, then shut down cleanly to
  `VMState="poweroff"`. Evidence: `dist/clausis-line-move-vbox-grub.png` and
  `dist/clausis-line-move-vbox-live.png`.
- Microphone-driven line movement in multiple third-party editors remains an
  open end-to-end test. Technical-preview and KI-Slop disclosures remain in
  force.
## 2026-08-10 verified semantic Protocol/runtime separation build

- Removed an accidental stale concrete copy of the initial line-context,
  current-line read, line-caret and line-selection logic from the
  `SemanticDesktop` typing Protocol. The live behavior remains solely in
  `PyAtSpiDesktop`; no command semantics were removed.
- Added an AST regression test requiring every Protocol method body to be one
  ellipsis. It also leaves the private line-context helper and every public line
  runtime method uniquely defined in the concrete class.
- All 586 Python tests passed under Debian 13, including the new interface-body
  assertion and representative real one-character line reading and adjacent-line
  move regression tests. The router remains at 142 command families.
- The standard ISO verifier passed checksum, BIOS/UEFI, SquashFS, Hermes,
  licensing, speech model, accessibility, installer binding and recovery-key
  checks. A separate extracted-SquashFS AST verifier proved signatures-only
  `SemanticDesktop`, exactly one concrete private helper, exactly one of each
  current-line runtime method and all 142 command patterns.
- Rebuilt ISO: `dist/clausis-0.4.1-amd64.iso`, 2,643,034,112 bytes, SHA-256
  `3f549db23b6c7547bccda1b2a4bfe0434e5e2f4c43177a825067437fadb2272d`.
- VirtualBox VM `Clausis` mounted that exact ISO at `IDE-0-0`, retained only the
  dedicated disposable `G:\VM\Clausis\Clausis.vdi` at `SATA-0-0`, reached the
  branded EFI/GRUB menu and branded GNOME live overview, then shut down cleanly
  to `VMState="poweroff"`. Evidence:
  `dist/clausis-protocol-cleanup-vbox-grub.png` and
  `dist/clausis-protocol-cleanup-vbox-live.png`.
- This removes a maintainability and review hazard but does not close physical
  microphone or third-party-editor end-to-end gates. Technical-preview and
  KI-Slop disclosures remain in force.

## 2026-08-10 verified exact adjacent-line join build

- Added confirmed German/English commands to join the focused text line with
  its previous or next line. The operation removes exactly the adjacent newline,
  preserves the expected caret position, and exposes 144 deterministic command
  families without placing text content in confirmations or audit summaries.
- The semantic adapter rejects selections, document boundaries, unsupported
  directions, fields over 100,000 characters and adjacent lines over 1,000
  characters. It verifies the complete result and caret state, and restores the
  original text and caret if verification fails.
- All 593 Python tests passed under Debian 13, including exact delimiter and
  caret behavior, boundaries, selection rejection, length bounds, rollback,
  router, policy, confirmation and broker coverage.
- The standard ISO verifier passed checksum, BIOS/UEFI, SquashFS, Hermes,
  licensing, speech model, accessibility, installer binding and recovery-key
  checks. A separate extracted-SquashFS verifier confirmed both join directions,
  bounds, exact deletion, caret handling, rollback and all 144 command patterns.
- Rebuilt ISO: `dist/clausis-0.4.1-amd64.iso`, 2,643,034,112 bytes, SHA-256
  `4eb2c65790fca7170bc732f83ba5ca1bd68a533ab4490ba36d798fc448b7d617`.
- VirtualBox VM `Clausis` mounted that exact ISO at `IDE-0-0`, retained only the
  dedicated disposable `G:\VM\Clausis\Clausis.vdi` at `SATA-0-0`, reached the
  branded EFI/GRUB menu and branded GNOME live overview, then shut down cleanly
  to `VMState="poweroff"`. Evidence: `dist/clausis-line-join-vbox-grub.png` and
  `dist/clausis-line-join-vbox-live.png`.
- Physical microphone input and joining in multiple third-party editors remain
  open end-to-end tests. Technical-preview and KI-Slop disclosures remain in
  force.

## 2026-08-10 verified exact line split build

- Added a confirmed German/English command that splits the bounded current text
  line at the bound AT-SPI caret by inserting exactly one newline. It works at
  either line edge and in an empty field, exposing 145 deterministic command
  families without placing field content in confirmation, result or audit data.
- Protected fields, current lines over 1,000 characters, active selections and
  fields that would reach 100,000 characters fail closed. Complete text, the
  caret immediately after the new delimiter and zero selections are read back;
  a mismatch restores and verifies the entire previous field and caret.
- All 599 Python tests passed under Debian 13, including exact middle/start/end/
  empty-field insertion, selection rejection, mismatch rollback, executor,
  router, policy and content-free confirmation coverage.
- The standard ISO verifier passed checksum, BIOS/UEFI, SquashFS, Hermes,
  licensing, speech model, accessibility, installer binding and recovery-key
  checks. A separate extracted-SquashFS verifier confirmed exact insertion,
  caret advancement, full readback, rollback, action wiring and all 145 command
  patterns.
- Rebuilt ISO: `dist/clausis-0.4.1-amd64.iso`, 2,643,034,112 bytes, SHA-256
  `7206ed02998e0c99c774d78b22c4722a24cc908fc1d391b29aac930379f1cfd4`.
- VirtualBox VM `Clausis` mounted that exact ISO at `IDE-0-0`, retained only the
  dedicated disposable `G:\VM\Clausis\Clausis.vdi` at `SATA-0-0`, reached the
  branded EFI/GRUB menu and complete GNOME live session with the visible
  `Clausis – KI-Hinweis`, then shut down cleanly to `VMState="poweroff"`.
  Evidence: `dist/clausis-line-split-vbox-grub.png` and
  `dist/clausis-line-split-vbox-live.png`.
- Physical microphone input and splitting in multiple third-party editors remain
  open end-to-end tests. Technical-preview and KI-Slop disclosures remain in
  force.

## 2026-08-10 verified bounded current-line indentation build

- Added confirmed German/English commands to indent the bounded current line by
  exactly four spaces or outdent it by exactly one leading tab/up to four
  leading spaces. Unindented lines fail explicitly, and the router now exposes
  147 deterministic command families without externalizing line content.
- Both actions reject protected fields, active selections and line/field
  overflow. They preserve the logical caret position, verify complete text,
  exact caret and zero selections, and restore and verify the complete previous
  field and caret on any mismatch.
- All 606 Python tests passed under Debian 13, including exact four-space
  insertion, tab/two-space/four-space removal, caret-inside-indent behavior,
  selection/length/direction rejection, rollback, executor, router, policy and
  content-free confirmation coverage.
- The standard ISO verifier passed checksum, BIOS/UEFI, SquashFS, Hermes,
  licensing, speech model, accessibility, installer binding and recovery-key
  checks. A separate extracted-SquashFS verifier confirmed both exact mutation
  paths, caret formulas, full readback, rollback, wiring and all 147 patterns.
- Rebuilt ISO: `dist/clausis-0.4.1-amd64.iso`, 2,643,034,112 bytes, SHA-256
  `15ab7dbfc2a76bb3efa72596e00315d9c174c3414f419dcb7123361962a74f06`.
- VirtualBox VM `Clausis` mounted that exact ISO at `IDE-0-0`, retained only the
  dedicated disposable `G:\VM\Clausis\Clausis.vdi` at `SATA-0-0`, reached the
  branded EFI/GRUB menu and complete branded GNOME live overview, then shut down
  cleanly to `VMState="poweroff"`. Evidence:
  `dist/clausis-line-indent-vbox-grub.png` and
  `dist/clausis-line-indent-vbox-live.png`.
- Physical microphone input and indentation behavior across multiple third-party
  editors remain open end-to-end tests. Technical-preview and KI-Slop
  disclosures remain in force.

## 2026-08-10 verified Windows/WSL direct-build hardening

- Reproduced two failures in the documented `scripts/build_iso.sh` path from a
  Windows DrvFS checkout: CRLF made shell entry points non-executable, while
  DrvFS `0777` metadata made Debhelper execute declarative config files. After
  fixing those, CRLF package-list entries were also shown to reach APT as invalid
  package names.
- Added `.gitattributes` LF rules for Linux entry points and normalized all 25
  versioned executable text files. The container now detects and converts text
  files to LF in its native copied tree, resets files/directories to `0644`/
  `0755`, and restores `0755` only for an explicit allowlist of entry points.
  Binary assets are excluded by the text-file probe.
- A regression test checks the LF attributes, byte content of the central build
  entry points and the container normalization/mode logic. Shell syntax for 20
  shell entry points, a dry Make parse and all 607 Python tests passed under
  Debian 13.
- The unmodified documented command `/mnt/p/Programmieren/clausis/scripts/build_iso.sh`
  then completed directly against the Windows/WSL worktree without a temporary
  source copy. Its built-in standard verifier and a separate rerun both passed
  checksum, BIOS/UEFI, SquashFS, Hermes, licensing, speech-model, accessibility,
  installer-binding and recovery-key checks.
- Directly rebuilt ISO: `dist/clausis-0.4.1-amd64.iso`, 2,643,034,112 bytes,
  SHA-256 `240b9ba68a3b8057c9b387eb551c0cd6103a90962835f9f22f46e2a4ea758624`.
- VirtualBox VM `Clausis` mounted that exact ISO at `IDE-0-0`, retained only the
  dedicated disposable `G:\VM\Clausis\Clausis.vdi` at `SATA-0-0`, reached the
  branded EFI/GRUB menu and complete branded GNOME live overview, then shut down
  cleanly to `VMState="poweroff"`. Evidence:
  `dist/clausis-direct-build-vbox-grub.png` and
  `dist/clausis-direct-build-vbox-live.png`.
- This closes the reproducible Windows/WSL source-build failure; physical audio,
  installer persistence and third-party-editor microphone gates remain open.
  Technical-preview and KI-Slop disclosures remain in force.

## 2026-08-10 verified one-shot correction-dialog build

- Replaced the previous acknowledgement-only `Korrigieren` / `Correct that`
  behavior with a distinct local `CORRECTING` runtime state. It requests exactly
  one replacement command, stores no transcript, and dispatches that replacement
  once through the unchanged router, broker and optional already-consented
  fallback path.
- Repeat preserves and repeats only the content-free correction prompt; cancel
  and stop clear the slot; repeated correction requests do not nest; matched,
  unmatched and fallback replacement utterances all consume it. The prompt
  explicitly states that an already executed action is not automatically undone.
- All 611 Python tests passed under Debian 13, including replacement dispatch,
  one-shot consumption, repeat/cancel/stop behavior, non-nesting and optional
  fallback coverage. The router remains at 147 command families.
- The regular hardened `scripts/build_iso.sh` path completed directly from the
  Windows/WSL worktree. Its standard verifier passed checksum, BIOS/UEFI,
  SquashFS, Hermes, licensing, speech model, accessibility, installer binding
  and recovery-key checks. A separate extracted-SquashFS verifier confirmed the
  correction state, prompt, one-shot reset and all 147 command patterns.
- Rebuilt ISO: `dist/clausis-0.4.1-amd64.iso`, 2,643,034,112 bytes, SHA-256
  `027c8c737de36e8dff8fb1da1c37773dc1e1d863873d6bcedc8f54d1a1ea33b5`.
- VirtualBox VM `Clausis` mounted that exact ISO at `IDE-0-0`, retained only the
  dedicated disposable `G:\VM\Clausis\Clausis.vdi` at `SATA-0-0`, reached the
  branded EFI/GRUB menu and complete branded GNOME live overview, then shut down
  cleanly to `VMState="poweroff"`. Evidence:
  `dist/clausis-correction-slot-vbox-grub.png` and
  `dist/clausis-correction-slot-vbox-live.png`.
- This closes the acknowledgement-only correction-dialog gap. It does not undo
  completed actions and does not replace the still-open requirement for exact
  post-state verification across every mutating adapter. Technical-preview and
  KI-Slop disclosures remain in force.

## 2026-08-10 verified fail-closed semantic dry-run partition build

- Audited the semantic developer-dry-run gate and found 21 existing word, line,
  selection and caret mutations missing from its manually maintained mutation
  set. Those actions could reach the semantic adapter despite `dry_run=True`,
  even though their individual production adapters had separate verification.
- Replaced the incomplete mutation list with a 12-action explicit read-only
  allowlist; `SEMANTIC_MUTATIONS` is now derived as every other semantic action.
  The current partition is exact and disjoint: 90 total semantic actions equal
  12 read-only plus 78 mutations. Future semantic actions therefore default to
  dry-run blocked until deliberately classified as read-only.
- Four new tests prove complete/disjoint partitioning, block every mutation
  before adapter dispatch, retain read-only dispatch and pin the 21 previously
  omitted actions. All 615 Python tests passed under Debian 13.
- The regular hardened `scripts/build_iso.sh` path completed directly from the
  Windows/WSL worktree. Its standard verifier passed checksum, BIOS/UEFI,
  SquashFS, Hermes, licensing, speech model, accessibility, installer binding
  and recovery-key checks. A separate extracted-SquashFS Python import proved
  the exact 90/12/78 partition and all formerly omitted mutations.
- Rebuilt ISO: `dist/clausis-0.4.1-amd64.iso`, 2,643,034,112 bytes, SHA-256
  `d01cfd8727405d6ecb6cd8578cd3c0282c06d360538933159dc748f27ec820e4`.
- VirtualBox VM `Clausis` mounted that exact ISO at `IDE-0-0`, retained only the
  dedicated disposable `G:\VM\Clausis\Clausis.vdi` at `SATA-0-0`, reached the
  branded EFI/GRUB menu and complete branded GNOME live overview, then shut down
  cleanly to `VMState="poweroff"`. Evidence:
  `dist/clausis-dry-run-partition-vbox-grub.png` and
  `dist/clausis-dry-run-partition-vbox-live.png`.
- This closes the developer-dry-run classification hole. It does not claim that
  every production mutation has complete semantic post-state verification;
  that broader audit remains open. Technical-preview and KI-Slop disclosures
  remain in force.

## 2026-08-10 verified monotonic correction-slot expiry build

- Bounded the one-shot correction dialog with a monotonic 30-second default
  expiry. Configured TTLs must be numeric, finite and between 5 and 120 seconds;
  wall-clock changes cannot prolong or prematurely expire the slot.
- At or after the exact deadline, the first late utterance is discarded without
  router/broker/fallback execution and an explicit expiry notice is returned.
  A later fresh utterance is handled normally. Stop, cancel and a fresh
  correction request retain priority after expiry; repeat preserves the slot
  only while it is still live.
- Four new timing/priority tests cover exact-deadline discard, acceptance just
  before expiry, stop/cancel/restart priority and invalid TTLs. All 619 Python
  tests passed under Debian 13; the router remains at 147 command families.
- The regular hardened `scripts/build_iso.sh` path completed directly from the
  Windows/WSL worktree. Its standard verifier passed checksum, BIOS/UEFI,
  SquashFS, Hermes, licensing, speech model, accessibility, installer binding
  and recovery-key checks. A separate extracted-SquashFS runtime test exercised
  exact expiry, no broker call, fresh-command behavior, stop priority and TTL
  validation against the installed code.
- Rebuilt ISO: `dist/clausis-0.4.1-amd64.iso`, 2,643,034,112 bytes, SHA-256
  `91fd23d6910f708b23f29793a440560bfacbf565066bf51c4f79a7ddae34fc1a`.
- VirtualBox VM `Clausis` mounted that exact ISO at `IDE-0-0`, retained only the
  dedicated disposable `G:\VM\Clausis\Clausis.vdi` at `SATA-0-0`, reached the
  branded EFI/GRUB menu and complete branded GNOME live overview, then shut down
  cleanly to `VMState="poweroff"`. Evidence:
  `dist/clausis-correction-ttl-vbox-grub.png` and
  `dist/clausis-correction-ttl-vbox-live.png`.
- This closes indefinite correction-slot lifetime. Physical microphone timing,
  interruption and background-speech behavior remain open hardware/session
  gates. Technical-preview and KI-Slop disclosures remain in force.

## 2026-08-10 verified correction wake-gate synchronization build

- Synchronized the local wake controller with the bounded one-shot correction
  dialog: its original monotonic 30-second deadline remains reachable even
  though the ordinary wake window is 25 seconds.
- The wake gate stays open for the remaining correction TTL plus a fixed
  five-second expiry grace. Repeat cannot move that absolute boundary. The
  first late replacement is discarded by the runtime and closes the gate;
  an explicit sleep command also clears the pending correction slot.
- The complete host suite passed: 625 tests. A separate verifier extracted the
  installed Clausis package from the ISO SquashFS and exercised an accepted
  replacement at 29.5 seconds, expiry within the grace interval, subsequent
  gate closure, the five-second constant and all 147 router patterns.
- Built `dist/clausis-0.4.1-amd64.iso` through the regular WSL/live-build path.
  Size: 2,643,034,112 bytes. SHA-256:
  `2bb2fc54651163dc0736333c2e586f94f6680e4d03198c8de7ef1f94c2ddd23c`.
- The build verifier passed its BIOS/UEFI, SquashFS, package, installer,
  recovery and embedded-code checks.
- VirtualBox `Clausis` used EFI, the exact new ISO on IDE 0-0 and only its
  dedicated `G:\VM\Clausis\Clausis.vdi` on SATA 0-0. The branded GRUB menu and
  complete GNOME live desktop were visually verified in
  `dist/clausis-correction-gate-vbox-grub.png` and
  `dist/clausis-correction-gate-vbox-live.png`; the VM then reached poweroff.
- Physical microphone timing, echo cancellation and real interruption latency
  remain open hardware tests. Technical-preview and KI-Slop disclosures remain
  in force.

## 2026-08-10 verified local trusted-audio abort build

- Added an exact, locally evaluated spoken abort to every protected recording
  stage: trusted challenge phrase, PIN, installer recovery-key readback and
  final destructive-installation phrase.
- Complete German and English abort utterances such as `Abbrechen`, `Stopp
  Clausis` and `Cancel` fail closed. Substrings and ambiguous bare `stopp` do
  not trigger. An abort deletes the temporary WAV, is acknowledged locally and
  prevents capability issuance or continuation to partitioning.
- The complete host suite passed: 629 tests. The installed package was also
  extracted from the final ISO SquashFS and independently exercised for exact
  matching, rejection of ambiguous phrases, temporary-recording deletion,
  trusted-confirmation abort and installer abort before challenge issuance.
- Built `dist/clausis-0.4.1-amd64.iso` through the regular WSL/live-build path.
  Size: 2,643,034,112 bytes. SHA-256:
  `0c70093a5759b6dae20a68077f2a43f31f289392b535cd31eef4ad7ec1eb7e4d`.
- The build verifier passed its BIOS/UEFI, SquashFS, package, installer,
  recovery and embedded-code checks.
- VirtualBox `Clausis` used EFI, the exact new ISO on IDE 0-0 and only its
  dedicated `G:\VM\Clausis\Clausis.vdi` on SATA 0-0. The branded GRUB menu and
  complete GNOME live desktop were visually verified in
  `dist/clausis-trusted-abort-vbox-grub.png` and
  `dist/clausis-trusted-abort-vbox-live.png`; the VM then reached poweroff.
- This closes the deterministic software abort gap, not physical microphone
  isolation, voice-clone/replay detection or hardware timing. Those production
  gates remain open. Technical-preview and KI-Slop disclosures remain in force.

## 2026-08-10 verified exact window-cycle post-state build

- Hardened semantic next/previous-window navigation. It now requires exactly
  one visible active starting window instead of guessing, calculates the
  adjacent target and accepts success only when that target becomes the sole
  active window.
- A rejected action, exception or inconsistent AT-SPI post-state attempts to
  restore the previous window focus and verifies the restoration. Failure to
  restore is reported distinctly and remains fail-closed.
- The complete host suite passed: 633 tests. The installed package was also
  extracted from the final ISO SquashFS and exercised independently for an
  exact successful transition, rejection of an ambiguous starting state and
  verified rollback after a mismatched post-state.
- Built `dist/clausis-0.4.1-amd64.iso` through the regular WSL/live-build path.
  Size: 2,643,034,112 bytes. SHA-256:
  `a2dba65d2136638300f4275d7dbe4f4e4bd828cfcac379026ca794037936e5e6`.
- The build verifier passed its BIOS/UEFI, SquashFS, package, installer,
  recovery and embedded-code checks.
- VirtualBox `Clausis` used EFI, the exact new ISO on IDE 0-0 and only its
  dedicated `G:\VM\Clausis\Clausis.vdi` on SATA 0-0. The branded GRUB menu and
  complete GNOME live desktop were visually verified in
  `dist/clausis-window-cycle-vbox-grub.png` and
  `dist/clausis-window-cycle-vbox-live.png`; the VM then reached poweroff.
- This closes the window-cycle post-state gap, not the remaining post-state
  work for every other semantic mutation or physical microphone/hardware
  validation. Technical-preview and KI-Slop disclosures remain in force.

## 2026-08-11 verified exact control-focus post-state build

- Hardened next/previous-control navigation inside the active window. It now
  rejects multiple focused controls, calculates the bounded target and accepts
  success only when exactly that target is focused in the freshly bound control
  list.
- A rejected focus request, exception or partial AT-SPI post-state verifies an
  already unchanged prior state or actively restores and verifies the previous
  focus. An un-restorable partial state is reported distinctly and fails closed.
  A valid initially focusless control list still selects the correct endpoint.
- The complete host suite passed: 637 tests. The installed package was also
  extracted from the final ISO SquashFS and independently exercised for exact
  success, rejection of multiple focus, rollback after partial focus and a
  separately reported rollback failure.
- Built `dist/clausis-0.4.1-amd64.iso` through the regular WSL/live-build path.
  Size: 2,643,034,112 bytes. SHA-256:
  `2ceaab18e87d39aab947ac470f44d8d3efae730d7c28014c6d14539b45591295`.
- The build verifier passed its BIOS/UEFI, SquashFS, package, installer,
  recovery and embedded-code checks.
- VirtualBox `Clausis` used EFI, the exact new ISO on IDE 0-0 and only its
  dedicated `G:\VM\Clausis\Clausis.vdi` on SATA 0-0. The branded GRUB menu and
  complete GNOME live desktop were visually verified in
  `dist/clausis-control-focus-vbox-grub.png` and
  `dist/clausis-control-focus-vbox-live.png`; the VM then reached poweroff.
- This closes the control-focus-cycle post-state gap, not the remaining
  post-state work for other semantic mutations or physical hardware validation.
  Technical-preview and KI-Slop disclosures remain in force.

## 2026-08-11 verified numeric AT-SPI rollback build

- Hardened exact named slider and spin-button mutations. Idempotent target
  values no longer invoke the widget; successful writes still require bounded
  numeric readback against the declared range and increment.
- Rejection, mismatch and an exception after partial mutation now restore the
  previously read value and verify it numerically with the same tolerance. An
  un-restorable partial value is reported distinctly and remains fail-closed.
- The complete host suite passed: 641 tests. The installed package was also
  extracted from the final ISO SquashFS and independently exercised for slider
  and spin-button rollback after exceptional partial mutation plus a separately
  reported failed numeric rollback.
- Built `dist/clausis-0.4.1-amd64.iso` through the regular WSL/live-build path.
  Size: 2,643,034,112 bytes. SHA-256:
  `983459fa01e027564d25938e13b1562102a4b6d7007ea1a64b3e2d87c4351b02`.
- The build verifier passed its BIOS/UEFI, SquashFS, package, installer,
  recovery and embedded-code checks.
- VirtualBox `Clausis` used EFI, the exact new ISO on IDE 0-0 and only its
  dedicated `G:\VM\Clausis\Clausis.vdi` on SATA 0-0. The branded GRUB menu and
  complete GNOME live desktop were visually verified in
  `dist/clausis-numeric-rollback-vbox-grub.png` and
  `dist/clausis-numeric-rollback-vbox-live.png`; the VM then reached poweroff.
- This closes the slider/spin-button rollback-verification gap, not the
  remaining post-state work for other semantic mutations or physical hardware
  validation. Technical-preview and KI-Slop disclosures remain in force.

## 2026-08-11 verified checked-state rollback build

- Hardened exact named check-box and switch mutations. The Toggle action's
  boolean result and the observed Checked state must both confirm success;
  idempotent requests still avoid invoking the widget.
- Rejection, mismatch and an exception after partial toggling now restore and
  verify the previously observed Checked state. An un-restorable partial toggle
  is reported distinctly and remains fail-closed.
- The complete host suite passed: 644 tests. The installed package was also
  extracted from the final ISO SquashFS and independently exercised for
  check-box and switch rollback after exceptional partial toggling plus a
  separately reported failed Checked-state rollback.
- Built `dist/clausis-0.4.1-amd64.iso` through the regular WSL/live-build path.
  Size: 2,643,034,112 bytes. SHA-256:
  `0bbe4ba154cf94ade1d6b2dc69330e1faa11cbdb30e49f4ddfdb8aaa4e26afb4`.
- The build verifier passed its BIOS/UEFI, SquashFS, package, installer,
  recovery and embedded-code checks.
- VirtualBox `Clausis` used EFI, the exact new ISO on IDE 0-0 and only its
  dedicated `G:\VM\Clausis\Clausis.vdi` on SATA 0-0. The branded GRUB menu and
  complete GNOME live desktop were visually verified in
  `dist/clausis-toggle-rollback-vbox-grub.png` and
  `dist/clausis-toggle-rollback-vbox-live.png`.
- The first ACPI shutdown attempt remained running after 60 seconds. A second
  ACPI request reached `VMState="poweroff"` after 36 seconds. This timing
  variance remains recorded rather than being treated as a shutdown guarantee.
- This closes the check-box/switch rollback-verification gap, not radio-button
  rollback verification, other semantic mutation post-states or physical
  hardware validation. Technical-preview and KI-Slop disclosures remain in
  force.

## 2026-08-11 verified radio-group rollback build

- Hardened exact named radio-button selection. More than one Checked starting
  control is rejected without mutation; an already uniquely selected target is
  idempotent. Successful selection requires the complete bound radio-group
  bitmap to contain exactly the requested target.
- Rejection, bitmap mismatch and an exception after partial selection now
  restore and verify the prior unique group bitmap. An absent prior selection
  cannot be fabricated during rollback, and an un-restorable group is reported
  distinctly and remains fail-closed.
- The complete host suite passed: 647 tests. The installed package was also
  extracted from the final ISO SquashFS and independently exercised for
  exceptional partial-selection rollback, rejection of a multiply Checked
  starting group and a separately reported failed group rollback.
- Built `dist/clausis-0.4.1-amd64.iso` through the regular WSL/live-build path.
  Size: 2,643,034,112 bytes. SHA-256:
  `5f83409767530d76029d2608828c4e7547da782fea34f99a2291e58db0d23531`.
- The build verifier passed its BIOS/UEFI, SquashFS, package, installer,
  recovery and embedded-code checks.
- VirtualBox `Clausis` used EFI, the exact new ISO on IDE 0-0 and only its
  dedicated `G:\VM\Clausis\Clausis.vdi` on SATA 0-0. The branded GRUB menu and
  complete GNOME live desktop, accessible setup dialog and local AI notice were
  visually verified in `dist/clausis-radio-rollback-vbox-grub.png` and
  `dist/clausis-radio-rollback-vbox-live.png`; the first ACPI request then
  reached poweroff.
- This closes the radio-group rollback-verification gap, not the remaining
  semantic mutation post-states or physical hardware validation.
  Technical-preview and KI-Slop disclosures remain in force.

## 2026-08-11 verified tree-state rollback build

- Hardened exact named tree-item Expand and Collapse mutations. The semantic
  action's boolean result and observed Expanded state must both confirm success.
- Rejection, mismatch and an exception after partial expansion/collapse now use
  the exact inverse action to restore and verify the prior Expanded state. An
  un-restorable partial tree state is reported distinctly and remains
  fail-closed.
- The complete host suite passed: 650 tests. The installed package was also
  extracted from the final ISO SquashFS and independently exercised for Expand
  and Collapse rollback after exceptional partial mutation plus a separately
  reported failed Expanded-state rollback.
- Built `dist/clausis-0.4.1-amd64.iso` through the regular WSL/live-build path.
  Size: 2,643,034,112 bytes. SHA-256:
  `3d8efb57d1a99839770e6fd4c18917515fbf5d9460ab9b80162ab4f4d24fb292`.
- The build verifier passed its BIOS/UEFI, SquashFS, package, installer,
  recovery and embedded-code checks.
- VirtualBox `Clausis` used EFI, the exact new ISO on IDE 0-0 and only its
  dedicated `G:\VM\Clausis\Clausis.vdi` on SATA 0-0. The branded GRUB menu and
  complete GNOME live desktop were visually verified in
  `dist/clausis-tree-rollback-vbox-grub.png` and
  `dist/clausis-tree-rollback-vbox-live.png`.
- The first ACPI shutdown attempt remained running after 60 seconds; a second
  request reached poweroff after 34 seconds. Because the same two-request
  pattern occurred in the checked-state build, delayed live-session ACPI
  shutdown is now a reproducible open VirtualBox/GNOME latency issue rather
  than a one-off variance.
- This closes the tree-state rollback-verification gap, not other semantic
  mutation post-states, the shutdown-latency issue or physical hardware
  validation. Technical-preview and KI-Slop disclosures remain in force.

## 2026-08-11 verified VirtualBox ACPI fallback build

- Reproduced the intermittent one-shot shutdown failure over three fresh boots
  of the prior ISO: the first two requests reached poweroff after 12.2 and 10.2
  seconds, while the third remained on the complete GNOME desktop after 50.8
  seconds.
- Before altering that failed guest, its journal proved that
  `systemd-logind` received `Power key pressed short`. `systemd-inhibit --list`
  showed `gsd-media-keys` owning the blocking low-level `handle-power-key`
  inhibitor, but no shutdown request followed.
- Added `acpid` plus an independent `button/power.*` handler. The handler calls
  `systemctl poweroff` only after `systemd-detect-virt --vm --quiet` succeeds,
  so normal physical-machine GNOME power-button handling is unchanged.
- The complete Debian/Linux suite passed: 651 tests. The ISO verifier now also
  requires the installed `acpid` package, event rule and VM handler, and checks
  the handler's virtualization guard and poweroff action directly in the final
  SquashFS.
- Built `dist/clausis-0.4.1-amd64.iso` through the regular WSL/live-build path.
  Size: 2,643,034,112 bytes. SHA-256:
  `04fba3e346b413d7cfcd1b2bd9deada541d8ce8f73afc8899a2f99ead4ba587e`.
- VirtualBox `Clausis` used EFI, the exact new ISO on IDE 0-0 and only its
  dedicated `G:\VM\Clausis\Clausis.vdi` on SATA 0-0. Three consecutive fresh
  boots reached `VMState="poweroff"` after exactly one ACPI request in 9.3,
  11.4 and 13.5 seconds. The complete live desktop is recorded in
  `dist/clausis-acpi-fallback-vbox-live-1.png` and
  `dist/clausis-acpi-fallback-vbox-live-3.png`.
- This closes the repeated VirtualBox live-session one-shot ACPI gate, not
  physical power-button, persistent-install or hardware endurance validation.
  Technical-preview and KI-Slop disclosures remain in force.

## 2026-08-11 verified AT-SPI activation rebind build

- Removed the generic control activator's unsafe action-index-zero fallback.
  Numbered, named and permission-control activation now re-queries the already
  bound node immediately before invocation and accepts only an explicit Click,
  Press, Activate, Toggle or Open action. An unrelated sole action and an
  action index that changed after discovery fail closed without invocation.
- Added regression coverage for an unrecognized Delete action, a reordered
  action list and a formerly safe action that became unsafe. The complete
  Debian/Linux suite passed: 654 tests.
- Built `dist/clausis-0.4.1-amd64.iso` through the regular WSL/live-build path.
  Size: 2,643,034,112 bytes. SHA-256:
  `b48ddbc69c79d855230de561dc3be3156933f7e6c49a84533f2058059323b9cb`.
- The final ISO verifier passed BIOS/UEFI, SquashFS, package, installer,
  recovery and embedded-code checks. It additionally extracted the installed
  `gnome_adapter.py` and required both the fresh action-name binding and the
  fail-closed no-permitted-action path.
- VirtualBox `Clausis` used EFI, 16,384 MiB RAM and 16 CPUs, with the exact new
  ISO on IDE 0-0 and only its dedicated `G:\VM\Clausis\Clausis.vdi` on SATA
  0-0. The branded GRUB menu and complete GNOME live desktop were visually
  verified in `dist/clausis-action-rebind-vbox-grub.png` and
  `dist/clausis-action-rebind-vbox-live.png`. Exactly one ACPI request reached
  `VMState="poweroff"` after 14.5 seconds.
- This closes the stale/unrecognized generic activation-vector gap, not
  application-specific irreversible-action post-state, persistent-install or
  physical-hardware validation. Technical-preview and KI-Slop disclosures
  remain in force.

## 2026-08-11 verified unique navigation and Shell action build

- Hardened semantic Back navigation to require exactly one matching action
  across the complete bound active window. The selected node's actions are
  re-read immediately before invocation; a stale Back action that becomes an
  unrelated action fails closed without calling either action object.
- Window-manager operations now reject duplicate matching localized aliases
  instead of selecting the first index. GNOME Shell operations first collect
  every valid matching control across all accessible GNOME Shell roots and
  require one globally unique target before using the shared fresh action
  rebind boundary.
- Added regression tests for a duplicate window action, unique Back action,
  duplicate Back controls, a stale Back-to-Delete change and duplicate GNOME
  Shell targets. The complete Debian/Linux suite passed: 659 tests.
- Built `dist/clausis-0.4.1-amd64.iso` through the regular WSL/live-build path.
  Size: 2,643,034,112 bytes. SHA-256:
  `02e0bf1e4b9b086e4d1f95d03ad51fcb2e8a171766f76b5baef4eac7ea1eca8a`.
- The final ISO verifier passed BIOS/UEFI, SquashFS, package, installer,
  recovery and embedded-code checks. It additionally required the installed
  adapter's ambiguous Back, window-action and GNOME-Shell-target rejection
  paths.
- VirtualBox `Clausis` used EFI, 16,384 MiB RAM and 16 CPUs, with the exact new
  ISO on IDE 0-0 and only its dedicated `G:\VM\Clausis\Clausis.vdi` on SATA
  0-0. The branded GRUB menu and complete GNOME live desktop were visually
  verified in `dist/clausis-unique-actions-vbox-grub.png` and
  `dist/clausis-unique-actions-vbox-live.png`. Exactly one ACPI request reached
  `VMState="poweroff"` after 9.3 seconds.
- This closes first-match ambiguity for semantic Back, active-window manager
  and GNOME Shell actions, not application-specific irreversible-action
  post-state, persistent-install or physical-hardware validation. Technical-
  preview and KI-Slop disclosures remain in force.

## 2026-08-11 verified strict active-window binding build

- Removed the adapter's implicit first-Showing-window fallback from every
  state read and mutation that requires an active window. Those operations now
  require exactly one AT-SPI Active frame, dialog or window; zero or multiple
  Active candidates fail closed before target discovery.
- Split non-mutating orientation onto a separate binding path. It prefers one
  unique Active window and may use a Showing fallback only when there is no
  Active window and exactly one Showing candidate. Multiple Active or Showing
  candidates are rejected rather than resolved by traversal order.
- Added regression tests proving that work never falls back to a merely
  Showing window, orientation accepts one unique Showing fallback, and both
  paths reject multiple Active windows. The complete Debian/Linux suite passed:
  662 tests.
- Built `dist/clausis-0.4.1-amd64.iso` through the regular WSL/live-build path.
  Size: 2,643,034,112 bytes. SHA-256:
  `92d540082ad8d76f77b01737a9fba297e0041f9564b71d440c2c8665c149b064`.
- The final ISO verifier passed BIOS/UEFI, SquashFS, package, installer,
  recovery and embedded-code checks. It additionally required the installed
  adapter's strict Active-only work binding, unique orientation fallback and
  ambiguous-active rejection paths.
- VirtualBox `Clausis` used EFI, 16,384 MiB RAM and 16 CPUs, with the exact new
  ISO on IDE 0-0 and only its dedicated `G:\VM\Clausis\Clausis.vdi` on SATA
  0-0. The branded GRUB menu and complete GNOME live desktop were visually
  verified in `dist/clausis-active-window-binding-vbox-grub.png` and
  `dist/clausis-active-window-binding-vbox-live.png`.
- A first one-request shutdown observation remained host-reported as Running
  beyond the 30-second timing gate but later powered off without another ACPI
  request. A fresh diagnostic boot then proved the VM fallback end to end:
  `acpi_listen` received `button/power PBTN 00000080 00000000`, the root
  broadcast immediately announced poweroff, and the same single request
  reached ACPI S5 and `VMState="poweroff"`. The event evidence is recorded in
  `dist/acpi-listen-diagnostic-result.png`; no second request was sent.
- This closes unsafe Showing-window target fallback, not application-specific
  irreversible-action post-state, persistent-install or physical-hardware
  validation. Technical-preview and KI-Slop disclosures remain in force.

## 2026-08-11 verified named-focus rollback build

- Hardened named focus changes so they require exactly one focused starting
  node in the bound active window. Missing or ambiguous starting focus now
  fails closed before the requested target is touched.
- Successful focus changes are accepted only when the complete window focus
  bitmap contains the requested target and no other focused node. Rejected,
  mismatched and exception-after-partial-mutation outcomes restore the exact
  previous focus; a failed restoration is reported separately.
- Added regressions for missing and ambiguous starting focus, rollback after a
  partially mutating exception, and explicit failed-rollback reporting. The
  complete Debian/Linux suite passed: 665 tests.
- Built `dist/clausis-0.4.1-amd64.iso` through the regular WSL/live-build path.
  Size: 2,643,034,112 bytes. SHA-256:
  `6119d0f8230b96a44af2de4ff22bd67da0dd540cffb8f4e442ab1712d2238b7f`.
- The final ISO verifier passed BIOS/UEFI, SquashFS, package, installer,
  recovery and embedded-code checks. It additionally required the installed
  adapter's unique starting-focus rejection, complete focus-bitmap check and
  named-focus failure path.
- VirtualBox `Clausis` used EFI, 16,384 MiB RAM and 16 CPUs, with the exact new
  ISO on IDE 0-0 and only its dedicated `G:\VM\Clausis\Clausis.vdi` on SATA
  0-0. The branded GRUB menu and complete GNOME live desktop were visually
  verified in `dist/clausis-named-focus-rollback-vbox-grub.png` and
  `dist/clausis-named-focus-rollback-vbox-live.png`. Exactly one ACPI request
  reached `VMState="poweroff"` after 9.3 seconds.
- Overall implementation status is estimated at 72 percent: the bootable live
  system, core voice/desktop integration, semantic safety and rollback layers,
  installer/recovery scaffolding and repeatable ISO/VM verification are in
  place. Remaining work includes broader application-specific accessibility
  coverage, persistent-install and upgrade edge cases, destructive-action
  end-to-end state validation, longer soak/regression runs, physical hardware
  coverage, compliance closure and release polish.
- This closes unsafe named-focus partial mutation, not those broader release
  gates. Technical-preview and KI-Slop disclosures remain in force.

## 2026-08-11 verified named-activation rebinding build

- Closed the discovery-to-invocation race for exact named controls. Immediately
  before `doAction()`, the adapter now requires the active AT-SPI window to be
  the identical object originally bound during discovery and requires the same
  target to occur exactly once in that window's freshly enumerated operable
  controls. A dialog switch, removed control, or newly hidden/insensitive target
  therefore fails before mutation.
- Added regressions that switch the active window or remove the target between
  discovery and invocation and prove that the action receives no call. The
  complete Debian/Linux suite passed: 667 tests.
- Built `dist/clausis-0.4.1-amd64.iso` through the regular WSL/live-build path.
  Size: 2,643,034,112 bytes. SHA-256:
  `590561c5967db5ab309cf1f28197ee49e0d5573d0309fa833aba93d8223b187b`.
- The final ISO verifier passed BIOS/UEFI, SquashFS, package, installer,
  recovery and embedded-code checks. It additionally required the installed
  adapter's active-window identity check and both fail-closed rebinding errors.
- VirtualBox `Clausis` used EFI, 16,384 MiB RAM and 16 CPUs, with the exact new
  ISO on IDE 0-0 and only its dedicated `G:\VM\Clausis\Clausis.vdi` on SATA
  0-0. The branded GRUB menu and complete GNOME live desktop were visually
  verified in `dist/clausis-named-activation-rebind-vbox-grub.png` and
  `dist/clausis-named-activation-rebind-vbox-live.png`. Exactly one ACPI request
  reached `VMState="poweroff"` after 8.3 seconds.
- The rounded overall estimate remains 72 percent: this closes one important
  stale-binding mutation path but does not materially reduce the larger open
  persistent-install, upgrade, third-party-application, soak, physical-hardware,
  compliance and release-polish work. Technical-preview and KI-Slop disclosures
  remain in force.

## 2026-08-11 verified numbered-activation snapshot build

- Bound every spoken control number to the identical active AT-SPI window and
  the complete ordered identity snapshot of operable controls. Immediately
  before mutation, any added, removed or reordered control now invalidates the
  number instead of silently retargeting it.
- Added adapter regressions for an unchanged successful snapshot, active-window
  replacement, control insertion, removal and reordering. Every mismatch proves
  that no candidate action was invoked. The complete Debian/Linux suite passed:
  670 tests.
- Built `dist/clausis-0.4.1-amd64.iso` through the regular WSL/live-build path.
  Size: 2,643,034,112 bytes. SHA-256:
  `33263a4b39d1915a63e7595caca10c604656cb1f65b161633082ca742ebfa0fb`.
- The final ISO verifier passed BIOS/UEFI, SquashFS, package, installer,
  recovery and embedded-code checks. It additionally required the installed
  adapter's numbered active-window rejection, changed-numbering rejection and
  ordered node-identity comparison.
- VirtualBox `Clausis` used EFI, 16,384 MiB RAM and 16 CPUs, with the exact new
  ISO on IDE 0-0 and only its dedicated `G:\VM\Clausis\Clausis.vdi` on SATA
  0-0. The branded GRUB menu and complete GNOME live desktop were visually
  verified in `dist/clausis-numbered-activation-rebind-vbox-grub.png` and
  `dist/clausis-numbered-activation-rebind-vbox-live.png`. The harmless Shift
  key was used only to clear GNOME's idle dim overlay before the final desktop
  capture. Exactly one ACPI request reached `VMState="poweroff"` after 9.3
  seconds.
- The rounded overall estimate remains 72 percent: numbered-control retargeting
  is closed, while persistent-install, upgrade, third-party-application, soak,
  physical-hardware, compliance and release-polish work remains open.
  Technical-preview and KI-Slop disclosures remain in force.

## 2026-08-11 verified permission-pair rebinding build

- Re-ran exact permission-pair recognition immediately before mutation on the
  identical active AT-SPI dialog. Both Allow and Deny controls must retain their
  original object identities and remain the sole recognized decision group; a
  replaced dialog or same-label replacement pair invokes neither side.
- Added regressions for an active-dialog swap and a complete same-label pair
  replacement, and updated the existing successful-path regression to prove two
  window bindings followed by exactly one intended action. The first complete
  run exposed that stale one-read expectation; after correcting it, the full
  Debian/Linux suite passed: 672 tests.
- Built `dist/clausis-0.4.1-amd64.iso` through the regular WSL/live-build path.
  Size: 2,643,034,112 bytes. SHA-256:
  `e060cfa47f1b7e93f253ee9ac383ea992597ebba691bb87b9a1cf4a582626464`.
- The ISO itself built successfully. Its first final verifier invocation failed
  only because a newly added grep literal used nested single quotes and was
  truncated by the surrounding shell command. After changing that literal to
  double quotes, the complete verifier was rerun against the same unchanged ISO
  and passed BIOS/UEFI, SquashFS, package, installer, recovery and embedded-code
  checks, including dialog identity, pair identity and both fail-closed errors.
- VirtualBox `Clausis` used EFI, 16,384 MiB RAM and 16 CPUs, with the exact new
  ISO on IDE 0-0 and only its dedicated `G:\VM\Clausis\Clausis.vdi` on SATA
  0-0. The branded GRUB menu and complete GNOME live desktop were visually
  verified in `dist/clausis-permission-pair-rebind-vbox-grub.png` and
  `dist/clausis-permission-pair-rebind-vbox-live.png`. Exactly one ACPI request
  reached `VMState="poweroff"` after 12.4 seconds.
- The rounded overall estimate remains 72 percent: permission-dialog
  retargeting is closed, while persistent-install, upgrade, third-party-
  application, soak, physical-hardware, compliance and release-polish work
  remains open. Technical-preview and KI-Slop disclosures remain in force.

## 2026-08-11 verified menu-target rebinding build

- Rebound semantic menu activation immediately before mutation to the identical
  active AT-SPI window, focused menu/menu-bar container and exact direct target
  object. A window switch, closed or changed menu, or same-label replacement
  item now fails before `doAction()`.
- Added regressions for an active-window swap and a same-label target in a newly
  focused replacement menu; both prove that neither old nor new action is
  invoked. The complete Debian/Linux suite passed: 674 tests.
- Built `dist/clausis-0.4.1-amd64.iso` through the regular WSL/live-build path.
  Size: 2,643,034,112 bytes. SHA-256:
  `e46f8f6ea788295ed8edde2fba07994f15a2f769a35242463856522ffa8f0cc7`.
- The final ISO verifier passed BIOS/UEFI, SquashFS, package, installer,
  recovery and embedded-code checks. It additionally required the installed
  adapter's menu-window rejection, changed menu/target rejection and exact
  container/target identity comparison.
- VirtualBox `Clausis` used EFI, 16,384 MiB RAM and 16 CPUs, with the exact new
  ISO on IDE 0-0 and only its dedicated `G:\VM\Clausis\Clausis.vdi` on SATA
  0-0. The branded GRUB menu and complete GNOME live desktop were visually
  verified in `dist/clausis-menu-rebind-vbox-grub.png` and
  `dist/clausis-menu-rebind-vbox-live.png`.
- Exactly one ACPI request was sent. The VM remained host-reported as Running
  after the initial 31-second gate and a further 45-second observation; no
  second request was sent. The same request then reached
  `VMState="poweroff"` at approximately 79 seconds total. Shutdown therefore
  succeeded but missed the normal timing gate and remains soak-test evidence,
  not a latency pass.
- The rounded overall estimate remains 72 percent: stale menu retargeting is
  closed, while persistent-install, upgrade, broader third-party-application,
  ACPI latency/soak, physical-hardware, compliance and release-polish work
  remains open. Technical-preview and KI-Slop disclosures remain in force.

## 2026-08-11 non-blocking VirtualBox ACPI handler build

- Changed the VM-only `acpid` fallback to execute
  `systemctl --no-block poweroff`, releasing acpid as soon as the systemd
  transaction is queued. The exact handler form is covered by the live-image
  test and ISO verifier. The complete Debian/Linux suite passed: 674 tests.
- Built `dist/clausis-0.4.1-amd64.iso` through the regular WSL/live-build path.
  Size: 2,643,034,112 bytes. SHA-256:
  `d1d7634e494a4a9085b491f985c4c96d9fd29089288d3e6e9e5698fecff1fa22`.
  The final ISO verifier passed BIOS/UEFI, SquashFS, package, installer,
  recovery and embedded-code checks, including the exact no-block handler.
- VirtualBox `Clausis` used EFI, 16,384 MiB RAM and 16 CPUs, with the exact new
  ISO on IDE 0-0, its dedicated `G:\VM\Clausis\Clausis.vdi` on SATA 0-0 and
  UART disabled. The branded GRUB menu and complete GNOME live desktop were
  visually verified in `dist/clausis-acpi-noblock-vbox-grub.png` and
  `dist/clausis-acpi-noblock-vbox-live.png`.
- Three independent fresh boots each received exactly one ACPI request. Runs 1
  and 2 reached verified `VMState="poweroff"` after 10.1 and 12.3 seconds. Run
  3 remained `VMState="running"` after the 150.1-second gate and a further
  120.8-second observation; no second request was sent. Its preserved host log
  is `dist/clausis-acpi-noblock-run3-vbox.log`, and the disposable VM was then
  powered off explicitly.
- The three-run gate therefore failed at 2/3. The no-block change is retained
  as bounded handler hardening, but it does not close the intermittent ACPI
  reliability defect. Overall progress remains approximately 72 percent;
  persistent installation, upgrade, application breadth, ACPI soak/root-cause,
  hardware, compliance and release polish remain open. Technical-preview and
  KI-Slop disclosures remain in force.

## 2026-08-11 official Hermes icon and readiness-gated VBox build

- Replaced the Clausis logo on `clausis-hermes-chat.desktop` with
  `Icon=hermes-agent`. The live-build hook installs the official
  `apps/desktop/assets/icon.png` directly from the exact pinned Hermes Agent
  commit as `/usr/share/pixmaps/hermes-agent.png`; no unrelated or generated
  substitute artwork is used.
- Added `scripts/vbox_acpi_smoke.ps1`. It refuses a running VM, unexpected ISO
  or VDI, and enabled UART; checks rendered purple Clausis branding in both the
  GRUB and complete-desktop screenshots; sends exactly one ACPI request; saves
  timeout evidence; and forcibly cleans up only the dedicated test VM on
  failure. This replaced unreliable fixed waits and resolution-only checks.
- The complete Debian/Linux suite passed: 675 tests. The final ISO verifier
  passed BIOS/UEFI, SquashFS, package, installer, recovery and embedded-code
  checks, including the installed Hermes pixmap and exact desktop icon name.
- Final `dist/clausis-0.4.1-amd64.iso` size: 2,643,034,112 bytes. SHA-256:
  `8b24a1ad9100c1dab44eba1e106fc53bbe5e1317f8c721f5be454b37a839f6f5`.
- The official black-and-white Hermes/N icon was visually verified in GNOME's
  `Hermes Agent` search result at
  `dist/clausis-hermes-icon-vbox-launcher.png`. GRUB evidence is
  `dist/clausis-hermes-icon-vbox-grub.png`.
- The final readiness-gated smoke run observed branded GRUB after 101.9
  seconds, the fully rendered Clausis desktop after another 95.7 seconds, and
  verified `VMState="poweroff"` 13.9 seconds after exactly one ACPI request.
  Earlier instrumented runs proved that VirtualBox can accept a host request
  without producing a guest power-key event at either logind or active acpid;
  ACPI reliability therefore remains open despite this passing final run.
- Overall progress remains approximately 72 percent. Persistent installation,
  upgrades, application breadth, ACPI soak/host-event reliability, physical
  hardware, compliance and release polish remain open. Technical-preview and
  KI-Slop disclosures remain in force.

## 2026-08-11 confirmed file-dialog completion build

- Added two deterministic German/English command families for explicitly
  accepting or cancelling a recognized file chooser. The offline router now
  exposes 149 command families. Selection, filename entry, path entry and
  folder navigation still never commit the dialog implicitly.
- The semantic adapter accepts only a recognized file-chooser role or exact
  localized chooser title with exactly one Open/Save/Select/Choose control and
  exactly one Cancel control. Both controls must expose one exact Click, Press
  or Activate action. The active dialog, recognized role/title, full pair and
  both concrete object identities are rebound immediately before invocation;
  generic dialogs, duplicates, action ambiguity, window swaps and same-label
  replacement controls fail without calling either action.
- Router, policy, confirmation broker, executor, real-adapter rebinding and
  dry-run derivation are covered by the complete Debian/Linux suite: 682 tests
  passed. The final ISO verifier also extracted the installed adapter and
  confirmed the new method and all fail-closed rebinding markers.
- Built `dist/clausis-0.4.1-amd64.iso` through the regular WSL/live-build path.
  Size: 2,643,034,112 bytes. SHA-256:
  `d80c357a90ab41c52fceac7392f3ccc16b9af585458bf5bea36c20a9e862f59d`.
- VirtualBox `Clausis` used EFI, 16,384 MiB RAM and 16 CPUs, the exact new ISO
  on IDE 0-0, its dedicated VDI on SATA 0-0 and UART disabled. Rendered branded
  GRUB and the complete live desktop were verified in
  `dist/clausis-file-dialog-vbox-grub.png` and
  `dist/clausis-file-dialog-vbox-live.png`. The readiness-gated run observed
  GRUB after 142.5 seconds, the complete desktop after another 136.3 seconds,
  and reached verified poweroff 17.8 seconds after exactly one ACPI request.
- Overall progress is now approximately 73 percent: the previously missing
  semantic file-dialog completion step is closed. Persistent installation,
  upgrades, broader portal/application coverage, ACPI soak reliability,
  physical hardware, compliance and release polish remain open.
  Technical-preview and KI-Slop disclosures remain in force.

## 2026-08-11 confirmed standard-dialog completion build

- Added two deterministic German/English command families for accepting or
  cancelling a recognized conventional standard dialog. The offline router now
  exposes 151 command families; both directions remain confirmed,
  non-reversible high-risk operations.
- The semantic adapter accepts exactly one OK/Cancel, Yes/No or
  Confirm/Cancel pair in an active dialog or alert. File choosers, permission
  pairs, missing controls, duplicate groups and ambiguous actions are rejected.
  The active window, complete pair and both concrete control identities are
  rebound immediately before the single invocation, so window or control
  replacement fails closed.
- Router, policy, broker, executor and real-adapter boundary/rebinding behavior
  are covered by the complete Debian/Linux suite: 689 tests passed. The final
  ISO verifier extracted the installed adapter and confirmed the method and
  both fail-closed rebinding markers.
- Built `dist/clausis-0.4.1-amd64.iso` through the regular WSL/live-build path.
  Size: 2,643,034,112 bytes. SHA-256:
  `fe4e36d329a98de6533f00f3c38d5667766db68a0684581cc4c7084b40d85f49`.
- VirtualBox `Clausis` used EFI, 16,384 MiB RAM and 16 CPUs, the exact new ISO
  on IDE 0-0, its dedicated VDI on SATA 0-0 and UART disabled. Rendered branded
  GRUB and the complete live desktop were verified in
  `dist/clausis-standard-dialog-vbox-grub.png` and
  `dist/clausis-standard-dialog-vbox-live.png`. The readiness-gated run observed
  GRUB after 143.9 seconds, the complete desktop after another 137.7 seconds,
  and reached verified poweroff 13.3 seconds after exactly one ACPI request.
- Overall progress is now approximately 74 percent: conventional standard
  dialog completion is closed. Persistent installation, upgrades, broader
  portal/application coverage, ACPI soak reliability, physical hardware,
  compliance and release polish remain open. Technical-preview and KI-Slop
  disclosures remain in force.

## 2026-08-11 explicit retry/apply standard-dialog build

- Added two distinct deterministic German/English command families for
  Retry/Wiederholen and Apply/Anwenden in conventional standard dialogs. The
  offline router now exposes 153 command families. Both remain confirmed,
  non-reversible high-risk operations and neither can substitute for Accept or
  for the other positive intent.
- The adapter recognizes exactly one Retry/Cancel or Apply/Cancel pair in
  addition to the existing conventional pairs. Cancellation still requires one
  complete unambiguous group. A mismatched positive intent, duplicate group,
  file chooser, permission pair, ambiguous action, window replacement or
  concrete-control replacement fails without invocation.
- The complete Debian/Linux suite passed: 691 tests. Focused adapter, router,
  policy and live-image tests also passed. The final ISO verifier extracted the
  installed adapter and confirmed both localized decision-pair definitions and
  the existing fail-closed rebinding markers.
- Built `dist/clausis-0.4.1-amd64.iso` through the regular WSL/live-build path.
  Size: 2,643,034,112 bytes. SHA-256:
  `3909bdb7d19ab6b06ef4c0c33df40a959c6cc598a1550e8f0f3c65fbe91b77fa`.
- VirtualBox `Clausis` used EFI, 16,384 MiB RAM and 16 CPUs, the exact new ISO
  on IDE 0-0, its dedicated VDI on SATA 0-0 and UART disabled. Rendered branded
  GRUB and the complete live desktop were verified in
  `dist/clausis-retry-apply-dialog-vbox-grub.png` and
  `dist/clausis-retry-apply-dialog-vbox-live.png`. The readiness-gated run
  observed GRUB after 144.6 seconds, the complete desktop after another 138.5
  seconds, and reached verified poweroff 17.2 seconds after exactly one ACPI
  request.
- Overall progress remains approximately 74 percent. This increment broadens a
  previously implemented standard-dialog boundary but does not by itself close
  another major release stage. Persistent installation, upgrades, broader
  portal/application coverage, ACPI soak reliability, physical hardware,
  compliance and release polish remain open. Technical-preview and KI-Slop
  disclosures remain in force.

## 2026-08-11 bounded standard-dialog reading build

- Added one confirmed German/English command family for reading an active
  regular dialog, bringing the offline router to 154 deterministic families.
  Existing orientation only reported application, title and focus; the new
  action supplies the previously missing static dialog message.
- The AT-SPI adapter accepts only dialog/alert roles and only unique names from
  static label, paragraph and description roles. It never queries editable
  text, rejects file choosers, skips protected nodes and fails closed above 20
  messages or 1,000 total characters rather than speaking a partial result.
  The complete spoken result is removed from the signed audit log.
- The complete Debian/Linux suite passed: 696 tests. Focused audit, router,
  policy and live-image tests also passed. The final ISO verifier extracted the
  installed adapter and confirmed the reader plus its hard size-limit marker.
- Built `dist/clausis-0.4.1-amd64.iso` through the regular WSL/live-build path.
  Size: 2,643,034,112 bytes. SHA-256:
  `90cad5b8eef3677006b5a0b12641326e7268745a178db2ffe972a1a1f44f65f1`.
- VirtualBox `Clausis` used EFI, 16,384 MiB RAM and 16 CPUs, the exact new ISO
  on IDE 0-0, its dedicated VDI on SATA 0-0 and UART disabled. Rendered branded
  GRUB and the complete live desktop were verified in
  `dist/clausis-dialog-read-vbox-grub.png` and
  `dist/clausis-dialog-read-vbox-live.png`. The readiness-gated run observed
  GRUB after 128.2 seconds, the complete desktop after another 122.0 seconds,
  and reached verified poweroff 13.4 seconds after exactly one ACPI request.
  A transient `showvminfo` console-object race printed after poweroff; an
  independent read two seconds later confirmed poweroff and exact mappings.
  The smoke helper now retries that bounded host-side read and suppresses only
  the transient native error before failing after ten unsuccessful attempts.
- A second boot exercised the hardened helper with the same ISO and no native
  race output. It observed GRUB after 149.7 seconds, the complete desktop after
  another 143.6 seconds and verified poweroff 15.6 seconds after its single
  ACPI request. Evidence is stored as
  `dist/clausis-dialog-read-vbox-retry-check-grub.png` and
  `dist/clausis-dialog-read-vbox-retry-check-live.png`.
- Overall progress is now approximately 75 percent: safe spoken access to
  static standard-dialog content is closed. Persistent installation, upgrades,
  broader portal/application coverage, ACPI soak reliability, physical
  hardware, compliance and release polish remain open. Technical-preview and
  KI-Slop disclosures remain in force.

## 2026-08-11 close-only standard-dialog build

- Added a distinct confirmed German/English command family for closing a
  close-only regular dialog, bringing the offline router to 155 deterministic
  families. It is separate from normal window closing and remains a
  non-reversible high-risk action.
- The adapter requires the complete actionable surface to contain exactly one
  control named Close, Schließen or Dismiss with exactly one Click, Press or
  Activate action. File choosers, decision pairs, permission prompts, extra
  controls and ambiguous actions are rejected. The active dialog and concrete
  close control are rebound immediately before invocation; object replacement
  fails without calling either old or new control.
- The complete Debian/Linux suite passed: 701 tests. Focused standard-dialog,
  router, policy and live-image tests also passed. The final ISO verifier
  extracted the installed adapter and confirmed the dismiss method plus its
  fail-closed concrete-control replacement marker.
- Built `dist/clausis-0.4.1-amd64.iso` through the regular WSL/live-build path.
  Size: 2,643,034,112 bytes. SHA-256:
  `a332503d3e564635b0adbdb2a5ba98e128a7e593bdfdb1fe05a21a6dbb346352`.
- VirtualBox `Clausis` used EFI, 16,384 MiB RAM and 16 CPUs, the exact new ISO
  on IDE 0-0, its dedicated VDI on SATA 0-0 and UART disabled. Rendered branded
  GRUB and the complete live desktop were verified in
  `dist/clausis-dialog-dismiss-vbox-grub.png` and
  `dist/clausis-dialog-dismiss-vbox-live.png`. The readiness-gated run observed
  GRUB after 159.8 seconds, the complete desktop after another 153.6 seconds,
  and reached verified poweroff 16.6 seconds after exactly one ACPI request.
- Overall progress remains approximately 75 percent. This closes another
  standard-dialog subcase but not a complete additional release stage.
  Persistent installation, upgrades, broader portal/application coverage,
  ACPI soak reliability, physical hardware, compliance and release polish
  remain open. Technical-preview and KI-Slop disclosures remain in force.

## 2026-08-11 bounded GNOME Shell notification-reading build

- Added one confirmed German/English command family for reading currently
  visible notifications, bringing the offline router to 156 deterministic
  families. Opening the notification center remains a separate semantic Shell
  mutation; reading never toggles or activates the panel.
- The adapter requires exactly one accessible GNOME Shell application and
  accepts only Showing nodes with the exact AT-SPI `notification` role plus
  static descendants. Calendar labels, editable roles and protected nodes are
  excluded. More than 20 notifications, 40 unique messages or 2,000 characters
  fail closed, and the complete spoken result is removed from the signed audit.
- Corrected the explicit semantic read-only allowlist to include the existing
  standard-dialog reader as well as the new notification reader. Both now reach
  the semantic adapter in developer dry-run while all unlisted future actions
  continue to default to blocked mutations. A partition-invariant test names
  both readers explicitly.
- The complete Debian/Linux suite passed: 706 tests. Focused notification,
  standard-dialog, semantic-partition, audit, router, policy and live-image
  tests also passed. The final ISO verifier extracted the installed adapter and
  confirmed the notification method plus its hard text-limit marker.
- Built `dist/clausis-0.4.1-amd64.iso` through the regular WSL/live-build path.
  Size: 2,643,034,112 bytes. SHA-256:
  `50b49aab1fb27a18e5bca61247291da13df83e991c87c59e6bfc591b644fb225`.
- VirtualBox `Clausis` used EFI, 16,384 MiB RAM and 16 CPUs, the exact new ISO
  on IDE 0-0, its dedicated VDI on SATA 0-0 and UART disabled. Rendered branded
  GRUB and the complete live desktop were verified in
  `dist/clausis-notification-read-vbox-grub.png` and
  `dist/clausis-notification-read-vbox-live.png`. The readiness-gated run
  observed GRUB after 129.2 seconds, the complete desktop after another 123.1
  seconds and reached verified poweroff 11.7 seconds after exactly one ACPI
  request.
- Overall progress is now approximately 76 percent: bounded spoken access to
  visible GNOME Shell notifications is closed. Persistent installation,
  upgrades, broader portal/application coverage, ACPI soak reliability,
  physical hardware, compliance and release polish remain open.
  Technical-preview and KI-Slop disclosures remain in force.

## 2026-08-11 numbered notification-dismissal build

- Numbered the visible notification-object summaries and added one distinct
  confirmed German/English command family for dismissing a number, bringing the
  offline router to 157 deterministic families. A notification with entirely
  protected content retains its index through a fixed non-sensitive placeholder
  so the spoken and actionable snapshots cannot drift.
- The non-reversible high-risk action carries only an integer from 1 through 20
  and no notification title. Immediately before mutation it rebinds the same
  GNOME Shell object and the complete ordered identity list of all Showing
  notification-role objects. Reordering, addition, removal or replacement
  fails without invocation. The bound target must expose exactly one Dismiss or
  Close action; Activate or ambiguous action sets are rejected.
- The complete Debian/Linux suite passed: 710 tests. Focused notification,
  semantic-partition, router, policy and live-image tests also passed. The final
  ISO verifier extracted the installed adapter and confirmed the dismissal
  method plus its fail-closed full-order replacement marker.
- Built `dist/clausis-0.4.1-amd64.iso` through the regular WSL/live-build path.
  Size: 2,643,034,112 bytes. SHA-256:
  `3822eedb3a9ac04174517c79f84d8000314a9f2d461400db7e80f6b6339902b5`.
- VirtualBox `Clausis` used EFI, 16,384 MiB RAM and 16 CPUs, the exact new ISO
  on IDE 0-0, its dedicated VDI on SATA 0-0 and UART disabled. Rendered branded
  GRUB and the complete live desktop were verified in
  `dist/clausis-notification-dismiss-vbox-grub.png` and
  `dist/clausis-notification-dismiss-vbox-live.png`. The readiness-gated run
  observed GRUB after 128.9 seconds, the complete desktop after another 122.7
  seconds and reached verified poweroff 11.1 seconds after exactly one ACPI
  request.
- Overall progress remains approximately 76 percent. This adds safe mutation
  to the completed notification-reading slice but does not close another whole
  release stage. Persistent installation, upgrades, broader portal/application
  coverage, ACPI soak reliability, physical hardware, compliance and release
  polish remain open. Technical-preview and KI-Slop disclosures remain in
  force.

## 2026-08-11 verified notification-dismissal post-state build

- Hardened numbered notification dismissal so a successful Dismiss or Close
  invocation alone is no longer reported as success. The adapter polls for up
  to two seconds and requires the same GNOME Shell object plus the exact
  original ordered notification identity list with only the selected object
  removed.
- An unchanged notification list or any foreign addition, removal, replacement
  or reordering now produces an explicit unconfirmed-post-state failure. The
  action remains correctly classified as non-reversible, so the implementation
  makes no rollback claim after an invoked dismissal.
- The complete Debian/Linux suite passed: 711 tests. Focused notification and
  live-image checks also passed, and the final ISO verifier confirmed the new
  post-state failure marker in the installed adapter.
- Built `dist/clausis-0.4.1-amd64.iso` through the regular WSL/live-build path.
  Size: 2,643,034,112 bytes. SHA-256:
  `b57dd1085bdbd78d7f79db2d859ac906102ddb15b25ece219ff35555d88840ed`.
- VirtualBox `Clausis` used EFI, 16,384 MiB RAM and 16 CPUs, the exact new ISO
  on IDE 0-0, its dedicated VDI on SATA 0-0 and UART disabled. Rendered branded
  GRUB and the complete live desktop were verified in
  `dist/clausis-notification-poststate-vbox-grub.png` and
  `dist/clausis-notification-poststate-vbox-live.png`. The readiness-gated run
  observed GRUB after 106.7 seconds, the complete desktop after another 100.6
  seconds and reached verified poweroff 10.7 seconds after exactly one ACPI
  request.
- Overall progress remains approximately 76 percent. This hardens the existing
  notification-dismissal slice rather than closing another complete release
  stage. Persistent installation, upgrades, broader portal/application
  coverage, ACPI soak reliability, physical hardware, compliance and release
  polish remain open. Technical-preview and KI-Slop disclosures remain in
  force.

## 2026-08-11 verified close-only dialog post-state build

- Hardened the distinct close-only standard-dialog action so an accepted
  Click, Press or Activate invocation alone is no longer reported as success.
  The adapter first binds the complete ordered top-level window identities of
  the same application, rebinds that full list with the active dialog and
  concrete control immediately before mutation, then polls for up to two
  seconds after invocation.
- Success requires that exact original order with only the bound dialog
  removed. An unchanged list, another addition, removal or replacement, or an
  unreadable application object produces an explicit unconfirmed-post-state
  failure. This non-reversible action makes no rollback claim after invocation.
- The complete Debian/Linux suite passed: 713 tests. Focused close-only-dialog
  tests and shell syntax checks passed. The final ISO verifier extracted the
  installed adapter and confirmed both the failure marker and exact identity-
  subtraction implementation marker.
- Built `dist/clausis-0.4.1-amd64.iso` through the regular WSL/live-build path.
  Size: 2,643,034,112 bytes. SHA-256:
  `7abfbc8832e60b8997c8ff78ef77bbc1cc801f9e6bf393a2c989bb3d102862a9`.
- VirtualBox `Clausis` used EFI, 16,384 MiB RAM and 16 CPUs, the exact new ISO
  on IDE 0-0, its dedicated VDI on SATA 0-0 and UART disabled. Visual inspection
  confirmed branded GRUB and the complete GNOME live desktop in
  `dist/clausis-dialog-rebind-retry-vbox-grub.png` and
  `dist/clausis-dialog-rebind-retry-vbox-live.png`. The readiness-gated run
  observed GRUB after 119.3 seconds, the complete desktop after another 113.2
  seconds and reached verified poweroff 11.4 seconds after exactly one ACPI
  request.
- The first run of this exact ISO also reached poweroff and produced both
  branded screenshots, but its host harness hit VirtualBox 7.2's transient
  `VBOX_E_INVALID_OBJECT_STATE` during the final `showvminfo`. The bounded
  retry now catches the native PowerShell error as intended; the complete
  repeated run above passed and is the release evidence.
- Overall progress remains approximately 76 percent. This hardens an existing
  standard-dialog slice rather than closing another complete release stage.
  Persistent installation, upgrades, broader portal/application coverage,
  ACPI soak reliability, physical hardware, compliance and release polish
  remain open. Technical-preview and KI-Slop disclosures remain in force.

## 2026-08-11 verified permission-dialog post-state and offline model-cache build

- Hardened permission Allow and Deny so the adapter binds the same application,
  active dialog, complete ordered top-level window identity list and exact
  decision-control pair immediately before invocation. Success now requires the
  exact original order with only the selected dialog removed within two seconds.
- An unchanged, unreadable or otherwise changed application window list produces
  an explicit unconfirmed-post-state failure. The non-reversible action makes no
  rollback claim after invocation.
- The complete Debian/Linux suite passed: 716 tests. Focused permission-dialog
  and live-image checks plus shell syntax checks passed. The final ISO verifier
  confirmed the installed permission guards and the pinned speech-model files.
- Two online build attempts could not resolve `huggingface.co`; neither
  overwrote the previously verified ISO. The pinned Faster Whisper base model
  was recovered from that verified image into the ignored build cache. A
  tracked SHA-256 manifest now verifies all four required files before builder
  copy, inside the chroot and again by extraction from the completed ISO. A
  download remains available only when the cache is absent or invalid.
- Built `dist/clausis-0.4.1-amd64.iso` through the regular WSL/live-build path.
  Size: 2,643,034,112 bytes. SHA-256:
  `01ea573b5116eb808b5b9e081d2fac4e39f83a52ddb6ca862077a0165f19fe86`.
- VirtualBox `Clausis` used EFI, 16,384 MiB RAM and 16 CPUs, the exact new ISO
  on IDE 0-0, its dedicated disposable VDI on SATA 0-0 and UART disabled.
  Visual inspection confirmed branded GRUB and the complete GNOME live desktop,
  including the Hermes Agent launcher with its matching icon, in
  `dist/clausis-permission-offline-vbox-grub.png` and
  `dist/clausis-permission-offline-vbox-live.png`. The readiness-gated run
  observed GRUB after 105.0 seconds, the complete desktop after another 98.8
  seconds and reached verified poweroff 10.4 seconds after exactly one ACPI
  request.
- Overall progress is approximately 77 percent. This closes the permission-
  dialog post-state hardening slice and makes the pinned offline speech model
  reproducibly verifiable. Persistent installation, upgrades, broader portal
  and application coverage, ACPI soak reliability, physical hardware,
  compliance and release polish remain open. Technical-preview and KI-Slop
  disclosures remain in force.

## 2026-08-11 verified file-chooser post-state build

- Hardened confirmed file-chooser Accept and Cancel so the adapter binds the
  same application, complete ordered top-level window identity list, active
  chooser and exact accept/cancel control pair immediately before invocation.
- Success now requires the exact original application-window order with only
  that chooser removed within two seconds. An unchanged chooser, unreadable
  state, foreign addition, removal, replacement or reordering produces an
  explicit unconfirmed-post-state failure. This non-reversible action makes no
  rollback claim after invocation.
- The complete Debian/Linux suite passed: 718 tests. Focused file-chooser tests
  and shell syntax checks passed. The final ISO verifier extracted the adapter
  from SquashFS and confirmed both new fail-closed markers, along with the
  pinned speech-model manifest and all existing media gates.
- The first unprivileged build invocation stopped before mutation because the
  WSL user lacked access to the root-owned Docker socket. The regular builder
  then ran through that same socket as WSL root. Its calling terminal timed out
  while the container continued; the container exited successfully, and the
  complete external ISO verifier was therefore run separately against the
  resulting medium and passed.
- Built `dist/clausis-0.4.1-amd64.iso` through the regular WSL/live-build path.
  Size: 2,643,034,112 bytes. SHA-256:
  `5739f5a0adf602bfce7bf6487c0fda4de3013b42fa88f43a9bd0a6110ae6efa0`.
- VirtualBox `Clausis` used EFI, 16,384 MiB RAM and 16 CPUs, the exact new ISO
  on IDE 0-0, its dedicated disposable VDI on SATA 0-0 and UART disabled.
  Visual inspection confirmed branded GRUB and the complete GNOME live desktop,
  including the Hermes Agent launcher with its matching icon, in
  `dist/clausis-file-dialog-vbox-grub.png` and
  `dist/clausis-file-dialog-vbox-live.png`. The readiness-gated run observed
  GRUB after 118.2 seconds, the complete desktop after another 112.0 seconds
  and reached verified poweroff 13.2 seconds after exactly one ACPI request.
- Overall progress remains approximately 77 percent. This hardens the existing
  file-portal commit slice rather than closing another complete release stage.
  Persistent installation, upgrades, broader portal/application coverage,
  ACPI soak reliability, physical hardware, compliance and release polish
  remain open. Technical-preview and KI-Slop disclosures remain in force.

## 2026-08-11 verified standard-dialog decision post-state build

- Hardened confirmed OK, Yes, Confirm, Retry, Apply and Cancel/No decisions so
  the adapter binds the same application, complete ordered top-level window
  identity list, active regular dialog and exact decision-control pair at the
  final mutation boundary.
- Success now requires the exact original application-window order with only
  that dialog removed within two seconds. An unchanged dialog, unreadable
  application state or any foreign addition, removal, replacement or reordering
  produces an explicit unconfirmed-post-state failure. The non-reversible action
  makes no rollback claim after invocation.
- The complete Debian/Linux suite passed: 720 tests. Eight focused
  standard-dialog tests and shell syntax checks passed. The final ISO verifier
  extracted the installed adapter from SquashFS and confirmed both new markers,
  the speech-model manifest and all existing release gates.
- The regular WSL-root build used the root-owned Docker socket. Its calling
  terminal reached its ten-minute output limit while the one builder container
  continued normally. That container completed live-build successfully and
  exited with status zero; the complete external ISO verifier was then run
  separately against the resulting medium and passed.
- Built `dist/clausis-0.4.1-amd64.iso` through the regular WSL/live-build path.
  Size: 2,643,034,112 bytes. SHA-256:
  `301ea054411ccdca752ad5b766542b25fb6e652b747cca4176b247b094a5c12b`.
- VirtualBox `Clausis` used EFI, 16,384 MiB RAM and 16 CPUs, the exact new ISO
  on IDE 0-0, its dedicated disposable VDI on SATA 0-0 and UART disabled.
  Visual inspection confirmed branded GRUB and the complete GNOME live desktop,
  including the Hermes Agent launcher with its matching icon, in
  `dist/clausis-standard-dialog-vbox-grub.png` and
  `dist/clausis-standard-dialog-vbox-live.png`. The readiness-gated run observed
  GRUB after 138.4 seconds, the complete desktop after another 132.2 seconds
  and reached verified poweroff 13.8 seconds after exactly one ACPI request.
- Overall progress remains approximately 77 percent. This hardens another
  existing standard-dialog portal slice rather than closing an entire release
  stage. Persistent installation, upgrades, broader portal/application
  coverage, ACPI soak reliability, physical hardware, compliance and release
  polish remain open. Technical-preview and KI-Slop disclosures remain in
  force.

## 2026-08-11 five-run readiness-gated VirtualBox ACPI soak

- Added `scripts/vbox_acpi_soak.ps1`, a bounded 2-to-20-run orchestrator around
  the existing single-run readiness gate. Every iteration independently refuses
  a running VM, unexpected ISO/VDI mapping or enabled UART through the delegated
  smoke harness, then requires rendered Clausis GRUB, the complete desktop and
  poweroff after exactly one ACPI request.
- The orchestrator hashes the ISO once, rejects any per-run hash mismatch,
  stops on the first failure and writes a JSON summary in `finally`, including
  partial completion and min/max poweroff latency. Per-run evidence prefixes
  prevent a later boot from reusing earlier screenshots.
- The initial live execution exposed a harness-only scalar handling error:
  PowerShell's single `PSCustomObject` result had no usable `.Count` property.
  The wrapper therefore reported 0/5 after the underlying first smoke had
  already powered off cleanly. It now materializes `@($result)`, requires
  exactly one element and then binds that element; syntax and the focused
  regression test passed before the clean retry.
- The complete Debian/Linux suite passed: 721 tests. This is a host-side release
  harness change and does not alter the already verified guest image, so no
  redundant ISO rebuild was performed. The tested ISO remained exactly
  `301ea054411ccdca752ad5b766542b25fb6e652b747cca4176b247b094a5c12b`,
  size 2,643,034,112 bytes.
- The clean series in `dist/clausis-acpi-soak-301ea054-retry-summary.json`
  passed 5/5 fresh boots. Runs 1 through 5 reached branded GRUB after 109.6,
  113.3, 111.1, 111.9 and 113.7 seconds; the complete desktop after another
  103.4, 107.2, 104.9, 105.8 and 107.6 seconds; and verified poweroff after
  11.0, 11.6, 9.4, 13.7 and 12.2 seconds respectively. Every run used one ACPI
  request, the same dedicated disposable VDI, EFI, 16,384 MiB RAM, 16 CPUs and
  UART disabled.
- Visual inspection of the first and fifth live screenshots confirmed the
  complete Clausis GNOME desktop and matching Hermes Agent icon. All ten GRUB
  and desktop images are uniquely named under
  `dist/clausis-acpi-soak-301ea054-retry-runNN-{grub,live}.png`.
- Overall progress is approximately 78 percent. This establishes repeatable
  bounded soak infrastructure and a passing five-run baseline, but it does not
  erase the earlier host-event loss evidence or close longer endurance and
  physical-hardware gates. Persistent installation, upgrades, broader
  application coverage, compliance and release polish remain open.
  Technical-preview and KI-Slop disclosures remain in force.

## 2026-08-11 disposable VirtualBox installation-boundary preflight

- Added `scripts/vbox_install_sandbox.ps1` to establish a safe host boundary
  for future destructive Calamares testing. It derives a unique VM and sandbox
  directory from the process ID, permits the directory only below the project's
  `dist/clausis-install-sandbox-*` namespace, and creates a new dynamic VDI
  there rather than accepting an existing disk path.
- The harness registers a separate Debian EFI VM, attaches only the exact ISO
  and newly created VDI, keeps UART off, delegates the full rendered GRUB/live-
  desktop/one-shot-ACPI gate, verifies the ISO hash and final poweroff result,
  then unregisters the VM with `--delete` and removes only the validated
  sandbox directory in `finally`.
- The first real attempt stopped before VM creation because native PowerShell
  promoted the expected missing-VM `showvminfo` result to an exception; only an
  empty sandbox directory was created and removed. The second reached dynamic
  VDI creation but treated VirtualBox's normal stderr progress as an exception;
  inventory proved no registered sandbox VM and exactly one 2-MiB disposable
  VDI, which was removed. Native calls now temporarily use Continue semantics
  and decide solely from the captured process exit code; both regressions have
  structural coverage.
- The complete Debian/Linux suite passed: 722 tests. PowerShell syntax and the
  focused sandbox safety test passed before the final real run. This host-only
  test harness does not alter the already verified guest ISO, so the tested
  image remained SHA-256
  `301ea054411ccdca752ad5b766542b25fb6e652b747cca4176b247b094a5c12b`,
  size 2,643,034,112 bytes.
- The final preflight created `Clausis-Install-Sandbox-17316` with a fresh
  65,536-MiB dynamic VDI under the project sandbox, observed branded GRUB after
  105.6 seconds and the complete GNOME desktop after another 99.4 seconds, then
  reached poweroff 11.0 seconds after exactly one ACPI request. Visual evidence
  is `dist/clausis-install-sandbox-preflight-final-{grub,live}.png`; the summary
  is `dist/clausis-install-sandbox-preflight-final-summary.json`.
- Independent post-run inventory confirmed the temporary VM was unregistered
  and its sandbox directory/VDI removed. The permanent `Clausis` VM and
  `G:\VM\Clausis\Clausis.vdi` were not attached to this test.
- Overall progress remains approximately 78 percent. This closes the missing
  safe disposable-VM boundary, not the protected Calamares execution, target
  copy, installed-system boot, recovery-key unlock or physical-hardware gates.
  Technical-preview and KI-Slop disclosures remain in force.

## 2026-08-11 disposable live setup foreground preflight

- Extended the readiness-gated VirtualBox smoke with an opt-in, bounded
  foreground capture. After the complete branded desktop is proven, the option
  sends only Escape to close GNOME's overview, waits a validated 1-to-120-second
  interval and captures a screenshot. It never tabs, activates or advances a
  setup or installer control; ordinary release smokes remain unchanged.
- The disposable installation sandbox always requests this evidence and
  requires `ForegroundCaptured=true`. Its default 45-second delay is long
  enough to distinguish a synchronous live-setup gate from the immediate
  overview hand-off while remaining bounded.
- PowerShell syntax, both focused smoke/sandbox regressions and the complete
  Debian/Linux suite passed: 722 tests. These are host-side harness changes and
  do not alter the already verified ISO; testing remained bound to SHA-256
  `301ea054411ccdca752ad5b766542b25fb6e652b747cca4176b247b094a5c12b`.
- A first disposable run captured the foreground after three seconds. It showed
  only the empty Clausis desktop, then reached poweroff in 10.5 seconds and
  removed its VM/VDI. A second fresh 65,536-MiB sandbox waited 45 seconds and
  captured the visible, focused **Clausis und Hermes einrichten** window with
  `Später oder nur Offline-Befehle` selected, cloud/API fields disabled and the
  explicit **Speichern und Installation fortsetzen** control. Evidence is
  `dist/clausis-install-foreground-delayed-foreground.png`.
- The delayed run observed branded GRUB after 147.8 seconds, the complete
  desktop after another 141.7 seconds, captured the foreground after 45 seconds,
  reached poweroff 7.8 seconds after one ACPI request and reported
  `SandboxRemoved=true`. No temporary sandbox VM or VDI remained.
- This proves that Calamares is synchronously gated behind the accessible
  Clausis setup dialog rather than silently absent. It does not yet activate
  that control, prove setup validation, display Calamares, partition the disk,
  boot an installed system or unlock it. Overall progress remains approximately
  78 percent; those installer stages remain open. Technical-preview and KI-Slop
  disclosures remain in force.

## 2026-08-11 disposable offline-setup transition probe

- Added an opt-in setup-transition probe that is rejected before VM start
  unless the expected VDI is inside the exact process-scoped
  `dist/clausis-install-sandbox-<PID>` boundary. It fills a fixed ephemeral test
  PIN twice through GTK mnemonics and attempts the setup save mnemonic only;
  it performs no Calamares interaction.
- PowerShell syntax, focused safety regressions and the complete Debian/Linux
  suite passed: 722 tests. A negative check also rejected the permanent
  `G:\VM\Clausis\Clausis.vdi` before starting a VM. These host-only harness
  changes did not require an ISO rebuild; the tested image remained size
  2,643,034,112 bytes with SHA-256
  `301ea054411ccdca752ad5b766542b25fb6e652b747cca4176b247b094a5c12b`.
- The real run created `Clausis-Install-Sandbox-6860` with a fresh dynamic
  65,536-MiB VDI, observed branded GRUB after 158.1 seconds and the complete
  desktop after another 151.9 seconds, then waited 45 seconds before the
  foreground transition. It reached poweroff 9.4 seconds after one ACPI
  request and reported `SandboxRemoved=true`.
- The final screenshot
  `dist/clausis-install-calamares-preflight-after-setup.png` shows both matching
  PIN fields filled, but the setup status still says **Noch nicht eingerichtet**
  and **Speichern und Installation fortsetzen** remains visible. Therefore the
  attempted Alt+S mnemonic did not activate the control; Calamares was not
  reached and received no input. The harness result name
  `OfflineSetupActivated=true` records that the input sequence was sent, not
  that the UI transition succeeded, and must not be treated as such evidence.
- Post-run inventory found no sandbox VM or directory. The permanent `Clausis`
  VM remained powered off with UART disabled, the exact ISO on IDE 0:0 and
  `G:\VM\Clausis\Clausis.vdi` on SATA 0:0. Overall progress remains
  approximately 78 percent. Robust save activation, Calamares display,
  partitioning, target copy, installed boot and recovery-key unlock remain open;
  technical-preview and KI-Slop disclosures remain in force.

## 2026-08-12 readiness-gated setup-to-Calamares transition

- The real disposable probes exposed two separate timing assumptions. Desktop
  branding could precede the setup window by more than 45 seconds, and the
  original live welcome synchronously waited for `spd-say -w` before starting
  setup. The guest now queues that welcome without waiting for audio completion;
  a visual setup-window gate prevents all PIN/save input until the large GTK
  setup surface is actually present.
- The save path no longer relies on the ineffective Alt+S mnemonic. From the
  repeat-PIN field it follows the declared GTK tab order, captures the visibly
  focused **Speichern und Installation fortsetzen** button, then sends Enter.
  The transition gate requires the setup surface to disappear before separately
  recognizing Calamares's large light content surface. A notification or empty
  desktop cannot satisfy that detector.
- The sandbox cleanup now retries only its already validated project-local path
  because VirtualBox briefly retained `VBoxHardening.log` after one unregister.
  The discovered orphan contained only that log and was removed after inventory
  proved that its VM was already absent.
- PowerShell and shell syntax, 21 focused live-image tests and the complete
  Debian/Linux suite passed: 722 tests. The guest change required a full ISO
  rebuild; `verify_iso.sh` passed. The resulting 2,643,034,112-byte image has
  SHA-256 `22ea96f937adedaa27193a88e03829ce9c52c428cb6200ac150de76726c84600`.
- The final fresh 65,536-MiB sandbox run used VM
  `Clausis-Install-Sandbox-6692`. It observed branded GRUB after 181.4 seconds,
  the complete desktop after another 177.3 seconds and the actual setup window
  after 35.2 additional seconds. Its before-save image proves matching masked
  PINs and focus on Save; its final image proves **Welcome to the Calamares
  installer for Debian 13**. No control inside Calamares was activated.
- The run reported `CalamaresReady=true`, reached poweroff 16.0 seconds after
  one ACPI request and reported `SandboxRemoved=true`. Post-run inventory found
  no sandbox VM or directory. The permanent `Clausis` VM remained powered off,
  UART disabled, with the new exact ISO on IDE 0:0 and
  `G:\VM\Clausis\Clausis.vdi` unchanged on SATA 0:0.
- This closes the accessible setup-to-Calamares-display gate. Partition choice,
  protected confirmation, target copy, installed-system boot, recovery-key
  unlock and physical-hardware validation remain open. Overall progress is now
  approximately 79 percent; technical-preview and KI-Slop disclosures remain
  in force.

## 2026-08-12 disposable Calamares partitions-page preflight

- Added a separate disposable-only navigation mode which is rejected before VM
  creation unless offline setup completion is also explicitly enabled. It
  advances only Welcome, Location and Keyboard, captures every page and stops
  immediately on Partitions without touching a partition control.
- Real diagnostics found that Calamares's partition module remained in its
  shared requirements gate because `os-prober` consumed its hard-coded
  60-second timeout. A root-only session-log capture over the automatically
  logged-in disposable TTY proved the exact module and timeout. Calamares
  3.3.14 is now patched to allow 15 seconds, then kill and boundedly reap the
  timed-out process. The existing OS-detection opportunity remains; the UI no
  longer waits a full minute or destroys a still-running process.
- Locale GeoIP was also made deterministic offline with `style: "none"` and an
  editable Europe/Berlin starting point. Removing the optional welcome power
  probe and disabling GeoIP did not by themselves resolve the partition wait;
  the session log, rather than those hypotheses, identified os-prober as the
  actual blocker.
- PowerShell and shell syntax, 21 focused live-image tests and the complete
  Debian/Linux suite passed: 722 tests. The patched Calamares package compiled,
  the full ISO rebuilt and `verify_iso.sh` passed, including its new final-
  SquashFS offline-locale check. The 2,643,034,112-byte ISO has SHA-256
  `e8a57e61d07ec52c55ac72df3eb0616f2f498386e3c946e38b2c0ca628b60cb4`.
- The final run used `Clausis-Install-Sandbox-28276` and a fresh dynamic
  65,536-MiB VDI. It observed branded GRUB after 256.4 seconds, desktop after
  another 252.3 seconds and setup after 107.4 additional seconds. Visual
  evidence proves Location with Europe/Berlin, Keyboard with English (US), and
  the Partitions page showing only `VBOX HARDDISK - 64.00 GiB (/dev/sda)`.
- On that final Partitions page neither **Erase disk** nor **Manual
  partitioning** was selected, **Next** was disabled, and the harness sent no
  further input. Thus no partition choice, format or disk write occurred.
- One ACPI request reached poweroff in 9.6 seconds and
  `SandboxRemoved=true`. Post-run inventory found no sandbox VM or directory;
  the permanent `Clausis` VM remained powered off with UART disabled, the exact
  ISO on IDE 0:0 and `G:\VM\Clausis\Clausis.vdi` unchanged on SATA 0:0.
- This closes the non-destructive navigation gate through the first disk page.
  Choosing Erase, protected pre-write confirmation, actual partitioning,
  target copy, installed boot and recovery-key unlock remain open. Overall
  progress is approximately 80 percent; technical-preview and KI-Slop
  disclosures remain in force.

## 2026-08-12 fail-closed Erase-selection probes

- Added a disposable-only Erase-selection switch guarded by the existing
  offline-setup and Partitions-navigation requirements. It captures the result,
  checks the radio indicator visually, never activates **Next**, and throws if
  selection is not visible.
- Three real VirtualBox probes did not visually select **Erase disk**. The first
  exposed unsupported VirtualBox 7.2 mouse subcommands and was invalid despite
  its preliminary result object; the harness was corrected so input alone can
  no longer count as success. Two keyboard-only variants were then rejected by
  the new visual gate. No partitioning or disk write occurred.
- One independent setup-focus retry also failed before Calamares and was not
  counted. All four sandbox summaries recorded `SandboxRemoved=true`; inventory
  afterwards contained only the permanent powered-off `Clausis` VM.
- The focused 21-test live-image suite and the complete Debian/Linux suite of
  722 tests pass. The safe Erase-selection gate remains open, so overall
  progress remains approximately 80 percent.

## 2026-08-12 GUI-mode navigation audit

- Added an explicitly guarded GUI/interaction-hold mode to the disposable
  sandbox harness. It cannot hold unless GUI mode, offline setup and navigation
  through Partitions are all requested. Windows PowerShell 5 compatibility was
  also fixed by resolving `$PSScriptRoot` defaults inside the script body.
- The real GUI run used the exact ISO and a new 65,536-MiB disposable VDI. Its
  Calamares Welcome page stayed in `Waiting for 1 module... (10 seconds)` while
  the prior harness continued sending navigation keys. This contradicted the
  reported navigation result and showed that input-sent flags were insufficient.
- The harness now samples the captured Calamares navigation highlight and fails
  unless **Partitions** is visually selected. Existing known-good and GUI-stuck
  captures have opposite sampled states, proving the discriminator covers this
  regression. The GUI sandbox still powered off in 6.5 seconds and was removed.
- The focused 21-test suite and all 722 Debian/Linux tests pass. No installer
  write occurred; Erase selection and the GUI-mode requirements stall remain
  open, so overall progress stays at approximately 80 percent.

## 2026-08-12 privileged Calamares accessibility audit

- A corrected TTY diagnostic proved that `os-prober` finished, the partition
  requirement was satisfied and all four Calamares requirements completed. The
  apparent GUI spinner stall was a stale VirtualBox GUI framebuffer, not an
  active module deadlock.
- AT-SPI diagnostics initially exposed only Mutter's window-frame controls for
  privileged Calamares. The live launcher now enables both Qt accessibility
  variables and carries the explicit `org.a11y.Bus` address through the
  privilege boundary. Calamares also starts in the correct GNOME dark theme.
- Two complete rebuilt ISOs passed the full verifier. The current 2,643,034,112-
  byte ISO has SHA-256
  `ca3893c7448395193e41ab7f8a7bdd525eda07b586a634264ffd580838aab9a5`.
- The VBox harness now recognizes both light and dark Calamares surfaces,
  validates the actual selected Partitions sidebar row, and samples only the
  real Erase radio center. This correction invalidated an intermediate false
  positive caused by sampling the adjacent blue navigation background.
- The final exact-radio attempt still failed the independent visual gate, so
  no selection, Next activation or disk write is claimed. Every disposable VM
  and VDI was removed. All 722 tests and 21 focused tests pass; progress remains
  approximately 80 percent.

## 2026-08-12 visible disposable Erase-selection gate

- Corrected the dark-theme Partitions detector to sample the actual y=383
  navigation row. A regression run then reached and visually proved the real
  Partitions page; Welcome is no longer accepted as a navigation success.
- Started `Clausis-Install-Sandbox-30760` in visible GUI mode with the exact ISO
  SHA-256 `ca3893c7448395193e41ab7f8a7bdd525eda07b586a634264ffd580838aab9a5`
  and a fresh 65,536-MiB disposable VDI. One unique VirtualBox window was bound
  and the visible Erase radio was clicked exactly once.
- Guest-framebuffer evidence at
  `dist/clausis-install-gui-click2-erase-selected.png` proves **Erase disk**
  selected, **Encrypt system** enabled by default, and the proposed layout:
  512 MiB EFI/FAT32, 1 GiB `CLAUSIS_BOOT`/ext4 and 62.5 GiB
  `CLAUSIS_ROOT`/Btrfs. Both passphrase fields stayed empty and **Next** stayed
  disabled, so no partition job or disk write started.
- The VM reached poweroff in 3.2 seconds and its summary records
  `SandboxRemoved=true`. Inventory afterwards contained only the permanent
  powered-off `Clausis` VM. This closes the selection-only gate; encrypted
  passphrase entry, Users, Summary, protected pre-write confirmation, target
  copy, installed boot and recovery unlock remain open. Overall progress is
  approximately 81 percent.

## 2026-08-12 encrypted Partitions-to-Users preflight

- Booted the exact current ISO in visible GUI mode as
  `Clausis-Install-Sandbox-29368` with a new 65,536-MiB disposable VDI and
  reached the visually verified dark-theme Partitions page.
- Selected Erase and entered the same throwaway, VM-only encryption passphrase
  into both fields. Guest evidence shows both masked values, the green valid
  indicator, **Encrypt system** enabled and `CLAUSIS_ROOT` identified as LUKS2.
  The passphrase itself is intentionally not retained in project documentation.
- The first visible click only focused Next and Enter remained bound to the
  password field. The exact, previously verified Alt+N mnemonic then advanced
  to Users. Evidence at `dist/clausis-install-gui-users-page.png` shows Users
  selected and its empty full-name, login, computer-name and account-password
  controls, with automatic login unchecked.
- No Users value was entered, Summary and Install were not opened, and no disk
  job began. The VM powered off in 3.2 seconds and its summary records
  `SandboxRemoved=true`; inventory afterwards contained only permanent
  `Clausis`. This closes the encrypted Partitions-to-Users navigation gate and
  raises overall progress to approximately 82 percent.

## 2026-08-12 disposable pre-install Summary gate

- Booted the exact current ISO as `Clausis-Install-Sandbox-29224` with a fresh
  65,536-MiB disposable VDI, selected encrypted Erase and reached Users.
- Entered the throwaway full name `Clausis Test`. Calamares derived and visibly
  validated login `clausist` and computer name `clausis-virtualbox`. Matching
  VM-only account passwords produced the green valid indicator; automatic login
  remained unchecked. Neither temporary password is retained in documentation.
- Alt+N opened Summary. Evidence at
  `dist/clausis-install-gui-summary-page.png` shows Europe/Berlin, American
  English with German locale formatting, Generic 105-key PC / English US, and
  Erase bound only to `/dev/sda (VBOX HARDDISK)`. The planned jobs include a new
  GPT table, 512-MiB `CLAUSIS_EFI` FAT32/boot, 1-GiB `CLAUSIS_BOOT` ext4 and
  62.5-GiB `CLAUSIS_ROOT` LUKS2.
- **Install** remained untouched; no confirmation or partition job started.
  The VM powered off in 3.2 seconds, `SandboxRemoved=true`, and inventory
  afterwards contained only permanent `Clausis`. This closes the pre-install
  Summary gate and raises overall progress to approximately 83 percent.

## 2026-08-12 full disposable encrypted installation and boot

- Recreated the validated configuration in `Clausis-Install-Sandbox-3548` on a
  fresh 65,536-MiB disposable VDI using exact ISO SHA-256
  `ca3893c7448395193e41ab7f8a7bdd525eda07b586a634264ffd580838aab9a5`.
- Opened the irreversible Calamares confirmation, verified that it referred to
  the disposable `/dev/sda (VBOX HARDDISK)`, and after explicit approval chose
  **Install Now**. Evidence captures initial partition creation at 4%, file-
  system population at 35%, and the final **All done** screen.
- Stopped the harness cleanup timer, powered off the guest, detached the ISO and
  changed boot order to disk only. The installed VDI booted to Debian 13's
  graphical LUKS prompt. The VM-only passphrase unlocked it and GDM displayed
  the created `Clausis Test` account.
- Logging in with the VM-only account password reached the installed Clausis
  GNOME desktop. Evidence shows the installed Clausis setup dialog, active
  speech-control notification and the Hermes Agent launcher with its matching
  Hermes icon.
- ACPI shut the installed guest down; a transient VirtualBox GUI session lock
  cleared on the first bounded retry. The exact sandbox VM and VDI were then
  deleted. Inventory afterwards contained only permanent powered-off
  `Clausis`; no test credential is retained in documentation.
- This closes the encrypted installation, disk-only boot, primary LUKS unlock,
  GDM login and installed-desktop gates. Recovery-key unlock, negative/failure
  recovery, endurance and physical-hardware validation remain open. Overall
  progress is approximately 90 percent.

## 2026-08-12 Recovery guard mode-binding correction

- Auditing the successful disposable installation found that no protected
  recovery-key readback occurred before partitioning. The guard command used
  `${gs[partitionChoices.install]}` while the patched partition module exported
  all other trusted metadata as flat global-storage values. An unresolved or
  empty mode therefore entered the standard non-Erase fallback and skipped the
  recovery guard instead of authorizing the destructive Erase transaction.
- The Calamares patch now derives and exports the flat, non-secret
  `clausisInstallMode` value directly from `InstallChoice::Erase`; the guard
  consumes that value. Regression tests and the final ISO verifier require the
  value in both the compiled partition module and installed guard configuration.
- All 722 project tests pass. The focused live-image configuration suite passes
  21 tests. A complete Calamares package and ISO rebuild succeeded, followed by
  `scripts/verify_iso.sh`. The new 2,643,034,112-byte ISO has SHA-256
  `cd242c1e4afeebc336b0e16c79984068e541a3203d47ec62733c64ed00627b3e`.
- VirtualBox validation of the corrected pre-write failure path and a complete
  spoken recovery-key readback plus recovery unlock remain release blockers.
  The overall project estimate therefore remains approximately 90 percent.

## 2026-08-12 disposable Recovery-guard negative test

- Added a fail-closed host harness restricted by exact pathname to a newly
  created `Clausis-Install-Sandbox-<pid>` VDI. Inside the real live guest it
  hashes the first four MiB of `/dev/sda`, executes the ISO-embedded
  `calamares-clausis --guard-transaction` for encrypted Btrfs Erase mode without
  microphone input, and hashes the same region again.
- The first diagnostic run failed closed because VBox keyboard injection
  stripped quotes around a typed ANSI sequence. It produced no passing marker,
  and its VM/VDI were removed. The harness was changed to quote-free `tput`
  output and rerun from a fresh VDI.
- `Clausis-Install-Sandbox-14520` passed on exact ISO SHA-256
  `cd242c1e4afeebc336b0e16c79984068e541a3203d47ec62733c64ed00627b3e`.
  `RecoveryGuardFailClosed=true` means all four guest-side predicates held:
  the guard returned non-zero, `/run/clausis-installer/recovery.key` was absent,
  `sfdisk` found no partition table, and the before/after hashes matched.
  Evidence is `dist/clausis-recovery-guard-negative2-recovery-guard-fail-closed.png`.
- ACPI reached poweroff in 11.7 seconds. The summary records
  `SandboxRemoved=true`; afterwards no sandbox VM or directory remained and the
  permanent `Clausis` VM was still powered off. All 722 tests and the focused
  21-test live-image configuration suite pass.
- This closes the corrected guard's destructive-failure negative gate. A real
  positive spoken recovery-key readback, LUKS enrollment and subsequent unlock
  remain release blockers. Overall progress is approximately 91 percent.

## 2026-08-13 executable Recovery bridge and final negative gate

- A stricter review invalidated the earlier negative probe as sufficient
  evidence: Debian installs the executable at
  `/usr/libexec/calamares-clausis/calamares_clausis.py`, while the Calamares
  guard and first probe invoked its containing directory. That still prevented
  writes, but did not exercise the intended Python bridge. The module, ISO
  verifier and VBox harness now use and require the exact executable path.
- The bridge now accepts only the explicitly exported `erase` and `other`
  values. Missing, legacy or unknown modes are denied instead of entering the
  non-Erase fallback. A new regression raises the full suite to 724 tests.
- Repeated real-guest diagnostics also found that a timed-out speech backend
  could fall through to another backend, blocking the pre-write job for several
  minutes and potentially replaying part of a protected key. `SystemSpeaker`
  now fails closed on its first `TimeoutExpired`; a focused test proves exactly
  one backend invocation. The final ISO verifier checks this code directly in
  SquashFS.
- The final 2,643,034,112-byte ISO has SHA-256
  `c7ad5e541f47632bd91bb4b70317517c503255db893a085db76b2c5e12061671`.
  The complete `scripts/verify_iso.sh` chain passes, including the flat mode,
  executable bridge path, invalid-mode rejection, recovery module and speaker
  timeout hardening.
- `Clausis-Install-Sandbox-1692` then ran the exact embedded bridge against its
  new 65,536-MiB `/dev/sda`, with audio output enabled and capture disabled.
  The bridge returned its own `denied` response; the staged recovery file was
  absent, `sfdisk` found no partition table and SHA-256 of the first four MiB
  matched before and after. Evidence is
  `dist/clausis-recovery-guard-final2-recovery-guard-fail-closed.png`.
- The specialized probe records `RecoveryGuardFailClosed=true`,
  `ForcedDisposableCleanup=true`, `FinalState=poweroff` and
  `SandboxRemoved=true`. Forced host cleanup is intentionally separate from
  the existing ACPI release gate. No sandbox VM/directory remains and the
  permanent `Clausis` VM remains powered off.
- This closes the real embedded-bridge negative gate. Positive spoken key
  readback, enrollment into the installed LUKS header and recovery unlock are
  still release blockers. Overall progress remains approximately 91 percent.

## 2026-08-13 encrypted install requires confirmed Recovery key

- Audited the later `luksbootkeyfile` job after closing the pre-write guard.
  Its patched code rejected malformed staged keys but still treated an absent
  staged key as optional. A future guard integration regression could therefore
  have allowed an encrypted installation to finish without the promised
  emergency credential.
- The Calamares patch now returns an encrypted-root setup error when
  `RecoveryKeyState::Absent` is observed after a LUKS device and passphrase have
  been established. The pre-existing no-LUKS-device path still leaves
  unencrypted installs unaffected. Focused tests and all 724 project tests pass.
- The patched Calamares 3.3.14 package compiled successfully. The complete ISO
  rebuilt and `scripts/verify_iso.sh` found the new mandatory-key error string
  in the actual `libcalamares_job_luksbootkeyfile.so` binary. The final
  2,643,034,112-byte ISO has SHA-256
  `cae6866f1930169988a43701a6ce9ba7d013bd8cf3bb4ed0c0e116b3a78729c4`.
- A new disposable VirtualBox run, `Clausis-Install-Sandbox-7604`, confirmed
  the real embedded guard still fails closed on this exact ISO:
  `RecoveryGuardFailClosed=true`, `ForcedDisposableCleanup=true`,
  `FinalState=poweroff` and `SandboxRemoved=true`. No sandbox resources remain.
- A positive spoken readback, actual LUKS key enrollment and recovery unlock
  remain the principal release blocker. Overall progress is approximately
  92 percent.

## 2026-08-13 disposable PipeWire recovery-audio inventory

- Added a disposable-only VirtualBox audio inventory mode. It enables capture
  only for an exact `Clausis-Install-Sandbox-<pid>` VDI, boots the final ISO,
  inventories the live guest from TTY3, and uses forced host cleanup separately
  from the ACPI release gate.
- The guest exposed one PipeWire `Built-in Audio` sink and source. Native
  `/usr/bin/pw-record`, `/usr/bin/pw-play` and `/usr/bin/pw-loopback` are all
  present; `arecord` and `pactl` are absent. This establishes that a local
  PipeWire monitor/loopback experiment is feasible without exporting a
  recovery key to the host.
- The verified run used ISO SHA-256
  `cae6866f1930169988a43701a6ce9ba7d013bd8cf3bb4ed0c0e116b3a78729c4`.
  `Clausis-Install-Sandbox-556` recorded `AudioInventoryPassed=true`,
  `ForcedDisposableCleanup=true`, `FinalState=poweroff` and
  `SandboxRemoved=true`. Evidence is
  `dist/clausis-audio-inventory-verified-audio-inventory.png` and its summary.
- This is capability evidence, not a positive recovery ceremony. Real TTS to
  local audio capture, STT readback, LUKS enrollment and recovery unlock remain
  release blockers. Overall progress remains approximately 92 percent.

## 2026-08-13 installer voice-runtime and local STT repair

- A real disposable PipeWire recording exposed that the installer bridge used
  `/usr/bin/env python3`. The ISO did contain the pinned Faster-Whisper package
  and model under `/opt/clausis`, but the bridge bypassed that environment and
  failed with `Lokale Spracherkennung ist nicht installiert.` This made a
  positive Recovery ceremony impossible despite the apparently complete
  package inventory.
- The bridge is now bound to `#!/opt/clausis/bin/python`. The final ISO verifier
  requires that exact interpreter plus the pinned `faster_whisper` and
  `sounddevice` files directly in SquashFS. The complete rebuild and verifier
  passed. The 2,643,034,112-byte ISO has SHA-256
  `5a138f8fb831629107a9e5f0e47c6e0a914e8606abcf9ec4e09566bb3f866813`.
- The first post-fix real-guest run proved that local Whisper now executes, but
  its deliberately short phrase was mistranscribed. The gate was made closer
  to the Recovery ceremony by speaking a clearly introduced digit sequence
  twice; no transcript injection or host audio substitution was used.
- `Clausis-Install-Sandbox-13196` then passed the complete harmless path on the
  exact new ISO: `spd-say` output, real PipeWire sink-monitor capture, a delayed
  `Audio/Source`, WAV recording, and local Faster-Whisper recognition of all
  three spoken digits. It records `PipeWireLoopbackPassed=true`,
  `ForcedDisposableCleanup=true`, `FinalState=poweroff` and
  `SandboxRemoved=true`. Evidence is
  `dist/clausis-pipewire-local-stt-clear-pipewire-loopback.png` and its summary.
- This closes the generic local TTS-to-STT transport/runtime gate. Full
  48-digit readback, the random confirmation phrase, LUKS enrollment and a
  subsequent Recovery-key unlock remain release blockers. Overall progress is
  approximately 93 percent.

## 2026-08-13 full-length Recovery readback trials

- Added a secret-free disposable gate which creates a random 12-by-4 Recovery
  key only inside the guest, speaks it through the real local backend, captures
  the simulated handwritten-note readback through PipeWire and compares the
  locally normalized transcript without printing either value.
- The trials found two production limitations hidden by short phrases: grouped
  digits could be pronounced as whole numbers, and the generic 25-second
  recorder bound is too short for 48 individually spoken digits. Recovery keys
  are now formatted digit by digit with pauses between all twelve groups, and
  only `DirectInstallConfirmation` gets a 90-second/1.8-second-silence recorder.
  Other confirmation recordings retain their tighter 25-second bound.
- Recovery transcription now supplies the pinned local model with a narrow
  German-digit context. The long key announcement is also split into bounded
  introduction, first key, repetition notice and second key calls so no single
  `SystemSpeaker` invocation can monopolize its 120-second safety bound.
- The complete ISO rebuilt and verified after the digit/recorder changes. The
  2,643,034,112-byte image has SHA-256
  `718aa19c459f88da81e7adfa6998488b9e8e9ba3d24978b536b25ae3002b68fe`.
- The exact 48-digit positive comparison is not closed yet. All failed trials
  removed their temporary WAV, VM and VDI and exposed only coarse failure
  classes, never a key or transcript. The permanent `Clausis` VM remained
  powered off with UART disabled. Overall progress remains approximately
  93 percent.

## 2026-08-13 segmented full-length Recovery checkpoint

- Split the long protected announcement into bounded introduction, first-key,
  repetition-notice and second-key speaker calls. A timeout still fails closed
  and never falls through to another backend for the same protected segment.
- The complete ISO build and structural verifier pass. The exact
  2,643,034,112-byte checkpoint ISO has SHA-256
  `994d47a50f9ab755ef1bb69ba2a8f6972b91c9d968800667bba0a67719513185`.
- A fresh disposable run exercised the new ISO but ended in the coarse
  `RECOVERY_READBACK_RUNTIME_FAILURE` class before an exact transcript compare.
  No key, transcript or WAV was exported; the guest removed the temporary WAV
  and the host removed the VM and VDI. This is recorded as an open release
  blocker, not a positive result.
- The generic short TTS-to-PipeWire-to-Whisper path remains proven. The full
  Recovery gate, random phrase, LUKS enrollment and Recovery unlock remain
  open. Overall progress stays approximately 93 percent.
