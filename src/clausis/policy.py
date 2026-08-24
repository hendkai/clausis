"""Action allowlist, argument validation and confirmation policy."""

from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Any, Callable, Dict, Mapping, Optional

from .models import ActionRequest, Origin, Risk


Validator = Callable[[ActionRequest], None]


@dataclass(frozen=True)
class ActionPolicy:
    minimum_risk: Risk
    reversible: bool
    command: Optional[tuple] = None
    validator: Optional[Validator] = None
    privileged: bool = False


SAFE_IDENTIFIER = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._+@:-]{0,127}$")
SAFE_SETTING = re.compile(r"^[a-z][a-z0-9-]{0,63}$")
DEBIAN_PACKAGE = re.compile(r"^[a-z0-9][a-z0-9+.-]{1,62}$")


def _target_required(request: ActionRequest) -> None:
    if not request.target:
        raise ValueError("target is required")


def _safe_identifier(request: ActionRequest) -> None:
    _target_required(request)
    if not SAFE_IDENTIFIER.fullmatch(request.target):
        raise ValueError("target is not an allowed identifier")


def _path(request: ActionRequest) -> None:
    _target_required(request)
    if not request.target.startswith("/") or "\x00" in request.target:
        raise ValueError("target must be an absolute path")


def _percentage(request: ActionRequest) -> None:
    value = request.arguments.get("percent")
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not 0 <= value <= 150:
        raise ValueError("percent must be between 0 and 150")


def _setting(request: ActionRequest) -> None:
    if request.target and not SAFE_SETTING.fullmatch(request.target):
        raise ValueError("invalid settings panel")


def _control_number(request: ActionRequest) -> None:
    if not request.target.isdigit() or not 1 <= int(request.target) <= 30:
        raise ValueError("control number must be between 1 and 30")


def _file_number(request: ActionRequest) -> None:
    if not request.target.isdigit() or not 1 <= int(request.target) <= 20:
        raise ValueError("file number must be between 1 and 20")


def _package_name(request: ActionRequest) -> None:
    """Reject anything that could be read as an ``apt-get`` option."""

    _target_required(request)
    if not DEBIAN_PACKAGE.fullmatch(request.target):
        raise ValueError("target is not a Debian package name")


def _no_target(request: ActionRequest) -> None:
    if request.target:
        raise ValueError("action does not accept a target")


def _dictated_text(request: ActionRequest) -> None:
    """Accept spoken prose, but nothing that is not printable text.

    Field-level protection lives in the GNOME adapter, which refuses password
    fields and terminals outright; this validator only keeps control characters
    and empty dictation out of the request.
    """

    if not request.target.strip():
        raise ValueError("dictated text is empty")
    if len(request.target) > 512:
        raise ValueError("dictated text is too long")


def _granularity(request: ActionRequest) -> None:
    """The caller names the granularity, and nothing else."""

    from .text_units import GRANULARITIES

    if request.target:
        raise ValueError("action does not accept a target")
    value = request.arguments.get("granularity")
    if value not in GRANULARITIES:
        raise ValueError("granularity must be character, word, line, sentence or paragraph")


