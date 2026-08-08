# Clausis: Weg zu vollständig sprach- und audiobedienbarem GNOME

Status: fortgeschriebene Lückenanalyse für Clausis 0.5.x. Diese Datei betrachtet
die Sprachsteuerung als Technik; was einem blinden Menschen zum vollständigen
Arbeiten fehlt, steht in [`BLIND_USE_GAP_ANALYSIS.md`](BLIND_USE_GAP_ANALYSIS.md). „Nur mit Sprache“ darf
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
Dazu kommen jetzt:

- Eine zweistufige Wake-Kette: ein Energiegate verwirft Stille für 0,03 % eines
  80-ms-Frames, erst danach läuft überhaupt ein Keyword-Modell. Solange es
  aktiv ist, wird nichts transkribiert, bevor das Wake-Wort erkannt wurde.
- Ein lokaler Unterbrechungsdetektor, der sich ohne zertifizierte
  Echounterdrückung **weigert** scharf zu schalten, weil Clausis sich sonst
  selbst unterbricht. `AudioMode.FULL_DUPLEX` ist erreichbar, aber nur wenn
  zertifizierte Hardware, gemeinsamer Takt, Echounterdrückung und ein
  gemessener Detektor zusammenkommen.
- Eine PipeWire-Konfiguration für `module-echo-cancel`.
- Nichtsprachliche Hörsignale für Aufwachen, Bestätigung, Fehler und Schlafen.

Es fehlt weiterhin das Wake-Word-Modell selbst: die Gewichte haben eine eigene
Lizenz, müssen zur tatsächlichen Aktivierungsphrase passen und ihre
Fehlauslöserate muss auf echter Hardware gemessen werden. Bis dahin bleibt die
Transkript-Erkennung aktiv, und das Flag `interrupt_detector` — das allein
Vollduplex freischaltet — darf nicht gesetzt werden. Bis diese Kette auf
zertifizierter Hardware geprüft ist, verspricht Clausis kein Vollduplex.

### 2. Semantische GNOME-Steuerung

Der `Clausis GNOME Adapter` liest AT-SPI begrenzt und ohne
Bildschirmkoordinaten. Umgesetzt sind:

- Orientierung: aktives Fenster, Fokus und bis zu 30 nummerierte Ziele;
  Fensterwechsel, Zurück und bestätigte nummerierte Aktivierung.
- Fenster schließen ausschließlich über die vom Programm selbst
  veröffentlichte Schließen-Aktion; Clausis beendet keinen Prozess gewaltsam.
- Diktat in fokussierte Textfelder über AT-SPI `EditableText`, inklusive
  Rücklesen des Feldinhalts nach dem Schreiben und harter Verweigerung in
  Passwortfeldern und Terminals.
- Standarddialoge: Öffnen, Speichern, einfache Meldung sowie Berechtigungs- und
  Anmeldeabfragen. Letztere bestätigt Clausis grundsätzlich nicht per Sprache —
  genau das wäre das Ziel eines eingeschleusten oder mitgehörten Satzes;
  Abbrechen bleibt sprachlich möglich, damit ein rein sprachlich bedienender
  Mensch nicht feststeckt.
- Zwischenablage (Vorlesen, Kopieren, Einfügen) mit denselben Verweigerungen
  wie beim Diktat, sowie Bildschirmtastatur, Bildschirmlupe und Orca als
  Schalter.
- Fensterverwaltung und Shell-Oberflächen über eine minimale
  GNOME-Shell-Erweiterung: Minimieren, Maximieren, Wiederherstellen,
  Arbeitsflächenwechsel, Fenster verschieben, Anwendungsraster,
  Schnelleinstellungen, Benachrichtigungen und Übersicht. Die Shell ist nicht
  Teil des AT-SPI-Baums; jede exportierte Methode ist parameterlos, damit ein
  kompromittierter Sitzungsprozess kein beliebiges Shell-Objekt benennen kann.

Die Erweiterung und die AT-SPI-Pfade sind bisher nur strukturell und gegen
einen nachgebildeten Baum getestet; ein Lauf in einer echten GNOME-Sitzung
steht aus. Noch ergänzt werden müssen:

