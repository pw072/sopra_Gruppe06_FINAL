# -----------------------------------------------------------------------------
# Berechtigungen über das Sicherheitslevel (datengetrieben)
#
# - Welches Level ein Benutzer hat, steht in berechtigungen.json:
#     * benutzer_level : einzelne Benutzer mit abweichendem Level (Overrides)
#     * standard_level : Level für alle übrigen Benutzer (Standard: 1 = Sachbearbeiter)
#   So ändert man die Rolle eines Benutzers ohne Code-Änderung und ohne
#   Schreibrechte auf die Datenbank - einfach die JSON pflegen.
#
# - Welche Aktion welches Mindest-Level braucht, steht ebenfalls in
#   berechtigungen.json (aktion_min_level). Auch das ist reine Datenpflege.
#
# - Statuswechsel werden zusätzlich in der DB über T_CODE_NEXT.SECURITY_LEVEL
#   geprüft; hier geht es nur darum, ob die Bereiche/Buttons sichtbar sind.
# -----------------------------------------------------------------------------

import json
import os


# Sichere Standardwerte, falls die JSON-Datei fehlt oder fehlerhaft ist.
_STANDARD = {
    "standard_level": 1,
    "benutzer_level": {},
    "aktion_min_level": {
        "create_delivery": 2,
        "create_picklist": 2,
        "change_delivery_status": 2,
        "change_pickliste_status": 2,
        "complete_order": 3,
        "cancel_order": 3,
    },
    "level_namen": {
        "1": "Sachbearbeiter",
        "2": "Fachkraft",
        "3": "Teamleiter",
    },
}

# Mögliche Dateinamen (Groß-/Kleinschreibung), damit die Konfiguration auch auf
# Systemen mit beachteter Schreibweise sicher gefunden wird.
_DATEINAMEN = ("berechtigungen.json", "Berechtigungen.json")


def _config():
    """Liest die Konfiguration aus berechtigungen.json (oder nimmt Standardwerte)."""
    ordner = os.path.dirname(__file__)
    for name in _DATEINAMEN:
        pfad = os.path.join(ordner, name)
        if os.path.exists(pfad):
            try:
                with open(pfad, encoding="utf-8") as datei:
                    return json.load(datei)
            except Exception:
                return _STANDARD
    return _STANDARD


def level_fuer_benutzer(username):
    """
    Bestimmt das Berechtigungslevel eines Benutzers aus berechtigungen.json.

    - Steht der Benutzer unter "benutzer_level", gilt dieses Level.
    - Sonst gilt "standard_level" (Standard: 1 = Sachbearbeiter).

    Der Abgleich ist unabhängig von Groß-/Kleinschreibung.
    """
    cfg = _config()
    try:
        standard = int(cfg.get("standard_level", 1))
    except (TypeError, ValueError):
        standard = 1

    if not username:
        return standard

    overrides = cfg.get("benutzer_level", {}) or {}
    gesucht = str(username).strip().lower()
    for name, lvl in overrides.items():
        if str(name).strip().lower() == gesucht:
            try:
                return int(lvl)
            except (TypeError, ValueError):
                return standard
    return standard


def can(level, action):
    """True, wenn das Sicherheitslevel hoch genug für die Aktion ist."""
    schwellen = _config().get("aktion_min_level", {})
    # Unbekannte Aktion: sicherheitshalber sperren (sehr hohes Level verlangen)
    noetiges_level = schwellen.get(action, 999)
    try:
        return int(level) >= int(noetiges_level)
    except (TypeError, ValueError):
        return False


def level_name(level):
    """Anzeigename (Rolle) zum Level (oder generisch 'Level X')."""
    namen = _config().get("level_namen", {})
    return namen.get(str(level), f"Level {level}")