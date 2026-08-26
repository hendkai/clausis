# Piper-Offline-Stimme — Lizenz und Herkunft

Clausis integriert Piper als Offline-Stimme über ein generisches
speech-dispatcher-Output-Modul (`piper-generic`, `sd_generic`). Diese Seite
dokumentiert Herkunft, Lizenz und Integrität der beiden Fremdkomponenten —
Piper selbst und das deutsche Stimmodell. Sie ist Abnahme-Kriterium der
Karte „Piper-Offline-Stimme“ (BLIND_USE_GAP_ANALYSIS §6) und Teil der
bestehenden Lizenz-Dokumentation (vgl. LICENSE, THIRD_PARTY_NOTICES.md).

## Komponenten

| Komponente | Version/Release | Quelle | Lizenz |
| --- | --- | --- | --- |
| Piper (Binär) | 2023.11.14-2 | https://github.com/rhasspy/piper/releases (statisches `piper_linux_x86_64.tar.gz`) | MIT |
| Stimmodell `de_DE-thorsten-medium` | — | https://huggingface.co/rhasspy/piper-voices (`de/de_DE/thorsten/medium/`) | CC0 |
| Trainingsdatensatz Thorsten-Voice | — | https://github.com/thorstenMueller/Thorsten-Voice | CC0 |

Warum keine Debian-Pakete: Debian 13 (trixie) enthält kein Piper-TTS-Paket
(das Paket „piper“ in trixie ist eine GTK-Anwendung zum Konfigurieren von
Gaming-Mäusen, thematisch und lizenztechnisch unabhängig). Binary und Modell
werden deshalb zur Image-Bauzeit heruntergeladen und per SHA-256 gepinnt —
nie zur Laufzeit (das OS muss beim ersten Start ohne Netz sprechen können).

## Piper-Code (MIT)

Piper von Rhasspy steht unter der MIT-Lizenz
(https://github.com/rhasspy/piper/blob/master/LICENSE). Das Release-Archiv
`piper_linux_x86_64.tar.gz` (Release 2023.11.14-2) enthält das statische
`piper`-Binary, `piper_phonemize`, gebündelte Bibliotheken und
espeak-ng-Daten. Es wird nach `/opt/piper` entpackt (Hook
`packaging/live-build/config/hooks/normal/021-clausis-piper.hook.chroot`).

SHA-256 des Release-Archivs (selbst erhoben, da Upstream keine Checksummen
veröffentlicht):

    a50cb45f355b7af1f6d758c1b360717877ba0a398cc8cbe6d2a7a3a26e225992

## Stimmodell de_DE-thorsten-medium (CC0)

Das Modell basiert auf dem Thorsten-Voice-Datensatz von Thorsten Müller
(https://github.com/thorstenMueller/Thorsten-Voice), der ausdrücklich CC0
(„public domain dedication“) ist; die MODEL_CARD des Modells in
rhasspy/piper-voices nennt Dataset und Lizenz CC0. Nach deutschem Recht ist
an CC0-Daten die Gemeinfreiheit per Rechtskraft nicht vollständig herstellbar;
CC0 ist hier die weitestmögliche Freigabe und für Weitergabe und Einbettung
in Clausis ausreichend geklärt. Die Stimme ist eine männliche deutsche
Einzelstimme (22.050 Hz, ~63 MB Medium-Qualität; das High-Modell wäre ~77 MB
und bliebe als Upgrade-Pfad offen, siehe BLIND §6).

SHA-256 (identisch mit dem von Hugging Face dokumentierten LFS-Objekt-Hash):

    de_DE-thorsten-medium.onnx      7e64762d8e5118bb578f2eea6207e1a35a8e0c30595010b666f983fc87bb7819
    de_DE-thorsten-medium.onnx.json 974adee790533adb273a1ac88f49027d2a1b8f0f2cf4905954a4791e79264e85

Beide Hashes sind im Build-Hook und in `src/clausis/piper_tts.py` gepinnt;
der Build bricht bei Abweichung ab. Die Herkunft der Modelldatei wurde am
2026-08-26 heruntergeladen und gegen den LFS-Hash verifiziert.

## Integrität und Aktualisierung

- Alle Pins (URLs + SHA-256) leben in `src/clausis/piper_tts.py`; der
  Build-Hook trägt dieselben Werte (ein Unit-Test bricht die CI, wenn sie
  auseinanderlaufen).
- Ein Update von Piper oder Modell = neue Version + neue Hashes in
  `piper_tts.py` und Hook, Lizenzprüfung erneut (Modell-Lizenz einzeln
  klären und hier nennen), dieser Datei eine neue Zeile hinzufügen.
- `speech-dispatcher` selbst (GPL) und `espeak-ng` bleiben Debian-Pakete;
  deren Lizenzen gelten unverändert (siehe THIRD_PARTY_NOTICES.md).
