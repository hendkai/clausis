# VoiceOS 0.1.0 – technische Vorschau

Erste bootfähige Debian-13-amd64-Testversion von VoiceOS mit GNOME, Calamares,
Orca, PipeWire, lokaler Faster-Whisper-Spracherkennung, eSpeak NG und dem
abgesicherten VoiceOS-Aktionskern.

## ISO herunterladen

GitHub erlaubt einzelne Release-Dateien nur bis 2 GiB. Deshalb besteht das
2,14-GiB-ISO aus den beiden Dateien:

- `voiceos-0.1.0-amd64.iso.part-aa`
- `voiceos-0.1.0-amd64.iso.part-ab`

Zusätzlich `voiceos-0.1.0-amd64.iso.sha256` herunterladen. Unter Linux beide
Teile in einem Ordner mit folgendem Befehl zusammensetzen:

```sh
cat voiceos-0.1.0-amd64.iso.part-aa voiceos-0.1.0-amd64.iso.part-ab > voiceos-0.1.0-amd64.iso
sha256sum -c voiceos-0.1.0-amd64.iso.sha256
```

Erwartete SHA-256-Prüfsumme:

`17ad4e1f09448de0386976fbddaa51e0f0dd16839d0cc9581aeb61afbb9f8cf2`

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
