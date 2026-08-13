# Clausis Core

Clausis Core is an executable Debian voice-first desktop prototype integrating
Hermes Agent without granting the agent unrestricted operating-system access.
The repository now builds a bootable Debian Live/Calamares USB image. It remains
a **technical preview, not a production-ready end-user operating system**.

> **KI-Slop / AI-slop transparency notice:** Dieses Projekt ist KI-Slop. Große
> Teile von Code, Tests, Dokumentation und Buildkonfiguration wurden mit
> generativer KI erstellt oder weiterentwickelt. Automatische Tests und die
> dokumentierten VirtualBox-Läufe reduzieren Risiken, ersetzen aber keine
> unabhängige menschliche Codeprüfung, Sicherheitsauditierung oder Freigabe für
> den Produktiveinsatz. Behandle jede nicht manuell geprüfte Funktion als
> potenziell fehlerhaft.

The current test image is published under
[`Releases`](https://github.com/hendkai/clausis/releases). Every `v*` Git tag
automatically starts a clean Debian ISO build and uploads split, checksummed
release assets through GitHub Actions.

## Test image herunterladen

Download all three files from the
[`v0.4.1` release](https://github.com/hendkai/clausis/releases/tag/v0.4.1):

- `clausis-0.4.1-amd64.iso.part-aa`
- `clausis-0.4.1-amd64.iso.part-ab`
- `clausis-0.4.1-amd64.iso.sha256`

Do **not** unpack the files. On Windows, place all three files in the same
folder, open PowerShell in that folder and run:

```powershell
cmd /c copy /b clausis-0.4.1-amd64.iso.part-aa+clausis-0.4.1-amd64.iso.part-ab clausis-0.4.1-amd64.iso
$expected = (Get-Content .\clausis-0.4.1-amd64.iso.sha256).Split()[0].ToUpper()
$actual = (Get-FileHash .\clausis-0.4.1-amd64.iso -Algorithm SHA256).Hash
if ($actual -ne $expected) { throw "Checksum mismatch - download the parts again" }
"Checksum OK: $actual"
```

Linux and Git Bash users can assemble and verify the ISO with:

```sh
cat clausis-0.4.1-amd64.iso.part-aa clausis-0.4.1-amd64.iso.part-ab > clausis-0.4.1-amd64.iso
sha256sum -c clausis-0.4.1-amd64.iso.sha256
```

On macOS, replace the verification command with:

```sh
shasum -a 256 -c clausis-0.4.1-amd64.iso.sha256
```

After verification, select `clausis-0.4.1-amd64.iso` directly as the optical
disk in VirtualBox. Do not unpack the resulting ISO.

## What works now

- Original Clausis boot branding for both GRUB/UEFI and Syslinux/BIOS.
- Matching GNOME identity with the Clausis listening-field wallpaper, dark
  color preference, purple speech accent, branded launchers and GDM logo,
  reduced animation and Atkinson Hyperlegible typography.
- 157 deterministic German/English offline command families.
- A persistent local wake gate: background transcripts are discarded until
  “Hallo Clausis”, the activation window closes automatically, and “Stopp
  Clausis” is handled before Hermes or any cloud fallback.
- `Correct that` / `Korrigieren` opens a local one-shot, 30-second correction
  slot based on a monotonic clock. Repeat
  keeps its content-free prompt active; cancel and stop clear it; exactly one
  replacement utterance then follows the normal router/broker/fallback path.
  The first late utterance is discarded rather than executed. No transcript is
  retained. The local wake gate stays open through the slot plus a fixed
  five-second expiry grace, without letting repeat extend that deadline. An
  expired replacement or an explicit sleep command closes the gate again.
  Clausis explicitly warns that an already executed action is not automatically
  undone.
- Semantic GNOME orientation through AT-SPI without screen coordinates:
  describe the active window/focus, enumerate numbered controls, move focus
  semantically, navigate back, move between accessible windows, and request
  minimize, maximize, restore or
  close only when the active AT-SPI frame exposes that exact semantic action.
  Window cycling requires exactly one active starting window, verifies that
  only the calculated neighbor becomes active and restores the prior focus on
  any mismatch.
  Overview and application-grid commands likewise target only exact controls
  exposed by GNOME Shell. A uniquely named current control can also be selected
  without coordinates. Immediately before numbered, named or permission-control
  activation, Clausis re-reads the bound node's action names and invokes only
  an explicit Click, Press, Activate, Toggle or Open action. A stale index or a
  control exposing only an unrelated action is rejected without invocation.
  Numbered activation also requires the identical active-window object and an
  identity-for-identity match of the complete ordered operable-control snapshot
  immediately before mutation. Added, removed or reordered controls invalidate
  the spoken number instead of silently retargeting it.
  Named activation additionally rebinds the active-window identity and requires
  the same target to remain exactly once in that window's freshly discovered
  operable controls immediately before mutation. A dialog switch, removed
  control or newly hidden/insensitive target therefore executes no action.
  Permission decisions re-run exact Allow/Deny-pair recognition on the
  identical active dialog immediately before mutation. Both controls must keep
  their original AT-SPI identities and remain the sole recognized decision
  group; a replaced dialog or look-alike pair executes neither side.
  Menu-item activation likewise rebinds the identical active window, focused
  semantic menu container and exact direct target immediately before
  `doAction()`. A closed/switched menu or same-label replacement item executes
  no action.
  Back navigation also requires exactly one matching action across the bound
  window and rebinds it before execution. Window-manager aliases and matching
  GNOME Shell targets must likewise resolve to exactly one candidate; duplicate
  localized actions or controls fail without invocation.
  A separate confirmed command reads only currently Showing AT-SPI nodes with
  the exact `notification` role from exactly one GNOME Shell application. It
  ignores calendar labels, editable controls and protected descendants, caps
  output at 20 notifications/40 unique text items/2,000 characters, and removes
  the complete spoken result from the signed audit trail.
  Spoken results number the exact visible notification objects. A separate
  confirmed high-risk command dismisses one number only after rebinding the
  same GNOME Shell object and the identity-for-identity complete ordered
  notification snapshot; it accepts exactly one Dismiss or Close action and
  carries no notification title in the request or audit.
  After invocation it polls for at most two seconds and reports success only
  when the same Shell exposes exactly the original order minus that one object;
  an unchanged or otherwise mutated list is an explicit unconfirmed-state
  failure rather than a false success.
  Every state read or mutation bound to an active window now requires exactly
  one AT-SPI Active frame/dialog/window; a merely Showing window is never used
  as a work target. Only the non-mutating orientation command may fall back,
  and then only when exactly one Showing window exists.
  Closing, numbered activation and named activation remain confirmation-gated.
  Next/previous-control focus cycling also verifies that
  exactly the calculated control becomes focused and restores the prior focus
  after any inconsistent AT-SPI result.
  Named focus changes likewise require exactly one focused starting node,
  verify the complete bound-window focus bitmap and restore that exact node
  after rejection, mismatch or an exception following partial focus movement.
  A failed restoration is reported separately and remains fail-closed.
- The active window can be moved to the previous/left or next/right workspace
  after trusted confirmation, but only when that exact directional action is
  exposed by the bound AT-SPI frame. Generic move actions and inferred keyboard
  shortcuts are rejected.
- A confirmed, irreversible `clear clipboard` command invokes only Wayland's
  fixed `wl-copy --clear` vector. It never reads or audits clipboard content and
  deliberately leaves the separate PRIMARY selection unchanged.
- A separate confirmed command copies the exact content of the currently
  focused AT-SPI text field through stdin to a fixed `wl-copy --type
  text/plain;charset=utf-8` process. Password/protected fields, empty text,
  NULs and content above 100,000 characters fail closed; the copied text never
  appears in argv, confirmation, result messages or the audit log.
- A confirmed current-line command reads only the line surrounding the AT-SPI
  text cursor, one character at a time, with a hard 1,000-character limit.
  Protected fields fail closed and the spoken line is redacted from the audit
  log. Two local commands move an unselected cursor to that line's exact start
  or end, verify the result, and restore the prior offset on mismatch.
- A local `select current line` command reuses those bounded line offsets,
  excludes the newline, requires an initially empty selection, verifies the
  exact selection and final caret, and restores the original cursor with no
  selection if AT-SPI reports any mismatch. Empty lines fail explicitly.
- A confirmed `delete current line` command removes the bounded nonempty line
  and exactly one matching newline: the following delimiter when present, or
  the preceding delimiter for the final line. It verifies the complete result,
  caret and empty selection, and restores the full prior field on mismatch.
- A confirmed `replace current line with …` command accepts 1–500 printable
  dictated characters, preserves surrounding newlines, verifies the complete
  field, final caret and empty selection, and restores the full prior state on
  mismatch. Neither old nor replacement content is repeated or audited.
- Two confirmed commands insert a new 1–500-character printable line directly
  above or below the bounded caret line. They support an empty field, preserve
  all existing text, verify full readback/caret/selection state, roll back the
  complete field on mismatch, and redact the dictated line from the audit.
- Two confirmed commands duplicate the bounded nonempty current line directly
  above or below itself. They never repeat or audit the copied content, require
  exact full-field/caret/selection verification, and restore the prior field and
  cursor if AT-SPI reports a mismatch.
- Two confirmed commands move the bounded current line up or down by swapping
  it with exactly one adjacent line. Both lines are capped at 1,000 characters;
  their contents remain out of requests/results/audits, relative caret position
  is preserved, and the complete field is restored on any mismatch.
- Two confirmed commands join the current line with the previous or next line
  by deleting exactly one verified newline. Both lines remain bounded, content
  stays out of requests/results/audits, the logical caret position is retained,
  and the entire prior field is restored on failure.
- A confirmed `split current line at the text cursor` command inserts exactly
  one newline at the bound caret, including at either line edge or in an empty
  field. It rejects active selections, verifies complete text, the advanced
  caret and empty selection state, and restores the prior field on mismatch.
- Confirmed `indent/outdent current line` commands add exactly four leading
  spaces or remove exactly one leading tab/up to four leading spaces. They keep
  the logical caret position, expose no line content, verify the complete field
  and restore its prior state on any mismatch.
- A distinct confirmed `copy text selection` command requires exactly one
  nonempty AT-SPI text selection in the focused safe field. Its offsets must be
  ordered, inside the reported character count and no more than 100,000
  characters apart; ambiguous, protected, incomplete or NUL-containing spans
  fail before the same stdin-only Wayland writer is called.
- A confirmed `delete text selection` command removes exactly one nonempty
  selection from the focused safe editable text object. It verifies the full
  resulting content and empty selection state; rejection or mismatch restores
  the previous content, caret and selection. Text content is never repeated.
- A confirmed `insert text at cursor` command inserts one printable dictated
  string of at most 500 characters at the validated caret of the focused safe
  editable text object. It requires no active selection, verifies the complete
  resulting content and caret, and restores the prior content and caret on any
  rejection or mismatch. Dictated content is redacted before audit signing.
- Two confirmed semantic editing commands delete exactly one AT-SPI character
  immediately before or after the validated caret. They require no selection,
  are idempotent at the corresponding text boundary, verify complete content
  and caret state, and restore both on any rejection or mismatch.
- Two local semantic selection commands mark exactly one AT-SPI character before
  or after the validated caret without reading its content. They require no
  existing selection, move the caret to the selected edge, are idempotent at
  text boundaries, and restore an empty selection plus the prior caret on any
  mismatch.
- Two confirmed semantic read commands announce exactly one AT-SPI character
  immediately before or after the validated caret. They fetch only that
  one-character span, perform no content read at a text boundary, reject
  protected or invalid fields before access, name whitespace explicitly, and
  redact the spoken character from the signed audit trail.
- Two confirmed word-orientation commands announce the previous or next
  Unicode word at the validated caret. They inspect only one-character AT-SPI
  spans, cap the search at 256 characters and the spoken word at 128
  characters, perform no content access at the corresponding field boundary,
  and redact the complete result before audit signing.
- Two local word-navigation commands move the validated caret to the previous
  or next Unicode word start without keyboard emulation. They reject active
  selections and protected fields, inspect at most 256 one-character AT-SPI
  spans, verify the exact resulting offset, and restore the prior caret on any
  rejection or mismatch.
- Two local word-selection commands mark exactly the previous or next Unicode
  word using at most 256 one-character AT-SPI reads. They require no existing
  selection, move the caret to the word's outer edge, verify the exact span and
  caret, and remove all residual spans plus restore the prior caret on mismatch.
- Two confirmed word-deletion commands remove exactly the previous or next
  bounded Unicode word. They snapshot the complete safe field, verify the full
  resulting content, caret, and empty selection state, and restore the complete
  prior content and caret on rejection or mismatch without repeating the word.
- Two confirmed word-replacement commands replace exactly the previous or next
  bounded Unicode word with one printable dictated string of at most 500
  characters. They verify complete resulting content, place the caret directly
  after the replacement, restore the complete prior field on mismatch, and
  redact the dictated target before audit signing.
- A confirmed `replace text selection` command replaces exactly one nonempty
  safe AT-SPI selection with one printable dictated string of at most 500
  characters. It verifies complete resulting content, caret, and cleared
  selection state; any rejection or mismatch restores the prior content, caret,
  and exact selection. The replacement is redacted before audit signing.
- A separate confirmed paste command reads at most 400,000 bytes from
  `wl-paste --type text` through a nonblocking five-second pipe, requires valid
  UTF-8 with at most 100,000 characters, and replaces only the focused safe
  editable AT-SPI field. Tabs and newlines are preserved; all other control
  characters fail closed. Exact readback is required and a mismatch is rolled
  back, while clipboard content remains absent from speech and audit.
- A confirmed `read clipboard` command uses the same bounded Wayland reader,
  normalizes the text for speech and announces when output beyond 1,000 spoken
  characters is omitted. Because speaking may disclose private data, approval
  is required first; the canonical confirmation contains no clipboard data and
  the complete result message is replaced by a redaction before audit signing.
- A confirmed `write to clipboard …` command accepts one printable dictated
  string of at most 500 characters, marks overwriting as irreversible and sends
  the text only through stdin to the fixed Wayland writer. The confirmation and
  result never repeat it; both this target and existing focused-field dictation
  are replaced by action-specific markers before the audit HMAC is computed.
- Trusted-confirmation commands can enable GNOME's built-in on-screen keyboard,
  Orca screen reader or screen magnifier through three fixed `gsettings`
  argument vectors.
  They accept no caller-controlled parameters. Voice commands to disable the
  on-screen keyboard or screen reader are intentionally not provided.
- A separate confirmed recovery command restarts Orca with speech explicitly
  enabled. Its packaged session adapter accepts only literal `restart`, spawns
  exactly `orca --replace --enable speech` as a detached process and reports an
  immediate startup exit; arbitrary Orca options are never accepted.
- A separate trusted-confirmation command sets the GNOME magnifier to an exact
  integer percentage from 100 through 3,200. The value is the only accepted
  argument and is converted to the schema's `mag-factor` double without shell
  interpretation.
- A separate trusted-confirmation command disables the GNOME magnifier through
  a fixed parameterless `screen-magnifier-enabled false` vector. Its spoken
  summary explicitly states that Orca and the on-screen keyboard stay enabled;
  no voice command disables either of those rescue facilities.
- Separate trusted-confirmation commands enable or disable the magnifier's
  lightness inversion using fixed boolean `gsettings` vectors. Disabling this
  visual filter does not disable the magnifier or another accessibility rescue
  facility.
- Magnifier color saturation can be set to an exact confirmed integer from
  0 through 100 percent; zero provides grayscale. The only accepted value is
  converted to the schema's `color-saturation` double without shell parsing.
- Magnifier brightness and contrast can each be set to an exact signed integer
  from -75 through +75 percent, matching GNOME Control Center. A packaged local
  adapter applies the canonical fraction to all three RGB channels with fixed
  argv vectors and rolls back already changed channels after a partial failure.
- The magnified view can be confirmed as full screen or restricted to the
  top, bottom, left or right half. Spoken phrases map only to GNOME's five
  installed `screen-position` enum values; arbitrary schema text is rejected.
- Separate confirmed commands show or hide the magnifier crosshairs through
  fixed boolean `show-cross-hairs` vectors. Hiding this visual guide does not
  disable the magnifier or another accessibility rescue facility.
- Magnifier crosshair opacity can be set to an exact confirmed integer from
  0 through 100 percent. The only accepted value is converted to the installed
  schema's `cross-hairs-opacity` double without shell parsing.
- Separate confirmed commands can make the crosshair lines stop around the
  magnified pointer or pass through it. Both use fixed boolean
  `cross-hairs-clip` vectors and do not disable the crosshairs or magnifier.
- Magnifier crosshair length can be set to an exact confirmed integer from 20
  through 4,096 pixels, matching the installed `cross-hairs-length` schema
  bounds. No caller-controlled text reaches the command vector.
- Magnifier crosshair thickness can be set to an exact confirmed integer from
  1 through 100 pixels, matching the installed GNOME Control Center slider.
  Only the validated decimal integer is appended to the fixed
  `cross-hairs-thickness` command prefix.
- Magnifier crosshair color accepts either a bounded common color name or exact
  red, green and blue integer channels from 0 through 255. Both routes produce
  the same typed RGB request; the executor alone formats canonical lowercase
  `#rrggbb` for the fixed `cross-hairs-color` prefix.
- Magnifier focus tracking can be confirmed as off, centered, proportional or
  push mode. Bounded German/English phrases map only to the four installed
  `focus-tracking` enum values; turning tracking off does not disable zoom.
- Separate confirmed commands apply the same four installed modes to magnifier
  text-caret and mouse-pointer tracking. They target only `caret-tracking` or
  `mouse-tracking`; disabling either tracker does not disable magnification.
- Separate confirmed commands enable or disable magnifier lens mode and
  scrolling at screen edges. Each action uses a fixed boolean `lens-mode` or
  `scroll-at-edges` vector, accepts no parameters and does not disable the
  magnifier or another accessibility rescue facility.
- One exactly and uniquely named visible AT-SPI element can receive focus even
  when it has no executable action, provided it explicitly exposes Focusable
  state and accepts `grabFocus()`. Clausis verifies Focused state and restores
  the previously focused element on a failed transition when possible.
- The focused AT-SPI entry/text/document-text field can be read aloud without
  confirmation. Reads are capped at 1,000 characters and normalized for
  speech; password, protected, secret and uninspectable fields fail closed, and
  the returned text is explicitly removed from the tamper-evident audit log.
- One exactly named AT-SPI progress bar in the active window can be read aloud
  as a percentage. Clausis accepts only a unique `progress bar` role with a
  finite, ordered range and a current value inside that range; it never writes
  through the Value interface.
- Confirmed text entry replaces only the currently focused AT-SPI editable-text
  widget, verifies readback, rolls back mismatches and never speaks the dictated
  value in its confirmation summary. Password, protected, secret and
  uninspectable fields fail closed.
- Confirmed list selection is restricted to the nearest focused AT-SPI
  `Selection` container. It requires one exact direct-child name, replaces and
  verifies the complete selection, and restores the previous selection on
  disagreement.
- A recognized active file chooser can mark one exact visible file or folder
  name in exactly one selection container. This action never invokes Open,
  Save or Select. Separate confirmed commands accept or cancel only a
  recognized chooser with one exact Open/Save/Select/Choose and Cancel pair;
  the same application, its complete ordered top-level window list, the active
  dialog and both concrete controls are rebound immediately before invocation.
  Success requires that exact original window order minus only the chooser
  within two seconds; replacement, ambiguity, an unchanged chooser or any
  foreign window mutation fails explicitly.
- A recognized Save dialog can set one single file name only in its focused,
  exactly labelled Name/File Name/Dateiname editable field. Readback and
  rollback are verified on the already-bound node; the Save control is never
  invoked by this action.
- A recognized file chooser can set one absolute canonical POSIX path only in
  its focused, exactly labelled Location/Path/Ort/Pfad editable field. The
  already-bound field is read back and rolled back on disagreement; no Enter,
  Open, Save, Select or Choose action is invoked.
- A recognized file chooser can navigate into one exact visible folder only
  when that direct selection child is uniquely named, carries semantic folder
  evidence (folder/directory role, exact folder attribute, or localized folder
  icon), and itself exposes an exact Open or Activate action. A file-like item,
  duplicate target or click-only item fails closed; the dialog accept control
  is never used for this navigation.
- In the nearest focused AT-SPI tree or tree table, one exact uniquely named
  tree item/row can be expanded or collapsed only through its exact Expand or
  Collapse action. Expandable/expanded state is checked before execution and
  the requested expanded state is read back afterwards. Rejection, mismatch or
  an exception after partial expansion uses the exact opposite action to
  restore and verify the prior state; rollback failure is distinct. Ordinary
  lists, duplicate names and generic click/toggle actions fail closed.
- In the nearest focused AT-SPI table or tree table exposing Selection, one
  exact row can be selected by its row name or an exact cell name. The target
  must resolve to exactly one direct row; values repeated across rows fail
  closed. Clausis replaces and verifies the complete direct-child selection
  bitmap and restores the previous bitmap on rejection or mismatch. A generic
  list is not accepted as a table.
- In the nearest focused AT-SPI page-tab-list exposing Selection, one exact
  uniquely named direct page tab can be selected. Clausis replaces and verifies
  the complete direct-child selection bitmap and restores it on rejection or
  mismatch; duplicate names and generic lists fail closed.
- One uniquely and exactly named AT-SPI slider in the bound active window can
  be set to a confirmed percentage from 0 through 100. The percentage is mapped
  to the widget's declared minimum, maximum and discrete increment; Clausis
  reads the result back and restores and verifies the previous value if the
  control rejects, partially mutates and raises, or reports a mismatch. A
  failed rollback is reported separately. Non-slider roles and invalid ranges
  fail closed.
- One uniquely and exactly named AT-SPI check box can be confirmed on or off
  only through its exact Toggle action and a checked-state readback. Rejection,
  mismatch or an exception after partial toggling restores and verifies the
  previous state; a failed rollback is reported separately. A radio
  button can likewise be selected through one exact Select or Click action;
  Clausis rejects multiple checked starting options, verifies the complete
  group bitmap and restores and verifies the previously checked radio button
  after rejection, mismatch or exceptional partial selection. Duplicate names,
  wrong roles, ambiguous actions and failed rollback remain closed failures.
- One uniquely and exactly named AT-SPI combo box exposing Selection can select
  one exact unique direct menu-item, list-item or option child. Clausis replaces
  and verifies the complete direct-child selection bitmap and restores the
  previous bitmap on rejection or mismatch. Generic lists, nested guesses,
  duplicate item names and unrelated child roles fail closed.
- One uniquely and exactly named AT-SPI spin button can be set to a confirmed
  finite numeric value within its declared minimum and maximum. The requested
  number must fit the declared increment exactly; Clausis does not silently
  round it. Readback is verified and the previous value is restored and
  verified on rejection, exceptional partial mutation or mismatch. A failed
  rollback is reported separately. Sliders, duplicate names and invalid ranges
  fail closed.
- One uniquely and exactly named AT-SPI switch can be confirmed on or off only
  through its exact Toggle action and a checked-state readback. Idempotent
  requests do not invoke the control. Exceptional partial toggles restore and
  verify the previous state, while a failed rollback is distinct. Check boxes,
  duplicate names, ambiguous actions and unchanged post-state fail closed.
- In the nearest focused AT-SPI menu or menu bar, one exact unique direct menu,
  check-menu or radio-menu item can be confirmation-gated and invoked only when
  it exposes exactly one Activate, Click or Press action. Ordinary lists,
  duplicate names, unrelated roles and ambiguous actions fail closed; Clausis
  never searches unrelated menus in the window for this command.
- A recognized active permission dialog can invoke exactly one side of one
  unambiguous Allow/Deny, Grant/Deny Access or Share/Don't Share pair. The
  application, complete ordered top-level window list, active dialog and both
  AT-SPI controls are rebound immediately before invocation; ordinary
  OK/Cancel dialogs, regular windows, duplicate controls and multiple decision
  groups fail closed. Afterwards Clausis polls for at most two seconds and
  accepts only the same application-window order without that dialog.
  Unchanged, foreign-mutated or unreadable state fails explicitly. Allowing and
  denying both require confirmation.
- A regular active dialog can be confirmed, cancelled, explicitly retried or
  applied only when it exposes exactly one conventional OK/Cancel, Yes/No,
  Confirm/Cancel, Retry/Cancel or Apply/Cancel pair. Retry and Apply have
  distinct commands and cannot be substituted for one another. File
  choosers and permission pairs are excluded, the action is classified as
  high-risk and non-reversible, and the same application, complete ordered
  top-level window list, dialog and both concrete controls are rebound
  immediately before invocation. Success requires that exact original window
  order minus only the dialog within two seconds. Duplicate groups,
  replacement nodes, ambiguous actions, an unchanged dialog and every foreign
  window mutation fail explicitly.
- A separate confirmed `read the dialog` command speaks only unique static
  labels, paragraphs and descriptions from one active regular dialog. It never
  queries editable text, excludes file choosers and protected nodes, caps the
  result at 20 items and 1,000 characters, and redacts the complete spoken
  result from the signed audit trail.
- A confirmed `close the dialog` command is separate from closing a normal
  window and accepts only an active regular dialog whose complete actionable
  surface is one exact Close/Schließen/Dismiss control. File choosers, paired
  decisions, extra controls, ambiguous actions and window/control replacement
  fail before the non-reversible high-risk invocation. The complete ordered
  application-window snapshot is also rebound immediately before it. Afterwards Clausis polls
  for at most two seconds and reports success only when the same bound
  application exposes the exact original top-level window order without that
  dialog; unchanged, foreign-mutated or unreadable state fails explicitly.
- Strict, versioned action messages and an allowlisted action broker.
- Provenance tainting for every Hermes or external-content action.
- Short-lived, single-use, action-bound confirmation capabilities.
- Trusted-confirmation state machine with random phrases and a derived PIN.
- Shell-free fixed-argument execution, dry-run by default.
- Tamper-evident, privacy-redacted audit records.
- Audio capability degradation and secret-free installer plan validation.
- Conservative read-only disk discovery that excludes the live medium,
  removable, mounted, read-only, undersized and unstably identified devices;
  plans are rebound to stable ID, exact size and serial suffix before hand-off.
- Calamares defaults to no destructive selection, preselected LUKS2 encryption,
  a separate boot partition and Btrfs root; keyboard and Orca manual mode remain.
- D-Bus interface definitions, hardened systemd units, Polkit and Debian
  packaging scaffolding.
- Local microphone capture, Faster-Whisper transcription and system TTS.
- Hermes Agent 0.20.0 preinstalled from a pinned upstream commit as the offline
  fallback. During installation Clausis checks the official upstream for the
  latest stable release, installs its frozen dependency lock and switches over
  only after a successful installation.
- Accessible Hermes provider setup before Calamares with local spoken provider
  choice, explicit cloud consent, masked keyboard-only API-key entry and Orca.
- The local offline assistant now starts before Calamares even when GPT Live is
  not selected, so window orientation, control lists, back and stop remain
  spoken without a network connection.
- Optional GPT Live mode for low-latency online speech during installation and
  on the installed desktop. It is off by default, needs a separate explicit
  audio-transmission consent and a keyboard-only OpenAI API key, and falls back
  to local voice control when unavailable.
- GPT Live can request only Clausis' typed allowlisted actions. It receives no
  shell, arbitrary program, plug-in, MCP or capability-token access; medium and
  higher-risk actions still require the separate trusted confirmation path.
- A desktop entry named **GPT Live sofort beenden** stops online audio locally,
  without waiting for the model or an internet connection. Reopening
  **Clausis und Hermes einrichten** lets the user disable GPT Live permanently.
- Automatic offline voice-control start after installation; “Stopp Hermes”
  stops it locally without asking a cloud model.
- Reproducible Debian Stable amd64 ISO build with GNOME, Orca and Calamares.

The remaining work before Clausis can honestly be called fully voice-operated
is tracked in
[`docs/VOICE_ONLY_GAP_ANALYSIS.md`](docs/VOICE_ONLY_GAP_ANALYSIS.md). The main
missing pieces are a dedicated low-latency wake-word/barge-in detector, broader
GNOME/portal coverage, physical confirmation-audio isolation, enforced
voice-native installation, a protected keyboard/Orca confirmation path and
boot/login/recovery audio. A reproduced VirtualBox failure showed that GNOME's
low-level power-key inhibitor could receive an ACPI event without initiating
shutdown. The image now includes an independent `acpid` fallback which queues
`systemctl --no-block poweroff` only when `systemd-detect-virt --vm` confirms a
virtual machine; releasing acpid immediately avoids serially holding its event
handler until S5. Diagnostic runs proved that VirtualBox can report a
successful host request without delivering any power-key event to either
`systemd-logind` or the active `acpid` service. The readiness-gated smoke test
verifies rendered Clausis branding in both GRUB and the complete desktop before
sending exactly one request. A fail-closed soak harness repeats that complete
gate against one fixed ISO hash and writes a machine-readable summary even
after a partial failure. The latest five-run series passed 5/5, reaching
poweroff in 9.4 to 13.7 seconds per run. Its host-side state reader also retries
VirtualBox 7.2's transient direct-session console-object race. Longer endurance
coverage and physical power-button behavior remain open release gates;
physical buttons stay owned by GNOME.
The installer now creates a high-entropy spoken
recovery key, requires the user to read all twelve noted groups back correctly,
and adds it directly to the encrypted LUKS2 system without placing
the key or disk passphrase in process arguments or Calamares state; the complete
install-and-unlock path still needs persistent-VM and hardware validation. A
host-side sandbox harness now creates a fresh dynamic VDI only below the
project's `dist/clausis-install-sandbox-*` directory, boots the exact ISO in a
separately registered EFI VM, verifies the live readiness gate and deletes only
that disposable VM/VDI in `finally`. This establishes the safe test boundary;
it does not yet claim that the protected Calamares and unlock flow completed.
A delayed foreground capture proves that the accessible Clausis setup dialog
does appear first with offline mode selected; Calamares is intentionally gated
behind completing that synchronous setup step rather than missing or silently
failing to start. A later disposable-VM probe safely filled both matching local
PIN fields through GTK mnemonics. The final readiness-gated probe focused the
save button through the declared GTK tab order, captured that state, activated
it with Enter and then proved the visible Calamares welcome page. Calamares was
not operated beyond displaying that page; partitioning and installation remain
explicit release blockers. A later disposable-only preflight also traversed
Location and Keyboard to the Partitions page. It showed only the fresh 64-GiB
VirtualBox disk, with neither Erase nor Manual selected and Next disabled; no
partition choice or disk write was made. Follow-up keyboard-only attempts to
select Erase did not produce a visually confirmed selection and were rejected
by the fail-closed screenshot gate; every disposable VM/VDI was removed. The
safe Erase-selection path therefore remains open and progress stays at 80%.
A GUI-mode follow-up exposed that sent navigation keys could previously count
as success while Calamares still displayed its Welcome requirements spinner.
The VBox harness now fails closed unless the Partitions navigation highlight is
visually detected in the captured guest framebuffer.
Further diagnostics found that privileged Calamares exposed only its Mutter
window frame, not its Qt controls, over AT-SPI. The live launcher now preserves
Qt accessibility settings and the explicit `org.a11y.Bus` address across the
privilege boundary. The rebuilt ISO is verified, but an exact Erase radio still
was not visually selected; this gate therefore remains open at 80%.
A subsequent visible VirtualBox GUI test bound one unique disposable-VM window
and clicked the actual Erase radio once. Guest-framebuffer evidence proves the
selected radio, encryption enabled by default, and the proposed 512-MiB EFI,
1-GiB `CLAUSIS_BOOT` ext4 and 62.5-GiB `CLAUSIS_ROOT` Btrfs layout. Passphrase
fields remained empty, Next remained disabled and no disk write occurred. This
closes the selection-only gate and raises overall progress to 81%.
A follow-up disposable GUI run entered matching throwaway encryption
passphrases, proved the green validation state and LUKS2 target, then used the
unique Next mnemonic to reach the Users page. No user fields, Summary, Install
control or disk job were touched. This closes the encrypted Partitions-to-Users
navigation gate and raises overall progress to 82%.
A further disposable run filled valid throwaway Users data, kept automatic
login disabled and reached Summary. The summary bound Erase to `/dev/sda (VBOX
HARDDISK)` and listed the new GPT, EFI, boot and encrypted-root jobs. Install
was never activated and the sandbox was removed. This closes the pre-install
summary gate and raises overall progress to 83%.
The full destructive installer flow is now proven on a dedicated disposable
VirtualBox disk. Calamares completed, the ISO was removed, the installed disk
booted to the graphical LUKS prompt, the temporary passphrase unlocked it, GDM
showed the created user and login reached the installed Clausis desktop. The
installed setup dialog, active speech-control notice and matching Hermes Agent
launcher icon were visible. The test VM/VDI was then deleted. Overall progress
is now approximately 90%; recovery-key boot, failure recovery and physical
hardware validation remain open.

## Build the installation ISO

Docker Desktop with amd64 emulation and at least 25 GB free storage is needed:

```sh
./scripts/build_iso.sh
```

The build entry points are pinned to LF by `.gitattributes`. Inside the builder,
the copied source tree also normalizes text line endings and restores only the
intentional executable modes, so the same command works from Windows/WSL DrvFS
checkouts without a separate `dos2unix`, `chmod` or temporary source copy.

The hybrid BIOS/UEFI image and SHA-256 file are written to `dist/`. See
[`docs/INSTALL_USB.md`](docs/INSTALL_USB.md) before selecting or overwriting a
USB device.

## Development

No network download is required for the core test suite:

```sh
PYTHONPATH=src python3 -m unittest discover -s tests -v
PYTHONPATH=src python3 -m clausis.cli route "Lautstärke 35 Prozent"
printf 'Netzwerkstatus\nStopp Hermes\n' | PYTHONPATH=src python3 -m clausis.runtime --stdin
```

The source/developer runtime remains a dry-run unless `--execute` is selected.
Its semantic action partition is fail-closed: only 12 explicitly enumerated
read-only operations reach the AT-SPI adapter in dry-run, while every other
current or future semantic action is derived as a mutation and blocked before
adapter dispatch.
The live-image launcher enables validated low-risk platform actions. Privileged
and medium-or-higher-risk actions without trusted confirmation fail closed.

## Trust boundaries

Hermes does not receive terminal, code-execution, file-write, skill-write or
capability-signing access. In version 0.4.1 Hermes is a reply-only fallback and
is launched with only its local `todo` toolset; it cannot send system actions to
the broker. The optional OpenAI Realtime frontend can propose only the fixed
action names published by Clausis; every proposal is reconstructed and checked
locally by the same typed broker. A separate trusted-confirmation service owns
confirmation phrases and capability issuance.

GPT Live sends microphone audio to OpenAI while it is active. The OpenAI API is
billed separately; a ChatGPT subscription does not automatically provide API
credit. Clausis stores the supplied API key in the selected user's private
configuration file (mode `0600`), never in the public installer plan, and does
not bundle a key. This technical preview does not yet provide a backend for
short-lived client tokens, so other malicious processes already running as the
same desktop user remain a credential-theft risk.

During the live installation GPT Live is a spoken companion and can control the
currently supported Clausis desktop actions. Calamares disk partition fields
are not yet controlled directly by GPT Live; those remain available through
the graphical, keyboard and Orca paths. A small source-built Calamares patch
exports only the non-secret selected target, mode, encryption state and
filesystem. Clausis rebinds those values immediately before the first
partition job and blocks a changed or weakened whole-disk proposal. The
protected phrase is now generated, spoken and checked inside that exact
pre-write process without entering Calamares state or stdout. Physical
trusted-audio isolation and persistent VirtualBox install/unlock validation are
still missing, so fully voice-native partitioning remains release-blocked.

Trusted confirmation no longer exposes `Begin`, `Approve`, a challenge phrase,
a PIN or a capability through the public D-Bus interface. The isolated
`clausis-confirm` system service speaks its own canonical summary, captures the
random phrase and PIN directly with the pinned local speech runtime, submits
the resulting action-bound capability to ActionBroker itself, and returns only
the final action result. At every protected recording step, an exact local
`Abbrechen`, `Stopp Clausis` or English equivalent aborts fail-closed, deletes
the temporary recording and is acknowledged locally. The installer stages only
a PBKDF2 verifier; plaintext PIN and raw confirmation recordings are not
persisted. Physical isolation from the desktop PipeWire graph, replay detection
and hardware validation remain production release blockers.

The latest recovery-guard audit found and fixed a Calamares mode-binding bug:
Erase mode is now exported as the flat `clausisInstallMode` value and verified
inside the built ISO. The corrected ISO passes all 722 project tests and the
complete structural verifier. A fresh disposable VirtualBox test of the
fail-closed recovery exchange now proves rejection without microphone input,
secret cleanup, an absent partition table and an unchanged target prefix.
Positive spoken readback and recovery-key unlock remain release blockers;
current overall progress is approximately 91 percent.

The final negative-gate ISO is SHA-256
`c7ad5e541f47632bd91bb4b70317517c503255db893a085db76b2c5e12061671`.
Its VirtualBox probe invokes the exact packaged Python bridge, requires the
bridge-owned `denied` response, verifies recovery-secret cleanup, confirms no
partition table and compares the first four MiB before and after. Missing or
unknown Calamares modes and timed-out speech backends fail closed.

Encrypted installations now have a second independent safeguard: the patched
Calamares LUKS job refuses to finish when no confirmed staged recovery key is
present. The final verified ISO is SHA-256
`994d47a50f9ab755ef1bb69ba2a8f6972b91c9d968800667bba0a67719513185`.
The installer bridge now runs through the pinned `/opt/clausis` voice runtime.
A disposable VirtualBox gate has proven real TTS output, PipeWire sink-monitor
capture and local Faster-Whisper recognition. Full 48-digit spoken readback,
actual key enrollment and recovery unlock remain open; overall progress is
approximately 93 percent. Full-length VirtualBox trials additionally led to
digit-by-digit group speech, a Recovery-only 90-second recording window and
bounded segmented TTS calls. The rebuilt ISO passes structural verification;
the exact 48-digit positive gate still fails closed at runtime and remains open.

## Licensing and AI notice

Clausis-owned code is GPL-3.0-or-later. Hermes Agent remains a separate MIT
component; its notice is preserved in the image. The MIT-licensed converted
`Systran/faster-whisper-base` model is bundled for offline speech recognition.
Its four runtime files are pinned by SHA-256. The image builder may reuse a
local cache extracted from a previously verified ISO only after checking the
complete manifest; the live-image hook and final ISO verifier check the same
hashes again. A missing or modified file fails the build instead of silently
changing the speech model.
No cloud credential or proprietary model weight is bundled.

The online installer accepts only the latest non-draft, non-prerelease tag from
the official `NousResearch/hermes-agent` GitHub repository. It records the tag
and commit in `/var/lib/clausis/hermes-install.json`. If lookup, download or the
frozen install fails, the pinned image version remains active and the first
installed login reports the fallback by speech and notification.

AI-assisted tools contributed to architecture, implementation and review.
Human maintainers remain responsible for validation and release approval; see
[`docs/compliance/AI_CONTRIBUTION.md`](docs/compliance/AI_CONTRIBUTION.md).
