# Clausis 0.5.0 – sicher gebundene Sprachinstallation

Clausis 0.5.0 ist eine öffentliche technische Vorschau für Tests in einer VM
oder auf entbehrlicher Hardware. Es ist noch kein Produktionssystem.

## Neu

- Der Installer bindet das ausgewählte Laufwerk unmittelbar vor dem ersten
  Schreibvorgang erneut an stabile Gerätekennung, exakte Größe und
  Seriennummer-Ende. Live-Medium, Wechseldatenträger, eingehängte,
  schreibgeschützte, zu kleine oder instabil benannte Laufwerke werden
  abgewiesen.
- Eine automatische Komplettinstallation ist nur mit LUKS2 und Btrfs möglich.
  Calamares wählt das Löschen eines Laufwerks niemals selbst vor.
- Vor dem Löschen liest Clausis den vollständigen Plan selbst vor und verlangt
  genau eine zufällige, kurzlebige Bestätigungsphrase. Phrase und Transkript
  erscheinen weder in Calamares-Variablen noch in Prozessargumenten.
- Clausis erzeugt einen sprachfreundlichen LUKS-Recovery-Schlüssel mit etwa
  159 Bit Entropie, liest ihn zweimal vor und fügt ihn intern dem verschlüsselten
  System hinzu. Temporäre Kopien werden überschrieben und gelöscht.
- Das Clausis-Hörsymbol, das dunkle Türkis-Violett-Design, Atkinson
  Hyperlegible, reduzierte Bewegung und die Barrierefreiheitsanzeige verbinden
  Bootmenü, GDM, GNOME und Einrichtungsdialog visuell.
- Hermes Agent bleibt offline vorinstalliert. Bei einer Online-Installation
  kann Clausis freiwillig die neueste offizielle stabile Hermes-Version
  installieren; bei Fehlern bleibt die geprüfte Image-Version aktiv.
- GPT Live kann freiwillig für flüssige Online-Sprache genutzt werden. Dafür
  gelten eine getrennte Einwilligung, ein eigener API-Schlüssel und weiterhin
  nur die typisierten Clausis-Aktionen ohne Shell- oder Plug-in-Zugriff.
- ISO-, Screenshot- und Release-Dateinamen werden nun aus einer einzigen
  Projektversion erzeugt. Ein Release-Tag muss exakt dazu passen.

## Windows und VirtualBox

Alle beiden `*.part-*`-Dateien und die `.sha256`-Datei herunterladen. Nicht
entpacken. In PowerShell im Download-Ordner ausführen:

```powershell
cmd /c copy /b clausis-0.5.0-amd64.iso.part-aa+clausis-0.5.0-amd64.iso.part-ab clausis-0.5.0-amd64.iso
$expected = (Get-Content .\clausis-0.5.0-amd64.iso.sha256).Split()[0].ToUpper()
$actual = (Get-FileHash .\clausis-0.5.0-amd64.iso -Algorithm SHA256).Hash
if ($actual -ne $expected) { throw "Prüfsumme falsch – Dateien erneut herunterladen" }
"Prüfsumme OK: $actual"
```

Danach `clausis-0.5.0-amd64.iso` in VirtualBox direkt als optisches Medium
auswählen. Das ISO selbst darf nicht entpackt werden.

Empfohlene Test-VM: Linux/Debian 64-bit, EFI eingeschaltet, 8 GB RAM, zwei
Prozessorkerne, mindestens 40 GB neue virtuelle Festplatte, Audioausgabe und
Mikrofoneingang aktiviert. Zuerst den Live-Start und die Sprachausgabe prüfen,
dann ausschließlich die leere virtuelle Festplatte auswählen. Nach der
Installation das ISO aus dem virtuellen Laufwerk entfernen und neu starten.
Prüfen, dass LUKS2 entsperrt, GNOME startet, das Clausis-Design sichtbar ist
und Hermes beziehungsweise die lokale Sprachsteuerung eingerichtet wurden.
Keine privaten API-Schlüssel oder echten persönlichen Daten in die Test-VM
eingeben.

## Bekannte Grenzen

- Die vollständige Installation und anschließende Entsperrung mit dem exakt
  gesprochenen Recovery-Schlüssel ist noch ein offenes persistentes VM-Gate.
- VirtualBox-spezifische Audio-, Mikrofon- und Echounterbrechungstests fehlen
  auf dem aktuellen Build-Rechner; die Bootprüfung erfolgt derzeit mit QEMU.
- Physische Audio-Isolation, geschützter Tastatur-/Orca-Bestätigungspfad,
  Stimmklon-/Replay-Erkennung, TPM/FIDO2 und automatischer Snapshot-Rollback
  sind noch nicht produktionsreif.
- Vor Tests auf echter Hardware müssen wichtige Dateien vollständig gesichert
  werden. Die Installation kann den ausgewählten Datenträger vollständig
  löschen.
