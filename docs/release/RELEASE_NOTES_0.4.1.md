# Clausis 0.4.1 – geschützte lokale Bestätigung

Diese technische Vorschau schließt den automatisierbaren D-Bus-PIN-Pfad aus
0.4.0. Sie ist weiterhin kein fertiges Produktionssystem.

## Neu

- `org.clausis.TrustedConfirm1` bietet nur noch
  `ConfirmAndSubmit(request)`. Es gibt keine öffentliche `Approve`-Methode und
  keine D-Bus-Argumente für Phrase, PIN oder Capability.
- Der isolierte Systemdienst spricht Zusammenfassung und Zufallsphrase selbst,
  nimmt Phrase und PIN lokal auf, löscht beide Aufnahmen und reicht das
  aktionsgebundene 30-Sekunden-Token selbst an den Broker weiter.
- Normale Bus-Clients können keine lokale Herkunft und kein fremdes
  Capability-Token einschleusen.
- Lokale Offline-Befehle und GPT Live rufen den Systemdienst erst auf, nachdem
  der lokale Broker eine Aktion ausdrücklich als bestätigungspflichtig
  eingestuft hat. Ein fehlender Dienst oder eine ungültige Antwort endet als
  Verweigerung.
- Die Sicherheits-PIN kann vor der Installation zweimal lokal gesprochen oder
  verdeckt eingegeben werden. Gespeichert wird nur ein versionierter
  PBKDF2-HMAC-SHA-256-Prüfwert.
- Calamares übernimmt den PIN-Prüfwert begrenzt, ohne Symlink-Folgen und atomar
  in das Zielsystem. Ohne eingerichteten Prüfwert startet der Dienst nicht.
- Ein eigener Starthelfer erzwingt für die Bestätigung denselben gepinnten
  Faster-Whisper-/Sounddevice-Laufzeitstapel wie für Clausis Audio.

## Sicherheitsgrenzen

- Physische Trennung vom PipeWire-/ALSA-Audiographen des Desktops ist noch
  nicht auf unterstützter Hardware bewiesen.
- Zufallsphrase und PIN reduzieren einfache Wiederholungsangriffe, sind aber
  kein ausreichender Schutz gegen gezielte Stimmklone oder Live-Audioinjektion.
- Privilegierte Produktionsadapter und die vollständige Verbindung aller
  GNOME-Sitzungsaktionen mit diesem Bestätigungspfad bleiben offen.
- Die vollständige Installation auf eine VirtualBox-Festplatte sowie Audio-
  und Nutzerprüfungen auf realer Hardware bleiben Release-Gates.

Clausis 0.4.1 bleibt ausdrücklich eine öffentliche technische Testversion.
