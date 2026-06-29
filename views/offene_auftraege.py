import streamlit as st
import pandas as pd

import pagination
from delivery_service import (
    get_kundenauftraege,
    get_kundenauftrag_positionen,
    lieferschein_aus_auftrag_erstellen,
    kundenauftrag_status_aendern,
)
from pickliste_service import pickliste_aus_auftrag_erstellen
from permissions import can


# Status-Codes als lesbare Namen
STATUS_COMPLETED = 73
STATUS_CANCELED = 74
DELIVERY_DELIVERED = "65"   # Lieferschein gilt als geliefert

ANZEIGE_SPALTEN = [
    "KundenauftragID",
    "LieferscheinID",
    "Kunde",
    "Auftragsstatus",
    "Lieferstatus",
    "AnzahlPositionen",
]


def anzeigen():
    st.header("Kundenaufträge")

    benutzer = st.session_state.get("benutzer", "UNKNOWN")
    level = st.session_state.get("level", 0)

    modus = st.radio(
        "Ansicht",
        ["Released", "Completed"],
        horizontal=True
    )

    try:
        daten = get_kundenauftraege(modus)
    except Exception as fehler:
        st.error("Die Kundenaufträge konnten nicht geladen werden.")
        st.exception(fehler)
        return

    if daten.empty:
        st.info("Es gibt hier aktuell keine Aufträge.")
        return

    daten["LieferscheinID"] = pd.to_numeric(
        daten["LieferscheinID"], errors="coerce"
    ).astype("Int64")

    daten["PicklistenID"] = pd.to_numeric(
        daten["PicklistenID"], errors="coerce"
    ).astype("Int64")

    # =========================================================================
    # Übersicht: Suche + Sortierung + Tabelle (mit Seiten) + Zeilenauswahl
    # =========================================================================
    st.subheader("Übersicht")

    # Suchfelder
    such_spalte1, such_spalte2, such_spalte3 = st.columns(3)
    with such_spalte1:
        such_kunde = st.text_input("Kundenname", key="f_kunde")
    with such_spalte2:
        such_auftrag = st.text_input("KundenauftragID", key="f_auftrag")
    with such_spalte3:
        such_lieferschein = st.text_input("LieferscheinID", key="f_lieferschein")

    # Sortierung
    sort_spalte, richtung_spalte = st.columns(2)
    with sort_spalte:
        sortieren_nach = st.selectbox(
            "Sortieren nach",
            ["KundenauftragID", "Kunde", "Auftragsstatus", "AnzahlPositionen", "LieferscheinID"]
        )
    with richtung_spalte:
        reihenfolge = st.radio(
            "Reihenfolge",
            ["Aufsteigend", "Absteigend"],
            horizontal=True
        )

    # Filtern
    gefiltert = daten.copy()
    if such_kunde:
        gefiltert = gefiltert[gefiltert["Kunde"].str.contains(such_kunde, case=False, na=False)]
    if such_auftrag:
        gefiltert = gefiltert[gefiltert["KundenauftragID"].astype(str).str.contains(such_auftrag, na=False)]
    if such_lieferschein:
        gefiltert = gefiltert[gefiltert["LieferscheinID"].astype(str).str.contains(such_lieferschein, na=False)]

    # Sortieren
    aufsteigend = (reihenfolge == "Aufsteigend")
    gefiltert = gefiltert.sort_values(by=sortieren_nach, ascending=aufsteigend)

    if gefiltert.empty:
        st.info("Kein Auftrag gefunden. Bitte Suche anpassen.")
        return

    # Seiten berechnen und aktuellen Ausschnitt bilden
    seiten_gesamt = pagination.anzahl_seiten(len(gefiltert))
    seite = pagination.aktuelle_seite("seite_auftraege", seiten_gesamt)
    start = (seite - 1) * pagination.SEITENGROESSE
    seiten_daten = gefiltert.iloc[start:start + pagination.SEITENGROESSE]

    # Tabelle mit Zeilenauswahl (Klick auf eine Zeile = bearbeiten)
    tabellen_key = f"tab_auftraege_{modus}_s{seite}_{such_kunde}_{such_auftrag}_{such_lieferschein}_{sortieren_nach}_{reihenfolge}"
    auswahl = st.dataframe(
        seiten_daten[ANZEIGE_SPALTEN],
        use_container_width=True,
        hide_index=True,
        on_select="rerun",
        selection_mode="single-row",
        key=tabellen_key
    )

    # Seiten-Navigation unten
    pagination.navigation("seite_auftraege", seite, seiten_gesamt)

    # =========================================================================
    # Bearbeiten: zeigt den in der Tabelle ausgewählten Auftrag
    # =========================================================================
    st.subheader("Bearbeiten")

    if modus == "Completed":
        st.info("Abgeschlossene Aufträge können hier nur eingesehen werden.")

    if not auswahl.selection["rows"]:
        st.info("Bitte in der Tabelle eine Zeile anklicken, um den Auftrag zu öffnen.")
        return

    position = auswahl.selection["rows"][0]
    auftrag = seiten_daten.iloc[position]

    order_id = int(auftrag["KundenauftragID"])
    lieferschein_id = auftrag["LieferscheinID"]
    hat_lieferschein = pd.notna(lieferschein_id)
    pickliste_id = auftrag["PicklistenID"]
    hat_pickliste = pd.notna(pickliste_id)

    st.write(f"**Kunde:** {auftrag['Kunde']}")
    st.write(f"**Kundenauftrag:** {order_id}")
    st.write(f"**Auftragsstatus:** {auftrag['Auftragsstatus']}")
    st.write(f"**Positionen:** {auftrag['AnzahlPositionen']}")
    if hat_lieferschein:
        st.write(
            f"**Lieferschein:** {int(lieferschein_id)} "
            f"(Status: {auftrag['Lieferstatus']})"
        )
    if hat_pickliste:
        st.write(f"**Pickliste:** {int(pickliste_id)}")

    positionen = get_kundenauftrag_positionen(order_id)
    st.dataframe(positionen, use_container_width=True)

    if modus != "Released":
        return

    st.markdown("**Aktionen**")

    aktion_links, aktion_rechts = st.columns(2)

    with aktion_links:
        if not can(level, "create_delivery"):
            st.caption("Lieferschein: keine Berechtigung")
        elif hat_lieferschein:
            st.caption("Lieferschein bereits vorhanden")
        else:
            if st.button("Lieferschein erstellen", key=f"btn_lieferschein_{order_id}"):
                try:
                    neue_id = lieferschein_aus_auftrag_erstellen(
                        order_id=order_id,
                        benutzer=benutzer
                    )
                    st.toast(f"Lieferschein {neue_id} für Auftrag {order_id} erstellt.")
                    st.rerun()
                except Exception as fehler:
                    st.error("Der Lieferschein konnte nicht erstellt werden.")
                    st.exception(fehler)

    with aktion_rechts:
        if not can(level, "create_picklist"):
            st.caption("Pickliste: keine Berechtigung")
        elif hat_pickliste:
            st.caption("Pickliste bereits vorhanden")
        else:
            if st.button("Pickliste erstellen", key=f"btn_pickliste_{order_id}"):
                try:
                    neue_id = pickliste_aus_auftrag_erstellen(
                        order_id=order_id,
                        kommissionierer=benutzer,
                        benutzer=benutzer
                    )
                    st.toast(f"Pickliste {neue_id} für Auftrag {order_id} erstellt.")
                    st.rerun()
                except Exception as fehler:
                    st.error("Die Pickliste konnte nicht erstellt werden.")
                    st.exception(fehler)

    moegliche_status = []
    if can(level, "complete_order"):
        moegliche_status.append("COMPLETED")
    if can(level, "cancel_order"):
        moegliche_status.append("CANCELED")

    if moegliche_status:
        lieferstatus_code = auftrag["LieferscheinStatusCode"]

        ziel_status = st.selectbox(
            "Auftragsstatus ändern auf",
            moegliche_status,
            key=f"auftragstatus_{order_id}"
        )

        if st.button("Auftragsstatus speichern", key=f"btn_auftragstatus_{order_id}"):
            if ziel_status == "COMPLETED" and str(lieferstatus_code) != DELIVERY_DELIVERED:
                st.warning(
                    "Der Auftrag kann erst auf COMPLETED gesetzt werden, "
                    "wenn der zugehörige Lieferschein den Status DELIVERED hat."
                )
            else:
                try:
                    neuer_code = (
                        STATUS_COMPLETED
                        if ziel_status == "COMPLETED"
                        else STATUS_CANCELED
                    )
                    kundenauftrag_status_aendern(
                        order_id=order_id,
                        neuer_status_id=neuer_code,
                        benutzer=benutzer
                    )
                    st.toast(f"Auftrag {order_id} wurde auf {ziel_status} gesetzt.")
                    st.rerun()
                except Exception as fehler:
                    st.error("Der Auftragsstatus konnte nicht geändert werden.")
                    st.exception(fehler)