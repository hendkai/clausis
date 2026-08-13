# Clausis architecture

Status: executable core prototype, version 0.4.1.

## Data flow

```text
microphone -> local STT -> VoiceRuntime -> OfflineRouter -> ActionBroker
                               |
                               +-- unmatched -> HermesOneShot -> spoken reply

microphone -> optional OpenAI Realtime -> typed function request -> ActionBroker
     ^                    |                                      |
     +---- streamed TTS <-+                         trusted confirmation for risk
```

The unprivileged audio frontend owns local STT, activation state and TTS. Its
local gate discards background transcripts until “Hallo Clausis”, expires the
short command window automatically and recognizes stop before an agent or cloud
fallback. Recording uses adaptive energy detection. Dedicated low-power
wake-word inference, echo cancellation and a tested interruption detector for
true barge-in remain open; all current hardware therefore announces
half-duplex. `VoiceRuntime` always checks deterministic offline commands first.
Only unmatched activated utterances may be sent to Hermes, and only after cloud
consent when a remote provider is used.

The pinned Faster-Whisper base model has a four-file SHA-256 manifest. A
previously verified ISO may seed the live-build output cache, but the builder
copies only the named files after a complete manifest check. The chroot hook
checks again before deciding whether an online download is needed, and the
final ISO verifier independently extracts and verifies the same files.

GPT Live is a separate, voluntary frontend. When enabled, 24 kHz PCM microphone
audio is streamed over a TLS WebSocket to the configured OpenAI Realtime model,
and returned PCM speech is played immediately. The model sees one narrow
`clausis_action` function and a stop function. It never receives a shell,
generic computer-use tool, capability token or arbitrary executable. Function
arguments are parsed with a strict schema, and origin, minimum risk and
reversibility are replaced with canonical local policy values before broker
submission. If connection or audio startup fails, the assistant announces the
failure and returns to local STT automatically.

## Trust boundaries

1. **Voice Runtime** is unprivileged and replaceable. A compromised STT model
   can propose requests but cannot execute them.
2. **Hermes OneShot** receives only unmatched text and is launched with the
   explicit local `todo` toolset. Its plain-text reply can be spoken but cannot
   become a system action. The separately tested typed `Hermes Adapter`
   discards caller-supplied origins and capability tokens, but is not connected
   to the 0.4.1 runtime yet.
3. **GPT Live frontend** holds the user's OpenAI key and streams audio only
   after separate opt-in. Its model can propose fixed typed actions, but cannot
   execute or confirm them. A per-user local stop marker and desktop launcher
   terminate streaming without cloud cooperation.
4. **Action Broker** accepts only allowlisted verbs and validated arguments. It
   does not accept shell strings and cannot reduce an action's minimum risk.
5. **Trusted Confirm** runs as the separate `clausis-confirm` system user. Its
   public API has only `ConfirmAndSubmit(request)`: the service creates and
   speaks the canonical summary and random phrase, captures phrase and PIN
   through its direct local audio frontend, and submits the capability to the
   broker itself. Neither secrets nor the capability are returned to the
   desktop caller. Tokens bind action, target, arguments, origin and expiry and
   are single-use.
6. **Platform adapters** translate one approved action into a fixed argv vector
   or desktop API call. Missing adapters fail closed.
7. **GNOME semantic adapter** runs inside the unprivileged user session and
   reads the bounded AT-SPI tree. It uses no screen coordinates or global input
   synthesis. Read-only orientation is low risk; arbitrary numbered activation
   is medium risk and requires a capability.

Broker and confirmer receive a root-created HMAC credential through systemd
credentials; Hermes and the desktop session do not receive it. The voice PIN
is enrolled before installation, persisted only as a versioned PBKDF2 verifier
and copied into the target through bounded, no-following Calamares code. The
service remains disabled when no verifier exists. Physical microphone/seat
isolation and replay resistance are not yet proven on supported hardware.

## Public action interface

```json
{
  "action": "file.move_to_trash",
  "target": "/home/user/example.txt",
  "arguments": {},
  "origin": "hermes",
  "risk": "high",
  "reversible": true,
  "capability_token": null,
  "expires_at": null
}
```

The versioned D-Bus names are `org.clausis.ActionBroker1` and
`org.clausis.TrustedConfirm1`. Unknown fields, oversized messages, relative
paths, unsafe identifiers and understated risk are rejected.
`TrustedConfirm1` intentionally exposes no separate begin/approve/deny methods
and accepts no phrase, PIN, file descriptor or capability from a caller.
The local and GPT-Live runtimes call this endpoint only after their in-process
broker has classified a request as confirmation-required. A missing service,
invalid response or audio failure is converted into a denial without exposing
provider or secret details. Every phrase, PIN, recovery-key readback and final
installer-phrase recording recognizes only a complete explicit local abort
utterance. It deletes the temporary recording, announces the abort locally and
does not continue to capability issuance or partitioning.

## Degradation

