"""Real GTK text-editing application used by the session-level AT-SPI smoke test.

It shows one window with one editable entry pre-filled with ``hallo welt hier``,
a multi-line ``Gtk.TextView`` with three paragraphs (the widget say-all and
line/paragraph navigation need — an entry is single-line and cannot provide
them), plus a hidden-visibility entry that GTK exposes with the ``password
text`` role, and grabs the focus for the plain entry, so the Clausis
text-editing adapter can exercise caret movement, selection, replacement,
undo/redo, granular reading, counted navigation and say-all — and the
password-field refusal — against live GTK widgets on a real accessibility bus.
"""

import sys

from gi.repository import GLib, Gtk


#: Multi-line content of the TextView: three paragraphs, seven lines, five
#: sentences — enough structure for line jumps, clamped line numbers, counted
#: word navigation and a say-all run that can pause after the second chunk.
MULTILINE_TEXT = (
    "Erste Zeile des Dokuments.\n"
    "Zweite Zeile folgt.\n"
    "\n"
    "Neuer Absatz beginnt hier.\n"
    "Noch eine Zeile mit Inhalt.\n"
    "\n"
    "Letzter Absatz."
)


window = Gtk.Window(title="ClausisSessionProbe")
box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
window.add(box)

entry = Gtk.Entry()
entry.set_text("hallo welt hier")
entry.set_can_focus(True)
box.pack_start(entry, expand=True, fill=True, padding=6)

view = Gtk.TextView()
view.get_buffer().set_text(MULTILINE_TEXT)
view.set_can_focus(True)
# Both Gtk.Entry and Gtk.TextView expose the AT-SPI role "text"; the
# accessible name is the only reliable way for the session client to find
# the multi-line widget on the bus.
view.get_accessible().set_name("MehrzeiligesFeld")
box.pack_start(view, expand=True, fill=True, padding=6)


# An entry with visibility off is what GTK exposes with the "password text"
# role — the widget class the dictation refusals must recognise on a real bus.
password = Gtk.Entry()
password.set_visibility(False)
password.set_can_focus(True)
box.pack_start(password, expand=True, fill=True, padding=6)

# A real widget GTK exposes with a native AT-SPI structure role: the list
# box answers role "list" on the bus, so the structure-navigation adapter
# has a genuine target in the session test (headings and links are browser
# roles GTK never fills — those stay fake-tree-only, honestly).
listbox = Gtk.ListBox()
listbox.get_accessible().set_name("StrukturListe")
listbox.set_can_focus(True)
for index in range(3):
    row = Gtk.ListBoxRow()
    row.add(Gtk.Label(label=f"Eintrag {index + 1}"))
    listbox.add(row)
box.pack_start(listbox, expand=True, fill=True, padding=6)

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
