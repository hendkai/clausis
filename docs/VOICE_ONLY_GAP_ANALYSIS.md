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
Die vier Laufzeitdateien des gepinnten Faster-Whisper-Modells besitzen feste
SHA-256-Werte. Ein lokaler Offline-Buildcache wird nur nach vollständiger
Manifestprüfung übernommen; Image-Hook und finaler ISO-Verifier prüfen dieselben
Hashes erneut, sodass ein fehlendes oder verändertes Modell den Build stoppt.
Noch fehlen ein dediziertes Wake-Word-Modell mit niedriger Dauerlast,
Echounterdrückung, ein lokal garantierter Unterbrechungsdetektor für echtes
Barge-in sowie eindeutige nichtsprachliche Hörsignale. Bis diese Kette auf
zertifizierter Hardware geprüft ist, verspricht Clausis kein Vollduplex.

### 2. Semantische GNOME-Steuerung

Der erste `Clausis GNOME Adapter` liest AT-SPI begrenzt und ohne
Bildschirmkoordinaten. Aktives Fenster, Fokus und bis zu 30 semantische Ziele
können vorgelesen werden; Fensterwechsel, Zurück und bestätigte nummerierte
Aktivierung sind typisierte Aktionen. Minimieren, Maximieren, Wiederherstellen
und bestätigtes Schließen werden nur dann ausgeführt, wenn das aktive AT-SPI-
Fenster die exakte semantische Aktion anbietet; es gibt keinen simulierten
Wayland-Eingabe-Fallback. Übersicht, Anwendungsraster, Schnelleinstellungen und
Benachrichtigungen werden ebenso nur über exakt benannte Bedienelemente der
zugänglichen Anwendung `GNOME Shell` ausgelöst. Innerhalb des aktiven Fensters
kann der Fokus semantisch zwischen sichtbaren ausführbaren Elementen wechseln.
Ein erneut gelesener, exakt eindeutiger Name kann bestätigungspflichtig
aktiviert werden; Mehrdeutigkeit bricht geschlossen ab. Direkt vor jeder
nummerierten, benannten oder Berechtigungs-Aktivierung liest Clausis die
Aktionsnamen am bereits gebundenen Knoten erneut. Ausschließlich Click, Press,
Activate, Toggle oder Open werden ausgeführt; ein veralteter Index oder eine
allein vorhandene fachfremde Aktion wie Delete bricht ohne Aufruf geschlossen
ab. Eine nummerierte Aktivierung bindet unmittelbar vor der Mutation außerdem
das identische aktive Fenster und die vollständige geordnete Identitätsliste
aller bedienbaren Controls erneut. Hinzugefügte, entfernte oder umsortierte
Ziele machen die zuvor gesprochene Nummer ungültig, statt sie still auf ein
anderes Bedienelement umzulenken. Die Zurück-Navigation verlangt zusätzlich
genau eine passende Aktion im
gesamten gebundenen Fenster und bindet sie vor dem Aufruf erneut. Auch
Fensteraktions-Aliase und GNOME-Shell-Ziele müssen jeweils global eindeutig
sein; doppelte lokalisierte Aktionen oder Bedienelemente bleiben unangetastet.
„Lies die Benachrichtigungen vor“ ist ein davon getrennter bestätigter
Lesezugriff. Er übernimmt ausschließlich aktuell sichtbare AT-SPI-Knoten mit
der exakten Rolle `notification` aus genau einer zugänglichen GNOME-Shell-
Anwendung. Kalenderbeschriftungen, editierbare Controls und geschützte
Nachfahren werden ignoriert. Mehr als 20 Benachrichtigungen, 40 eindeutige
Textteile oder 2.000 Zeichen brechen geschlossen ab; die vollständige
Sprachausgabe wird aus dem signierten Audit entfernt.
Jede sichtbare Benachrichtigung behält dabei eine Nummer, auch wenn ihr Inhalt
vollständig geschützt ist. „Verwirf Benachrichtigung Nummer …“ ist ein
getrennter bestätigter Hochrisikobefehl ohne Titel im Request. Unmittelbar vor
der Mutation müssen dieselbe GNOME-Shell-Objektidentität und die vollständige
geordnete Liste aller sichtbaren Benachrichtigungsobjekte identisch bleiben;
das Ziel muss genau eine semantische Dismiss- oder Close-Aktion anbieten.
Nach dem Aufruf liest Clausis bis zu zwei Sekunden lang erneut. Erfolg wird nur
gemeldet, wenn dieselbe Shell exakt die ursprüngliche Reihenfolge ohne das eine
gewählte Objekt zeigt. Eine unveränderte Liste oder jede andere Entfernung,
Hinzufügung beziehungsweise Umsortierung bleibt ein ausdrücklicher Fehler mit
nicht bestätigtem Nachzustand.
Eine Berechtigungsentscheidung erkennt das exakte Erlauben-/Ablehnen-Paar
unmittelbar vor der Mutation ein zweites Mal im identischen aktiven Dialog.
Beide Controls müssen ihre ursprüngliche AT-SPI-Identität behalten und weiterhin
die einzige erkannte Entscheidungsgruppe bilden; ein ausgetauschter Dialog oder
gleich benanntes Ersatzpaar löst keine Seite aus.
Zusätzlich müssen dieselbe Anwendung und ihre vollständige geordnete Top-Level-
Fensterliste unmittelbar vor der Mutation identisch bleiben. Nach dem Aufruf
liest Clausis bis zu zwei Sekunden erneut. Erfolg wird nur gemeldet, wenn exakt
die ursprüngliche Fensterreihenfolge ohne den Berechtigungsdialog verbleibt;
ein unveränderter, fremd veränderter oder nicht lesbarer Nachzustand bleibt ein
ausdrücklicher Fehler ohne Rollbackbehauptung.
Auch die Menüeintragsaktivierung bindet unmittelbar vor `doAction()` das
identische aktive Fenster, den fokussierten semantischen Menücontainer und das
exakte direkte Ziel erneut. Ein geschlossenes oder gewechseltes Menü sowie ein
gleich benannter Ersatzeintrag lösen keine Aktion aus.
Alle an ein aktives Fenster gebundenen Zustandsabfragen und Mutationen verlangen
genau ein AT-SPI-Active-Frame, -Dialog oder -Window. Ein nur sichtbares Fenster
wird niemals als Arbeitsziel verwendet. Ausschließlich die nicht mutierende
Orientierung darf auf Showing zurückfallen, und auch dann nur bei genau einem
sichtbaren Fenster; mehrere aktive oder sichtbare Kandidaten brechen
geschlossen ab.
Noch ergänzt werden müssen:

Ein sichtbares und fokussierbares AT-SPI-Element kann auch ohne ausführbare
Aktion über seinen exakten eindeutigen Namen fokussiert werden. Clausis nutzt
Component `grabFocus()` ohne Tastensimulation, prüft den Focused-Nachzustand und
verlangt vor der Mutation genau einen fokussierten Ausgangsknoten. Die komplette
Fokusbitmap des gebundenen Fensters muss anschließend exakt das Ziel enthalten.
Ablehnung, Abweichung oder eine Ausnahme nach teilweiser Fokusverschiebung stellt
den vorherigen Knoten wieder her und prüft erneut die vollständige Bitmap; ein
Rollbackfehler wird getrennt gemeldet. Bereits fokussierte Ziele bleiben ohne
Mutation erfolgreich.

Das fokussierte editierbare Textfeld kann nach Bestätigung semantisch ersetzt
oder geleert werden. Der Inhalt wird in Bestätigung und Ergebnis nicht
wiederholt, der Nachzustand wird exakt gelesen und bei Abweichung auf den
vorherigen Wert zurückgesetzt. Passwort-, geschützte, geheime oder nicht
zuverlässig klassifizierbare Felder werden abgelehnt.

