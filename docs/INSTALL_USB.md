# Clausis-Installationsstick erstellen

## Voraussetzungen

- Ein x86-64-PC mit mindestens 8 GB RAM.
- Ein USB-Stick mit mindestens 8 GB. Sein bisheriger Inhalt wird beim Schreiben
  des ISO vollständig überschrieben.
- Die Dateien `clausis-0.2.1-amd64.iso` und
  `clausis-0.2.1-amd64.iso.sha256` aus `dist/`.

## Prüfsumme kontrollieren

Unter Linux oder macOS im Download-Ordner:

```sh
sha256sum -c clausis-0.2.1-amd64.iso.sha256
```

Auf macOS wird stattdessen
`shasum -a 256 -c clausis-0.2.1-amd64.iso.sha256` verwendet.

## Empfohlener grafischer Weg

1. Raspberry Pi Imager oder balenaEtcher öffnen.
2. „Eigenes Image“ und `clausis-0.2.1-amd64.iso` auswählen.
3. Den USB-Stick anhand von Hersteller und Größe eindeutig prüfen.
4. Schreiben und anschließende Verifikation starten.
5. Den Ziel-PC neu starten und im UEFI-/Bootmenü den USB-Stick auswählen.

## Start und Installation

Clausis startet als Live-System ohne Passwortabfrage. Nach dem GNOME-Start wird
Orca vor allen Dialogen gestartet und der KI-Hinweis gesprochen. Zuerst erscheint
die zugängliche Hermes-Einrichtung; danach öffnet sich Calamares. Anbieterwahl
und Cloud-Einwilligung können lokal gesprochen werden. API-Schlüssel werden aus
Sicherheitsgründen verdeckt per Tastatur eingegeben und nie vorgelesen. Orca
kann mit `Super`+`Alt`+`S` umgeschaltet werden. Die Installation verändert
Datenträger erst nach der Zusammenfassung und Bestätigung im Installer.
Während der Zielinstallation sucht Clausis online nach der neuesten offiziellen
stabilen Hermes-Version. Ohne Internet oder bei einem Installationsfehler bleibt
die geprüfte Version aus dem ISO aktiv; der Zustand wird beim ersten Login
gesprochen und angezeigt.

Nach der Installation startet die lokale Sprachsteuerung beim Anmelden
automatisch und kündigt die Mikrofonaktivierung an. „Stopp Hermes“ beendet sie
lokal. Die Einrichtung kann jederzeit über „Clausis und Hermes einrichten“ im
Anwendungsmenü erneut geöffnet werden.

Diese 0.2.1-Version ist ein technischer Teststand. Vor dem Einsatz müssen
wichtige Dateien separat gesichert werden. Stimm-PIN, TPM-Bindung, automatisches
Rollback und vollständig sprachbedienbare Partitionierung sind noch nicht als
fertig freigegeben.

## Download aus dem GitHub-Release

Weil das ISO knapp über der GitHub-Grenze für eine einzelne Release-Datei
liegt, werden zwei Teile angeboten. Beide `*.part-*`-Dateien und die
`.sha256`-Datei in denselben Ordner herunterladen. Anschließend:

```sh
./scripts/reassemble_iso.sh /pfad/zum/download-ordner
```

Alternativ können die beiden Teile mit `cat` in alphabetischer Reihenfolge
zusammengefügt und danach mit der veröffentlichten SHA-256-Summe geprüft werden.
