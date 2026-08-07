"""Small real GTK application used by the containerized AT-SPI smoke test."""

from gi.repository import GLib, Gtk


window = Gtk.Window(title="ClausisProbe")
button = Gtk.Button(label="Check")
window.add(button)
window.show_all()
button.grab_focus()
GLib.timeout_add_seconds(20, Gtk.main_quit)
Gtk.main()