Der Inhalt eines fokussierten AT-SPI-Textfelds kann ohne Bestätigung bis zu
1.000 Zeichen vorgelesen werden. Nur Entry-, Text- und Document-Text-Rollen mit
prüfbaren Schutzattributen sind zugelassen; Passwort-, geschützte, geheime und
nicht prüfbare Felder brechen vor dem Lesen geschlossen ab. Der gelesene Inhalt
wird nicht in das manipulationsgeschützte Aktionsprotokoll geschrieben.

Eine exakt und eindeutig benannte AT-SPI-Fortschrittsanzeige im aktiven Fenster
kann ohne Bestätigung als Prozentwert vorgelesen werden. Clausis akzeptiert nur
die Rolle Progress Bar mit endlichem, geordnetem Wertebereich und einem darin
liegenden aktuellen Wert. Die Value-Schnittstelle wird dabei ausschließlich
gelesen und niemals verändert.

Im nächsten fokussierten AT-SPI-`Selection`-Container kann ein direkter
Listeneintrag nach exaktem, eindeutigem Namen bestätigt ausgewählt werden.
Clausis ersetzt und prüft die vollständige Auswahl; bei Ablehnung oder
Abweichung wird die vorherige Auswahl geprüft wiederhergestellt. Andere Listen
im Fenster werden nicht durchsucht.

Ein aktiver Datei-Auswahldialog wird über seine AT-SPI-Rolle oder einen exakten
bekannten Öffnen-/Speichern-/Auswählen-Titel sowie getrennte semantische
Bestätigen- und Abbrechen-Aktionen erkannt. Darin kann genau ein sichtbarer
Datei- oder Ordnername in genau einem Auswahlcontainer markiert werden. Diese
Aktion bestätigt den Dialog ausdrücklich nicht; Öffnen, Speichern oder
Auswählen bleibt ein eigener bestätigungspflichtiger Schritt. Zwei getrennte
Befehle können den erkannten Dateidialog anschließend bestätigen oder
abbrechen. Clausis verlangt dafür genau ein bekanntes
Öffnen-/Speichern-/Auswählen-/Choose- und Abbrechen-Paar, bindet dieselbe
Anwendung, ihre vollständige geordnete Top-Level-Fensterliste, das aktive
Fenster und beide konkreten Controls unmittelbar vor der Mutation erneut und
bricht bei Fenster-, Paar- oder Objektwechsel ohne Aktion ab. Nach der Aktion
gilt nur exakt diese Reihenfolge ohne den ausgewählten Dateidialog innerhalb
von zwei Sekunden als Erfolg; ein unveränderter Dialog, eine fremde Mutation
oder ein unlesbarer Zustand wird ausdrücklich als nicht bestätigter
Nachzustand gemeldet.

In einem erkannten Speichern-Dialog kann ein einzelner Dateiname nur in das
fokussierte, exakt als Name, File Name, Filename oder Dateiname bezeichnete
editierbare Feld geschrieben werden. Prüfung und Schreibvorgang bleiben an
dasselbe AT-SPI-Objekt gebunden; Readback und Rollback entsprechen der sicheren
Texteingabe. Der Speichern-Knopf wird dabei nicht ausgelöst.

In einem erkannten Dateidialog kann ein absoluter kanonischer POSIX-Pfad nur in
das fokussierte, exakt als Location, Path, Ort oder Pfad bezeichnete editierbare
Feld geschrieben werden. Relative Pfade, doppelte Trenner und `.`-/`..`-
Komponenten werden abgelehnt. Prüfung, Readback und Rollback bleiben an dasselbe
AT-SPI-Objekt gebunden. Die Aktion simuliert weder Enter noch löst sie Öffnen,
Speichern, Auswählen oder Choose aus; Navigation und Dialogabschluss bleiben
getrennte bestätigungspflichtige Schritte.

Ein exakt und eindeutig benannter sichtbarer Ordner kann innerhalb des
gebundenen Dateidialogs geöffnet werden, wenn der direkte Eintrag eines
AT-SPI-`Selection`-Containers durch Rolle, exaktes Attribut oder lokalisiertes
Ordnersymbol ausdrücklich als Ordner erkennbar ist und selbst eine exakte
Open-/Activate-Aktion anbietet. Dateiähnliche, doppelte, unklassifizierbare oder
nur klickbare Ziele werden abgelehnt. Clausis betätigt für diese Navigation
nicht den Bestätigen-Knopf des Dateidialogs.

Im nächsten fokussierten AT-SPI-Baum oder einer Baumtabelle kann ein exakt und
eindeutig benanntes Baum-Element beziehungsweise eine Zeile bestätigt auf- oder
zugeklappt werden. Clausis verlangt eine exakte Expand-/Collapse-Aktion, prüft
den Expandable-/Expanded-Vorzustand und liest den Expanded-Nachzustand zurück.
Ablehnung, Abweichung oder eine Ausnahme nach Teiländerung verwendet die exakte
Gegenaktion, um den alten Zustand wiederherzustellen und zu prüfen; ein
Rollbackfehler wird getrennt gemeldet. Normale Listen, doppelte Namen und
generische Click-/Toggle-Aktionen brechen geschlossen ab.

Im nächsten fokussierten AT-SPI-Menü oder in der Menüleiste kann ein direkter
Menu Item-, Check Menu Item- oder Radio Menu Item-Eintrag über seinen exakten
eindeutigen Namen bestätigt ausgelöst werden, wenn er genau eine Activate-,
Click- oder Press-Aktion anbietet. Gewöhnliche Listen, andere Menüs im Fenster,
falsche Rollen, doppelte Namen und mehrdeutige Aktionen brechen geschlossen ab.

In der nächsten fokussierten AT-SPI-Tabelle oder Baumtabelle mit Selection-
Schnittstelle kann eine direkte Zeile über ihren exakten Zeilennamen oder einen
exakten Zellnamen ausgewählt werden. Der Wert muss genau eine Zeile bestimmen;
Wiederholungen in mehreren Zeilen brechen geschlossen ab. Clausis ersetzt und
prüft die vollständige direkte Auswahlbitmap und stellt sie bei Ablehnung oder
Abweichung wieder her. Eine gewöhnliche Liste gilt nicht als Tabelle.

In der nächsten fokussierten AT-SPI-Registerkartenliste mit Selection-
Schnittstelle kann eine direkte Registerkarte über ihren exakten, eindeutigen
Namen ausgewählt werden. Clausis ersetzt und prüft die vollständige direkte
Auswahlbitmap und stellt sie bei Ablehnung oder Abweichung wieder her. Doppelte
Namen und gewöhnliche Listen brechen geschlossen ab.

Ein exakt und eindeutig benannter AT-SPI-Schieberegler im einmal gebundenen
aktiven Fenster kann auf einen bestätigten ganzzahligen Prozentwert von 0 bis
100 gesetzt werden. Clausis bildet den Prozentwert auf Minimum, Maximum und die
gemeldete Schrittweite ab, liest den Nachzustand zurück und stellt bei Ablehnung
oder Abweichung sowie bei einer Ausnahme nach Teilmutation den vorherigen Wert
wieder her und prüft ihn numerisch. Eine nicht bestätigte Rücksetzung wird
getrennt gemeldet. Andere Rollen und ungültige Wertebereiche brechen geschlossen
ab.

Ein exakt und eindeutig benanntes AT-SPI-Kontrollkästchen kann bestätigt ein-
oder ausgeschaltet werden, wenn es genau eine Toggle-Aktion und einen prüfbaren
Checked-Zustand anbietet. Ein Optionsfeld kann über genau eine Select- oder
Click-Aktion ausgewählt werden. Ablehnung, Abweichung oder eine Ausnahme nach
teilweiser Kontrollkästchen-Umschaltung stellt den alten Zustand wieder her und
prüft ihn; ein Rollbackfehler wird getrennt gemeldet. Clausis liest den
Checked-Nachzustand zurück und versucht bei einer fehlgeschlagenen Optionsfeldauswahl, das zuvor ausgewählte
Feld im gebundenen Fenster wiederherzustellen. Mehrfach markierte
Ausgangsgruppen werden abgelehnt; nach der Aktion wird die vollständige
Checked-Bitmap geprüft. Ablehnung, Abweichung oder eine Ausnahme nach
Teilselektion stellt die vorige eindeutige Auswahl wieder her und prüft sie.
Doppelte Namen, falsche Rollen, mehrdeutige Aktionen und Rollbackfehler brechen
geschlossen ab.

