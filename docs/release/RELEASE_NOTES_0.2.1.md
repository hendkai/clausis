# Clausis 0.2.1 – technische Vorschau

Diese Version installiert bei einer Festplatteninstallation die zu diesem
Zeitpunkt neueste offizielle stabile Hermes-Agent-Veröffentlichung.

## Neu

- Clausis fragt während des Calamares-Installationslaufs ausschließlich den
  offiziellen GitHub-Endpunkt von `NousResearch/hermes-agent` ab.
- Entwürfe, Vorabversionen und unerwartete Tag-Namen werden abgelehnt.
- Die exakte Veröffentlichung wird mit ihrem eingefrorenen `uv.lock`
  installiert; MIT-Lizenz und aufgelöster Commit werden geprüft beziehungsweise
  lokal dokumentiert.
- Erst nach vollständigem Erfolg wird der Hermes-Starter atomar umgeschaltet.
- Ohne Internet oder bei einem Fehler bleibt Hermes 0.20.0 aus dem ISO aktiv.
  Clausis erklärt diesen Zustand beim ersten Login per Sprache und Mitteilung.
- Der barrierefreie Einrichtungsdialog erklärt den Aktualisierungsvorgang schon
  vor dem Start des Installers.

Die aktuellste stabile Upstream-Veröffentlichung zum Entwicklungszeitpunkt war
`v2026.8.3` vom 3. August 2026. Maßgeblich ist jedoch die neueste stabile
Veröffentlichung zum tatsächlichen Installationszeitpunkt.

## Sicherheitsgrenze

Der Updater verwendet TLS, das offizielle GitHub-Repository, eine strikte
Tag-Grammatik und die eingefrorene Abhängigkeitsdatei. Eine kryptografische
Prüfung gegen Clausis-eigene vertrauenswürdige Hermes-Maintainer-Schlüssel ist
noch nicht umgesetzt. Ein kompromittiertes offizielles Upstream-Konto bleibt
daher ein bekanntes Risiko. Clausis 0.2.1 ist weiterhin eine technische
Vorschau und nicht für produktive Systeme freigegeben.
