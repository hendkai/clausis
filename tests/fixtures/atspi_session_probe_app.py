"""Real GTK text-editing application used by the session-level AT-SPI smoke test.

It shows one window with one editable entry pre-filled with ``hallo welt hier``
and grabs the focus for it, so the Clausis text-editing adapter can exercise
caret movement, selection, replacement, undo/redo and granular reading against
a live GTK widget on a real accessibility bus.
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