- komplexe Fokusbewegung und weitere widget-spezifische Aktionen;
- Navigation in Dateilisten und Ordnerbäumen eines Dateidialogs;
- Diktat mit Satzzeichen-Kommandos und Cursor-Navigation im Feld;
- weitere Orca-Funktionen über die reine Ein- und Ausschaltung hinaus.

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

Die automatisierbare D-Bus-PIN-Übertragung wurde entfernt. Der isolierte
Systemdienst erzeugt und spricht die kanonische Zusammenfassung und eine
zufällige Phrase selbst, nimmt Phrase und PIN direkt lokal auf, löscht beide
temporären Aufnahmen und reicht das kurzlebige aktionsgebundene Token selbst an
den Broker weiter. D-Bus gibt weder Phrase, PIN noch Capability an Hermes oder
den Desktop zurück. Der Einrichtungsdialog kann die PIN zweimal lokal erkennen;
Calamares übernimmt nur den PBKDF2-Prüfwert in das Zielsystem.

Noch fehlen der physische Nachweis, dass PipeWire/ALSA auf unterstützter
Hardware wirklich vom Desktop-Audiographen getrennt ist, belastbare
Wiedergabe-/Stimmklon-Erkennung, privilegierte Produktionsadapter sowie ein
lokal garantiertes gesprochenes Abbruchsignal während der Bestätigung. Bis
diese Punkte geprüft sind, bleibt der Pfad eine technische Vorschau.

### 5. Installation, Anmeldung und Wiederherstellung

Die read-only Datenträgererkennung ist umgesetzt. Sie bietet nur beschreibbare,
nicht entfernbare, mindestens 32-GiB-große, nicht eingehängte Gesamtdatenträger
mit stabiler `/dev/disk/by-id`-Kennung an und sperrt insbesondere das gestartete
Live-Medium. Ein Plan wird vor der Übergabe erneut an Kennung, exakte Größe und
Seriennummer-Ende gebunden. Der kanonische Text nennt vollständiges Löschen,
Zielidentität, Dateisystem, Bootmodus, Verschlüsselung, Benutzer, Sprache und
Zeitzone. Eine exakte, einmalige Zufallsphrase mit Ablauf und fail-closed
Vergleich ist als interner Baustein vorhanden.

Calamares startet weiterhin ohne vorausgewählte Löschaktion. Verschlüsselung
ist vorausgewählt; die Zielkonfiguration verwendet LUKS2, ein getrenntes
unverschlüsseltes `/boot` und Btrfs. Eine minimale, aus der exakten Debian-Quelle
gebaute Calamares-Anpassung exportiert Zielgerät, Modus, Verschlüsselungsstatus
und Dateisystem ohne Passphrase. Ein Clausis-Wächter bindet diese Werte direkt
vor dem ersten Partitionsjob erneut an die aktuelle Hardware. Geändertes Ziel,
fehlende stabile Kennung, Einhängung, deaktiviertes LUKS oder anderes Dateisystem
brechen eine automatische Komplettinstallation ab. Manuelle, Koexistenz- und
Ersetzen-Modi bleiben als von Calamares selbst bestätigte Tastatur-/Orca-Wege.

Der Wächter erzeugt die Zufallsphrase nun erst nach der erneuten Zielbindung,
spricht Datenträgeridentität und Löschprofil selbst, nimmt genau eine lokale
Antwort auf und löscht die Aufnahme. Phrase und Transkript erscheinen weder in
Calamares-Variablen noch auf stdout. Derselbe Prozess erzeugt einen zufälligen
Recovery-Key mit etwa 159 Bit Entropie, spricht ihn zweimal und legt ihn nur
kurzzeitig root-lesbar im flüchtigen `/run` ab. Das angepasste
`luksbootkeyfile`-Modul fügt ihn nach der Partitionierung direkt als LUKS-Key
hinzu und entfernt alle temporären Kopien. Die nachgewiesene Trennung des
Audiogeräts von der Desktop-Sitzung, ein zugänglicher Verifikationstest des
notierten Schlüssels und der gleichwertige geschützte Tastaturweg fehlen
weiterhin. Die Lösung verwendet kein Screen-Scraping; die Produktionsfreigabe
bleibt blockiert.