In einem exakt und eindeutig benannten AT-SPI-Kombinationsfeld mit Selection-
Schnittstelle kann ein direkter Eintrag mit der Rolle Menu Item, List Item oder
Option über seinen exakten eindeutigen Namen ausgewählt werden. Clausis ersetzt
und prüft die vollständige direkte Auswahlbitmap und stellt sie bei Ablehnung
oder Abweichung wieder her. Gewöhnliche Listen, verschachtelte Vermutungen,
doppelte Namen und andere Kindrollen brechen geschlossen ab.

Ein exakt und eindeutig benanntes AT-SPI-Zahlenfeld mit der Rolle Spin Button
kann auf einen bestätigten endlichen Zahlenwert innerhalb seines gemeldeten
Minimums und Maximums gesetzt werden. Der verlangte Wert muss exakt zur
gemeldeten positiven Schrittweite passen; Clausis rundet ihn nicht stillschweigend.
Der Nachzustand wird zurückgelesen und bei Ablehnung oder Abweichung der vorige
Wert wiederhergestellt und numerisch geprüft; dasselbe gilt bei einer Ausnahme
nach Teilmutation. Eine nicht bestätigte Rücksetzung wird getrennt gemeldet.
Schieberegler, doppelte Namen und ungültige Wertebereiche brechen geschlossen ab.

Ein exakt und eindeutig benannter AT-SPI-Schalter mit der Rolle Switch kann
bestätigt ein- oder ausgeschaltet werden, wenn er genau eine Toggle-Aktion und
einen prüfbaren Checked-Zustand anbietet. Eine Ausnahme nach Teilumschaltung
stellt den alten Zustand wieder her und prüft ihn; ein Rollbackfehler bleibt
getrennt. Bereits erfüllte Zustände lösen keine Aktion aus. Kontrollkästchen,
doppelte Namen, mehrdeutige Aktionen und ein
unveränderter Nachzustand brechen geschlossen ab.

Ein aktiver Berechtigungsdialog kann mit den ausdrücklichen Befehlen
„Berechtigung erlauben“ oder „Berechtigung ablehnen“ bedient werden. Clausis
akzeptiert nur Dialog-/Alert-Rollen mit genau einem vollständigen, bekannten
Erlauben-/Ablehnen-, Zugriff-gewähren-/verweigern- oder Freigeben-/Nicht-
freigeben-Paar. Anwendung, vollständige Fensterliste, Dialog und Paar werden
unmittelbar vor der Aktion erneut gebunden und der exakte Nachzustand wird
begrenzt geprüft. OK-/Abbrechen-Dialoge, normale Fenster, fehlende,
doppelte oder mehrere Entscheidungsgruppen brechen geschlossen ab; beide Wege
bleiben bestätigungspflichtig.

Getrennte, ebenfalls bestätigungspflichtige Standarddialog-Kommandos können
genau ein konventionelles OK-/Abbrechen-, Ja-/Nein-,
Bestätigen-/Abbrechen-, Wiederholen-/Abbrechen- oder
Anwenden-/Abbrechen-Paar bedienen. Wiederholen und Anwenden sind eigenständige
Intents und werden niemals gegeneinander oder gegen Bestätigen ausgetauscht.
Dateiauswahldialoge und Berechtigungspaare sind ausdrücklich ausgeschlossen.
Unmittelbar vor der Aktion bindet Clausis dieselbe Anwendung, ihre vollständige
geordnete Top-Level-Fensterliste, das aktive Dialogfenster, das vollständige
Paar und die beiden konkreten Bedienelemente erneut; Austausch, Mehrdeutigkeit
oder ein geändertes Paar brechen ohne Aktivierung geschlossen ab. Nach der
Aktion gilt nur die ursprüngliche Fensterreihenfolge ohne genau diesen Dialog
innerhalb von zwei Sekunden als Erfolg. Ein unveränderter, unlesbarer oder
fremd veränderter Nachzustand wird ausdrücklich als unbestätigt gemeldet.
Beide Richtungen sind als nicht reversible Hochrisikoaktionen eingestuft und
beanspruchen nach einer ausgelösten Aktion keinen Rollback.

„Lies den Dialog vor“ ist davon getrennt und liest nach Bestätigung nur
eindeutige statische AT-SPI-Beschriftungen, Absätze und Beschreibungen eines
aktiven regulären Dialogs. Editierbare Textfelder werden niemals abgefragt,
Dateiauswahldialoge und geschützte Knoten sind ausgeschlossen. Maximal 20
Einträge und insgesamt 1.000 Zeichen werden gesprochen; Überschreitungen
brechen statt einer unvollständigen Teilausgabe geschlossen ab. Der gesamte
gesprochene Inhalt wird aus dem signierten Audit entfernt.

„Schließe den Dialog“ ist zusätzlich von „Fenster schließen“ getrennt. Der
bestätigte Hochrisikobefehl akzeptiert nur einen aktiven regulären Dialog,
dessen gesamte ausführbare Kontrollmenge aus genau einem semantischen
Close-/Schließen-/Dismiss-Bedienelement besteht. Dateiauswahl, vollständige
Entscheidungspaare, jeder zusätzliche Aktionsknopf und mehrdeutige Aktionen
werden abgelehnt. Dialog und konkrete Kontrolle werden unmittelbar vor der
nicht reversiblen Aktivierung erneut an ihre Objektidentität gebunden.
Auch die vollständige geordnete Top-Level-Fensterliste derselben Anwendung muss
unmittelbar vor der Mutation identisch bleiben.
Nach dem Aufruf liest Clausis bis zu zwei Sekunden lang die Top-Level-Fenster
derselben gebundenen Anwendung erneut. Erfolg wird nur gemeldet, wenn exakt die
ursprüngliche Reihenfolge ohne den geschlossenen Dialog verbleibt. Ein
unveränderter, fremd veränderter oder nicht lesbarer Nachzustand bleibt ein
ausdrücklicher Fehler; wegen der nicht reversiblen Aktion wird kein Rollback
behauptet.

Das aktive Fenster kann nach vertrauenswürdiger Bestätigung auf die vorherige
beziehungsweise linke oder nächste beziehungsweise rechte Arbeitsfläche
verschoben werden, wenn das einmal gebundene AT-SPI-Fenster genau diese
gerichtete Aktion anbietet. Generische Move-Aktionen, Tastenkürzel und
Wayland-Eingabesimulation werden nicht als Ersatz verwendet.

Die integrierte GNOME-Bildschirmtastatur, der Orca-Screenreader und die
Bildschirmvergrößerung können über drei getrennte, vertrauenswürdig bestätigte
Sprachbefehle eingeschaltet werden. Alle Aktionen verwenden vollständig feste
`gsettings`-Argumentvektoren und akzeptieren keine Ziele oder Zusatzargumente.
Ein bestÃ¤tigter parameterloser Sprachbefehl kann allein die VergrÃ¶ÃŸerung mit
dem festen Wert `screen-magnifier-enabled false` wieder ausschalten. Sein
kanonischer Text nennt ausdrÃ¼cklich, dass Orca und Bildschirmtastatur
eingeschaltet bleiben. Sprachbefehle zum Abschalten dieser beiden verbleibenden
Rettungswege sind absichtlich nicht vorhanden.

Ein getrennter bestätigter Recovery-Befehl startet Orca mit ausdrücklich
aktivierter Sprachausgabe neu. Der paketierte Sitzungsadapter akzeptiert nur
den Literalmodus `restart`, trennt exakt `orca --replace --enable speech` als
Langläufer ab und erkennt einen sofortigen Startabbruch. Beliebige Orca-Optionen
oder ein Sprachbefehl zum Abschalten des Screenreaders werden nicht angeboten.