| Failure | Behavior |
|---|---|
| No network | Offline router continues; an attempted Hermes reply fails after its provider/network error or the 45-second hard timeout. |
| No remote model | Same as no network; no silent provider fallback. |
| GPT Live unavailable | A spoken notice is emitted and the existing local voice loop starts automatically. |
| User wants online audio stopped | “GPT Live sofort beenden” writes a local per-user stop marker; the Realtime loop checks it independently of the cloud. |
| Unknown audio hardware | Device presence is probed locally and Clausis announces safe half-duplex; no Barge-in promise is made. |
| No microphone | Setup, desktop, keyboard and Orca remain available; the current automatic voice loop cannot accept a stop phrase. |
| No audio | Keyboard, visual setup and Orca remain available. |
| Broker refusal | Canonical reason is spoken and displayed; no automatic bypass. |
| Hermes release lookup or install fails | The launcher remains on the pinned image version; status is recorded and announced at first installed login. |
| System package update fails | Health-check and snapshot scaffolding exist, but automatic rollback is not wired in 0.4.1. |

## Implemented for the 0.4.1 image

- Hermes Agent 0.20.0 is installed from pinned upstream commit
  `0957277f2f468bac22bbfcfa7c43029858c9597e` with its frozen dependency set
  and upstream's pinned uv 0.9.28.
- After Calamares creates the target account, Clausis queries only the official
  GitHub latest-release endpoint, rejects drafts, prereleases and unexpected
  tag formats, fetches that exact tag and installs it with its `uv.lock`.
  `/usr/local/bin/hermes` is atomically switched only after the new executable
  exists; the image copy stays available as a fallback. The release tag,
  resolved commit and publication time are recorded locally.
- The live-session setup is labelled for assistive technology, starts Orca
  before the installer, supports local provider-name and cloud-consent speech
  recognition and never accepts API keys through speech.
- A Calamares shell-process job copies the private staged Hermes configuration
  into the newly-created target account after the user job completes.
- Unmatched voice questions use Hermes one-shot replies after provider setup;
  only the `todo` toolset is exposed and the reply is spoken.
- Optional GPT Live setup uses a separate consent and masked key field. The
  assistant streams speech only when both are present and offers only fixed
  broker actions. The setup can be reopened to withdraw consent and erase the
  GPT Live key from Clausis' dedicated managed `.gpt-live.env` file.
- GNOME uses a Clausis listening-field wallpaper, the same emblem for Clausis
  launchers and GDM, supported dark/purple appearance preferences, reduced
  motion, a larger cursor, persistent accessibility status and Atkinson
  Hyperlegible type. These are system defaults, not an invasive GTK fork, so
  application accessibility and future GNOME updates retain their standard
  behavior.
- Local wake gating, activation timeout, always-available stop/sleep phrases and
  hardware capability degradation run before Hermes or GPT fallback.
- The AT-SPI adapter describes the active application/window/focus, lists up to
  30 current semantic controls, navigates back, cycles accessible windows and
  invokes minimize, maximize, restore or close only when the active frame
  exposes that exact action. Cycling refuses an ambiguous active-window state,
  requires the calculated adjacent window to become the sole active window and
  restores and verifies the previous focus after any mismatch. It also invokes
  overview, the application grid,
  quick settings or notifications only through exact controls of the accessible
  `GNOME Shell` application. All of these mutations honor developer dry-run
  mode. Within the active window it cycles focus through current visible
  actionable controls with AT-SPI `grabFocus()`. The cycle rejects multiple
  focused controls, verifies the exact calculated target and restores and
  verifies the previous focus after a mismatch. It can activate one exact,
  uniquely named control after re-reading the tree. Close and arbitrary named
  or numbered activation remain confirmation-gated.
- Notification reading is separate from the notification-center toggle. It
  requires exactly one accessible GNOME Shell application and reads only
  currently Showing nodes with the exact AT-SPI `notification` role plus their
  static descendants. Calendar labels, editable roles and protected nodes are
  excluded; 20 notifications, 40 unique messages and 2,000 characters are
  hard limits, and the complete spoken result is audit-redacted.
- Each spoken notification maps to its visible-object index, including a fixed
  placeholder for an entirely protected item. Numbered dismissal is a separate
  non-reversible high-risk action. It rebinds the same GNOME Shell object and
  the complete ordered notification identity snapshot before invoking exactly
  one Dismiss or Close action; the request contains only the bounded number.
  After invocation a two-second bounded poll accepts only the same Shell and
  the original ordered identity sequence with the selected object removed.
  Any unchanged or otherwise mutated post-state is reported as unconfirmed.
- Semantic dry-run classification is complete by construction. A small explicit
  allowlist contains the 14 orientation/read operations; `SEMANTIC_MUTATIONS`
  is derived as every other member of `SEMANTIC_ACTIONS`. Consequently new
  text, caret, selection or control actions default to blocked in developer
  dry-run instead of requiring a second manually synchronized allowlist.
- Confirmed text entry uses only the focused AT-SPI editable-text interface.
  It rejects sensitive or uninspectable fields, redacts dictated content from
  the spoken confirmation, verifies exact readback and attempts a verified
  rollback on disagreement. No key events or clipboard are synthesized.
