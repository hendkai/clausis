# Clausis 0.3.0 – technische Vorschau

Diese Version ergänzt freiwilliges GPT Live für eine flüssigere Online-
Sprachbedienung während der Live-Installation und auf dem installierten System.
Die bisherige lokale Sprachsteuerung bleibt erhalten und funktioniert weiterhin
ohne OpenAI-Konto und ohne Internet.

## Neu

- GPT Live ist standardmäßig ausgeschaltet und wird im barrierefreien
  Einrichtungsdialog ausdrücklich angeboten.
- Für die laufende Übertragung des Mikrofon-Audios an OpenAI ist eine separate
  Einwilligung erforderlich. Der OpenAI API-Schlüssel wird verdeckt per
  Tastatur eingegeben und nur in einer privaten Datei des Benutzers gespeichert.
- Die OpenAI API wird separat abgerechnet; ein ChatGPT-Abonnement enthält nicht
  automatisch API-Guthaben.
- Bei Netzwerk- oder Audiofehlern wechselt Clausis mit gesprochener Erklärung
  automatisch zurück zur lokalen Sprachsteuerung.
- Der Menüeintrag **GPT Live sofort beenden** stoppt die Online-Übertragung
  lokal, ohne Antwort des Modells und auch bei ausgefallenem Internet.
- GPT Live erhält ausschließlich eine feste Liste typisierter Clausis-Aktionen.
  Es erhält kein Terminal, keine freie Programmausführung, keine Plug-ins, kein
  MCP und keine Bestätigungs-Tokens. Riskante Aktionen bleiben hinter der
  vertrauenswürdigen Clausis-Bestätigung.
- Während der Installation dient GPT Live als Sprachbegleiter. Die Calamares-
  Partitionierung selbst ist noch nicht vollständig sprach-nativ und bleibt
  zusätzlich über GUI, Tastatur und Orca bedienbar.
- Die Installation aktualisiert Hermes Agent weiterhin auf die zum
  Installationszeitpunkt neueste offizielle stabile Version und behält bei
  Fehlern die geprüfte ISO-Version als Rückfall.

## Wichtige Grenzen

Dies ist eine öffentliche technische Vorschau, keine produktionsreife
Distribution. Ein echter OpenAI-Realtime-Lauf mit Testkonto, physische
Audiohardware, vollständige Calamares-Installation, Orca-Nutzerstudien,
signierte Images und der geschützte Bestätigungspfad sind weiterhin offene
Abnahmepunkte. Andere Prozesse, die bereits unter demselben Desktop-Benutzer
laufen, könnten den privat gespeicherten API-Schlüssel auslesen.