Der Vergrößerungsfaktor kann mit einem getrennten, vertrauenswürdig bestätigten
Befehl exakt auf einen ganzzahligen Wert von 100 bis 3.200 Prozent gesetzt
werden. Clausis akzeptiert ausschließlich dieses eine typisierte Prozentfeld
und wandelt es ohne Shell-Interpretation in den `mag-factor` des installierten
GNOME-Schemas um; der Bestätigungstext nennt den konkreten Wert.

Die Helligkeits- beziehungsweise Farbinvertierung der GNOME-Lupe kann mit zwei
getrennten bestätigten Befehlen ein- oder ausgeschaltet werden. Beide verwenden
vollständig feste boolesche `invert-lightness`-Vektoren und akzeptieren keine
Parameter. Das Ausschalten dieses visuellen Filters schaltet weder die Lupe
noch einen anderen Barrierefreiheits-Rettungsweg aus.

Die Farbsättigung der GNOME-Lupe kann bestätigt auf einen ganzzahligen Wert von
0 bis 100 Prozent gesetzt werden; 0 Prozent ergibt Graustufen. Clausis
akzeptiert nur dieses eine typisierte Feld und wandelt es ohne
Shell-Interpretation in den `color-saturation`-Wert von 0,00 bis 1,00 um.

Helligkeit und Kontrast der GNOME-Lupe können jeweils bestätigt auf einen
vorzeichenbehafteten ganzzahligen Wert von -75 bis +75 Prozent gesetzt werden;
das entspricht den installierten GNOME-Reglern. Ein fest paketierter lokaler
Adapter überträgt den kanonischen Bruchwert auf alle drei RGB-Kanäle. Scheitert
ein späterer Kanal, stellt er bereits geänderte Kanäle auf ihre zuvor gelesenen
Werte zurück. Freie Schlüssel, Modi oder Zahlenzeichenketten werden abgelehnt.

Der vergrößerte Bildbereich kann bestätigt auf Vollbild oder exakt die obere,
untere, linke beziehungsweise rechte Bildschirmhälfte gesetzt werden. Die
Sprachformen werden auf die fünf installierten `screen-position`-Enumwerte
abgebildet; Ziel, Zusatzfelder und beliebige Schemawerte werden abgelehnt.

Das Fadenkreuz der GNOME-Lupe kann mit zwei getrennten bestätigten Befehlen
ein- oder ausgeblendet werden. Beide Aktionen verwenden vollständig feste
boolesche `show-cross-hairs`-Vektoren und akzeptieren weder Ziele noch
Zusatzargumente. Das Ausblenden schaltet die Lupe selbst nicht aus.

Die Deckkraft des Lupen-Fadenkreuzes kann bestätigt auf einen ganzzahligen Wert
von 0 bis 100 Prozent gesetzt werden. Clausis akzeptiert ausschließlich dieses
eine typisierte Feld und wandelt es ohne Shell-Interpretation in den
`cross-hairs-opacity`-Wert von 0,00 bis 1,00 um.

Die Fadenkreuzlinien können mit getrennten bestätigten Befehlen in der Mitte um
den vergrößerten Zeiger ausgespart oder wieder durchgehend dargestellt werden.
Beide Aktionen verwenden feste boolesche `cross-hairs-clip`-Vektoren und
akzeptieren keine Parameter. Das Aufheben der Aussparung deaktiviert weder das
Fadenkreuz noch die Lupe.

Die Länge der Fadenkreuzlinien kann bestätigt auf einen ganzzahligen Wert von
20 bis 4.096 Pixel gesetzt werden. Diese Grenzen entsprechen dem installierten
`cross-hairs-length`-Schema. Clausis akzeptiert nur das typisierte Feld
`pixels`; Ziel, Zusatzfelder und andere Zahlentypen werden abgelehnt.

Die Dicke der Fadenkreuzlinien kann bestätigt auf einen ganzzahligen Wert von
1 bis 100 Pixel gesetzt werden. Dieser Bereich entspricht exakt dem Regler der
installierten GNOME-Einstellungsoberfläche. Nur das typisierte Feld `pixels`
wird an den festen Schlüssel `cross-hairs-thickness` angehängt; Ziel,
Zusatzfelder, andere Zahlentypen und Werte außerhalb des Bereichs scheitern.

Die Fadenkreuzfarbe kann bestätigt als gebräuchlicher deutscher oder englischer
Farbname sowie über exakte RGB-Kanäle eingestellt werden. Intern akzeptiert die
Policy ausschließlich die drei ganzzahligen Felder `red`, `green` und `blue`
von jeweils 0 bis 255. Erst der Executor erzeugt daraus die kanonische
Kleinschreibung `#rrggbb` für den festen Schlüssel `cross-hairs-color`; freie
gesprochene Zeichenketten erreichen den Systembefehl nicht.

Die Fokusverfolgung der GNOME-Lupe kann bestätigt ausgeschaltet, zentriert,
proportional oder schiebend eingestellt werden. Deutsche und englische
Sprachformen werden ausschließlich auf die vier installierten
`focus-tracking`-Enumwerte abgebildet. Das Ausschalten der Verfolgung schaltet
die Lupe selbst nicht aus.

Textcursor- und Mauszeigerverfolgung können mit zwei getrennten bestätigten
Befehlen ebenfalls ausgeschaltet, zentriert, proportional oder schiebend
eingestellt werden. Jeder Befehl ist an genau `caret-tracking` beziehungsweise
`mouse-tracking` gebunden und akzeptiert nur die vier installierten Enumwerte.
Das Ausschalten eines Trackers deaktiviert die Lupe nicht.

Linsenmodus und Scrollen am Bildschirmrand können jeweils mit getrennten
bestätigten Ein-/Aus-Befehlen gesteuert werden. Die vier Aktionen sind ohne
Parameter fest an `lens-mode true/false` beziehungsweise
`scroll-at-edges true/false` gebunden. Das Ausschalten einer Option deaktiviert
weder die Lupe noch einen anderen barrierefreien Rettungsweg.

- robuste Shell-Integration für Anwendungen ohne semantische Fensteraktionen;
  das gerichtete Verschieben des aktiven Fensters auf eine benachbarte
  Arbeitsfläche ist bei exakt angebotener AT-SPI-Aktion vorhanden;
- robustere Abdeckung von Shell-Versionen, die diese Shell-Bedienelemente nicht
  über AT-SPI anbieten;
- weitere Bereichs- und widget-spezifische Auswahlaktionen; benannte
  Fokusbewegung jenseits ausführbarer Elemente, gebundenes Auf-/Zuklappen in Bäumen
  und Baumtabellen, direkte verifizierte Tabellenzeilenauswahl sowie gebundene
  Registerkartenauswahl, gebundene Schiebereglerwerte sowie geprüfte
  Kontrollkästchen-, Optionsfeld-, Kombinationsfeld- und Zahlenfeldaktionen
  sowie getrennte geprüfte Schalter- und gebundene Menüeintragsaktionen sind
  vorhanden;
- Navigation, Pfadeingabe und weitere Varianten von Datei-, Ordner-, Öffnen-,
  Speichern- und Berechtigungsdialogen; sichtbare Zielauswahl, sichere
  Datei- und Pfadeingabe, gebundene sichtbare Ordnernavigation und eine erste
  gebundene Berechtigungsentscheidung sowie
  generische nummerierte oder exakt benannte Bedienung sind vorhanden;
- Weitergehende Vergrößerungs- und Orca-Funktionen; das bestätigte Schreiben
  eines druckbaren diktierten Texts bis 500 Zeichen, das dauerhafte Leeren der
  Wayland-Zwischenablage mit festem `wl-copy --clear` sowie das sichere
  Einschalten von Bildschirmtastatur, Vergrößerung und Orca sind vorhanden.
  Der Leeren-Befehl liest oder protokolliert keinen Inhalt und verändert die
  getrennte PRIMARY-Auswahl nicht.