- Clipboard clearing is a separate parameterless, confirmation-gated and
  irreversible action using only `wl-copy --clear` in the caller's Wayland
  session. It does not read, return or audit clipboard data and does not touch
  the independent PRIMARY selection. Copying, pasting and bounded clipboard
  reading are exposed as separate policy-bound voice actions below.
- Focused-text copying reuses the bound AT-SPI focus and protection checks but
  preserves the exact text rather than the normalized speech form. It rejects
  empty, protected, incomplete, NUL-containing or over-100,000-character input
  before spawning fixed `wl-copy --type text/plain;charset=utf-8`; content is
  carried only on stdin and is absent from argv, confirmation, result and audit.
- Selection copying separately requires `Text.nSelections == 1`, obtains only
  selection zero, and validates ordered in-range offsets plus a 100,000-character
  span ceiling before exact readback. Empty, multiple, protected, incomplete or
  NUL-containing selections fail closed and never reach the clipboard writer.
- Selection speech reuses that exact single-span boundary without touching the
  clipboard. Because audible output can disclose private content, the action is
  confirmation-gated, normalizes whitespace, and speaks at most 1,000
  characters with an explicit truncation notice. The canonical confirmation
  contains no content, and the audit message/details are replaced with the
  fixed `[REDACTED: selected text]` marker before chain signing.
- Select-all is a separate low-risk, parameterless AT-SPI action for the once-
  bound focused safe text object. It accepts only 1 through 100,000 characters,
  snapshots at most 64 valid existing spans, replaces them with exactly
  `(0, characterCount)`, and verifies `nSelections` plus the exact offsets.
  Rejection or mismatch restores and verifies the previous spans; protected,
  empty, oversized, malformed, or uninspectable text objects fail closed.
- Clear-selection is the matching low-risk correction action. It snapshots at
  most 64 nonempty in-range spans from the once-bound safe text object, removes
  them in descending index order, and requires `nSelections == 0`. An already
  empty selection is idempotent. Partial rejection or an observable mismatch
  removes residual spans, restores every original span in order, verifies the
  full snapshot, and otherwise reports a closed rollback failure.
- Caret-to-start and caret-to-end are separate parameterless low-risk actions
  over the once-bound safe AT-SPI Text interface. Character count and the prior
  `caretOffset` must be inside a 0-through-100,000-character object. The fixed
  target is exactly zero or `characterCount`; an already matching offset is
  idempotent. `setCaretOffset` acceptance and exact readback are required, and
  rejection, exception, or mismatch triggers a verified restoration of the
  prior offset. Password/protected and malformed objects fail before mutation.
- Delete-selection is a confirmation-gated action bound to exactly one nonempty
  selection in the focused safe editable text object. It snapshots at most
  100,000 characters, caret and span, invokes AT-SPI `EditableText.deleteText`,
  and accepts only the exact resulting full content with zero selections. Any
  rejection or mismatch restores and verifies the prior content, caret and
  selection; confirmation and result messages omit the text.
- Caret-previous and caret-next reuse the same bound metadata, mutation,
  readback, and rollback boundary but derive only `max(0, caretOffset - 1)` or
  `min(characterCount, caretOffset + 1)`. Thus each command moves exactly one
  AT-SPI character, including across non-ASCII text, and becomes idempotent at
  the corresponding edge. Callers cannot supply arbitrary numeric offsets.
- Caret description is a separate parameterless read-only action over the same
  once-bound safety checks. It reports only accessible field name, validated
  `caretOffset`, and bounded `characterCount`; it never calls `getText`.
  Protected/password roles are rejected before querying Text, preventing even
  password-length disclosure. Invalid offsets, roles, attributes, or counts
  fail closed without mutation.
- Insert-at-caret is confirmation-gated and accepts one printable 1-to-500
  character target that is redacted before audit signing. The once-bound safe
  editable text object must have no active selection and remain at or below
  100,000 characters. The adapter snapshots complete content and caret, invokes
  `EditableText.insertText`, moves the caret to the exact end of the insertion,
  and verifies full content, caret and zero selections. Any rejection or
  mismatch restores and verifies the prior content and caret.
- Delete-previous-character and delete-next-character are separate confirmed,
  parameterless operations over the same once-bound safe editable text object.
  With zero selections they derive only `[caret-1, caret)` or
  `[caret, caret+1)`, making Unicode code points single semantic characters and
  the corresponding boundary idempotent. `EditableText.deleteText`, complete
  expected-content readback, exact caret, and zero selections are required;
  any failure restores and verifies the prior complete content and caret.
- Select-previous-character and select-next-character are local parameterless
  mutations over the same safe bounded text metadata, but never read content.
  Starting from exactly zero selections they derive only `[caret-1, caret)` or
  `[caret, caret+1)`, add that one span, move the caret to its outer edge, and
  verify span, count, and caret. The corresponding boundary is idempotent; any
  rejection or mismatch removes all residual spans and restores the prior
  empty selection and caret.
