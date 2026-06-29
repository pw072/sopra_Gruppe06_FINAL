from datetime import date
from db import fetch_df, execute_scalar, execute_non_query


def get_kundenauftraege(modus="Offen"):
    """
    Lädt Kundenaufträge je nach Modus:
      "Offen" / "Released" -> nur Kundenaufträge mit Status RELEASED
      "Completed"           -> Status COMPLETED (73)

    Zusätzlich pro Auftrag:
      LieferscheinID         -> ID des (neuesten) Lieferscheins, falls vorhanden
      Lieferstatus           -> lesbarer Status des Lieferscheins
      LieferscheinStatusCode -> Roh-Code (intern für die COMPLETED-Regel)
    """
    if modus == "Completed":
        where = "so.SO_STATUS = 73"
    else:
        # Kundenauftragsseite: Es sollen nur freigegebene Aufträge erscheinen.
        # Vorher wurden alle nicht abgeschlossenen/nicht stornierten Aufträge geladen,
        # dadurch waren z. B. auch OFFEN und INVOICE CREATED sichtbar.
        where = "UPPER(LTRIM(RTRIM(ISNULL(lso.ORDER_STATUS, '')))) = 'RELEASED'"

    sql = f"""
        SELECT
            so.ORDER_ID AS KundenauftragID,
            c.COMPANY_NAME AS Kunde,
            ISNULL(lso.ORDER_STATUS, CAST(so.SO_STATUS AS NVARCHAR(50))) AS Auftragsstatus,
            COUNT(soi.ORDER_ITEM_ID) AS AnzahlPositionen,
            (
                SELECT TOP 1 d.DELIVERY_ID
                FROM dbo.T_DELIVERY d
                WHERE d.ORDER_ID = so.ORDER_ID
                ORDER BY d.DELIVERY_ID DESC
            ) AS LieferscheinID,
            (
                SELECT TOP 1 COALESCE(lsd.DELIVERY_STATUS, CAST(d.STATUS AS NVARCHAR(50)))
                FROM dbo.T_DELIVERY d
                LEFT JOIN dbo.LOV_STATUS_DELIVERY lsd
                    ON TRY_CONVERT(INT, d.STATUS) = lsd.CODE_ID
                WHERE d.ORDER_ID = so.ORDER_ID
                ORDER BY d.DELIVERY_ID DESC
            ) AS Lieferstatus,
            (
                SELECT TOP 1 d.STATUS
                FROM dbo.T_DELIVERY d
                WHERE d.ORDER_ID = so.ORDER_ID
                ORDER BY d.DELIVERY_ID DESC
            ) AS LieferscheinStatusCode,
            (
                SELECT TOP 1 p.PICKLISTE_ID
                FROM dbo.T_G06_PICKLISTE p
                WHERE p.ORDER_ID = so.ORDER_ID
                ORDER BY p.PICKLISTE_ID DESC
            ) AS PicklistenID
        FROM dbo.T_SALESORDER so

        INNER JOIN dbo.T_SALESORDER_ITEMS soi
            ON so.ORDER_ID = soi.ORDER_ID

        LEFT JOIN dbo.LOV_STATUS_ORDER lso
            ON so.SO_STATUS = lso.CODE_ID

        LEFT JOIN dbo.T_SALESOFFER sf
            ON so.SALESOFFER_ID = sf.SALESOFFER_ID

        LEFT JOIN dbo.T_CUSTOMER c
            ON sf.CUSTOMER_ID = c.CUSTOMER_ID

        WHERE {where}

        GROUP BY
            so.ORDER_ID,
            c.COMPANY_NAME,
            lso.ORDER_STATUS,
            so.SO_STATUS,
            so.INS_DATE

        ORDER BY
            so.INS_DATE DESC,
            so.ORDER_ID DESC
    """

    return fetch_df(sql)


def get_kundenauftrag_positionen(order_id):
    sql = """
        SELECT
            soi.ORDER_ITEM_ID AS Position,
            m.MAT_NR AS Artikelnummer,
            m.MAT_DESCR AS Artikelbezeichnung,
            soi.QUANTITY AS Menge,
            m.MAT_STOCK_AMOUNT AS Lagerbestand,
            CASE
                WHEN m.MAT_STOCK_AMOUNT >= soi.QUANTITY THEN 'Ja'
                ELSE 'Nein'
            END AS VollstaendigVerfuegbar
        FROM dbo.T_SALESORDER_ITEMS soi

        INNER JOIN dbo.T_MATERIAL m
            ON soi.MAT_ID = m.ID_MAT

        WHERE soi.ORDER_ID = ?

        ORDER BY soi.ORDER_ITEM_ID
    """

    return fetch_df(sql, (order_id,))


def lieferschein_aus_auftrag_erstellen(order_id, benutzer):
    sql = """
        DECLARE @neue_delivery_id INT;

        EXEC stored_proc.sp_ins_G06_delivery_from_order
            @order_id = ?,
            @delivery_date = ?,
            @caller = ?,
            @delivery_id = @neue_delivery_id OUTPUT;

        SELECT @neue_delivery_id AS DELIVERY_ID;
    """

    neue_delivery_id = execute_scalar(
        sql,
        (
            order_id,
            date.today(),
            benutzer
        )
    )

    return neue_delivery_id