Der exakte Inhalt eines aktuell fokussierten, nicht geschützten AT-SPI-Textfelds
kann nach Bestätigung in die Wayland-Zwischenablage kopiert werden. Passwort-
und Schutzfelder, leere, unvollständige, NUL-haltige oder mehr als 100.000
Zeichen lange Inhalte scheitern geschlossen. Der Inhalt wird nur über stdin an
den festen `wl-copy`-Prozess übertragen und erscheint weder in argv noch in
Bestätigung, Ergebnis oder Audit.

Eine getrennte bestätigte Aktion kopiert exakt eine aktive AT-SPI-Textauswahl
aus dem fokussierten sicheren Textfeld. Clausis verlangt genau eine nicht leere
Auswahl, geordnete Offsets innerhalb der gemeldeten Zeichenzahl und höchstens
100.000 ausgewählte Zeichen. Mehrdeutige, geschützte, unvollständig gelesene
oder NUL-haltige Spannen scheitern vor dem stdin-basierten Wayland-Writer.

Dieselbe exakt gebundene einzelne Auswahl kann nach einer inhaltsfreien
Bestätigung vorgelesen werden, ohne die Zwischenablage zu verändern. Für die
Sprachausgabe werden Leerzeichen normalisiert und höchstens 1.000 Zeichen mit
einem ausdrücklichen Kürzungshinweis ausgegeben. Weil gesprochener Inhalt
private Daten offenlegen kann, ersetzt das signierte Audit Nachricht und
Details vollständig durch `[REDACTED: selected text]`.

Der lokale Befehl „Alles im Textfeld auswählen“ markiert den gesamten Inhalt
eines fokussierten, nicht geschützten AT-SPI-Textobjekts ohne Tastatur- oder
Mausemulation. Zulässig sind 1 bis 100.000 Zeichen und höchstens 64 vorherige,
gültige Auswahlspannen. Der Adapter ersetzt diese mit der exakten Spanne vom
Anfang bis zur gemeldeten Zeichenzahl, prüft Auswahlzahl und Offsets und stellt
bei Ablehnung oder Abweichung die vorherigen Spannen verifiziert wieder her.

„Textauswahl aufheben“ ist der zugehörige lokale Korrekturbefehl. Er prüft bis
zu 64 nicht leere, geordnete Spannen im einmal gebundenen sicheren Textobjekt,
entfernt sie in absteigender Indexreihenfolge und verlangt anschließend exakt
null Auswahlen. Ein bereits leerer Zustand ist erfolgreich idempotent. Bei
Teilablehnung oder Abweichung werden Restspannen entfernt und alle vorherigen
Spannen in ursprünglicher Reihenfolge wiederhergestellt und nachgelesen.

„Textauswahl löschen“ entfernt nach einer inhaltsfreien Bestätigung genau eine
nicht leere Auswahl aus dem fokussierten, nicht geschützten und editierbaren
AT-SPI-Textobjekt. Der Adapter liest höchstens 100.000 Zeichen, verlangt danach
den exakt erwarteten Gesamtinhalt und null Auswahlen. Bei Ablehnung, Ausnahme
oder Abweichung stellt er den vorherigen Inhalt, die Cursorposition und die
ursprüngliche Auswahl verifiziert wieder her; der gelöschte Text erscheint
weder in Bestätigung noch Ergebnis.

Zwei weitere lokale Befehle bewegen den Textcursor im fokussierten sicheren
AT-SPI-Textobjekt exakt an den Anfang oder das Ende. Zeichenzahl und vorheriger
`caretOffset` müssen innerhalb eines auf 100.000 Zeichen begrenzten Objekts
liegen. Bereits erreichte Grenzen sind idempotent; andernfalls werden Annahme
und exakter neuer Offset geprüft. Ablehnung, Ausnahme oder Abweichung löst eine
verifizierte Rücksetzung auf den alten Offset aus. Passwort- und Schutzfelder
werden vor jeder Mutation abgewiesen.

„Cursor ein Zeichen vor“ und „Cursor ein Zeichen zurück“ verwenden dieselbe
gebundene Prüfung und Rücksetzung, leiten aber ausschließlich den vorherigen
Offset plus oder minus genau ein AT-SPI-Zeichen ab. Nicht-ASCII-Zeichen bleiben
damit einzelne semantische Zeichen; am Anfang beziehungsweise Ende ist der
Befehl idempotent. Beliebige gesprochene Zahlenoffsets werden nicht akzeptiert.

„Wo ist der Textcursor?“ ist eine getrennte lokale Orientierungsaktion. Sie
gibt nur den zugänglichen Feldnamen, den geprüften `caretOffset` und die
begrenzte Gesamtzeichenzahl aus und ruft `getText` nicht auf. Schutz- und
Passwortfelder werden vor der Textschnittstelle abgewiesen, damit auch ihre
Länge nicht offengelegt wird. Ungültige Rollen, Attribute, Offsets oder
Zeichenzahlen scheitern ohne Mutation.

„Füge am Textcursor … ein“ schreibt nach inhaltsfreier Bestätigung einen
einzelnen druckbaren diktierten Text von 1 bis 500 Zeichen an den validierten
`caretOffset` eines fokussierten sicheren editierbaren Textobjekts. Eine aktive
Auswahl, Schutzattribute, unvollständiger Altinhalt oder ein Ergebnis über
100.000 Zeichen brechen vor der Mutation ab. Clausis prüft anschließend den
vollständigen erwarteten Inhalt, den Cursor direkt hinter der Einfügung und
null Auswahlen. Ablehnung, Ausnahme oder Abweichung stellt Inhalt und Cursor
verifiziert wieder her; Diktat, Bestätigung, Ergebnis und signiertes Audit
enthalten den eingefügten Text nicht.

„Zeichen vor dem Textcursor löschen“ und „Zeichen nach dem Textcursor löschen“
entfernen nach Bestätigung jeweils exakt ein AT-SPI-Zeichen links oder rechts
des validierten Cursors. Damit bleiben auch mehrbyteige Unicode-Zeichen eine
einzelne semantische Einheit. Eine aktive Auswahl, Schutzattribute, ungültige
Metadaten oder mehr als 100.000 Zeichen brechen vor der Mutation ab. Am Anfang
beziehungsweise Ende ist die passende Aktion idempotent; sonst werden der
vollständige erwartete Inhalt, der exakte Cursor und null Auswahlen geprüft.
Ablehnung oder Abweichung stellt Inhalt und Cursor verifiziert wieder her.

„Zeichen vor dem Textcursor auswählen“ und „Zeichen nach dem Textcursor
auswählen“ markieren ohne Bestätigung genau eine semantische AT-SPI-Spanne links
oder rechts des validierten Cursors und bewegen den Cursor an deren äußere
Kante. Die Befehle lesen den Zeicheninhalt nicht. Eine bestehende Auswahl,
Schutzattribute, ungültige Metadaten oder mehr als 100.000 Zeichen scheitern vor
der Mutation; an der passenden Textgrenze bleibt der Zustand unverändert. Eine
abgelehnte oder abweichende Auswahl wird vollständig entfernt und der vorige
Cursor verifiziert wiederhergestellt.

„Zeichen vor dem Textcursor vorlesen“ und „Zeichen nach dem Textcursor
vorlesen“ sind getrennte bestätigungspflichtige Offenlegungsaktionen. Nach
Rollen-, Schutz-, Zeichenanzahl- und Cursorprüfung liest der Adapter exakt die
eine AT-SPI-Spanne links oder rechts des Cursors. An der jeweiligen Textgrenze
erfolgt überhaupt kein Inhaltszugriff. Leerzeichen, Tabulator und Zeilenumbruch
werden eindeutig benannt; das Zeichen selbst erscheint weder in der
Bestätigung noch im signierten Audit.

