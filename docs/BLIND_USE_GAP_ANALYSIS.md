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

Es fehlt:

- **Cursor-Navigation**: „an den Anfang", „drei Wörter zurück", „ans Zeilenende",
  „nächster Absatz", „Zeile 12".
- **Auswahl und Ersetzen**: „markiere den Satz", „ersetze *Meier* durch *Maier*",
  „lösche die Auswahl", „alles markieren".
- **Satzzeichen und Formatierung beim Diktat**: „Komma", „Punkt", „Fragezeichen",
  „neue Zeile", „neuer Absatz", „Anführungszeichen auf/zu", „groß schreiben".
  Ohne das entsteht nur ein Textblock ohne Interpunktion.
- **Buchstabiermodus**: „A wie Anton, N wie Nordpol" — unverzichtbar für Namen,
  Passwörter (soweit erlaubt), Dateinamen, Kennungen.
- **Diktiermodi**: Zahlen, Datum, Uhrzeit, E-Mail-Adresse, URL, Dateipfad
  brauchen je eigene Umsetzung; „punkt de" muss zu `.de` werden, nicht zu
  „ punkt de".
- **Rückgängig/Wiederholen** als Sprachbefehl, mit Ansage, was rückgängig wurde.
- **Vorlesen mit Granularität**: Zeichen, Wort, Zeile, Satz, Absatz, ganzes
  Dokument — mit Positionsmerker, Pause und Fortsetzen an derselben Stelle.
- **Korrektur-Slots über den Dialog hinweg**: „nein, ich meinte …" muss die
  letzte Äußerung ersetzen, nicht eine neue anhängen.

Ohne diesen Block ist jede Textarbeit jenseits eines Einzeilers unmöglich.

## 2. Lesen und strukturelle Navigation

Orientierung heißt heute: aktives Fenster, Fokus, bis zu 30 nummerierte Ziele.
Für Inhalte reicht das nicht.

Es fehlt:

- **Durchgehendes Vorlesen** („Say-All") mit Positionsverfolgung, Unterbrechen
  und Fortsetzen.
- **Strukturnavigation**: von Überschrift zu Überschrift, Liste zu Liste,
  Landmarke zu Landmarke, Link zu Link. Orca kann das; Clausis kennt es nicht.
- **Tabellen**: Zeile/Spalte wechseln, Kopfzeilen mitsprechen, „Zelle B3",
  „lies die Spalte vor".
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
- **Rücknahme einer Sprachaktion** („das war falsch, mach es rückgängig").
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
