## 2026-08-26 — GLM 5.3 via Hermes (follow-up fix, uncommittiertes WIP aus Run 24)

Der Dispatcher-Gab-up-Rest wurde manuell fertiggezogen: AT-SPI meldet die Rolle
von Gtk.ListBox in dieser GTK-Version als „list box" (ATK_ROLE_LIST_BOX, per
gtk-3-24-a11y-Quellen und Live-Bus verifiziert), nicht als „list". Die
Rollen-Menge der Listeneinheit enthält deshalb jetzt beide Schreibweisen
(frozenset({"list", "list box"})), und der Session-Client akzeptiert für den
Fokus-Check nach dem Sprung beide Rollen — sonst würde der Smoke je nach
GTK-Version den echten Listen-Sprung fälschlich als Fehler werten. Keine
Verhaltensänderung sonst; Suite 712+1019 grün, CI bleibt grün.
