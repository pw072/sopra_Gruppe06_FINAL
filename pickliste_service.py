from db import fetch_df, execute_scalar, execute_non_query


def get_picklisten():
    """Eine Zeile pro Pickliste (nur Kopfdaten) für die Übersicht."""
    # Die View liefert die Spalte als KOMMISSIONIERER (Großschreibung). Wir
    # benennen sie auf "Kommissionierer" um, weil der UI-Code diese Schreibweise
    # erwartet (pandas ist Groß-/Kleinschreibung-sensitiv).
    sql = """
        SELECT DISTINCT
            PicklistenID,
            KundenauftragID,
            Picklistenstatus,
            KOMMISSIONIERER AS Kommissionierer
        FROM list_views.V_LIST_G06_PICKLISTE
        ORDER BY PicklistenID DESC
    """
    return fetch_df(sql)


def get_pickliste_details(pickliste_id):
    """Alle Daten zu einer Pickliste, inklusive Positionen."""
    sql = """
        SELECT
            PicklistenID,
            KundenauftragID,
            Picklistenstatus,
            KOMMISSIONIERER AS Kommissionierer,
            Artikelnummer,
            Artikelbezeichnung,
            Menge
        FROM list_views.V_LIST_G06_PICKLISTE
        WHERE PicklistenID = ?
        ORDER BY Artikelnummer
    """
    return fetch_df(sql, (pickliste_id,))


# -----------------------------------------------------------------------------
# Pickliste aus einem Kundenauftrag erstellen
# -----------------------------------------------------------------------------

def pickliste_aus_auftrag_erstellen(order_id, kommissionierer, benutzer):
    """Ruft sp_ins_G06_pickliste_from_order auf und gibt die neue Pickliste-ID zurück."""
    sql = """
        DECLARE @neue_pickliste_id INT;

        EXEC stored_proc.sp_ins_G06_pickliste_from_order
            @order_id = ?,
            @kommissionierer = ?,
            @caller = ?,
            @pickliste_id = @neue_pickliste_id OUTPUT;

        SELECT @neue_pickliste_id AS PICKLISTE_ID;
    """

    neue_pickliste_id = execute_scalar(
        sql,
        (
            order_id,
            kommissionierer,
            benutzer
        )
    )

    return neue_pickliste_id


# -----------------------------------------------------------------------------
# Pickliste-Status ändern (level-basiert)
# -----------------------------------------------------------------------------

def get_erlaubte_pickliste_status(pickliste_id, user_level):
    """
    Liefert die erlaubten Folgestatus einer Pickliste, gefiltert nach dem
    SecurityLevel des Benutzers. Quelle: View LOV_STATUS_FOLGE (basiert auf
    T_CODE_NEXT inkl. SECURITY_LEVEL).

    Rückgabespalten: CODE_NEXT_ID, STATUS_NEXT, SECURITY_LEVEL
    """
    sql = """
        SELECT f.CODE_NEXT_ID, f.STATUS_NEXT, f.SECURITY_LEVEL
        FROM dbo.LOV_STATUS_FOLGE f
        WHERE f.CODE_TYPE = 'PICKSTATUS'
          AND f.CODE_ID = (
                SELECT TRY_CONVERT(INT, STATUS)
                FROM dbo.T_G06_PICKLISTE
                WHERE PICKLISTE_ID = ?
          )
          AND f.CODE_ID <> f.CODE_NEXT_ID
          AND f.SECURITY_LEVEL <= ?
        ORDER BY f.CODE_NEXT_ID
    """
    return fetch_df(sql, (pickliste_id, user_level))


def pickliste_status_aendern(pickliste_id, neuer_status_id, benutzer):
    """
    Ruft sp_upd_G06_pickliste_status auf.
    Die Prüfung der erlaubten Statusfolge passiert zusätzlich in der Prozedur.
    """
    sql = """
        EXEC stored_proc.sp_upd_G06_pickliste_status
            @pickliste_id = ?,
            @newstatus_id = ?,
            @caller = ?;
    """
    execute_non_query(
        sql,
        (
            pickliste_id,
            neuer_status_id,
            benutzer
        )
    )