Audio bei der LUKS-Entsperrung und am Anmeldebildschirm ist umgesetzt: die
Ansagen werden bei der Paketkonfiguration vorgerendert, weil es im Initramfs
keinen Synthesizer gibt, und von einem minimalen ALSA-Player abgespielt, den
der Initramfs-Hook zusammen mit den Sound-Modulen einbindet. Die Ansage sagt
ausdrücklich, dass das Passwort über die Tastatur einzugeben ist und nicht
vorgelesen wird. Am GDM-Greeter, wo noch nichts von Clausis läuft, ist Orca
aktiviert. Jeder Schritt ist best effort und darf einen Start nie blockieren.

Das Btrfs-Subvolume-Layout ist jetzt deklariert und passt zum Rollback: nur `/`
liegt innerhalb der Rücknahmegrenze, `/home`, `/var/log`, `/var/lib/clausis`,
`/.snapshots`, die Caches und die Auslagerungsdatei bewusst außerhalb. Eine
zurückgenommene Aktualisierung darf die manipulationssichere Protokollkette
nicht mit löschen — sonst verschwände genau der Nachweis dessen, was die
Aktualisierung getan hat. Fehlt das Layout, läuft die Rücknahme trotzdem, sagt
aber ausdrücklich, dass das Protokoll betroffen sein kann.

Es fehlt weiterhin die Prüfung dieser Kette auf echter Hardware. Stimme allein ist keine sichere
Festplattenentsperrung; FIDO2, TPM-PIN und Recovery-Key bleiben nötig.

### 6. Anwendungen und Erweiterbarkeit

Für Kernprogramme braucht Clausis geprüfte Adapter und ein versioniertes
Voice-Action-Profil. Unbekannte Anwendungen können über AT-SPI erkundet werden,
aber irreversible Aktionen bleiben gesperrt. Neue Plug-ins benötigen Signatur,
Manifest, Herkunft, Berechtigungen und automatische Injektionsprüfungen; eine
KI darf sie nicht autonom erzeugen und sofort aktivieren.

### 7. Ausfall- und Qualitätssicherung

Für kein Netz, defektes Mikrofon, fehlende Stimme, abgestürzten Broker,
blockierten Dialog und fehlerhaftes Update gibt es jetzt je einen benannten
Recoveryweg in `clausis.recovery`. Jeder Eintrag nennt zwingend den
gleichwertigen Tastatur-/Orca-Weg; ein Test lässt keinen Fehlerfall ohne einen
solchen zu. Fällt die Sprachausgabe selbst aus, wechselt der `Announcer` auf
eine Desktop-Benachrichtigung — die Orca vorliest — und zuletzt auf das
Terminal. Eine Ausnahme aus Broker oder Adapter beendet die Sprachschleife
nicht mehr, sondern wird zu einer gesprochenen Meldung mit Tastaturweg; „Stopp"
funktioniert danach weiter. Der Healthcheck trennt außerdem „ein Update hat
etwas kaputtgemacht, das ein Rollback repariert" von „diesem Rechner fehlt eine
Fähigkeit", damit ein fehlendes Mikrofon kein Rollback auslöst.

Das Snapshot-Rollback ist inzwischen verdrahtet: Paket- und Sicherheits-
aktualisierungen laufen zwischen einem `pre`- und einem `post`-Snapshot, danach
prüft der Healthcheck, und eine fehlgeschlagene oder sprachbrechende
Aktualisierung wird automatisch zurückgenommen. Noch offen: Recovery-Audio in
Initramfs, LUKS-Entsperrung und GDM sowie ein Lauf auf echtem Btrfs mit
snapper. Abnahmetests müssen echte GNOME-Sitzungen
und physische Audiogeräte einbeziehen: Latenz, Fehlauslösungen, Barge-in,
Hintergrundsprache, synthetische Stimmen, Prompt Injection und Stromausfall.

## Empfohlene Reihenfolge

1. Dediziertes Wake-Word, lokale Unterbrechung und zertifiziertes Barge-in.
2. GNOME-Adapter auf Shell, Portale und Standarddialoge ausweiten.
3. Geschütztes Bestätigungsportal und privilegierte Adapter.
4. Sprach-nativer Installer sowie Boot-, Login- und Recovery-Audio.
5. Geprüfte Anwendungsprofile, Hardwarematrix und Nutzerstudien.

Erst wenn diese fünf Stufen auf unterstützter Hardware bestanden sind, sollte
Clausis als vollständig sprachbedienbares Betriebssystem bezeichnet werden.
