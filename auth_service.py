from db import fetch_df


# -----------------------------------------------------------------------------
# Standard-/Demo-Logins
# -----------------------------------------------------------------------------
# Diese Benutzer funktionieren unabhängig von der Datenbank-Tabelle T_USER.
# Dadurch könnt ihr die App mit festen Rollen testen/vorführen:
#   Benutzername: Sachbearbeiter | Fachkraft | Teamleiter
#   Passwort:    Sopra123
#
# Hinweis: Für ein Produktivsystem sollte man solche festen Passwörter entfernen
# und ausschließlich Benutzer aus der Datenbank verwenden.
_STANDARD_LOGINS = {
    "sachbearbeiter": "Sopra123",
    "fachkraft": "Sopra123",
    "teamleiter": "Sopra123",
}


def _ist_standard_login(username, passwort):
    """Prüft die festen Standard-/Demo-Logins, unabhängig von Groß-/Kleinschreibung beim Benutzernamen."""
    if username is None or passwort is None:
        return False

    benutzer = str(username).strip().lower()
    return _STANDARD_LOGINS.get(benutzer) == str(passwort)


def pruefe_login(username, passwort):
    """
    Prüft Benutzername und Passwort.

    1) Zuerst werden die Standard-/Demo-Logins geprüft:
       - Sachbearbeiter / Sopra123
       - Fachkraft / Sopra123
       - Teamleiter / Sopra123

    2) Falls keiner davon passt, wird wie bisher gegen dbo.T_USER geprüft.
    """
    if _ist_standard_login(username, passwort):
        return True

    sql = """
        SELECT COUNT(*) AS Treffer
        FROM dbo.T_USER
        WHERE USERNAME = ?
          AND USERPASS = ?
    """
    ergebnis = fetch_df(sql, (username, passwort))
    return int(ergebnis["Treffer"].iloc[0]) > 0


def get_user_level(username):
    """
    Liest den SecurityLevel des Benutzers über die in der Datenbank
    vorhandene Funktion dbo.fn_get_user_securitylevel (Quelle:
    T_USER.SECURITYLEVEL). Gibt 0 zurück, wenn nichts gefunden wird.

    Dieses Level steuert über permissions.py / berechtigungen.json,
    welche Aktionen ein Benutzer ausführen darf.
    """
    df = fetch_df("SELECT dbo.fn_get_user_securitylevel(?) AS Level", (username,))
    if df.empty:
        return 0
    wert = df["Level"].iloc[0]
    return int(wert) if wert is not None else 0