- Read-previous-character and read-next-character are separate confirmed,
  parameterless disclosure actions. After role, protection, count, and caret
  validation they call `Text.getText` for exactly `[caret-1, caret)` or
  `[caret, caret+1)`; at the corresponding boundary they return without any
  content call. Space, tab, and newline receive explicit spoken names. The
  confirmation contains no content and the audit result is replaced with a
  fixed side-specific marker before chain signing.
- Read-previous-word and read-next-word are confirmed parameterless disclosure
  actions over the same once-bound role, privacy, count, and caret checks. They
  skip punctuation or whitespace and collect a Unicode alphanumeric word with
  apostrophe, hyphen, and underscore connectors using only one-character
  `getText` calls. At most 256 characters are inspected and at most 128 word
  characters are accepted; the matching field boundary needs no content call.
  The spoken result is replaced by a side-specific audit marker.
- Caret-previous-word and caret-next-word are local parameterless mutations
  over the same once-bound Unicode word classification. They require zero
  selections, inspect at most 256 one-character spans, and derive only the
  previous or next word-start offset. The matching field edge is content-free
  and idempotent. Every mutation verifies the exact caret plus zero selections;
  rejection or mismatch restores and verifies the prior offset.
- Select-previous-word and select-next-word reuse the bounded Unicode word
  search but derive an exact nonempty `[start, end)` span. Starting from zero
  selections, they add only that span, move the caret to its outer edge, and
  verify selection count, offsets, and caret. The corresponding field edge is
  content-free and idempotent. Any failure removes every residual selection
  and restores the prior caret before returning an error.
- Delete-previous-word and delete-next-word are confirmed parameterless edits.
  After the same zero-selection and 256-character word-span search, the adapter
  snapshots the complete bounded field, deletes only the derived span, and
  calculates the exact shifted or unchanged caret for backward or forward
  deletion. Full resulting content, caret, and zero selections are required;
  failure restores and verifies the complete prior content and caret.
- Replace-previous-word and replace-next-word are confirmed typed edits over
  the same bounded span search. A printable 1-to-500-character target is
  redacted before audit signing. The complete prior field is captured, the
  exact expected content is written atomically, and the caret is placed
  directly after the replacement. Full content, caret, zero selections, and a
  100,000-character result ceiling are verified; failure restores the complete
  prior field and caret.
- Replace-selection is confirmation-gated and accepts one printable 1-to-500
  character target that is redacted before audit signing. The once-bound safe
  editable text object must expose exactly one ordered nonempty selection.
  Clausis constructs the complete expected content, applies it atomically,
  moves the caret behind the replacement, and verifies full content, caret, and
  zero selections. Any rejection or mismatch restores and verifies the prior
  complete content, caret, and exact selection span.
- Focused-text paste obtains text only from fixed `wl-paste --type text` through
  a nonblocking reader capped before decode at 400,000 bytes and five seconds.
  Strict UTF-8, a 100,000-character ceiling and a small control-character
  allowlist precede the bound AT-SPI mutation. The adapter verifies exact
  readback and restores the old field content on rejection, exception or
  mismatch; clipboard data is never included in request, speech, result or audit.
- Clipboard speech is a distinct confirmation-gated read action over the same
  bounded reader. It normalizes whitespace and speaks at most 1,000 characters
  with an explicit truncation notice. The challenge summary never includes the
  content, and `AuditLog` replaces both message and details with a fixed
  clipboard redaction before computing the chain HMAC.
- Dictated clipboard writes accept exactly one nonempty printable target up to
  500 characters and no argument object, then reuse the fixed stdin-only
  Wayland writer. The action is irreversible because it overwrites prior state.
  `AuditLog` now replaces dictated targets for both clipboard writes and
  focused-field text entry with distinct fixed markers before chain signing,
  closing the older text-entry request-target disclosure.
- Focused-text reading accepts only AT-SPI entry, text or document-text roles
  whose protection attributes are inspectable. It reads at most 1,000
  characters, normalizes whitespace for speech and rejects password,
  protected or secret markers before querying Text. The spoken content is
  redacted from the audit result and details.
- Progress reading binds the active window once, requires one exact unique
  `progress bar` name and reads only finite AT-SPI Value fields. Minimum must be
  below maximum and current must lie inside the range; the percentage is
  rounded to the nearest integer without calling `setCurrentValue`.
- Confirmed list selection walks only from the focused accessible up to the
  nearest `Selection` interface, requires one exact direct-child name, replaces
  and verifies the complete child-selection bitmap, and rolls the bitmap back
  on failure.
- Visible file/folder selection requires an active recognized AT-SPI file
  chooser, exact accept/cancel controls and one unique matching selection
  container. It only marks the item; Open/Save/Select is intentionally a
  separate confirmation-bound control action.
- Confirmed file-chooser commit binds the same application, the complete
  ordered top-level window snapshot, active chooser and both exact controls at
  the final mutation boundary. It reports success only when a bounded poll sees
  the original window order minus that chooser; unchanged, foreign-mutated or
  unreadable state fails explicitly without claiming rollback.
- Save-file name entry additionally requires an exact Save dialog, distinct
  Save/Cancel controls and a focused editable named Name, File Name, Filename
  or Dateiname. The already-bound node is mutated and verified, preventing an
  active-window switch between validation and write; Save remains separate.