„Wort vor dem Textcursor vorlesen“ und „Wort nach dem Textcursor vorlesen“
ergänzen eine bestätigungspflichtige Wortorientierung. Nach denselben einmalig
gebundenen Rollen-, Schutz-, Zeichenanzahl- und Cursorprüfungen überspringt der
Adapter Leer- und Satzzeichen und sammelt ein Unicode-Wort mit Bindestrich,
Apostroph oder Unterstrich ausschließlich über Ein-Zeichen-`getText`-Spannen.
Die Suche ist auf 256 geprüfte Zeichen und das Wort auf 128 Zeichen begrenzt;
an der passenden Feldgrenze erfolgt kein Inhaltszugriff. Das Ergebnis wird vor
der Audit-Signatur vollständig durch einen richtungsspezifischen Marker ersetzt.

„Cursor ein Wort zurück“ und „Cursor ein Wort vor“ bewegen den Textcursor ohne
Tastatur- oder Mausemulation zum vorherigen beziehungsweise nächsten
Unicode-Wortanfang. Eine aktive Auswahl, Schutzattribute oder ungültige
Metadaten werden vor Inhaltszugriff abgewiesen. Die Suche verwendet höchstens
256 einzelne AT-SPI-Zeichenspannen; an der passenden Feldgrenze ist sie
inhaltsfrei und idempotent. Nach der Mutation müssen exakter Zieloffset und null
Auswahlen vorliegen, andernfalls wird der vorherige Cursor verifiziert
wiederhergestellt.

„Wort vor dem Textcursor auswählen“ und „Wort nach dem Textcursor auswählen“
markieren lokal genau die benachbarte Unicode-Wortspanne. Ausgangszustand sind
null Auswahlen; höchstens 256 einzelne AT-SPI-Zeichenspannen bestimmen Anfang
und Ende. Der Cursor wandert an die äußere Wortkante, anschließend müssen exakt
eine Auswahl, die berechneten Offsets und der Zielcursor nachlesbar sein. An der
passenden Feldgrenze bleibt der Zustand ohne Inhaltszugriff unverändert. Bei
Ablehnung oder Abweichung werden alle Restspannen entfernt und der vorige
Cursor verifiziert wiederhergestellt.

„Wort vor dem Textcursor löschen“ und „Wort nach dem Textcursor löschen“
entfernen nach inhaltsfreier Bestätigung genau die durch dieselbe begrenzte
Unicode-Suche bestimmte Wortspanne. Null Auswahlen und höchstens 256 einzelne
Suchabfragen sind Voraussetzung; anschließend wird der vollständige sichere
Feldinhalt bis 100.000 Zeichen gesichert. Clausis verlangt den exakt erwarteten
Gesamtinhalt, den für Rückwärts- oder Vorwärtslöschung berechneten Cursor und
null Auswahlen. Ablehnung oder Abweichung stellt Inhalt und Cursor verifiziert
wieder her; das gelöschte Wort wird nicht wiederholt.

„Wort vor dem Textcursor durch … ersetzen“ und „Wort nach dem Textcursor durch
… ersetzen“ schreiben nach inhaltsfreier Bestätigung einen druckbaren
diktierten Ersatz von 1 bis 500 Zeichen in genau die begrenzt bestimmte
Unicode-Wortspanne. Das Gesamtergebnis darf 100.000 Zeichen nicht überschreiten.
Clausis setzt den Cursor direkt hinter den Ersatz und verlangt vollständigen
erwarteten Inhalt, exakten Cursor und null Auswahlen. Bei Ablehnung oder
Abweichung werden vollständiger Altinhalt und Cursor verifiziert
wiederhergestellt; das Diktat wird vor der Audit-Signatur fest redigiert.

„Ersetze die Textauswahl durch …“ ersetzt nach inhaltsfreier Bestätigung genau
eine nicht leere Auswahl im fokussierten sicheren editierbaren Textobjekt durch
1 bis 500 druckbare diktierte Zeichen. Altinhalt, Auswahlspanne, Cursor und der
vollständige erwartete Nachinhalt müssen innerhalb von 100.000 Zeichen liegen.
Clausis verlangt danach exakt den erwarteten Gesamtinhalt, den Cursor direkt
hinter dem Ersatz und null Auswahlen. Ablehnung oder Abweichung stellt den
vorigen Gesamtinhalt, Cursor und die exakte Auswahlspanne verifiziert wieder
her; Auswahl- und Ersatzinhalt erscheinen nicht in Bestätigung, Ergebnis oder
signiertem Audit.

Der begrenzte Textinhalt der Wayland-Zwischenablage kann nach Bestätigung in
das aktuell fokussierte, nicht geschützte und editierbare AT-SPI-Textfeld
eingefügt werden. Ein nichtblockierender Reader begrenzt vor dem Dekodieren auf
400.000 Byte und fünf Sekunden; nur valides UTF-8 bis 100.000 Zeichen mit
Tabulator und Zeilenumbruch als erlaubten Steuerzeichen wird akzeptiert. Die
Mutation verlangt exaktes Readback und rollt bei Ablehnung, Ausnahme oder
Abweichung auf den alten Feldinhalt zurück. Der Inhalt erscheint nicht in
Anfrage, Bestätigung, Ergebnis, Sprachausgabe oder Audit.

Der Textinhalt der Wayland-Zwischenablage kann nach einer inhaltsfreien
Bestätigung vorgelesen werden. Derselbe byte- und zeitbegrenzte Reader wird
verwendet; für Sprache werden Leerzeichen normalisiert und höchstens 1.000
Zeichen mit ausdrücklichem Kürzungshinweis ausgegeben. Weil die Ausgabe private
Daten offenlegen kann, bleibt sie bestätigungspflichtig. Vor dem signierten
Audit ersetzt Clausis Nachricht und Details vollständig durch einen festen
Redaktionsmarker.

Ein bestätigter Befehl schreibt einen einzelnen druckbaren diktierten Text bis
500 Zeichen über stdin in die Wayland-Zwischenablage und überschreibt deren
alten Inhalt irreversibel. Zusatzargumente und nicht druckbare Zeichen werden
abgelehnt. Bestätigung und Ergebnis wiederholen den Text nicht. Vor der
Audit-Signatur ersetzt Clausis sowohl dieses Target als auch das bereits
vorhandene Diktat für fokussierte Textfelder durch aktionsspezifische feste
Marker; damit ist die zuvor mögliche Offenlegung des Textfeld-Diktats im
Request-Audit ebenfalls geschlossen.

Mauskoordinaten und Bildschirmerkennung dürfen nur ein gekennzeichneter
Best-Effort-Fallback sein. Unter Wayland soll Clausis keine globale
Eingabesimulation als Hauptschnittstelle verwenden.

### 3. Sprachdialog für Orientierung und Korrektur

Die lokalen Befehle „Wo bin ich?“, „Was kann ich hier tun?“, „Lies das Fenster
vor“, „Nummer drei“, „Zurück“, „Wiederholen“, „Korrigieren“ und „Abbrechen“ sind
umgesetzt. Ziele werden nummeriert aus dem aktuellen AT-SPI-Baum gelesen. Noch
ist nun ein dialogübergreifender, einmaliger Korrektur-Slot umgesetzt: Wiederholen
hält die inhaltsfreie Aufforderung offen, Abbrechen und Stopp löschen sie, und
genau die nächste andere Äußerung läuft einmalig durch denselben Router-/Broker-
und gegebenenfalls bereits eingewilligten Fallback-Pfad. Kein Transkript wird
im Slot gespeichert. Eine monotone Ablaufzeit von 30 Sekunden begrenzt ihn auch
zeitlich; die erste verspätete Äußerung wird verworfen statt ausgeführt. Stopp,
Abbrechen und ein neuer Korrekturaufruf behalten nach Ablauf Vorrang. Das lokale
Aufwach-Gate bleibt bis zur ursprünglichen Ablaufzeit plus fünf Sekunden
Verwerfungs-Spielraum offen; Wiederholen verlängert diese Grenze nicht. Ablauf
und ein ausdrücklicher Schlafbefehl schließen das Gate. Eine bereits ausgeführte
Aktion wird ausdrücklich nicht als automatisch rückgängig dargestellt.
Der semantische Fensterwechsel rät bei keinem oder mehreren aktiven Fenstern
nicht mehr, sondern verlangt genau einen Ausgangsfokus. Danach muss allein das
berechnete Nachbarfenster aktiv sein; bei Abweichung wird der alte Fokus
nachweislich wiederhergestellt. Dasselbe gilt nun für nächstes/vorheriges
Bedienelement: Mehrfachfokus wird abgelehnt, der berechnete Zielfokus exakt
geprüft und ein abweichender Teilzustand auf den vorherigen Fokus zurückgesetzt.
Benannte Aktivierung bindet unmittelbar vor `doAction()` zusätzlich die
AT-SPI-Identität des aktiven Fensters erneut und verlangt dasselbe Ziel genau
einmal in dessen frisch gelesener bedienbarer Kontrollmenge. Ein zwischenzeitlich
gewechseltes Fenster, entferntes Ziel oder nicht mehr sichtbares beziehungsweise
sensitives Ziel führt deshalb zu keiner Mutation.
Weiterhin fehlt eine vollständige
Nachzustandsprüfung für jede andere schreibende Aktion. Der Developer-Dry-Run ist
hingegen jetzt vollständig klassifiziert: Nur zwölf ausdrücklich lesende
semantische Aktionen dürfen den Adapter erreichen, alle übrigen und zukünftig
hinzukommenden semantischen Aktionen gelten automatisch als Mutation und werden
vor dem Adapteraufruf blockiert.

