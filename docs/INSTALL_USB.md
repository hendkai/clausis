# Clausis-Installationsstick erstellen

## Voraussetzungen

- Ein x86-64-PC mit mindestens 8 GB RAM.
- Ein USB-Stick mit mindestens 8 GB. Sein bisheriger Inhalt wird beim Schreiben
  des ISO vollständig überschrieben.
- Die Dateien `clausis-0.1.1-amd64.iso` und
  `clausis-0.1.1-amd64.iso.sha256` aus `dist/`.

## Prüfsumme kontrollieren

Unter Linux oder macOS im Download-Ordner:

```sh
sha256sum -c clausis-0.1.1-amd64.iso.sha256
```

Auf macOS kann ersatzweise `shasum -a 256 clausis-0.1.1-amd64.iso` verwendet
und die Ausgabe mit der `.sha256`-Datei verglichen werden.

## Empfohlener grafischer Weg

1. Raspberry Pi Imager oder balenaEtcher öffnen.
2. „Eigenes Image“ und `clausis-0.1.1-amd64.iso` auswählen.
3. Den USB-Stick anhand von Hersteller und Größe eindeutig prüfen.
4. Schreiben und anschließende Verifikation starten.
5. Den Ziel-PC neu starten und im UEFI-/Bootmenü den USB-Stick auswählen.

## Start und Installation

Clausis startet als Live-System. Nach dem GNOME-Start wird der KI-Hinweis
gesprochen und der Calamares-Installer geöffnet. Orca kann jederzeit mit
`Super`+`Alt`+`S` aktiviert werden. Die Anwendung „Clausis Sprachsteuerung“
startet die lokale Sprachschleife. Die Installation verändert Datenträger erst
nach der Zusammenfassung und Bestätigung im Installer.

Diese 0.1.1-Version ist ein technischer Teststand. Vor dem Einsatz müssen
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
