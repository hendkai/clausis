#!/usr/bin/env python3
"""Instantiate the real GTK setup and verify its protected PIN controls."""

from pathlib import Path

import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk

from clausis.setup_app import SetupWindow


def descendants(widget):
    yield widget
    if isinstance(widget, Gtk.Container):
        for child in widget.get_children():
            yield from descendants(child)


window = SetupWindow(Path("/tmp/clausis-setup-probe"), stage_for_installer=True)
assert not window.confirmation_pin.get_visibility()
assert not window.confirmation_pin_repeat.get_visibility()
assert window.confirmation_pin.get_input_purpose() == Gtk.InputPurpose.PIN
assert any(isinstance(item, Gtk.ScrolledWindow) for item in descendants(window.window))
print("real GTK setup has masked PIN fields and a scrollable layout")