### 4. Vertrauenswürdige Bestätigung

Die automatisierbare D-Bus-PIN-Übertragung wurde entfernt. Der isolierte
Systemdienst erzeugt und spricht die kanonische Zusammenfassung und eine
zufällige Phrase selbst, nimmt Phrase und PIN direkt lokal auf, löscht beide
temporären Aufnahmen und reicht das kurzlebige aktionsgebundene Token selbst an
den Broker weiter. D-Bus gibt weder Phrase, PIN noch Capability an Hermes oder
den Desktop zurück. Der Einrichtungsdialog kann die PIN zweimal lokal erkennen;
Calamares übernimmt nur den PBKDF2-Prüfwert in das Zielsystem.

Jede geschützte Aufnahme für Phrase, PIN, Recovery-Key-Rücklesen und finale
Installationsphrase kündigt nun den lokalen Abbruch an. Nur eine vollständige,
explizite deutsche oder englische Abbruchäußerung beendet den Ablauf fail-closed,
löscht die temporäre Aufnahme und verhindert Capability-Ausgabe beziehungsweise
Partitionierung. Noch fehlen der physische Nachweis, dass PipeWire/ALSA auf
unterstützter Hardware wirklich vom Desktop-Audiographen getrennt ist,
belastbare Wiedergabe-/Stimmklon-Erkennung und privilegierte
Produktionsadapter. Bis diese Punkte geprüft sind, bleibt der Pfad eine
technische Vorschau.

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
nach dem korrekten lokalen Zurücklesen aller zwölf notierten Vierergruppen
kurzzeitig root-lesbar im flüchtigen `/run` ab. Eine Abweichung bricht vor der
Bestätigungsphrase und Partitionierung ab. Das angepasste
`luksbootkeyfile`-Modul fügt ihn nach der Partitionierung direkt als LUKS-Key
hinzu und entfernt alle temporären Kopien. Die nachgewiesene Trennung des
Audiogeräts von der Desktop-Sitzung, der gleichwertige geschützte Tastaturweg
und der persistente Installations- und Entsperrtest in VirtualBox fehlen
weiterhin. Die Lösung verwendet kein Screen-Scraping; die Produktionsfreigabe
bleibt blockiert.

Der Host-Testunterbau kann inzwischen eine separat registrierte EFI-VM mit
einer ausschließlich neu erzeugten dynamischen VDI unter dem Projekt-`dist`
anlegen, die exakte ISO-Zuordnung und den vollständigen Live-Boot prüfen und
nur diese disposable VM samt VDI im `finally` wieder entfernen. Ein realer
Preflight hat diese Isolationsgrenze und den Cleanup bestätigt. Er führt den
geschützten Calamares-Ablauf jedoch bewusst noch nicht aus und ist daher kein
Installations-, Zielkopier-, Boot- oder Entsperrnachweis.

Eine zusätzliche nicht mutierende Vordergrundaufnahme schließt zunächst nur
die GNOME-Übersicht und wartet begrenzt. Nach drei Sekunden war lediglich der
Desktop sichtbar; nach 45 Sekunden erschien der zugängliche Clausis-Setup-
Dialog mit vorausgewähltem Offline-Weg. Damit ist belegt, dass Calamares nicht
lautlos ausfällt, sondern synchron hinter dem noch nicht abgeschlossenen Setup
wartet. Ein weiterer, strikt auf die disposable Installer-VDI begrenzter Lauf
befüllte beide übereinstimmenden PIN-Felder über GTK-Mnemonics. Der anschließend
gesendete Speichern-Mnemonic aktivierte die sichtbare Schaltfläche jedoch nicht;
der Setup-Dialog blieb mit beiden maskierten PINs geöffnet. Calamares wurde
nicht betreten und erhielt keine Eingabe. Eine robuste semantische Aktivierung
des Speicherns war damit zunächst offen. Der nachfolgende, readiness-geprüfte
Lauf löste dies über die deklarierte GTK-Tab-Reihenfolge: Er wartete auf das
sichtbare Setup-Fenster, befüllte beide PINs, fokussierte die Speichern-
Schaltfläche nachweisbar, aktivierte sie mit Enter und akzeptierte erst nach dem
Verschwinden des Setup-Fensters die separat erkannte große helle Calamares-
Oberfläche. Die Welcome-Seite von Calamares 13 wurde sichtbar; innerhalb von
Calamares erfolgte keine Eingabe. Partitionierung und vollständige Installation
bleiben offen. Ein nachfolgender, ausschließlich an die disposable VDI
gebundener Preflight navigierte über Location und Keyboard bis zur
Partitionsseite. Dort war nur `VBOX HARDDISK - 64.00 GiB (/dev/sda)` sichtbar;
weder Löschen noch manuelle Partitionierung war ausgewählt und Weiter war
deaktiviert. Es erfolgte keine Partitionsauswahl und kein Schreibzugriff.

Zusätzlich fehlen durchgängiges Audio in Initramfs, LUKS-Entsperrung, GDM,
Recovery, Btrfs-Subvolume-Layout und Rollback. Stimme allein ist keine sichere
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
Die zeitweise verworfenen VirtualBox-ACPI-Ereignisse wurden im laufenden Gast
ursächlich eingegrenzt: `systemd-logind` protokollierte den Tastendruck, während
`gsd-media-keys` den systemnahen `handle-power-key`-Inhibitor hielt, aber keinen
Shutdown auslöste. Clausis installiert deshalb einen unabhängigen `acpid`-
Fallback, der ausschließlich bei positivem `systemd-detect-virt --vm` ein
Poweroff mit `systemctl --no-block` anfordert und damit den seriellen
`acpid`-Handler unmittelbar nach Übergabe an systemd freigibt. Instrumentierte
Diagnoseläufe belegten zusätzlich einen VirtualBox-Hostfehler: Trotz vom Host
erfolgreich gemeldetem Request erschien im vollständig gestarteten Gast weder
bei `systemd-logind` noch beim aktiven, mit beiden Regeln geladenen `acpid` ein
Power-Key-Ereignis. Der neue Smoke-Test wartet deshalb auf tatsächlich
gerendertes Clausis-Branding in GRUB und fertigem Desktop, statt feste
Bootzeiten oder nur eine Auflösung zu verwenden. Ein fail-closed Soak-Harness
wiederholt diesen vollständigen Ablauf gegen einen festen ISO-Hash, benennt
jede Bild-Evidenz eindeutig und schreibt auch bei einem Teilfehler eine
maschinenlesbare Zusammenfassung. Die aktuelle Final-ISO-Serie bestand fünf
frische Boots mit jeweils genau einem Impuls; Poweroff folgte nach 9,4 bis 13,7
Sekunden. Die zuvor nachgewiesene sporadische Host-Ereigniszustellung ist damit
nicht widerlegt: längere Endurance-Läufe bleiben Release-Gate. Physische
Power-Tasten verbleiben unverändert bei GNOME; Hardwaretests bleiben Teil der
Release-Abnahme.