# -----------------------------------------------------------------------------
# Lieferscheine anzeigen
# -----------------------------------------------------------------------------

def get_lieferscheine():
    """Eine Zeile pro Lieferschein (nur Kopfdaten) für die Übersicht."""
    sql = """
        SELECT DISTINCT
            LieferscheinID,
            KundenauftragID,
            Kundenfirma,
            Lieferdatum,
            Lieferstatus
        FROM list_views.V_LIST_G06_LIEFERSCHEIN
        ORDER BY LieferscheinID DESC
    """
    return fetch_df(sql)


def get_lieferschein_details(lieferschein_id):
    """Alle Daten zu einem Lieferschein, inklusive Positionen."""
    sql = """
        SELECT
            LieferscheinID,
            KundenauftragID,
            Kundenfirma,
            Ansprechpartner,
            Lieferadresse_Strasse,
            Lieferadresse_PLZ,
            Lieferadresse_Ort,
            Lieferadresse_Bundesland,
            Absenderadresse,
            Lieferdatum,
            Lieferstatus,
            Artikelnummer,
            Artikelbezeichnung,
            Menge
        FROM list_views.V_LIST_G06_LIEFERSCHEIN
        WHERE LieferscheinID = ?
        ORDER BY Artikelnummer
    """
    return fetch_df(sql, (lieferschein_id,))


# -----------------------------------------------------------------------------
# Lieferschein-Status ändern (level-basiert)
# -----------------------------------------------------------------------------

def get_erlaubte_lieferschein_status(delivery_id, user_level):
    """
    Liefert die erlaubten Folgestatus eines Lieferscheins, gefiltert nach dem
    SecurityLevel des Benutzers.

    Quelle ist die vorhandene View LOV_STATUS_FOLGE, die genau das abbildet,
    was in T_CODE_NEXT (inkl. SECURITY_LEVEL) hinterlegt ist. Wir liefern nur
    echte Folgestatus (kein Übergang auf sich selbst), deren benötigtes Level
    das Benutzer-Level nicht übersteigt.

    Rückgabespalten: CODE_NEXT_ID, STATUS_NEXT, SECURITY_LEVEL
    """
    sql = """
        SELECT f.CODE_NEXT_ID, f.STATUS_NEXT, f.SECURITY_LEVEL
        FROM dbo.LOV_STATUS_FOLGE f
        WHERE f.CODE_TYPE = 'DELIVERYSTATUS'
          AND f.CODE_ID = (
                SELECT TRY_CONVERT(INT, STATUS)
                FROM dbo.T_DELIVERY
                WHERE DELIVERY_ID = ?
          )
          AND f.CODE_ID <> f.CODE_NEXT_ID
          AND f.SECURITY_LEVEL <= ?
        ORDER BY f.CODE_NEXT_ID
    """
    return fetch_df(sql, (delivery_id, user_level))


def lieferschein_status_aendern(delivery_id, neuer_status_id, benutzer):
    """
    Ruft sp_upd_G06_delivery_status auf.
    Die Prüfung der erlaubten Statusfolge passiert zusätzlich in der Prozedur.
    """
    sql = """
        EXEC stored_proc.sp_upd_G06_delivery_status
            @delivery_id = ?,
            @newstatus_id = ?,
            @caller = ?;
    """
    execute_non_query(
        sql,
        (
            delivery_id,
            neuer_status_id,
            benutzer
        )
    )


# -----------------------------------------------------------------------------
# Auftragsstatus ändern (73 = COMPLETED, 74 = CANCELED)
# -----------------------------------------------------------------------------

def kundenauftrag_status_aendern(order_id, neuer_status_id, benutzer):
    """
    Setzt den Status eines Kundenauftrags in T_SALESORDER.
    Die Regel (COMPLETED nur bei DELIVERED) und die Level-Prüfung passieren
    in der Ansicht, bevor diese Funktion aufgerufen wird.
    """
    sql = """
        UPDATE dbo.T_SALESORDER
        SET SO_STATUS = ?,
            UPD_USER = ?,
            UPD_DATE = GETDATE()
        WHERE ORDER_ID = ?
    """
    execute_non_query(
        sql,
        (
            neuer_status_id,
            benutzer,
            order_id
        )
    )


# -----------------------------------------------------------------------------
# Material-Nachbuchung (Bestand / Reservierung) beim Lieferschein-Statuswechsel
#
# Hintergrund:
#   Die Prozedur stored_proc.sp_upd_G06_delivery_status bucht den BESTAND
#   (MAT_STOCK_AMOUNT) bereits selbst:
#     - IN TRANSIT (52)   -> Bestand wird reduziert (+ Eintrag T_STOCK_MOVEMENTS)
#     - RETOURNIERT (68)  -> Bestand wird wieder erhöht
#   Sie prüft außerdem, dass der Bestand nicht negativ wird (Abbruch bei
#   zu wenig Bestand). Diese Prozedur dürfen wir nicht ändern.
#
#   Was dort FEHLT, ist die RESERVIERUNG (MAT_RESERVATIONS). Die ergänzen wir
#   hier über die vorhandene Prozedur dbo.sp_upd_material_reservierung:
#     - FREIGABE -> MAT_RESERVATIONS wird reduziert
#   Wir geben höchstens so viel frei, wie reserviert ist (nie unter 0).
# -----------------------------------------------------------------------------