- File-chooser location entry requires a recognized file chooser with distinct
  accept/cancel controls, an absolute canonical POSIX path without `.` or `..`
  components, and a focused editable named Location, Path, Ort or Pfad. The
  already-bound node uses the same verified readback and rollback path as safe
  text entry. The action never synthesizes Enter or invokes Open, Save, Select
  or Choose, so navigation/commit remains a separate confirmed action.
- Visible-folder navigation searches only direct children of AT-SPI Selection
  containers in the once-bound recognized file chooser. One exact unique name
  must have explicit folder evidence through its role, one exact accessibility
  attribute, or a localized folder icon descendant, and the item itself must
  expose Open or Activate. The adapter invokes that item action directly;
  click-only/file-like targets, ambiguity and missing evidence fail closed, and
  the chooser's accept control is not invoked.
- Tree expansion/collapse starts from the focused accessible and walks at most
  twelve parents to the nearest tree or tree-table container. It searches only
  tree-item/row roles in that bound subtree, requires one exact unique name and
  one exact Expand or Collapse action, checks expandable/expanded pre-state and
  verifies expanded post-state. Rejection, mismatch or exceptional partial
  mutation invokes the exact inverse action and verifies the old state; an
  un-restorable state fails distinctly. Ordinary lists, ambiguity and generic
  toggles fail closed.
- Table-row selection starts from the focused accessible and walks at most
  twelve parents to the nearest table or tree-table exposing AT-SPI Selection.
  Only direct row/table-row children are selectable; an exact row name or exact
  cell/table-cell name must identify exactly one row. The complete direct-child
  selection bitmap is replaced and verified through the shared rollback path.
  Duplicate values across rows, generic lists and uninspectable selection state
  fail closed.
- Tab selection starts from the focused accessible and walks at most twelve
  parents to the nearest page-tab-list exposing AT-SPI Selection. Only direct
  page-tab children are eligible and the exact accessible name must be unique.
  The complete direct-child selection bitmap is replaced and verified through
  the shared rollback path; duplicate names, generic lists and uninspectable
  selection state fail closed.
- Slider changes bind the active window once, then require one exact unique
  accessible name with the `slider` role and a finite AT-SPI Value range. A
  requested integer percentage from 0 through 100 is mapped to the declared
  minimum and maximum and rounded to the nearest declared minimum increment.
  The resulting value is read back; rejection, exceptional partial mutation or
  mismatch triggers restoration and numeric verification of the previously
  read value. An un-restorable value has a distinct fail-closed result.
- Check-box state changes bind the active window once and require one exact
  unique `check box` role with exactly one Toggle action. Radio selection
  similarly requires one exact unique `radio button` role with exactly one
  Select or Click action. Checked state is read before and after invocation;
  idempotent requests do not invoke an action. Check-box rejection, mismatch or
  exceptional partial toggling restores and verifies the previous state, with
  a distinct rollback failure. Radio selection rejects multiple checked
  starting controls, verifies the complete group bitmap and restores and
  verifies the prior unique selection after rejection, mismatch or exceptional
  partial selection. Unchanged or un-restorable state fails closed.
- Combo-box selection binds the active window once and requires one exact unique
  `combo box` role exposing AT-SPI Selection. Only an exact unique direct child
  with role `menu item`, `list item` or `option` is eligible. Selection uses the
  shared complete child-bitmap verifier and rollback path; generic lists,
  nested-item inference, duplicate names and other child roles fail closed.
- Numeric spin-button changes bind the active window once and require one exact
  unique `spin button` role with a finite AT-SPI Value range. The requested
  finite number must lie within minimum and maximum and align with a declared
  positive minimum increment within a bounded tolerance; no implicit rounding
  is performed. The value is read back and rejection, exceptional partial
  mutation or mismatch triggers restoration and numeric verification of the
  previously read value. An un-restorable value fails distinctly.
- Switch state changes bind the active window once and require one exact unique
  `switch` role with exactly one Toggle action. Checked state is read before and
  after invocation; exceptional partial toggles restore and verify the old
  state and a failed rollback is distinct. Idempotent requests do not invoke
  the control, while check boxes, ambiguity and unchanged post-state fail closed. This deliberately
  remains distinct from the `check box` action despite the shared state logic.
- Menu-item activation starts from the focused accessible and walks at most
  twelve parents to the nearest `menu` or `menu bar`. Only direct `menu item`,
  `check menu item` or `radio menu item` children are eligible; an exact name
  must be unique and exactly one Activate, Click or Press action must exist.
  Generic lists, unrelated menus, role mismatches and ambiguous action surfaces
  fail closed. The action remains confirmation-gated because menu effects vary.
- Permission decisions require an active AT-SPI dialog or alert and exactly one
  complete allow/deny, grant/deny-access or share/don't-share control pair.
  The application, complete ordered top-level window identities, active dialog
  and both controls are rebound immediately before invocation. A bounded
  postcondition accepts only the same application-window order minus that
  dialog; unchanged, foreign-mutated or unreadable state never reports success.
  Generic OK/Cancel dialogs, ordinary application frames, missing or duplicate
  sides and multiple decision groups are rejected. Both allow and deny are
  confirmation-gated and honor developer dry-run mode.