## Empfohlene Reihenfolge

1. Dediziertes Wake-Word, lokale Unterbrechung und zertifiziertes Barge-in.
2. GNOME-Adapter auf Shell, Portale und Standarddialoge ausweiten.
3. Geschütztes Bestätigungsportal und privilegierte Adapter.
4. Sprach-nativer Installer sowie Boot-, Login- und Recovery-Audio.
5. Geprüfte Anwendungsprofile, Hardwarematrix und Nutzerstudien.

Erst wenn diese fünf Stufen auf unterstützter Hardware bestanden sind, sollte
Clausis als vollständig sprachbedienbares Betriebssystem bezeichnet werden.
### Aktuelle Zeile lesen und begrenzen

„Lies die aktuelle Zeile vor“ liest nach Bestätigung ausschließlich die mit
Ein-Zeichen-Zugriffen ermittelte Zeile am Textcursor. Geschützte Felder und
Zeilen über 1.000 Zeichen werden abgelehnt; der Inhalt erscheint nicht im
Audit. „Cursor an den Zeilenanfang“ und „Cursor an das Zeilenende“ funktionieren
lokal nur ohne Auswahl und setzen bei einer abweichenden AT-SPI-Rückmeldung den
vorherigen Cursorstand wieder her. Ein mikrofongetriebener End-to-End-Test in
realen Drittanbieter-Editoren bleibt offen.

„Wähle die aktuelle Zeile aus“ verwendet dieselben begrenzten Zeilengrenzen,
schließt den Zeilenumbruch aus und funktioniert nur bei zuvor leerer Auswahl.
Die Aktion prüft Auswahlspanne und Cursorposition; bei Ablehnung oder
Abweichung entfernt sie jede Teilauswahl und stellt den ursprünglichen Cursor
wieder her. Leere Zeilen werden ausdrücklich abgelehnt. Danach können die
bereits getrennt abgesicherten Befehle zum Kopieren, Löschen oder Ersetzen der
Auswahl verwendet werden.

„Lösche die aktuelle Zeile“ ist eine getrennt bestätigte Korrekturaktion. Sie
entfernt eine nicht leere, höchstens 1.000 Zeichen lange Zeile und genau einen
passenden Umbruch: bevorzugt den folgenden, bei der letzten Zeile den
vorherigen. Danach müssen Gesamttext, Cursor und leere Auswahl exakt stimmen;
anderenfalls wird der vollständige vorige Feldinhalt samt Cursor verifiziert
wiederhergestellt. Der gelöschte Inhalt erscheint weder in Bestätigung noch
Ergebnismeldung oder Audit.
### Aktuelle Zeile ersetzen

„Ersetze die aktuelle Zeile durch …“ nimmt nach inhaltsfreier Bestätigung 1 bis
500 druckbare diktierte Zeichen an. Nur die begrenzte Zeilenspanne wird ersetzt;
vorhandene Zeilenumbrüche bleiben erhalten. Gesamttext, Cursor direkt hinter
dem Ersatz und null Auswahlen müssen exakt zurückgelesen werden, sonst stellt
Clausis den vollständigen vorherigen Feldzustand wieder her. Alter Text und
Ersatz erscheinen weder in Bestätigung noch Ergebnis oder signiertem Audit.
### Neue Zeile oberhalb oder unterhalb

„Füge die Zeile … oberhalb/unterhalb der aktuellen Zeile ein“ sind zwei
getrennt bestätigte Aktionen für 1 bis 500 druckbare Zeichen ohne Zeilenumbruch.
Die aktuelle Zeile und alle vorhandenen Trennzeichen bleiben erhalten; ein
leeres Feld wird direkt mit der neuen Zeile befüllt. Gesamttext, Cursor und
leere Auswahl werden exakt geprüft, bei Abweichung wird der vollständige vorige
Feldzustand wiederhergestellt. Das Diktat wird weder wiederholt noch auditiert.
### Aktuelle Zeile duplizieren

„Dupliziere die aktuelle Zeile oberhalb/unterhalb“ kopiert nach Bestätigung die
begrenzte nicht leere Zeile direkt in die gewünschte Richtung. Bereits aktive
Auswahlen werden abgelehnt. Der Zeileninhalt wird weder in die Anfrage noch in
Bestätigung, Ergebnis oder Audit übernommen. Gesamttext, Cursor und leere
Auswahl werden exakt geprüft; eine Abweichung stellt den vollständigen vorigen
Feldzustand wieder her.
### Aktuelle Zeile verschieben

„Verschiebe die aktuelle Zeile nach oben/unten“ vertauscht nach Bestätigung die
begrenzte aktuelle Zeile exakt mit einer ebenfalls höchstens 1.000 Zeichen
langen Nachbarzeile. Dokumentgrenzen und bestehende Auswahlen werden abgelehnt.
Die relative Cursorposition in der verschobenen Zeile bleibt erhalten; beide
Inhalte bleiben außerhalb von Anfrage, Bestätigung, Ergebnis und Audit. Bei
abweichendem Gesamttext, Cursor oder Auswahlzustand wird alles zurückgesetzt.
### Wartbare Adaptergrenze

Das `SemanticDesktop`-Protocol enthält ausschließlich Signaturen; sämtliche
AT-SPI-, Datenschutz- und Rollback-Logik liegt einmalig in `PyAtSpiDesktop`.
Ein AST-Test lehnt konkrete Methodenkörper im Interface ab. Damit können neue
Sprachaktionen nicht versehentlich eine veraltete Protocol-Kopie statt der
tatsächlichen Laufzeitimplementierung fortschreiben.
### Zeilen verbinden

„Verbinde die aktuelle Zeile mit der vorherigen/nächsten“ entfernt nach
Bestätigung exakt den dazwischenliegenden Zeilenumbruch. Beide Zeilen bleiben
auf je 1.000 Zeichen begrenzt; fehlende Nachbarn und bestehende Auswahlen werden
abgelehnt. Die logische Cursorposition bleibt erhalten, Inhalte verlassen den
Adapter nicht, und Gesamttext, Cursor sowie Auswahlzustand werden geprüft und
bei Abweichung vollständig wiederhergestellt.

### Zeile am Textcursor teilen

„Teile die aktuelle Zeile am Textcursor“ fügt nach Bestätigung genau einen
Zeilenumbruch an der gebundenen Cursorposition ein. Das funktioniert auch am
Zeilenanfang, Zeilenende und in einem leeren Feld. Geschützte Felder, Zeilen
über 1.000 Zeichen, aktive Auswahlen und ein dadurch zu großes Gesamtfeld
werden abgelehnt. Gesamttext, Cursor direkt nach dem neuen Umbruch und leerer
Auswahlzustand werden exakt geprüft; bei Abweichung werden vorheriger Text und
Cursor vollständig wiederhergestellt. Zeileninhalt erscheint weder in
Bestätigung noch Ergebnis oder Audit.

### Aktuelle Zeile ein- und ausrücken

„Rücke die aktuelle Zeile ein“ fügt nach Bestätigung genau vier Leerzeichen
am gebundenen Zeilenanfang ein. „Rücke die aktuelle Zeile aus“ entfernt genau
einen führenden Tabulator oder bis zu vier führende Leerzeichen und lehnt eine
nicht eingerückte Zeile ab. Auswahl und Überlänge scheitern geschlossen; die
logische Cursorposition bleibt erhalten. Gesamttext, Cursor und leerer
Auswahlzustand werden exakt geprüft und bei Abweichung vollständig
wiederhergestellt. Der Zeileninhalt erscheint in keiner externen Meldung und
nicht im Audit.