# Status-Codes (DELIVERYSTATUS) für die Material-Logik
DELIVERY_IN_TRANSIT = 52
DELIVERY_DELIVERED = 65
DELIVERY_CANCELED = 66
DELIVERY_RETOURNIERT = 68


def get_lieferschein_material_mengen(delivery_id):
    """
    Liefert je Material die Gesamtmenge der Lieferpositionen sowie den aktuellen
    Bestand und die aktuelle Reservierung. Basis ist T_DELIVERY_ITEM
    (= Auftragsmengen, da keine Teillieferungen).
    """
    sql = """
        SELECT
            di.ID_MAT AS MatId,
            m.MAT_NR AS Artikelnummer,
            m.MAT_DESCR AS Bezeichnung,
            SUM(di.QUANTITY) AS Menge,
            ISNULL(m.MAT_RESERVATIONS, 0) AS Reserviert,
            ISNULL(m.MAT_STOCK_AMOUNT, 0) AS Bestand
        FROM dbo.T_DELIVERY_ITEM di
        INNER JOIN dbo.T_MATERIAL m ON di.ID_MAT = m.ID_MAT
        WHERE di.DELIVERY_ID = ?
        GROUP BY di.ID_MAT, m.MAT_NR, m.MAT_DESCR, m.MAT_RESERVATIONS, m.MAT_STOCK_AMOUNT
        ORDER BY m.MAT_NR
    """
    return fetch_df(sql, (delivery_id,))


def reservierung_freigeben(delivery_id, benutzer):
    """
    Gibt die Reservierungen der Lieferpositionen frei
    (dbo.sp_upd_material_reservierung, Aktion 'FREIGABE' -> MAT_RESERVATIONS sinkt).

    Es wird je Material höchstens so viel freigegeben, wie aktuell reserviert ist,
    damit MAT_RESERVATIONS nicht unter 0 fällt.

    Rückgabe: Liste von Dicts mit Artikelnummer, bestellter Menge und tatsächlich
    freigegebener Menge.
    """
    mengen = get_lieferschein_material_mengen(delivery_id)
    ergebnis = []
    for _, zeile in mengen.iterrows():
        mat_id = int(zeile["MatId"])
        menge = int(zeile["Menge"])
        reserviert = int(zeile["Reserviert"])
        freigabe = min(menge, max(reserviert, 0))   # nie unter 0
        if freigabe > 0:
            execute_non_query(
                "EXEC dbo.sp_upd_material_reservierung @action = ?, @mat_id = ?, @amount = ?",
                ("FREIGABE", mat_id, freigabe),
            )
        ergebnis.append({
            "Artikelnummer": zeile["Artikelnummer"],
            "Menge": menge,
            "Freigegeben": freigabe,
        })
    return ergebnis


def material_nachbuchung(delivery_id, neuer_status_id, benutzer):
    """
    Führt nach einem erfolgreichen Lieferschein-Statuswechsel die nötige
    Material-Nachbuchung aus und gibt eine Bestätigungsmeldung (str) zurück
    (oder None, wenn für diesen Status nichts zu tun ist).

    - IN TRANSIT (52): Bestand wurde bereits von der Status-Prozedur reduziert;
      hier zusätzlich die Reservierung freigeben.
    - CANCELED (66):   nur Reservierung freigeben (Bestand bleibt unverändert).
    - RETOURNIERT (68): Bestand wurde bereits von der Status-Prozedur erhöht;
      hier nur die Bestätigungsmeldung.
    """
    neuer_status_id = int(neuer_status_id)

    if neuer_status_id == DELIVERY_IN_TRANSIT:
        freigaben = reservierung_freigeben(delivery_id, benutzer)
        teile = [
            f"{f['Artikelnummer']}: Bestand -{f['Menge']}, Reservierung -{f['Freigegeben']}"
            for f in freigaben
        ]
        return "Warenausgang gebucht – Bestand und Reservierung aktualisiert. " + "; ".join(teile)

    if neuer_status_id == DELIVERY_CANCELED:
        freigaben = reservierung_freigeben(delivery_id, benutzer)
        teile = [f"{f['Artikelnummer']}: Reservierung -{f['Freigegeben']}" for f in freigaben]
        return "Lieferung storniert – Reservierung freigegeben. " + "; ".join(teile)

    if neuer_status_id == DELIVERY_RETOURNIERT:
        mengen = get_lieferschein_material_mengen(delivery_id)
        teile = [f"{r['Artikelnummer']}: Bestand +{int(r['Menge'])}" for _, r in mengen.iterrows()]
        return "Retoure gebucht – Bestand wieder erhöht. " + "; ".join(teile)

    return None