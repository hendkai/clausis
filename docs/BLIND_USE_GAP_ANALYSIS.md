# Was fehlt zu einem vollständig sprachbedienbaren Linux für blinde Menschen

Status: Bestandsaufnahme, Stand Clausis 0.5.0 + laufende Arbeit.

Diese Analyse beantwortet eine andere Frage als
[`VOICE_ONLY_GAP_ANALYSIS.md`](VOICE_ONLY_GAP_ANALYSIS.md). Dort geht es um die
Sprachsteuerung als Technik. Hier geht es um die Person: Was muss ein blinder
Mensch tun können, ohne je auf den Bildschirm zu sehen — und was davon geht
heute nicht?

## 0. Vorbemerkung zu „100 %"

Kein Betriebssystem der Welt erfüllt heute „100 % per Sprache bedienbar", und
eine Zahl ohne Messvorschrift ist eine Behauptung, keine Eigenschaft. Bevor
Clausis das je sagen darf, braucht es eine **Aufgabenliste**, die blinde
Testpersonen ohne fremde Hilfe und ohne Bildschirm abschließen — zum Beispiel:

- einen Rechner von USB installieren, verschlüsseln und einrichten,
- sich anmelden, ins WLAN kommen, E-Mail lesen und beantworten,
- ein Dokument diktieren, korrigieren, formatieren, speichern, verschicken,
- eine Datei im Web finden, herunterladen, umbenennen, in einen Ordner legen,
- ein Programm installieren, ein Update einspielen, einen Fehler zurücknehmen,
- eine defekte Anmeldung reparieren und wieder ins System kommen.

Erst wenn diese Liste vollständig, wiederholbar und auf mehreren
Hardwareprofilen besteht, ist die Aussage belegt. Alles darunter ist ein
Zwischenstand — auch der hier beschriebene.

Wichtig ist außerdem: **Sprache ersetzt keinen Screenreader.** Orca bleibt
gleichwertig und muss es bleiben. Ein Blindensystem, das nur noch spricht, wenn
das Mikrofon funktioniert, ist kein Fortschritt.

---

## 1. Texterstellung und -bearbeitung — die größte Lücke

Clausis kann heute Text **einfügen**, das letzte Wort löschen, das Feld leeren
und den Inhalt vorlesen. Für echtes Arbeiten reicht das bei weitem nicht.

Umgesetzt (2026-08-24; zuerst gegen nachgebaute AT-SPI-Bäume, danach gegen ein
echtes GTK-Programm auf echtem AT-SPI-Bus verifiziert — Xvfb + dbus-run-session
+ at-spi-bus-launcher + GTK_MODULES=gail:atk-bridge + matchbox-WM, siehe
`scripts/atspi_session_smoke.sh` und den GitHub-Workflow „AT-SPI session
smoke"; das ist ein echter Bus und ein echtes Widget, aber noch kein vollständiger
GNOME-Desktop): Satzzeichen-Kommandos am Satzende, Cursor-Navigation
(Anfang/Ende/Wort vor und zurück, Vorlesen ab Cursor), Auswahl (alles markieren,
Wort, Satz), Ersetzen der Auswahl, Löschen der Auswahl, Rückgängig/Wiederholen
über die widget-eigene Aktion, Vorlesen mit Granularität (Zeichen/Wort/Zeile/
Satz/Absatz am Cursor) und der Buchstabiermodus („A wie Anton" → A,
deutsch/englisch, mit Ziffern). Der Sitzungstest deckt auch die
Passwortfeld-Verweigerung auf dem echten Bus ab.

