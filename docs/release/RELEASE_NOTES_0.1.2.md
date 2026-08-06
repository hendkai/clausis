# Clausis 0.1.2 – technische Vorschau

Diese Testversion ersetzt den gelben Debian-Helm im Startmenü durch ein
eigenes, für Clausis generiertes Logo. Außerdem enthält sie die fehlende
Debian-Komponente `user-setup`, damit die grafische Live-Sitzung den Benutzer
`clausis` anlegt und automatisch anmeldet.

## ISO herunterladen

GitHub erlaubt einzelne Release-Dateien nur bis 2 GiB. Deshalb besteht das ISO
aus den beiden Dateien:

- `clausis-0.1.2-amd64.iso.part-aa`
- `clausis-0.1.2-amd64.iso.part-ab`

Zusätzlich `clausis-0.1.2-amd64.iso.sha256` herunterladen. Die drei Dateien
nicht entpacken, sondern unverändert in denselben Ordner legen.

### Windows (PowerShell)

Im Ordner mit den drei heruntergeladenen Dateien PowerShell öffnen und
ausführen:

```powershell
cmd /c copy /b clausis-0.1.2-amd64.iso.part-aa+clausis-0.1.2-amd64.iso.part-ab clausis-0.1.2-amd64.iso
$expected = (Get-Content .\clausis-0.1.2-amd64.iso.sha256).Split()[0].ToUpper()
$actual = (Get-FileHash .\clausis-0.1.2-amd64.iso -Algorithm SHA256).Hash
if ($actual -ne $expected) { throw "Pruefsumme falsch - Dateien erneut herunterladen" }
"Pruefsumme OK: $actual"
```

Danach `clausis-0.1.2-amd64.iso` direkt in VirtualBox als optisches Medium
auswählen. Die fertige ISO nicht entpacken.

### Linux oder Git Bash

```sh
cat clausis-0.1.2-amd64.iso.part-aa clausis-0.1.2-amd64.iso.part-ab > clausis-0.1.2-amd64.iso
sha256sum -c clausis-0.1.2-amd64.iso.sha256
```

Die gültige SHA-256-Prüfsumme steht in der zusammen mit den ISO-Teilen
erzeugten Datei `clausis-0.1.2-amd64.iso.sha256`.

## Änderungen seit 0.1.1

- Eigenes Clausis-Zeichen aus C, Sprachwelle und Audiopuls.
- Neue Boot-Hintergründe für GRUB/UEFI und Syslinux/BIOS.
- Fehlende `user-setup`-Abhängigkeit für das grafische Live-Autologin ergänzt.
- Interne Berechtigungsgruppe in `clausis-control` umbenannt, damit sie nicht
  mit dem Live-Benutzer `clausis` kollidiert.
- Regressionstests für Branding, Bildformate und Live-Systemkonfiguration.
- 67 automatisierte Kern-, Sicherheits-, Branding- und Konfigurationstests.

## Wichtige Grenzen

Dies ist ausdrücklich eine Vorabversion für Tests. Hermes-Anbietereinrichtung,
vollständige sprachgesteuerte Partitionierung, Voice-PIN, TPM/LUKS und Rollback
sind noch nicht fertig. Vor Installationsversuchen müssen wichtige Daten extern
gesichert werden.
