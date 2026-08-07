# Clausis 0.4.0 – technische Vorschau

Diese Version beginnt die funktionale Umsetzung der Voice-only-Roadmap. Sie
macht aus Clausis noch kein vollständig sprachbedienbares Betriebssystem.

## Neu

- Lokale Aktivierung mit „Hallo Clausis“ und einem automatisch ablaufenden
  Befehlsfenster. Hintergrundtranskripte gelangen vorher weder zu Hermes noch
  zu einem Cloud-Fallback.
- „Stopp Clausis“, „Stopp Hermes“ und die englischen Varianten werden in jedem
  lokalen Hörzustand erkannt. „Geh schlafen“ schließt das Aktivierungsfenster.
- Lokale Hardwareprobe und hörbar angekündigter Halbduplex-Fallback. Auch auf
  geeigneter Hardware wird noch kein Barge-in versprochen, solange der lokale
  Unterbrechungsdetektor nicht implementiert und physisch geprüft ist.
- Erster semantischer GNOME-Adapter über AT-SPI, ohne Mauskoordinaten oder
  Screen-Scraping.
- Neue Offline-Befehle: „Wo bin ich?“, „Lies das Fenster vor“, „Was kann ich
  hier tun?“, „Nummer drei“, „Zurück“, „Wiederholen“, „Korrigieren“ und
  „Abbrechen“.
- Das aktuelle Fenster, der Fokus und bis zu 30 ausführbare Bedienelemente
  werden aus dem aktuellen Accessibility-Baum gelesen und nummeriert.
- Beliebige nummerierte Aktivierungen sind als mittleres Risiko eingestuft und
  bleiben ohne getrennte vertrauenswürdige Bestätigung gesperrt.
- GPT Live kann die neuen semantischen Clausis-Aktionen nur über das typisierte
  Broker-Schema anfordern; es erhält weiterhin keine Shell oder Capability.

## Weiterhin offen

- Dediziertes Wake-Word-Modell, Echounterdrückung und echtes Barge-in.
- Vollständige GNOME-Shell-, Portal-, Datei- und Berechtigungsdialoge.
- Nicht automatisierbare Audio-/Seat-Bestätigung statt des prototypischen
  D-Bus-PIN-Transports.
- Sprach-native Partitionierung sowie Audio in LUKS, GDM und Recovery.
- Vollständige Installation auf virtuelle Festplatte in VirtualBox und
  Abnahme mit realer Audiohardware.

Clausis 0.4.0 bleibt ausdrücklich eine technische Testversion.
