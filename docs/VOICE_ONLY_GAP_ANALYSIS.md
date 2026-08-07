# Clausis: Weg zu vollständig sprach- und audiobedienbarem GNOME

Status: technische Lückenanalyse für Clausis 0.3.x. „Nur mit Sprache“ darf
nicht bedeuten, dass Tastatur und Orca entfernt werden. Diese bleiben
gleichwertige Rettungs- und Barrierefreiheitswege.

## Was heute bereits funktioniert

- Lokale Aufnahme, Offline-Spracherkennung und Sprachausgabe.
- Deterministische Kernbefehle für Lautstärke, Anwendungen, Netzwerk und einige
  Systemfunktionen.
- Optionales GPT Live mit flüssigerer Sprache und ausschließlich typisierten
  Clausis-Aktionen.
- Ein zugänglicher Einrichtungsdialog vor Calamares und automatischer Start der
  Sprachsteuerung im installierten System.
- Ein Aktionsbroker, der freie Shell-Befehle verhindert und riskante Aktionen
  von einer getrennten Bestätigung abhängig macht.

Das reicht noch nicht für ein vollständig sprachbedienbares Betriebssystem.
Insbesondere sind unbekannte GNOME-Dialoge, Dateiauswahl, Fensterverwaltung,
Boot-Fehler und die Datenträgeraufteilung noch nicht durchgängig abgedeckt.

## Fehlende Systembausteine

### 1. Dauerhafte lokale Audio-Schicht

Clausis benötigt einen unprivilegierten PipeWire-Dienst mit lokalem Wake-Word,
VAD, Echounterdrückung und echtem Barge-in. „Stopp Clausis“ muss vor jeder
Cloud- oder Agentenverarbeitung lokal erkannt werden. Bei ungeeigneter Hardware
muss der Dienst hörbar in Halbduplex wechseln. Mikrofon, Lautsprecher und
Erkennungszustand brauchen eindeutige Audio-Signale, die nicht mit gesprochenen
Antworten verwechselt werden.

### 2. Semantische GNOME-Steuerung

Ein `Clausis GNOME Adapter` muss AT-SPI, definierte D-Bus-Schnittstellen und
xdg-desktop-portals verbinden. Er braucht typisierte Aktionen für:

- aktives Fenster lesen, wechseln, minimieren, maximieren, schließen und auf
  eine Arbeitsfläche verschieben;
- Übersicht, Anwendungen, Schnelleinstellungen und Benachrichtigungen;
- zugängliche Bedienelemente auflisten, benennen, fokussieren und auslösen;
- Datei-, Ordner-, Öffnen-, Speichern- und Berechtigungsdialoge;
- Zwischenablage, Bildschirmtastatur, Vergrößerung und Orca-Funktionen.

Mauskoordinaten und Bildschirmerkennung dürfen nur ein gekennzeichneter
Best-Effort-Fallback sein. Unter Wayland soll Clausis keine globale
Eingabesimulation als Hauptschnittstelle verwenden.

### 3. Sprachdialog für Orientierung und Korrektur

Das System braucht überall dieselben lokalen Befehle: „Wo bin ich?“, „Was kann
ich hier tun?“, „Lies das Fenster vor“, „Nummer drei“, „Zurück“, „Wiederholen“,
„Korrigieren“ und „Abbrechen“. Mehrdeutige Ziele müssen nummeriert vorgelesen
werden. Nach jeder Aktion muss Clausis Erfolg, Ablehnung oder unveränderten
Zustand anhand des tatsächlichen GNOME-Zustands melden – nicht anhand einer
Modellbehauptung.

### 4. Vertrauenswürdige Bestätigung

Neustart, Löschen, Paketinstallation, Konten, Berechtigungen und Datenträger
dürfen weder Hermes noch GPT Live selbst bestätigen. Erforderlich sind ein vom
GNOME-Desktop getrenntes Audio-/Seat-Portal, eine zufällige Bestätigungsphrase,
kurzlebige gebundene Tokens und ein lokaler Abbruch. Die heutige prototypische
D-Bus-PIN-Übertragung ist dafür nicht ausreichend.

### 5. Installation, Anmeldung und Wiederherstellung

Calamares muss Installationsdaten über ein eigenes Sprach-Backend erhalten,
nicht durch Screen-Scraping. Datenträgerplan, Verschlüsselung und Zielgerät
müssen vollständig vorgelesen und mit einer zufälligen Phrase bestätigt werden.
Zusätzlich fehlen durchgängiges Audio in Initramfs, LUKS-Entsperrung, GDM,
Recovery und Rollback. Stimme allein ist keine sichere
Festplattenentsperrung; FIDO2, TPM-PIN und Recovery-Key bleiben nötig.

### 6. Anwendungen und Erweiterbarkeit

Für Kernprogramme braucht Clausis geprüfte Adapter und ein versioniertes
Voice-Action-Profil. Unbekannte Anwendungen können über AT-SPI erkundet werden,
aber irreversible Aktionen bleiben gesperrt. Neue Plug-ins benötigen Signatur,
Manifest, Herkunft, Berechtigungen und automatische Injektionsprüfungen; eine
KI darf sie nicht autonom erzeugen und sofort aktivieren.

### 7. Ausfall- und Qualitätssicherung

Für kein Netz, defektes Mikrofon, fehlende Stimme, abgestürzten Broker,
blockierten Dialog und fehlerhaftes Update braucht es jeweils gesprochene sowie
Orca-/Tastatur-Recoverywege. Abnahmetests müssen echte GNOME-Sitzungen und
physische Audiogeräte einbeziehen: Latenz, Fehlauslösungen, Barge-in,
Hintergrundsprache, synthetische Stimmen, Prompt Injection und Stromausfall.

## Empfohlene Reihenfolge

1. Lokaler Audio-Daemon mit Wake-Word, VAD und garantiertem Not-Aus.
2. GNOME-Adapter für Fenster, Fokus, zugängliche Elemente und Portale.
3. Einheitlicher Orientierungs- und Korrekturdialog.
4. Geschütztes Bestätigungsportal und privilegierte Adapter.
5. Sprach-nativer Installer sowie Boot-, Login- und Recovery-Audio.
6. Geprüfte Anwendungsprofile, Hardwarematrix und Nutzerstudien.

Erst wenn diese sechs Stufen auf unterstützter Hardware bestanden sind, sollte
Clausis als vollständig sprachbedienbares Betriebssystem bezeichnet werden.
