# Clausis 0.2.0 – Entwicklungsstand

Diese Version arbeitet auf das barrierefreie Installationsziel hin. Hermes
Agent ist im Image vorinstalliert und die Anbieter-Einrichtung beginnt vor dem
Debian-Installer mit lokaler Sprachausgabe, Orca- und Tastaturunterstützung.

## Wesentliche Änderungen

- Hermes Agent 0.20.0 aus fest gepinntem Upstream-Commit mit eingefrorener
  Lockdatei und der von Upstream verwendeten uv-Version 0.9.28.
- Zugänglicher GTK-Dialog für Offline-, Nous-, OpenRouter-, Anthropic-, GLM-,
  lokale und OpenAI-kompatible Anbieter.
- Lokale Spracheingabe für Anbieterwahl und eindeutige Cloud-Einwilligung.
- API-Schlüssel ausschließlich in einem geschützten Tastaturfeld; keine
  Spracherfassung, Ausgabe oder Protokollierung von Schlüsseln.
- Ausdrückliche Cloud-Einwilligung vor jeder Cloud-Konfiguration.
- Orca startet vor Setup und Calamares; Qt-Barrierefreiheit ist erzwungen.
- Private Hermes-Einstellungen werden nach der Calamares-Benutzeranlage in das
  installierte Benutzerkonto übernommen.
- Nicht erkannte Offline-Fragen werden nach der Einrichtung an Hermes
  weitergegeben und als Sprache ausgegeben. Dabei ist nur das harmlose lokale
  `todo`-Toolset sichtbar; Terminal-, Datei-, Browser- und Codewerkzeuge bleiben
  gesperrt.
- Eigener geschützter Hermes-Chat-Starter im GNOME-Anwendungsmenü.
- Nach der Installation startet die Offline-Sprachsteuerung automatisch,
  kündigt die Mikrofonaktivierung an und kann lokal mit „Stopp Hermes“ beendet
  werden. Der Installer wird im installierten System nicht erneut geöffnet.
- Automatischer Start speichert keine erkannten Sätze in einer Protokolldatei;
  technische Anbieterfehler werden nicht vorgelesen, damit darin enthaltene
  Geheimnisse nicht über die Sprachausgabe offengelegt werden.
- 88 automatisierte Tests sowie reale Debian-13-Prüfungen für Hermes-Start,
  Tool-Filter und GTK-Zugänglichkeitsnamen bestanden.
- Das finale Hybrid-ISO wurde strukturell geprüft und unter x86-64 QEMU bis
  GNOME gestartet. Der grafische Nachweis zeigt Autologin und direkt den
  Clausis/Hermes-Einrichtungsdialog ohne Login- oder Debian-Tour-Fenster.
- Die Windows-Teildateien wurden wieder zusammengesetzt und ergaben exakt die
  veröffentlichte SHA-256-Prüfsumme.

## Noch nicht als fertig nachgewiesen

Eine Installation auf physischer Hardware, echte Mikrofon-/Lautsprechertests
und eine Nutzerstudie stehen noch aus. Insbesondere sind vollständig
sprachgesteuerte Partitionierung, OAuth im Clausis-Dialog, LUKS/TPM,
Voice-PIN, Wake-Word, Echounterdrückung und die geforderte Nutzerstudie mit
blinden Personen weiterhin Release-Blocker.

Die exakten Prüfergebnisse und Grenzen stehen in
`docs/release/ISO_0.2.0_TEST_REPORT.md`.
