# Clausis testen — Anleitung für blinde und sehbehinderte Testpersonen

Danke, dass Sie das ausprobieren. Diese Seite ist so geschrieben, dass sie sich
mit einem Screenreader gut vorlesen lässt: kurze Absätze, keine Tabellen, keine
Bilder, keine Diagramme.

## Lesen Sie das bitte zuerst

**Clausis ist unfertig und wurde noch nie von einem blinden Menschen benutzt.**
Sie sind nicht die Kontrollinstanz am Ende — Sie sind die ersten, die es
überhaupt ausprobieren. Rechnen Sie damit, dass Dinge nicht funktionieren.

Konkret:

- **Installieren Sie Clausis nicht auf einem Rechner, den Sie brauchen.**
  Nehmen Sie eine virtuelle Maschine oder einen Zweitrechner, dessen Daten Sie
  entbehren können. Die Installation löscht den gewählten Datenträger
  vollständig.
- **Tastatur und Orca bleiben immer der gleichwertige Weg.** Wenn die Sprache
  hängt, ist das ein Fehler von Clausis, nicht Ihrer. Sie kommen mit der
  Tastatur weiter.
- **An diesen Stellen verweigert Clausis absichtlich die Sprache**: Passwörter,
  Berechtigungsabfragen, die Festplattenentsperrung und das Terminal. Das ist
  kein Fehler, sondern Absicht — dort wäre ein mitgehörter Satz gefährlich.
  Wenn Sie das für falsch halten, sagen Sie es uns; das ist eine der Fragen,
  bei denen wir Ihre Meinung am dringendsten brauchen.
- **GPT Live sendet Raumaudio an OpenAI.** Es ist standardmäßig aus. Schalten
  Sie es nur ein, wenn Sie das wollen, und beachten Sie: die Offline-Variante
  ist schlechter, was die Entscheidung unfreier macht als sie sein sollte.

## Der Diagnosebericht

Bevor Sie etwas melden, erzeugen Sie diesen Bericht. Er beantwortet die
Rückfragen, die wir sonst stellen müssten.

```bash
clausis-report --output ~/clausis-bericht.json
```

Clausis liest Ihnen zuerst eine Zusammenfassung vor, damit Sie wissen, was Sie
gleich teilen. Der Bericht enthält **keine** Aufnahmen, keine Transkripte,
keine Dateinamen, keine Zugangsdaten und keine Aktionsziele — nur, welche
Aktion wie oft mit welchem Ergebnis lief.

Sie können ihn vor dem Absenden mit jedem Texteditor oder mit Orca durchgehen.

## Die Aufgaben

Versuchen Sie diese Aufgaben **ohne fremde Hilfe und ohne auf den Bildschirm zu
sehen**. Notieren Sie zu jeder: geschafft, teilweise, gar nicht — und wie lange
Sie gebraucht haben.

Wenn Sie eine Aufgabe nur mit der Tastatur geschafft haben, ist das „teilweise".
Genau diese Unterscheidung ist für uns die wichtigste Information.

### Block A: Grundlagen

1. Herausfinden, wo Sie gerade sind: „Hallo Clausis. Wo bin ich?"
2. Erfahren, was Sie tun können: „Was kann ich hier tun?"
3. Ein Programm öffnen und wieder schließen.
4. Die Lautstärke ändern und den Systemzustand abfragen.
5. Clausis anhalten: „Stopp Clausis". Kommt es sofort zur Ruhe?

### Block B: Text

6. Einen Satz in ein Textfeld diktieren.
7. Das letzte Wort löschen und neu diktieren.
8. Sich vorlesen lassen, was im Feld steht.
9. Einen Text mit Komma und Punkt diktieren. *Das geht derzeit noch nicht — wir
   möchten wissen, wie sehr es fehlt.*
10. Den Text speichern: Dialog öffnen, Dateinamen diktieren, bestätigen.

### Block C: Fenster und Oberfläche

11. Zwischen zwei Fenstern wechseln.
12. Ein Fenster minimieren und wiederherstellen.
13. Die Übersicht und die Schnelleinstellungen öffnen.
14. Auf eine andere Arbeitsfläche wechseln.

### Block D: System

15. Nach Updates suchen lassen.
16. Eine Datei im persönlichen Ordner suchen.
17. Einen Neustart auslösen und die Bestätigung durchlaufen. *Sie können bei der
    Bestätigung abbrechen — uns interessiert, ob der Weg verständlich ist.*

### Block E: Wenn etwas kaputtgeht

18. Ziehen Sie das Mikrofon ab. Sagt Clausis Ihnen, wie es weitergeht?
19. Schalten Sie die Sprachausgabe ab. Erreicht Sie die Meldung trotzdem?
20. Starten Sie neu und hören Sie, ob bei der Festplattenentsperrung eine
    Ansage kommt.

### Block F: Installation (nur auf einem entbehrlichen Rechner)

21. Von USB starten und bis zur Sprachbedienung kommen.
22. Die Installation durchlaufen, einschließlich Verschlüsselung.
23. Sich den Wiederherstellungsschlüssel vorlesen lassen und notieren.
24. Neu starten, entsperren, anmelden.

## Was uns am meisten hilft

Bei jedem Problem:

- **Was wollten Sie tun?** In Ihren Worten, nicht in technischen.
- **Was haben Sie gesagt?** Wörtlich, wenn Sie es noch wissen.
- **Was ist passiert?** Was hat Clausis gesagt oder eben nicht gesagt.
- **Kamen Sie weiter?** Mit Tastatur und Orca, oder gar nicht.
- Der Diagnosebericht.

Besonders wertvoll sind zwei Arten von Rückmeldung, nach denen sonst niemand
fragt:

- **Wo hat Clausis geschwiegen?** Stille an einer Stelle, an der eine Rückmeldung
  hätte kommen müssen, ist der schlimmste Fehler in einem solchen System — und
  in keinem Protokoll sichtbar.
- **Wo war es langsamer oder umständlicher als Orca und Tastatur allein?**
  Clausis muss besser sein als der heutige Weg, nicht nur anders. Wenn es das
  nicht ist, ist das ein Ergebnis und kein Versagen Ihrerseits.

## Wohin damit

Öffnen Sie einen Fehlerbericht im Projekt-Repository. Vorlagen für
Barrierefreiheits-Rückmeldungen liegen bereit und fragen genau die Punkte oben
ab.

Für sicherheitsrelevante Funde nutzen Sie bitte den Weg in `SECURITY.md`:
GitHub Private Vulnerability Reporting im Projekt-Repository
(**Security → Report a vulnerability**) — dort erreicht Sie der Bericht direkt
und vertraulich.

## Wenn Sie mehr tun möchten

Wir suchen ausdrücklich Menschen aus der Zielgruppe, die nicht nur testen,
sondern mitentscheiden — welche Funktionen zuerst kommen, wie die Sprache
klingt, wo Sicherheit und Bedienbarkeit gegeneinander abgewogen werden. Wenn
Sie das interessiert, sagen Sie Bescheid.
