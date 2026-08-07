# Clausis: Weg zu vollständig sprach- und audiobedienbarem GNOME

Status: fortgeschriebene Lückenanalyse für Clausis 0.4.x. „Nur mit Sprache“ darf
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
- Ein lokales Aktivierungsfenster: Hintergrundtranskripte werden bis „Hallo
  Clausis“ verworfen; „Stopp Clausis“ wird vor Agent und Cloud behandelt.
- Ein erster AT-SPI-Adapter für aktives Fenster, Fokus, nummerierte
  Bedienelemente, semantisches Zurück und Fensterwechsel.
- Lokale, anwendungsübergreifende Befehle für Orientierung, Wiederholung,
  Korrektur und Abbruch.

Das reicht noch nicht für ein vollständig sprachbedienbares Betriebssystem.
Insbesondere sind unbekannte GNOME-Dialoge, Dateiauswahl, Fensterverwaltung,
Boot-Fehler und die Datenträgeraufteilung noch nicht durchgängig abgedeckt.

## Fehlende Systembausteine

### 1. Dauerhafte lokale Audio-Schicht

Der persistente lokale Prozess, die STT-basierte Aktivierung, das lokale
Not-Aus, die Hardwareprobe und der ehrliche Halbduplex-Fallback sind umgesetzt.
Noch fehlen ein dediziertes Wake-Word-Modell mit niedriger Dauerlast,
Echounterdrückung, ein lokal garantierter Unterbrechungsdetektor für echtes
Barge-in sowie eindeutige nichtsprachliche Hörsignale. Bis diese Kette auf
zertifizierter Hardware geprüft ist, verspricht Clausis kein Vollduplex.

### 2. Semantische GNOME-Steuerung

Der erste `Clausis GNOME Adapter` liest AT-SPI begrenzt und ohne
Bildschirmkoordinaten. Aktives Fenster, Fokus und bis zu 30 semantische Ziele
können vorgelesen werden; Fensterwechsel, Zurück und bestätigte nummerierte
Aktivierung sind typisierte Aktionen. Noch ergänzt werden müssen:

- aktives Fenster lesen, wechseln, minimieren, maximieren, schließen und auf
  eine Arbeitsfläche verschieben;
- Übersicht, Anwendungen, Schnelleinstellungen und Benachrichtigungen;
- komplexe Fokusbewegung und weitere widget-spezifische Aktionen;
- Datei-, Ordner-, Öffnen-, Speichern- und Berechtigungsdialoge;
- Zwischenablage, Bildschirmtastatur, Vergrößerung und Orca-Funktionen.

Mauskoordinaten und Bildschirmerkennung dürfen nur ein gekennzeichneter
Best-Effort-Fallback sein. Unter Wayland soll Clausis keine globale
Eingabesimulation als Hauptschnittstelle verwenden.

### 3. Sprachdialog für Orientierung und Korrektur

Die lokalen Befehle „Wo bin ich?“, „Was kann ich hier tun?“, „Lies das Fenster
vor“, „Nummer drei“, „Zurück“, „Wiederholen“, „Korrigieren“ und „Abbrechen“ sind
umgesetzt. Ziele werden nummeriert aus dem aktuellen AT-SPI-Baum gelesen. Noch
fehlen dialogübergreifende Korrektur-Slots und eine vollständige
Nachzustandsprüfung für jede schreibende Aktion.

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

1. Dediziertes Wake-Word, lokale Unterbrechung und zertifiziertes Barge-in.
2. GNOME-Adapter auf Shell, Portale und Standarddialoge ausweiten.
3. Geschütztes Bestätigungsportal und privilegierte Adapter.
4. Sprach-nativer Installer sowie Boot-, Login- und Recovery-Audio.
5. Geprüfte Anwendungsprofile, Hardwarematrix und Nutzerstudien.

Erst wenn diese fünf Stufen auf unterstützter Hardware bestanden sind, sollte
Clausis als vollständig sprachbedienbares Betriebssystem bezeichnet werden.
