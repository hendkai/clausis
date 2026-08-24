"""Real GTK text-editing application used by the session-level AT-SPI smoke test.

It shows one window with one editable entry pre-filled with ``hallo welt hier``
plus a hidden-visibility entry that GTK exposes with the ``password text``
role, and grabs the focus for the plain entry, so the Clausis text-editing
adapter can exercise caret movement, selection, replacement, undo/redo,
granular reading — and the password-field refusal — against live GTK widgets
on a real accessibility bus.
"""

import sys

from gi.repository import GLib, Gtk


window = Gtk.Window(title="ClausisSessionProbe")
box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
window.add(box)

entry = Gtk.Entry()
entry.set_text("hallo welt hier")
entry.set_can_focus(True)
box.pack_start(entry, expand=True, fill=True, padding=6)

# An entry with visibility off is what GTK exposes with the "password text"
# role — the widget class the dictation refusals must recognise on a real bus.
password = Gtk.Entry()
password.set_visibility(False)
password.set_can_focus(True)
box.pack_start(password, expand=True, fill=True, padding=6)

label = Gtk.Label(label="Textbearbeitung")
box.pack_start(label, expand=False, fill=False, padding=6)

window.show_all()
entry.grab_focus()

marker = sys.argv[1] if len(sys.argv) > 1 else ""
if marker:
    with open(marker, "w", encoding="utf-8") as handle:
        handle.write("ready\n")

GLib.timeout_add_seconds(45, Gtk.main_quit)
Gtk.main()