Umgesetzt (2026-08-24, mehrstufige Navigation): „drei Wörter zurück", „nächster
Absatz", „Zeile 12" und „Zeile zwölf" bewegen den Cursor in einem Befehl — der
Adapter loopt intern über die Einheit (Wort/Zeile/Satz/Absatz), clampt ehrlich
an den Grenzen („Anfang erreicht, Wort-Navigation stoppt hier. Der Cursor steht
auf Position 0 von 47") und meldet die erreichte Position; Zeilennummern über
das Dokumentende hinaus werden abgefangen und auf die letzte Zeile gesetzt („Das
Dokument hat nur 7 Zeilen, ich stehe jetzt in Zeile 7"). Leerzeilen sind keine
Navigationseinheiten. Ziffern (1–3-stellig) und gesprochene Zahlwörter teilen
sich das Zahlvokabular des Zahl-Diktiermodus — seit 2026-08-25 bis 999.999
(s. Diktiermodi-Reste unten); die Sprung-/Schritt-Obergrenzen bleiben ehrlich
Zeile 1–999 und 1–99 Schritte.
Verifiziert gegen den Fake-Baum und im GTK-Sitzungstest gegen eine echte
mehrzeilige `Gtk.TextView` (3 Absätze, 7 Zeilen).

Teilweise umgesetzt (2026-08-24, Diktiermodi): E-Mail-Adressen, URLs/Dateipfade
und Zahlen haben je einen eigenen Diktiermodus mit explizitem Trigger —
„diktiere e-mail hendrik at kaiser-mail punkt de" → `hendrik@kaiser-mail.de`,
„diktiere url https doppelpunkt schrägstrich schrägstrich example punkt de" →
`https://example.de`, „diktiere zahl drei Komma eins vier" → `3,14`,
„diktiere zahl zweiundzwanzig" → `22`. Die Umwandlung feuert nur beim
expliziten Modus-Trigger, nie mitten in einer Äußerung (konsistent mit der
Satz-Ende-Regel für Satzzeichen); nicht parsembare Zahlen werden ehrlich
abgelehnt statt geraten, und der Modus-Ausgang bleibt schema-valide
(printable-only, ≤ 512 Zeichen, Injection-Korpus-Regression grün).

Umgesetzt (2026-08-25, Diktiermodi-Reste): Die vier offenen Punkte aus dem
Status vom 2026-08-24 sind geschlossen. **Datum**: „diktiere datum zwölfter
august 2026" → `12.08.2026` — Tag als Ziffer, Kardinal- oder Ordinalwort
(„zwölf"/„zwölfter"/„zwölften"), Monat als Ziffer oder deutscher/englischer
Monatsname („12 punkt 8 2026" geht ebenfalls), Jahr 1900–2099 als Ziffern
oder zusammengesetztes Zahlwort („zweitausendsechsundzwanzig"); der Kalender
entscheidet (30./31., Schaltjahr), alles Unparsembare wird ehrlich abgelehnt.
**Uhrzeit**: „diktiere uhrzeit vierzehn uhr dreißig" → `14:30` — bewusst nur
„H uhr" und „H uhr M" (24 h, Minuten als Ziffern oder Zahlwort);
umgangssprachliche Formen („halb drei", „viertel nach fünf") bleiben ehrlich
abgelehnt, weil das 14:30/15:30-Rätsel nicht geraten wird. **Zahlwörter bis
999.999**: das gemeinsame Vokabular (Zahl-Modus + Navigation) versteht jetzt
Hundert-/Tausend-Komposition („dreihundertfünfundzwanzig",
„zweitausendvierhundert", „einundzwanzigtausend"); getrennt gesprochene
Großzahlen bleiben Ziffernketten („hundert eins" → `1001`), Zahlen über
999.999 werden abgelehnt; die Zeilen-Navigation profitiert automatisch mit
(„zeile zweihundertfünfundzwanzig" → Zeile 225), ihr Cap bleibt aber ehrlich
1–999 („zeile tausend" lehnt ab), ebenso das Schritt-Cap 1–99 („hundert
wörter weiter" lehnt ab). **Pfad-Trenner**: „diktiere pfad" macht jedes
gesprochenes Wort zu einem Pfadsegment — „schrägstrich home hendrik" →
`/home/hendrik` (fixt `/homehendrik`); „punkt" klebt vorn am nächsten
Segment („home hendrik punkt bashrc" → `home/hendrik/.bashrc`, „punkt bashrc"
→ `.bashrc`), Zahlwörter werden Ziffern. Modus-Ausgang bleibt schema-valide
(printable, ≤ 512), Injection-Korpus-Regression weiter grün.

Umgesetzt (2026-08-25, Korrektur-Slot): „nein, ich meinte <text>" ersetzt das
letzte Diktat im fokussierten Feld, statt eine neue Äußerung anzuhängen — der
Blind Use Case „falsch verstanden, sofort korrigieren" ohne Feld-Leeren oder
Wort-Löschen. Der Adapter merkt sich pro Feld die exakte Zeichenspanne des
letzten Diktats (Feld-Schlüssel wie der Say-All-Merker: Anwendung|Fenster|
Fokus-Name); ein neues Diktat überschreibt den Merker, ein Fokuswechsel
verwirft ihn. Vor dem Ersetzen wird die gemerkte Spanne gegen den Live-Inhalt
geprüft — stimmt sie nicht mehr byte-identisch (unter der Hand hinein
getippt), wird ehrlich verweigert („Das Feld hat sich geändert, ich kann den
Abschnitt nicht sicher ersetzen"), nie falsch ersetzt. Die Mechanik ist
Bereichsauswahl über das AT-SPI-Textinterface (`addSelection`) plus Ersetzen
über `EditableText` — kein `select_all`-Fallback, der das Feld zerstören
könnte; Felder ohne Auswahl-Interface werden ehrlich abgelehnt. Ebenso
ehrlich: „Ich habe nichts diktiert, was ich ersetzen könnte" ohne Diktat-
Merker, und „Das letzte Diktat war in einem anderen Feld" nach Fokuswechsel.
Die Ersetzung selbst wird zum neuen Merker (Korrektur der Korrektur) und
verwirft den Say-All-Merker des Feldes (Feld hat sich geändert). Der Payload
folgt exakt dem Diktat-Vertrag (printable-only, ≤ 512, Kontrollbytes verwei-
gert vor jedem Adapter); keine Aktionen-Rücknahme („nein ich meinte löschen"
diktiert das Wort „löschen", kein Undo-Trick), und der Diktiermodus-Auslöser
feuert nicht innerhalb des Korrektur-Trigger (gleiche Satz-Ende-Regel wie
Satzzeichen) — eine E-Mail korrigiert man als neue Modus-Äußerung. Verifiziert
gegen den Fake-Baum und im GTK-Sitzungstest (diktieren → korrigieren → Feld
lesen). Offen bleibt die Rücknahme über den Dialog hinweg (Äußerungs-Stack,
s. o. und § 11).

Es fehlt weiterhin:

- **Grenze Kommando-Token als Name**: Ein Wort, das zufällig ein
  Kommando-Token ist („dot", „slash", „punkt" als Name), wird umgeformt —
  Ausweg ist das Escape „wörtlich"/„literal" vor dem Wort, ohne Vorwissen
  aber nicht auffindbar (gleiche Grundspannung wie beim Satzzeichen-Befehl
  am Satzende).
- **Umgangssprachliche Uhrzeiten**: „halb drei", „viertel nach/vor" haben
  bewusst keinen Uhrzeit-Modus (V1-Grenze: das 14:30/15:30-Rätsel wird
  nicht geraten); diktiere sie als „vierzehn uhr dreißig".
- **Leerzeichen in Dateinamen**: Der Pfad-Modus verkettet pro Segment —
  „meine datei v2" wird zu `meine/datei/v2`. Ausweg: Buchstabier-Modus oder
  „wörtlich"-Escape pro Wort (dokumentierte V1-Grenze).
- **URL-Doppelpunkt mitten im Host**: Ein gesprochenes „doppelpunkt" wird in
  URLs nur direkt nach einem Schema (https etc.) umgesetzt, nie mitten in
  Host/Port (bewusste V1-Grenze; unverändert durch die Zahlwort-Erweiterung).
- **Getrennt gesprochene Großzahlen**: „zwei tausend" (zwei Wörter) wird zur
  Ziffernkette `21000`-artig verkettet — korrekt zufällig, aber kein
  Kompositions-Parsing (`21.000` diktiert man als ein Wort
  „einundzwanzigtausend" oder als Ziffern). Ehrliche Grenze des Token-Modells.
- **Korrektur-Slots über den Dialog hinweg**: „nein, ich meinte …" ersetzt
  jetzt das letzte Diktat im selben Feld (s. unten, Korrektur-Slot) — über
  den Dialog hinweg (letzten *Befehl* rücknehmen, Äußerungs-Stack) bleibt
  offen, das braucht ein anderes Modell als der Feld-Merker.

Ohne diesen Block ist jede Textarbeit jenseits eines Einzeilers unmöglich.

## 2. Lesen und strukturelle Navigation

Orientierung heißt heute: aktives Fenster, Fokus, bis zu 30 nummerierte Ziele.
Für Inhalte reicht das nicht.

Umgesetzt (2026-08-24, Say-All): „lies alles vor" liest das fokussierte Feld
satzweise über speech-dispatcher vor (Chunk-für-Chunk im Hintergrund-Thread,
die Kommando-Schleife bleibt frei), „stopp" bricht ab (speech-dispatcher-Cancel
`spd-say -C`), „lies weiter" setzt am Merker fort („Weiter in Zeile 2. Sagen
Sie Stopp zum Pausieren."). Der Merker ist ein Zeichen-Offset nach dem letzten
komplett gesprochenen Satz, gilt pro Feld und wird bei Fokuswechsel oder
bewusster Navigation ehrlich verworfen; nach dem vollständigen Vorlesen steht
der Cursor einmalig am Feldende. Der unterbrochene Satz wird bei der
Fortsetzung ab seinem Anfang wiederholt. Verifiziert im Sitzungstest gegen
eine echte `Gtk.TextView` inklusive Stopp mitten im Satz und Fortsetzen am
Merker. Bekannte Grenzen, bewusst offen: keine Geschwindigkeitsänderung
während des Vorlesens, kein Highlighting, „stopp" wird (Halbduplex-Mikrofon)
zuverlässig frühestens an der Satzgrenze erkannt, und der Merker gilt nicht
dokumentübergreifend.

Umgesetzt (2026-08-25, Strukturnavigation): „nächste Überschrift“, „vorheriger
Link“, „nächste Liste“, „nächste Landmarke“ (deutsch/englisch, je Richtung)
springen zwischen Strukturelementen des aktiven Fensters — Orca-ähnlich, aber
ehrlich auf das begrenzt, was AT-SPI wirklich liefert. Der Adapter wandert den
Baum ab fokussiertem Fenster, matcht Überschriften/Links/Listen über die
AT-SPI-Rollen (heading/link/list) und Landmarken über das Objekt-Attribut
`xml-roles` (main/navigation/banner …), das nur der Browser füllt — GTK
exponiert keine ARIA-Rollen, also verweigert Clausis Landmarken dort ehrlich.
Ein Treffer wird fokussiert (nie aktiviert — ein Link-Landing klickt nie) und
kurz angesagt (Rolle + Name). Nichts gefunden ist eine ehrliche Ansage („Keine
weiteren Überschriften in diesem Fenster“), Position bleibt, kein simulierter
Sprung, kein Wrap-Around. Keine Zähler in V1 („drei Überschriften weiter“
bleibt offen; das count-Muster der mehrstufigen Navigation kann folgen).
Grenzen, bewusst offen: GTK liefert keine Heading-/Link-Rollen — Überschriften
und Links gibt es erst mit Browser/Editor, die Landmarken-Suche ist auf dem
echten Bus noch nicht gegen einen Browser verifiziert (Fake-Baum-Tests decken
das Matching ab), Tabellen und Web sind eigene Blöcke (unten).

Es fehlt:

- **Strukturnavigation in der Praxis**: das Rollen-Matching steht, aber erst
  Firefox/Chromium machen Überschriften, Links und Landmarken auf dem echten
  Bus nutzbar — die Browser-Profile sind der nächste Block (siehe Webinhalte).
- **Tabellen**: Zeile/Spalte wechseln, Kopfzeilen mitsprechen, „Zelle B3“,
  „lies die Spalte vor“.
- **Webinhalte**: Der Browser ist die wichtigste Anwendung überhaupt. Firefox
  und Chromium liefern AT-SPI, aber Webseiten brauchen ein eigenes Modell
  (Formulare, ARIA-Rollen, Live-Regionen, Cookie-Banner, Einwilligungsdialoge).
- **Dokumente**: PDF, Office-Dateien, E-Mail-HTML.
- **Terminalausgabe vorlesen** — siehe nächster Punkt.

## 3. Das Terminal — ein bewusst offener Zielkonflikt

Clausis **verweigert** Diktat und Einfügen in Terminals, weil dort eine Zeile
Text ein Befehl ist. Für die Sicherheit ist das richtig. Für einen blinden
Administrator oder Entwickler bedeutet es: das Terminal ist per Sprache gar
nicht bedienbar.

Nötig wäre ein getrennter, ausdrücklich eingeschalteter Terminalmodus mit:

- Vorlesen der Ausgabe (Scrollback, letzte Zeile, letzter Befehl mit Rückgabewert),
- einer Allowlist unkritischer Befehle ohne Bestätigung,
- Bestätigungspflicht für alles andere, mit vorgelesenem exakten Befehl,
- hartem Ausschluss von Passworteingaben,
- und einer Anzeige, dass der Modus aktiv ist.

Das ist Neuland und sicherheitskritisch. Es einfach freizuschalten wäre
fahrlässig; es dauerhaft zu verweigern schließt eine Berufsgruppe aus.

## 4. Anwendungsabdeckung

Heute: generische AT-SPI-Erkundung plus einige typisierte Aktionen. Es fehlen
geprüfte Profile für die Programme, die den Alltag ausmachen:

Browser, E-Mail, Dateiverwaltung, Texteditor/Office, Kalender, Kontakte,
Medienwiedergabe, Softwarecenter, PDF-Betrachter, Bildbetrachter,
Archivmanager, Einstellungen, Terminal.

Dazu fehlt das Fundament dafür:

- ein **versioniertes Voice-Action-Profil** pro Anwendung,
- ein **Plug-in-Format** mit Signatur, Manifest, Herkunft, Berechtigungen und
  automatischer Injektionsprüfung,
- und die Regel, dass eine KI ein Profil **nicht autonom erzeugen und sofort
  aktivieren** darf.

## 5. Menüs, Popovers und Fokus-Randfälle

- **Menüleisten und Kontextmenüs** (das Sprach-Äquivalent zum Rechtsklick).
- **Popovers und Aufklapplisten** in GNOME — über AT-SPI schwer greifbar.
- **Verschachtelte modale Dialoge**, Assistenten mit Vor/Zurück.
- **Flüchtige Meldungen** (Toasts), die vorbei sind, bevor jemand reagiert:
  sie brauchen einen Verlauf, den man abrufen kann.
- **Ziehen und Ablegen** braucht ein sprachliches Äquivalent („verschiebe
  Nummer 3 nach Nummer 7").
- **Mehrere Bildschirme**, Fenster außerhalb des sichtbaren Bereichs.

## 6. Qualität der Sprachausgabe

espeak-ng ist verständlich, aber über Stunden anstrengend. Es fehlt:

Teilweise umgesetzt (2026-08-24): Geschwindigkeit (schneller/langsamer/normal)
und Synthesesprache (deutsch/englisch) als feste Sprachbefehle über
speech-dispatcher — bewusst als feste Argumentevektoren ohne freie Werte.

Es fehlt weiterhin:

- eine **bessere Offline-Stimme** (etwa Piper) mit geklärter Lizenz,
- **Geschwindigkeit, Stimme, Tonhöhe und Sprache per Sprachbefehl** änderbar,
- **Ausführlichkeitsstufen** (Anfänger/Fortgeschritten) und einstellbare
  Satzzeichen-Ausführlichkeit,
- **Sprachwechsel mitten im Text** (deutsches Dokument mit englischen Zitaten),
- **Aussprachewörterbuch** für Namen, Abkürzungen, Fachbegriffe.

## 7. Qualität der Spracherkennung

Faster-Whisper *base* ist für Diktat und für Eigennamen zu schwach. Es fehlt:

- **Vokabular-Biasing** auf installierte Programme, Kontakte, Dateinamen,
- ein **größeres Modell** dort, wo die Hardware es trägt, mit ehrlicher
  Abwägung zwischen Genauigkeit und Latenz,
- **Robustheit gegen Akzente, Dialekte und Sprechbehinderungen** — Dysarthrie
  ist selbst eine Behinderung, und ein Barrierefreiheitswerkzeug, das nur
  Standardaussprache versteht, schließt Menschen aus,
- **Störgeräusche, Fernseher, mehrere Sprechende im Raum**,
- **Sprecherverifikation**, falls sie kommen soll — mit biometrischer DPIA.

## 8. Authentifizierung — der harte Zielkonflikt

Clausis verweigert bewusst: Diktat in Passwortfelder, Bestätigen von
Berechtigungsabfragen, Sprachentsperrung der Festplatte. Jede dieser
Verweigerungen ist einzeln richtig. Zusammen bedeuten sie: **genau an den
Stellen, an denen es zählt, wird der blinde Mensch auf die Tastatur
zurückverwiesen.**

Das ist heute die ehrlichste Lösung, aber keine gute. Nötig wäre:

- **FIDO2-Hardwaretoken** als primärer Anmelde- und Bestätigungsweg — ein
  Tastendruck auf einem Stick ist blind bedienbar und nicht durch Raumsprache
  auslösbar,
- **TPM plus PIN** für die Festplattenentsperrung,
- **Passwortmanager-Integration**, bei der Clausis nie das Geheimnis sieht,
- ein **geschütztes Bestätigungsportal** außerhalb des Desktop-Audiographen,
- **Wiederherstellungscodes**, die vorgelesen und geprüft werden können.

## 9. Boot, Anmeldung, Installation, Rettung

Umgesetzt: Ansage bei der Festplattenentsperrung aus dem Initramfs, sprechender
Anmeldebildschirm über Orca, Recovery-Wege für Ausfälle im laufenden System.

Es fehlt:

- **GRUB/Bootmenü** ist stumm — bei einem Startproblem steht ein blinder Mensch
  vor einem schweigenden Rechner.
- **Notfall-Shell und Rettungsmodus** ohne Sprache.
- **Sprachnative Partitionierung**: Datenträgerauswahl geht, die Aufteilung
  selbst nicht.
- **Verifikationstest des Recovery-Keys** vor Installationsende.
- **WLAN-Einrichtung**: das Passwort ist ein Passwortfeld — siehe Punkt 8.
- **Firmware/BIOS** liegt vollständig außerhalb.

## 10. Oberflächen außerhalb von GNOME

- **Electron-Anwendungen** (VS Code, Slack, Signal) mit wechselhafter
  AT-SPI-Qualität.
- **Flatpak/Snap** in Sandkästen, die den Accessibility-Bus nicht durchreichen.
- **X11-only-Programme** unter Wayland.
- **Anwendungen ganz ohne Barrierefreiheitsschnittstelle** — dort hilft nur
  Druck auf die Hersteller oder ein gekennzeichneter Best-Effort-Weg.

## 11. Interaktionsmodell und Fehlerkorrektur

- **Rückfrage bei Mehrdeutigkeit** („Meinten Sie Firefox oder Files?").
- **Rücknahme einer Sprachaktion** („das war falsch, mach es rückgängig") —
  für *Diktat* ist der erste Schritt umgesetzt („nein, ich meinte …" ersetzt
  das letzte Diktat im selben Feld, siehe § 1 Korrektur-Slot); die Rücknahme
  einer beliebigen *Aktion* über den Dialog hinweg bleibt offen.
- **Verlauf**: „was habe ich zuletzt gemacht?"
- **Kontextgedächtnis** über mehrere Sätze („öffne sie", „schließe das wieder").
- **Barge-in** ist architektonisch da, aber ungemessen; die Wake-Word-
  Fehlauslöserate ist unbekannt.
- **Hilfe im Kontext**: „was kann ich hier sagen?" existiert für Bedienelemente,
  nicht für den ganzen Befehlsvorrat.

## 12. Prüfung mit blinden Menschen — die eigentliche Lücke

Alles oben ist Technik. Das hier ist wichtiger:

**An Clausis hat bisher kein blinder Mensch mitgearbeitet und keiner hat es
getestet.** Ein Barrierefreiheitssystem, das ausschließlich von Sehenden
entworfen, geschrieben und bewertet wurde, ist eine Vermutung darüber, was
gebraucht wird — auch die Priorisierung in diesem Dokument.

Das Projekt geht den Weg über die Community: erst etwas Benutzbares, dann
Rückmeldung von denen, die es betrifft. Das ist ein tragfähiger Weg, aber er
steht und fällt mit zwei Dingen:

- **Ein Kanal, der ankommt.** Kontakt läuft über das Projekt-Repository:
  sicherheitsrelevante Funde über GitHub Private Vulnerability Reporting
  (siehe `SECURITY.md`), Barrierefreiheits-Rückmeldung über die Vorlagen.
  Siehe [`TESTING_FOR_BLIND_USERS.md`](TESTING_FOR_BLIND_USERS.md) und die
  Fehlerberichtsvorlagen.
- **Eine Kennzeichnung, die nicht mehr verspricht als geprüft ist.** Wer das
  Abbild herunterlädt, muss vor dem Installieren wissen, dass noch niemand aus
  der Zielgruppe es benutzt hat. Ein sehender Tester kann eine Fehlbedienung
  am Bildschirm auffangen; genau das kann die Zielgruppe nicht.

Sobald sich Rückmeldung einstellt, gilt weiterhin:

- Aufgabenbenchmark aus Abschnitt 0 mit Abschlussquote und Zeitbedarf,
- Vergleich gegen den heutigen Stand der Technik (Orca plus Tastatur) —
  Clausis muss **besser** sein als das, nicht nur anders,
- Entlohnung, sobald das Projekt Mittel hat; unbezahltes Testen durch
  Betroffene ist auf Dauer kein Beteiligungsmodell,
- am besten eine blinde Person mit Entscheidungsbefugnis im Projekt.

## 13. Rechtliches und Normatives

- **EN 301 549** und **BITV 2.0** als Prüfmaßstab für Desktop-Software.
- **European Accessibility Act**, falls Clausis je vertrieben wird.
- **Biometrische DPIA**, sobald Sprecherverifikation kommt.
- **Lizenzen** für Stimme, Wake-Word-Modell und STT-Modell.
- **Cloud-Datenflüsse**: GPT Live sendet Raumaudio; das ist bei einem Werkzeug,
  das eine Behinderung ausgleicht, besonders heikel, weil der Verzicht darauf
  nicht wirklich freiwillig ist, wenn die Offline-Variante schlechter arbeitet.

---

## Empfohlene Reihenfolge

**Projektentscheidung (Hendrik, 2026-08-08): erst bauen, dann testen.** Eine
Beteiligung blinder Menschen lässt sich nicht organisieren, bevor es etwas zum
Ausprobieren gibt; Rückmeldung kommt über die Community, wenn sich eine bildet.
Diese Reihenfolge folgt dieser Entscheidung. Was sie voraussetzt, steht in
Abschnitt 12: ein funktionierender Rückmeldekanal und eine Kennzeichnung, die
niemanden in die Irre führt, solange nichts geprüft ist.

1. **Rückmeldung möglich machen.** Testprotokoll
   ([`TESTING_FOR_BLIND_USERS.md`](TESTING_FOR_BLIND_USERS.md)),
   Fehlerberichtsvorlagen und der sprachbedienbare Diagnosebericht
   (`clausis-report`, oder gesprochen „Fehlerbericht") sind umgesetzt. **Der
   Kontakt läuft jetzt über GitHub**: `security.txt` und `SECURITY.md` zeigen
   auf Private Vulnerability Reporting im Projekt-Repository;
   Barrierefreiheits-Rückmeldung läuft über die Fehlerberichte im Repository.
2. **Textbearbeitung und Vorlesen mit Granularität** (Abschnitte 1 und 2) —
   ohne das ist der Rechner kein Arbeitsgerät.
3. **Bessere Stimme und bessere Erkennung** (6 und 7) — sie begrenzen alles
   andere.
4. **FIDO2 und geschütztes Bestätigungsportal** (8) — sie lösen den
   Zielkonflikt, statt ihn zu verwalten.
5. **Browser- und Anwendungsprofile** (4), beginnend mit dem Browser.
6. **Terminalmodus** (3) mit eigenem Sicherheitskonzept.
7. **Boot- und Rettungswege** (9).
8. **Hardwarematrix, Latenzmessung, Nutzerstudien** und erst danach jede
   Aussage über Vollständigkeit.

## Wann Clausis „vollständig sprachbedienbar" sagen darf

Wenn die Aufgabenliste aus Abschnitt 0 von mindestens fünf blinden Personen auf
mindestens drei Hardwareprofilen ohne fremde Hilfe abgeschlossen wird, die
Ergebnisse veröffentlicht sind, und Tastatur plus Orca dabei durchgehend als
gleichwertiger Weg funktioniert haben.

Vorher lautet die ehrliche Beschreibung: **ein sprachgesteuerter Aufsatz auf
einem barrierefreien Debian — nützlich, aber kein Ersatz für Screenreader und
Tastatur.**