- Conventional standard-dialog mutation is a separate high-risk adapter. It
  binds exactly one OK/Cancel, Yes/No, Confirm/Cancel, Retry/Cancel or
  Apply/Cancel group; positive intents are not interchangeable, file choosers
  and permission pairs are excluded. The same application, complete ordered
  top-level window snapshot, active dialog and both concrete controls are
  rebound immediately before one semantic invocation. A bounded postcondition
  accepts only the original order minus that dialog; unchanged, foreign-mutated
  or unreadable state never reports success and makes no rollback claim.
- Standard-dialog reading is an independent confirmed read-only action. It
  traverses the bounded active-dialog tree but accepts names only from static
  label, paragraph and description roles, skips protected nodes, never queries
  editable text and rejects file choosers. Twenty unique messages and 1,000
  total characters are hard limits, and the complete result is audit-redacted.
- Close-only informational dialogs use another independent high-risk action.
  The entire actionable control list must contain exactly one control named
  Close, Schließen or Dismiss with one Click, Press or Activate action. The
  dialog and concrete control identities are rebound immediately before
  invocation; the complete ordered application-window snapshot is rebound at
  the same boundary. File choosers, decision pairs and any extra action are rejected.
  A bounded postcondition requires the same application and its exact original
  ordered top-level window identities minus only the dismissed dialog;
  unchanged, foreign-mutated or unreadable state never reports success.
- Orientation, repeat, correction and cancel commands are deterministic and
  offline. Correction enters a distinct one-shot runtime state without storing
  either the prior or replacement transcript. Repeat preserves the prompt,
  cancel and stop clear it, and the next other utterance is dispatched once
  through the unchanged router/broker/fallback path. A monotonic 30-second TTL
  bounds the slot; the first utterance at or after expiry is discarded and an
  expiry notice is returned. Stop, cancel and a fresh correction request retain
  priority even after expiry. The local wake gate follows the original runtime
  deadline plus a fixed five-second expiry grace; repeat cannot extend it, and
  expiry or an explicit sleep command closes the gate. Configured TTLs must be
  finite and between 5 and 120 seconds. The prompt states that an already
  executed action is not implicitly undone. Numbered control activation is
  re-read immediately before execution and remains confirmation-gated.
- Named focus binds the active window once and searches its bounded AT-SPI tree
  for one exact unique accessible name that is both Showing and Focusable. It
  uses Component `grabFocus()` without key synthesis, verifies Focused state,
  treats an already focused target idempotently and attempts to restore the
  previously focused accessible if the transition cannot be confirmed.
- Workspace moves bind the active window once and invoke only an exact AT-SPI
  frame action for the previous/left or next/right workspace. Each direction
  has a distinct trusted-confirmation summary; generic move actions, keyboard
  shortcuts and compositor input synthesis are not accepted.
- Accessibility rescue enablement uses fixed `gsettings set` vectors for the
  GNOME `screen-keyboard-enabled`, `screen-reader-enabled` and
  `screen-magnifier-enabled` preferences. All actions reject targets and
  arguments and require trusted confirmation. A separate fixed, parameterless
  action may disable only magnification and explicitly announces that Orca and
  the on-screen keyboard remain enabled. No voice action disables those two
  rescue facilities.
- Orca speech recovery uses a separate fixed session adapter. It accepts only
  literal `restart`, detaches exactly `orca --replace --enable speech`, closes
  inherited file descriptors and reports an immediate child exit. The action
  cannot forward arbitrary Orca settings and remains confirmation-gated.
- Magnifier zoom accepts exactly one integer `percent` field from 100 through
  3,200, matching the useful magnifying portion of the installed schema's
  `0.1`–`32.0` range. The fixed command prefix targets only `mag-factor`; the
  executor appends a canonical decimal factor after policy validation.
- Magnifier lightness inversion maps two parameterless confirmed actions to
  fixed `invert-lightness true` and `invert-lightness false` vectors. The
  disable action affects only this visual filter and does not disable any
  accessibility application.
- Magnifier saturation accepts exactly one confirmed integer `percent` field
  from 0 through 100. The fixed command prefix targets only
  `color-saturation`; the executor appends its canonical `0.00`–`1.00` double.
- Magnifier screen position accepts exactly one of the five installed enum
  values: `full-screen`, `top-half`, `bottom-half`, `left-half` or
  `right-half`. The fixed command prefix targets only `screen-position`; the
  router maps bounded German/English phrases to those values before policy.
- Magnifier crosshairs map two parameterless confirmed actions to fixed
  `show-cross-hairs true` and `show-cross-hairs false` vectors. The disable
  action affects only this visual guide and never disables magnification.
- Crosshair opacity accepts exactly one confirmed integer `percent` field from
  0 through 100. The fixed command prefix targets only `cross-hairs-opacity`;
  the executor appends its canonical `0.00`–`1.00` double.
