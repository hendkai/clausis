# Clausis 0.6.0 – Textarbeit, Struktur und eine bessere Stimme

Clausis 0.6.0 ist eine technische Vorschau für Tests in einer VM oder auf
entbehrlicher Hardware. Es ist noch kein Produktionssystem.

## Neu

- **Mehrstufige Cursor-Navigation**: „drei Wörter zurück", „nächster
  Absatz", „Zeile 12" und „Zeile zwölf" bewegen den Cursor in einem
  Befehl — mit ehrlichem Anhalten an den Grenzen und einer Positionsansage.
- **Say-All mit Pause und Fortsetzen**: „lies alles vor" liest das
  fokussierte Feld satzweise vor, „stopp" bricht ab, „lies weiter" setzt
  am Merker fort. Die Kommando-Schleife bleibt dabei frei.
- **Vollständige Diktiermodi**: Datum („zwölfter august 2026" →
  `12.08.2026`, mit Kalenderprüfung), Uhrzeit („14 uhr 30"), Zahlwörter
  bis 999.999 („zweihundertfünfundzwanzig") und Pfad-Trenner („schrägstrich
  home hendrik" → `/home/hendrik`). Nicht Parsembares wird ehrlich
  abgelehnt, nie geraten.
- **Korrektur-Slot**: „nein, ich meinte …" ersetzt das letzte Diktat im
  Feld — mit Byte-Identitäts-Check: Hat sich das Feld unter der Hand
  geändert, wird ehrlich verweigert statt falsch ersetzt.
- **Strukturnavigation**: „nächste Überschrift", „vorheriger Link",
  „nächste Liste", „nächste Landmarke" — auch im Browser: Der Sprung
  bleibt auf das angezeigte Dokument begrenzt (Browser-Chrome und
  vorinstallierte Tabs sind außen vor) und gegen echte firefox-esr-Rollen
  auf echtem Accessibility-Bus verifiziert. Links werden dabei nie
  aktiviert.
- **Piper als neuronale Offline-Stimme**: Die natürlichere Stimme ersetzt
  espeak-ng als deutsche Standardstimme (Integration als
  speech-dispatcher-Modul, kein zweites TTS-System). Binary und Modell
  (Thorsten-Voice, CC0; Piper MIT) werden zur Image-Bauzeit mit
  SHA-256-Pins geladen — der erste Start spricht ohne Netz. Fehlt das
  Modell, fällt das System ehrlich auf espeak-ng zurück.

## Grenzen, bewusst offen

- Sprachbedienung im Browser beschränkt sich auf Struktur-Sprünge;
  Aktivierung, Tabellen, Formulare und Live-Regionen folgen später.
- Die Piper-Sprachqualität ist auf echter Hardware zu bewerten; der Bau
  prüft Struktur, Pins und Fallback-Kette.
- Wie gehabt: keine Diktate in Passwortfeldern oder Terminals, keine
  Sprachfreigabe von Berechtigungsdialogen.

## Windows und VirtualBox

Alle beiden `*.part-*`-Dateien und die `.sha256`-Datei herunterladen. Nicht
entpacken. In PowerShell im Download-Ordner ausführen:

```powershell
cmd /c copy /b clausis-0.6.0-amd64.iso.part-aa+clausis-0.6.0-amd64.iso.part-ab clausis-0.6.0-amd64.iso
$expected = (Get-Content .\clausis-0.6.0-amd64.iso.sha256).Split()[0].ToUpper()
$actual = (Get-FileHash .\clausis-0.6.0-amd64.iso -Algorithm SHA256).Hash
if ($actual -ne $expected) { throw "Checksum mismatch - download the parts again" }
"Checksum OK: $actual"
```

Linux und Git Bash:

```sh
cat clausis-0.6.0-amd64.iso.part-aa clausis-0.6.0-amd64.iso.part-ab > clausis-0.6.0-amd64.iso
sha256sum -c clausis-0.6.0-amd64.iso.sha256
```

macOS:

```sh
shasum -a 256 -c clausis-0.6.0-amd64.iso.sha256
```

Das Aneinanderhängen der Teile ist bewusst Teil der Verifikation: Es
prüft, dass die Teile vollständig sind.

## Testen in einer VM

VirtualBox: neue VM (Typ Linux, Debian 64-bit), mindestens 4096 MB RAM,
2 CPUs, 20 GB Festplatte. Unter „Audio" die Standardausgabe wählen — ohne
Audiogerät bleibt die Sprachausgabe stumm, das System läuft aber. Das ISO
als optisches Laufwerk einbinden und starten. Getestet werden kann ab dem
Bootmenü: jede Ansage, die Sprachsteuerung nach der Anmeldung und die
Installation über Calamares auf einer entbehrlichen Platte.
