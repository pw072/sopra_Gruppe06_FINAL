from db import fetch_df


def get_eventlog(tabelle="Alle"):
    """
    Holt die letzten 200 Einträge aus dem Eventlog, neueste zuerst.

    Wenn eine bestimmte Tabelle gewählt wurde (z. B. T_DELIVERY),
    filtern wir darauf. Bei "Alle" zeigen wir alles.
    """
    if tabelle and tabelle != "Alle":
        sql = """
            SELECT TOP (200)
                EventLogID,
                TableName AS Tabelle,
                RecordID AS DatensatzID,
                EventType AS Aktion,
                EventTime AS Zeitpunkt,
                ChangedBy AS Benutzer
            FROM dbo.T_EVENTLOG
            WHERE TableName = ?
            ORDER BY EventTime DESC
        """
        return fetch_df(sql, (tabelle,))

    sql = """
        SELECT TOP (200)
            EventLogID,
            TableName AS Tabelle,
            RecordID AS DatensatzID,
            EventType AS Aktion,
            EventTime AS Zeitpunkt,
            ChangedBy AS Benutzer
        FROM dbo.T_EVENTLOG
        ORDER BY EventTime DESC
    """
    return fetch_df(sql)