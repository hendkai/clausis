# Clausis 0.3.1 – technische Vorschau

Diese Version verbindet den GNOME-Desktop sichtbar mit dem bereits vorhandenen
Clausis-Bootlogo und dokumentiert den noch fehlenden Weg zu einem wirklich
vollständig sprachbedienbaren System.

## Neu

- Neuer 2560×1440-Clausis-Hintergrund mit ruhigem dunklem Hörfeld, Cyan für
  Orientierung und Violett für aktive Sprache.
- Das Clausis-Zeichen wird für Sprachsteuerung, Hermes-Einrichtung, geschützten
  Chat und den GDM-Anmeldebildschirm verwendet.
- GNOME startet mit unterstützter dunkler Darstellung und violettem Akzent,
  ohne ein schwer wartbares eigenes GTK-Fork-Theme.
- Atkinson Hyperlegible wird als Oberflächenschrift installiert; Cursor und
  Text sind etwas größer, der Barrierefreiheitsstatus bleibt sichtbar.
- Animationen und Hot Corners sind standardmäßig reduziert, damit Bedienung
  vorhersehbarer bleibt und unnötige Bewegung vermieden wird.
- `docs/VOICE_ONLY_GAP_ANALYSIS.md` beschreibt konkret die noch fehlenden
  Audio-, GNOME-, Sicherheits-, Installer- und Recovery-Bausteine.

## Wichtige Grenzen

Die Gestaltung macht Clausis konsistenter und zugänglicher, ersetzt aber keine
Sprachschnittstelle. Vollständige GNOME-Steuerung über AT-SPI und Portale,
lokales Wake-Word/VAD/Barge-in, die geschützte Bestätigung, sprach-native
Partitionierung sowie Boot- und Recovery-Audio bleiben offene Release-Gates.
Clausis 0.3.1 ist weiterhin eine technische Vorschau.