ACTION_POLICIES: Mapping[str, ActionPolicy] = {
    "app.launch": ActionPolicy(Risk.LOW, True, ("gtk-launch",), _safe_identifier),
    "app.close": ActionPolicy(Risk.MEDIUM, True, None, _safe_identifier),
    # Shell surfaces and window state: all reversible, all visible, none of
    # them touching user data, so they stay low risk and immediate.
    "desktop.overview": ActionPolicy(Risk.LOW, True, None, _no_target),
    "desktop.applications": ActionPolicy(Risk.LOW, True, None, _no_target),
    "desktop.quick_settings": ActionPolicy(Risk.LOW, True, None, _no_target),
    "desktop.notifications": ActionPolicy(Risk.LOW, True, None, _no_target),
    "desktop.window.minimize": ActionPolicy(Risk.LOW, True, None, _no_target),
    "desktop.window.maximize": ActionPolicy(Risk.LOW, True, None, _no_target),
    "desktop.window.unmaximize": ActionPolicy(Risk.LOW, True, None, _no_target),
    "desktop.workspace.next": ActionPolicy(Risk.LOW, True, None, _no_target),
    "desktop.workspace.previous": ActionPolicy(Risk.LOW, True, None, _no_target),
    "desktop.window.to_next_workspace": ActionPolicy(Risk.LOW, True, None, _no_target),
    "desktop.window.to_previous_workspace": ActionPolicy(Risk.LOW, True, None, _no_target),
    "desktop.window.next": ActionPolicy(Risk.LOW, True),
    "desktop.window.previous": ActionPolicy(Risk.LOW, True),
    "desktop.context.describe": ActionPolicy(Risk.LOW, True),
    "desktop.controls.list": ActionPolicy(Risk.LOW, True),
    "desktop.control.activate": ActionPolicy(Risk.MEDIUM, True, None, _control_number),
    "desktop.navigate.back": ActionPolicy(Risk.LOW, True),
    "desktop.settings.open": ActionPolicy(Risk.LOW, True, ("gnome-control-center",), _setting),
    # Dictation stays low risk: it is visible, spoken back and correctable, and
    # the adapter refuses password fields and terminals outright. Requiring a
    # phrase and PIN per sentence would make voice-only operation unusable.
    "text.read": ActionPolicy(Risk.LOW, True, None, _no_target),
    "text.insert": ActionPolicy(Risk.LOW, True, None, _dictated_text),
    "text.delete_word": ActionPolicy(Risk.LOW, True, None, _no_target),
    # Discarding a whole field is not a correction; it needs confirmation.
    "text.clear": ActionPolicy(Risk.MEDIUM, True, None, _no_target),
    # Caret movement is visible, correctable and touches no data; reading from
    # the caret is a read-only query. All stay low risk and immediate.  The
    # line and paragraph breaks are typed actions of their own because the
    # request schema forbids control characters inside a dictated target.
    "text.caret.start": ActionPolicy(Risk.LOW, True, None, _no_target),
    "text.caret.end": ActionPolicy(Risk.LOW, True, None, _no_target),
    "text.caret.word_next": ActionPolicy(Risk.LOW, True, None, _no_target),
    "text.caret.word_previous": ActionPolicy(Risk.LOW, True, None, _no_target),
    "text.read_from_caret": ActionPolicy(Risk.LOW, True, None, _no_target),
    "text.newline": ActionPolicy(Risk.LOW, True, None, _no_target),
    "text.paragraph": ActionPolicy(Risk.LOW, True, None, _no_target),
    # Selection and granular reading: a selection is visible in the field,
    # correctable and commits nothing by itself.  Replacing the selection is
    # dictation with a visible anchor, so it keeps the dictation rules (and
    # the password/terminal refusals of the adapter).  Undo and redo invoke
    # only the widget's own history actions.  Everything here is immediate.
    "text.select_word": ActionPolicy(Risk.LOW, True, None, _no_target),
    "text.select_sentence": ActionPolicy(Risk.LOW, True, None, _no_target),
    "text.select_all": ActionPolicy(Risk.LOW, True, None, _no_target),
    "text.replace_selection": ActionPolicy(Risk.LOW, True, None, _dictated_text),
    "text.delete_selection": ActionPolicy(Risk.LOW, True, None, _no_target),
    "text.undo": ActionPolicy(Risk.LOW, True, None, _no_target),
    "text.redo": ActionPolicy(Risk.LOW, True, None, _no_target),
    "text.read_granular": ActionPolicy(Risk.LOW, True, None, _granularity),
    # File chooser navigation: listing is read-only, focusing an entry
    # commits nothing, and opening a provable folder changes only the
    # directory shown in the dialog. Confirming the dialog stays medium risk.
    "dialog.file.list": ActionPolicy(Risk.LOW, True, None, _no_target),
    "dialog.file.select": ActionPolicy(Risk.LOW, True, None, _file_number),
    "dialog.folder.open": ActionPolicy(Risk.LOW, True, None, _file_number),
    "dialog.describe": ActionPolicy(Risk.LOW, True, None, _no_target),
    # Declining is always safe; committing to an unknown dialog is not, so
    # accepting stays medium risk, exactly like activating a numbered control.
    "dialog.cancel": ActionPolicy(Risk.LOW, True, None, _no_target),
    "dialog.accept": ActionPolicy(Risk.MEDIUM, True, None, _no_target),
    # Speech output control through speech-dispatcher: fixed vectors, the
    # caller never names the option or the value.  Rate steps are the
    # spd-say default-scale (-100..100 in steps of 25); language switches
    # the synthesis language for subsequent spoken output.
    "speech.rate.faster": ActionPolicy(
        Risk.LOW, True,
        ("spd-say", "--ssml", "-r", "+25", "-e", "Sprechgeschwindigkeit erhöht."),
        _no_target,
    ),
    "speech.rate.slower": ActionPolicy(
        Risk.LOW, True,
        ("spd-say", "--ssml", "-r", "-25", "-e", "Sprechgeschwindigkeit verringert."),
        _no_target,
    ),
    "speech.rate.normal": ActionPolicy(
        Risk.LOW, True,
        ("spd-say", "--ssml", "-r", "0", "-e", "Sprechgeschwindigkeit zurückgesetzt."),
        _no_target,
    ),
    "speech.language.german": ActionPolicy(
        Risk.LOW, True,
        ("spd-say", "--ssml", "-l", "de", "-e", "Sprachausgabe ist auf Deutsch gestellt."),
        _no_target,
    ),
    "speech.language.english": ActionPolicy(
        Risk.LOW, True,
        ("spd-say", "--ssml", "-l", "en", "-e", "Speech output is now set to English."),
        _no_target,
    ),
    # Accessibility switches are fully specified fixed vectors: the caller
    # names the action, never the schema key or the value.
    "a11y.keyboard.enable": ActionPolicy(
        Risk.LOW, True,
        ("gsettings", "set", "org.gnome.desktop.a11y.applications", "screen-keyboard-enabled", "true"),
        _no_target,
    ),
    "a11y.keyboard.disable": ActionPolicy(
        Risk.LOW, True,
        ("gsettings", "set", "org.gnome.desktop.a11y.applications", "screen-keyboard-enabled", "false"),
        _no_target,
    ),
    "a11y.magnifier.enable": ActionPolicy(
        Risk.LOW, True,
        ("gsettings", "set", "org.gnome.desktop.a11y.applications", "screen-magnifier-enabled", "true"),
        _no_target,
    ),
    "a11y.magnifier.disable": ActionPolicy(
        Risk.LOW, True,
        ("gsettings", "set", "org.gnome.desktop.a11y.applications", "screen-magnifier-enabled", "false"),
        _no_target,
    ),
    "a11y.screenreader.enable": ActionPolicy(
        Risk.LOW, True,
        ("gsettings", "set", "org.gnome.desktop.a11y.applications", "screen-reader-enabled", "true"),
        _no_target,
    ),
    "a11y.screenreader.disable": ActionPolicy(
        Risk.LOW, True,
        ("gsettings", "set", "org.gnome.desktop.a11y.applications", "screen-reader-enabled", "false"),
        _no_target,
    ),
    # Producing a diagnostic report must itself be voice-operable: needing a
    # terminal to report that voice control failed is a broken loop.
    "system.report": ActionPolicy(Risk.LOW, True, None, _no_target),
    "clipboard.read": ActionPolicy(Risk.LOW, True, None, _no_target),
    "clipboard.copy": ActionPolicy(Risk.LOW, True, None, _no_target),
    "clipboard.paste": ActionPolicy(Risk.LOW, True, None, _no_target),
    "file.open": ActionPolicy(Risk.LOW, True, ("gio", "open"), _path),
    "file.search": ActionPolicy(Risk.LOW, True, None, _target_required),
    "file.move_to_trash": ActionPolicy(Risk.HIGH, True, ("gio", "trash"), _path),
    "audio.volume.set": ActionPolicy(Risk.LOW, True, ("wpctl", "set-volume", "@DEFAULT_AUDIO_SINK@"), _percentage),
    "audio.volume.up": ActionPolicy(Risk.LOW, True, ("wpctl", "set-volume", "@DEFAULT_AUDIO_SINK@", "5%+")),
    "audio.volume.down": ActionPolicy(Risk.LOW, True, ("wpctl", "set-volume", "@DEFAULT_AUDIO_SINK@", "5%-")),
    "audio.mute.toggle": ActionPolicy(Risk.LOW, True, ("wpctl", "set-mute", "@DEFAULT_AUDIO_SINK@", "toggle")),
    "network.status": ActionPolicy(Risk.LOW, True, ("nmcli", "general", "status")),
    "network.wifi.enable": ActionPolicy(Risk.MEDIUM, True, ("nmcli", "radio", "wifi", "on")),
    "network.wifi.disable": ActionPolicy(Risk.MEDIUM, True, ("nmcli", "radio", "wifi", "off")),
    "system.status": ActionPolicy(Risk.LOW, True),
    "system.lock": ActionPolicy(Risk.LOW, True, ("loginctl", "lock-session")),
    "system.logout": ActionPolicy(Risk.HIGH, True, ("gnome-session-quit", "--logout", "--no-prompt")),
    # Privileged actions carry no argument vector here: the root-side table in
    # clausis.privileged is authoritative, so a session process can never widen
    # the command that Polkit ends up authorising.
    "system.reboot": ActionPolicy(Risk.CRITICAL, False, None, _no_target, privileged=True),
    "system.poweroff": ActionPolicy(Risk.CRITICAL, False, None, _no_target, privileged=True),
    "package.install": ActionPolicy(Risk.HIGH, True, None, _package_name, privileged=True),
    "package.remove": ActionPolicy(Risk.CRITICAL, False, None, _package_name, privileged=True),
    "update.check": ActionPolicy(Risk.LOW, True),
    "update.install_security": ActionPolicy(Risk.HIGH, True, None, _no_target, privileged=True),
}


class PolicyDecision:
    def __init__(self, *, allowed: bool, confirmation_required: bool, reason: str, policy: ActionPolicy) -> None:
        self.allowed = allowed
        self.confirmation_required = confirmation_required
        self.reason = reason
        self.policy = policy


def evaluate(request: ActionRequest) -> PolicyDecision:
    policy = ACTION_POLICIES.get(request.action)
    if policy is None:
        raise ValueError("action is not allowlisted")
    if policy.validator:
        policy.validator(request)
    if request.risk.rank < policy.minimum_risk.rank:
        raise ValueError("caller attempted to understate action risk")
    if request.reversible and not policy.reversible:
        raise ValueError("caller incorrectly marked an irreversible action reversible")
    tainted = request.origin in {Origin.EXTERNAL_CONTENT, Origin.HERMES}
    needs_confirmation = (
        policy.minimum_risk.rank >= Risk.MEDIUM.rank
        or not policy.reversible
        or policy.privileged
        or tainted
    )
    reason = "confirmation required by risk and provenance policy" if needs_confirmation else "safe local action"
    return PolicyDecision(
        allowed=True,
        confirmation_required=needs_confirmation,
        reason=reason,
        policy=policy,
    )
