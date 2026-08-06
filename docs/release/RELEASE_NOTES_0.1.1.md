# Clausis 0.1.1 – technische Vorschau

Erste bootfähige Debian-13-amd64-Testversion von Clausis mit GNOME, Calamares,
Orca, PipeWire, lokaler Faster-Whisper-Spracherkennung, eSpeak NG und dem
abgesicherten Clausis-Aktionskern.

## ISO herunterladen

GitHub erlaubt einzelne Release-Dateien nur bis 2 GiB. Deshalb besteht das
2,14-GiB-ISO aus den beiden Dateien:

- `clausis-0.1.1-amd64.iso.part-aa`
- `clausis-0.1.1-amd64.iso.part-ab`

Zusätzlich `clausis-0.1.1-amd64.iso.sha256` herunterladen. Unter Linux beide
Teile in einem Ordner mit folgendem Befehl zusammensetzen:

```sh
cat clausis-0.1.1-amd64.iso.part-aa clausis-0.1.1-amd64.iso.part-ab > clausis-0.1.1-amd64.iso
sha256sum -c clausis-0.1.1-amd64.iso.sha256
```

Die für den veröffentlichten Server-Build gültige SHA-256-Prüfsumme steht in
`clausis-0.1.1-amd64.iso.sha256`. Diese Datei wird im selben automatischen
Build wie die beiden ISO-Teile erzeugt.

Danach kann das ISO mit Raspberry Pi Imager oder balenaEtcher auf einen
USB-Stick mit mindestens 8 GB geschrieben werden.

## Verifizierter Stand

- 60 automatisierte Kern- und Sicherheitstests bestanden.
- Vollständiger ISO-Medienbereich lesbar.
- BIOS- und UEFI-Bootabbilder vorhanden.
- Kernel, Initramfs und Live-System booteten unter x86-64-QEMU bis zum GNOME
  Display Manager.

## Wichtige Grenzen

Dies ist ausdrücklich eine Vorabversion für Tests. Das genaue ISO wurde noch
nicht auf physischer Hardware installiert. Hermes-Anbietereinrichtung,
vollständige sprachgesteuerte Partitionierung, Voice-PIN, TPM/LUKS und Rollback
sind noch nicht fertig. Vor Installationsversuchen müssen wichtige Daten extern
gesichert werden.