- Crosshair center clipping maps two parameterless confirmed actions to fixed
  `cross-hairs-clip true` and `cross-hairs-clip false` vectors. Disabling the
  clip changes only line intersection at the pointer and leaves magnification
  and crosshair visibility enabled.
- Crosshair length accepts exactly one confirmed integer `pixels` field from
  20 through 4,096, matching the installed schema range. The fixed command
  prefix targets only `cross-hairs-length`; the executor appends the validated
  canonical decimal integer.
- Crosshair thickness accepts exactly one confirmed integer `pixels` field
  from 1 through 100, matching the adjustment embedded in the installed GNOME
  Control Center. The fixed prefix targets only `cross-hairs-thickness`; other
  fields, number types and out-of-range values fail before confirmation.
- Crosshair color accepts exactly three integer fields, `red`, `green` and
  `blue`, each from 0 through 255. Bounded German/English color names are mapped
  locally to the same typed request. Only the executor creates canonical
  lowercase `#rrggbb`; caller-controlled strings never reach the fixed
  `cross-hairs-color` command prefix.
- Magnifier focus tracking accepts exactly one of the four installed enum
  values: `none`, `centered`, `proportional` or `push`. The fixed command prefix
  targets only `focus-tracking`; bounded German/English phrases are mapped to
  the enum before policy validation.
- Magnifier caret and mouse tracking are separate actions with fixed prefixes
  targeting only `caret-tracking` and `mouse-tracking`. Each accepts the same
  four installed enum values and maps unambiguous German/English phrases before
  policy validation; `none` affects only that tracker, not magnification.
- Magnifier brightness and contrast each accept one signed integer `percent`
  field from -75 through +75, matching the installed Control Center sliders.
  The executor converts it to a canonical two-decimal fraction for the fixed
  `clausis-magnifier-filter brightness|contrast` adapter. That adapter reads
  and sets only the three fixed red, green and blue schema keys and restores
  already changed channels if a later channel fails.
- Magnifier lens mode and scrolling at screen edges each use separate enable
  and disable actions with complete fixed `lens-mode` or `scroll-at-edges`
  boolean vectors. They reject targets and arguments before trusted
  confirmation; disabling either option does not disable magnification.

## Installer safety foundation after 0.4.1

- A fixed-argument, read-only `lsblk --json` inventory rejects the live medium,
  removable, read-only, mounted, undersized and non-stably identified devices.
- The immutable public plan can carry the stable by-id path, exact byte size,
  model and serial suffix. It is rebound to freshly discovered hardware before
  hand-off; missing, duplicated, changed or newly mounted targets fail closed.
- Whole-disk erase is the only mode the voice-plan validator accepts. Coexist
  and manual partitioning remain keyboard/Orca fallback paths and are not
  falsely presented as voice-native.
- The exact pre-write process creates a single-use confirmation phrase only
  after rebinding the selected disk. It speaks the destructive summary,
  records one local answer and expires after 120 seconds.
- Calamares never preselects erase. Its default proposal is LUKS2 with a
  separate unencrypted `/boot`, Btrfs root and swap file. The separate boot
  volume avoids relying on GRUB to unlock Argon2-backed LUKS2.
- The setup window now keeps status and primary buttons outside the scrollable
  form so they stay visible at small virtual-machine resolutions.
- A nine-line GPL-compatible patch is built against Debian's exact Calamares
  3.3.14-1 source. On leaving the partition page it publishes only selected
  device node, mode, encryption boolean and filesystem to GlobalStorage; the
  LUKS passphrase is never exported.
- `shellprocess@clausis-guard` is inserted immediately before the partition
  placeholder in Calamares' execution sequence. For whole-disk mode it re-runs
  discovery and denies a missing, changed, mounted, removable, unstable,
  unencrypted or non-Btrfs target before any Calamares partition job starts.

The target/profile enforcement boundary is now tied to Calamares' execution
queue. That same pre-write process now creates the expiring random phrase,
speaks the freshly rebound disk identity and destructive profile, captures one
local response and deletes its temporary recording. Neither phrase nor
transcript is placed in Calamares global storage, arguments or stdout. It also
creates a 12-by-4-digit recovery key with about 159 bits of entropy, speaks it
twice and stages it root-only in tmpfs. A second minimal Calamares patch adds
that key to the installed LUKS2 volume while the original passphrase remains
inside Calamares, then removes both temporary key files. Key material enters
neither process arguments nor GlobalStorage. Physical trusted-audio isolation,
an accessible verification of the noted key, an equivalent protected keyboard
path and a persistent-disk VM test remain release blockers.

## Not implemented after 0.4.1

- Dedicated low-power wake-word inference, certified echo cancellation and
  true Barge-in.
- Complete GNOME Shell and xdg-desktop-portal coverage beyond the first AT-SPI
  adapter.
- Hermes-to-broker system-action wiring; 0.4.1 Hermes output is reply-only.
- Physical proof of trusted microphone/seat isolation and replay detection;
  the former string-based D-Bus PIN transport has been removed.
