"""Assert that the real AT-SPI registry exposes the GTK smoke fixture."""

from clausis.gnome_adapter import PyAtSpiDesktop


context = PyAtSpiDesktop().context()
print(context.spoken_location())
print(context.spoken_controls())
assert context.window == "ClausisProbe"
assert any(control.name == "Check" for control in context.controls)