- Speaker verification, replay detection or biometric enrollment.
- Persistent VirtualBox install/unlock verification, TPM enrollment, Btrfs
  subvolume snapshots and rollback.
- Physical trusted-audio isolation and an equivalent protected keyboard/Orca
  confirmation path for the guarded Calamares transaction.
- Short-lived OpenAI client credentials from a trusted backend; 0.4.1 stores
  the voluntarily supplied standard API key in the user's private `0600` file.
- Cryptographic verification of the upstream Hermes release tag against a
  Clausis-owned allowlist of maintainer keys; the current updater relies on TLS
  and the official GitHub repository boundary.
- Provider OAuth inside the Clausis dialog; OAuth providers currently hand off
  to the upstream Hermes flow.

These are explicit release blockers, not silently mocked capabilities.
The staged implementation sequence is documented in
`docs/VOICE_ONLY_GAP_ANALYSIS.md`.
### Bounded current-line orientation

Current-line orientation never requests the complete field. The GNOME adapter
binds the focused non-protected text object, validates its character count,
cursor and selection metadata, then scans outward with exact one-character
AT-SPI reads until newline boundaries. A line longer than 1,000 characters
fails closed. Reading is confirmation-gated and audit-redacted. Moving to the
current line start or end is local and low risk, requires an empty selection,
verifies both the final caret offset and zero selections, and rolls back to the
previous offset if verification fails.

The related current-line selection action uses the same bound focus object and
line scan. It excludes the newline, refuses empty lines and existing
selections, then requires the exact `[start, end)` selection and a caret at
`end`. Any rejection, exception or observed mismatch removes all partial
selections and restores the original caret before reporting failure.

Current-line deletion is a separate confirmation-gated mutation. It snapshots
the bounded full field only after the safe line binding, removes the line plus
the following newline when possible (otherwise the preceding newline for the
last line), and requires exact full-text readback, the computed caret and zero
selections. Any failure restores and verifies the previous full text and caret.
### Rollback-safe current-line replacement

Current-line replacement is independently confirmation-gated. It accepts only
1–500 printable characters, substitutes exactly the bounded line span while
preserving delimiters, and requires exact complete-text readback, a caret
immediately after the replacement and zero selections. Its request target is
replaced by a fixed audit marker; rollback restores the prior full field and
cursor and verifies both.
### Verified line insertion

Two confirmation-gated actions insert one printable 1–500-character line above
or below the bounded caret line. Above inserts at the current start; below
inserts after the current end, so existing delimiters and content remain
stable. An empty field becomes the dictated line without an artificial newline.
Both variants require exact full-text readback, the computed caret and zero
selections, redact their targets in the audit and restore the entire previous
field and caret on mismatch.
### Privacy-preserving line duplication

Current-line duplication is confirmation-gated in both directions. It reuses
the bounded one-character line scan, refuses empty lines or existing
selections, and inserts the already-bound line content above or below without
placing that content in the request, confirmation, result or audit. Exact full
readback, calculated caret and zero selections are mandatory; failure restores
and verifies the previous complete field and cursor.
### Adjacent-line swapping

Moving a line up or down is confirmation-gated and implemented as an exact swap
with one adjacent line, not simulated keystrokes. Both current and neighboring
line are bounded to 1,000 characters, an existing selection fails closed, and
document boundaries produce an explicit error. The adapter preserves the
caret's relative offset within the moved line, verifies the complete field and
zero selections, exposes no line content outside the adapter, and restores the
full previous field/caret on mismatch.
### Semantic adapter interface boundary

`SemanticDesktop` is a structural typing contract only: every method body is a
single ellipsis and it contains no AT-SPI binding, privacy check or mutation
logic. All concrete behavior, including the private bounded line-context
helper, lives exactly once in `PyAtSpiDesktop`. An AST regression test enforces
this boundary so stale interface copies cannot silently diverge from runtime
security checks.
### Exact adjacent-line joining

Joining with the previous or next line is confirmation-gated and deletes one
specific newline through `EditableText`, never via simulated keys. Both lines
are independently bounded to 1,000 characters, selections and missing
neighbors fail closed, and line content remains inside the adapter. The
complete result, logical caret and zero selections are verified; rollback
restores the full previous field and cursor.

### Exact line splitting at the caret

Splitting the current line is separately confirmation-gated and inserts exactly
one newline at the already-bound AT-SPI caret. The bounded current-line lookup
rejects protected fields, lines over 1,000 characters and active selections;
the full field remains capped below 100,000 characters after insertion. The
adapter verifies complete text readback, the caret immediately after the new
delimiter and zero selections. Any mismatch restores and verifies the complete
previous field and caret, while line content remains outside confirmations,
results and audit records.

### Bounded current-line indentation

Indenting inserts exactly four spaces at the start of the already-bound line;
outdenting removes one leading tab or up to four leading spaces and rejects an
unindented line. The current line must remain within the 1,000-character bound,
active selections fail closed, and the logical caret position is preserved even
when it lies inside removed indentation. Both confirmed actions verify complete
text, caret and zero selections and restore the previous field on mismatch.
Line content never enters the request, confirmation, result or audit record.
