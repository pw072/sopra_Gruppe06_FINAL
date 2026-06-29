import streamlit as st

import pagination
from pickliste_service import (
    get_picklisten,
    get_pickliste_details,
    get_erlaubte_pickliste_status,
    pickliste_status_aendern,
)
from permissions import can


ANZEIGE_SPALTEN = [
    "PicklistenID",
    "KundenauftragID",
    "Picklistenstatus",
    "Kommissionierer",
]

# PICKSTATUS: 171 = PICKED (darf erst gesetzt werden, wenn alles abgehakt ist)
PICK_PICKED = 171


def anzeigen():
    st.header("Pickliste")
    st.write("Hier werden alle Picklisten angezeigt.")

    benutzer = st.session_state.get("benutzer", "UNKNOWN")
    level = st.session_state.get("level", 0)

    try:
        picklisten = get_picklisten()

        if picklisten.empty:
            st.info("Es gibt aktuell keine Picklisten.")
            return

        # =====================================================================
        # Übersicht: Suche + Sortierung + Tabelle (mit Seiten) + Zeilenauswahl
        # =====================================================================
        st.subheader("Übersicht")

        such_spalte1, such_spalte2, such_spalte3 = st.columns(3)
        with such_spalte1:
            such_pickliste = st.text_input("PicklistenID", key="pl_f_pickliste")
        with such_spalte2:
            such_auftrag = st.text_input("KundenauftragID", key="pl_f_auftrag")
        with such_spalte3:
            such_kommissionierer = st.text_input("Kommissionierer", key="pl_f_komm")

        sort_spalte, richtung_spalte = st.columns(2)
        with sort_spalte:
            sortieren_nach = st.selectbox(
                "Sortieren nach",
                ["PicklistenID", "KundenauftragID", "Picklistenstatus", "Kommissionierer"]
            )
        with richtung_spalte:
            reihenfolge = st.radio(
                "Reihenfolge",
                ["Aufsteigend", "Absteigend"],
                horizontal=True
            )

        gefiltert = picklisten.copy()
        if such_pickliste:
            gefiltert = gefiltert[gefiltert["PicklistenID"].astype(str).str.contains(such_pickliste, na=False)]
        if such_auftrag:
            gefiltert = gefiltert[gefiltert["KundenauftragID"].astype(str).str.contains(such_auftrag, na=False)]
        if such_kommissionierer:
            gefiltert = gefiltert[gefiltert["Kommissionierer"].astype(str).str.contains(such_kommissionierer, case=False, na=False)]

        aufsteigend = (reihenfolge == "Aufsteigend")
        gefiltert = gefiltert.sort_values(by=sortieren_nach, ascending=aufsteigend)

        if gefiltert.empty:
            st.info("Keine Pickliste gefunden. Bitte Suche anpassen.")
            return

        seiten_gesamt = pagination.anzahl_seiten(len(gefiltert))
        seite = pagination.aktuelle_seite("seite_pickliste", seiten_gesamt)
        start = (seite - 1) * pagination.SEITENGROESSE
        seiten_daten = gefiltert.iloc[start:start + pagination.SEITENGROESSE]

        tabellen_key = f"tab_pl_s{seite}_{such_pickliste}_{such_auftrag}_{such_kommissionierer}_{sortieren_nach}_{reihenfolge}"
        auswahl = st.dataframe(
            seiten_daten[ANZEIGE_SPALTEN],
            use_container_width=True,
            hide_index=True,
            on_select="rerun",
            selection_mode="single-row",
            key=tabellen_key
        )

        pagination.navigation("seite_pickliste", seite, seiten_gesamt)

        # =====================================================================
        # Detailansicht: zeigt die in der Tabelle ausgewählte Pickliste
        # =====================================================================
        st.subheader("Detailansicht")

        if not auswahl.selection["rows"]:
            st.info("Bitte in der Tabelle eine Zeile anklicken, um die Pickliste zu öffnen.")
            return

        position = auswahl.selection["rows"][0]
        gewaehlt = seiten_daten.iloc[position]

        details = get_pickliste_details(int(gewaehlt["PicklistenID"]))
        kopf_daten = details.iloc[0]
        pickliste_id = int(kopf_daten["PicklistenID"])

        st.write(f"**Pickliste:** {kopf_daten['PicklistenID']}")
        st.write(f"**Kundenauftrag:** {kopf_daten['KundenauftragID']}")
        st.write(f"**Status:** {kopf_daten['Picklistenstatus']}")
        st.write(f"**Kommissionierer:** {kopf_daten['Kommissionierer']}")

        # =====================================================================
        # Kommissionier-Checkliste: links neben jedem Artikel ein Häkchen.
        # Ist die Pickliste schon PICKED, sind alle Häkchen vorab gesetzt und
        # die Liste ist nur noch lesend.
        # =====================================================================
        ist_picked = "PICKED" in str(kopf_daten["Picklistenstatus"]).upper()
        checkliste_aktiv = can(level, "change_pickliste_status") and not ist_picked

        positionen = details[["Artikelnummer", "Artikelbezeichnung", "Menge"]].copy()
        positionen.insert(0, "Erledigt", ist_picked)

        st.write("**Positionen – jeden kommissionierten Artikel abhaken:**")
        bearbeitet = st.data_editor(
            positionen,
            hide_index=True,
            use_container_width=True,
            # Nur die Häkchen-Spalte ist editierbar; ist die Liste nicht aktiv,
            # ist alles schreibgeschützt (disabled=True).
            disabled=(["Artikelnummer", "Artikelbezeichnung", "Menge"]
                      if checkliste_aktiv else True),
            column_config={
                "Erledigt": st.column_config.CheckboxColumn(
                    "✓", help="Artikel kommissioniert / abgehakt", width="small"
                ),
                "Artikelnummer": st.column_config.TextColumn("Artikelnummer"),
                "Artikelbezeichnung": st.column_config.TextColumn("Artikelbezeichnung"),
                "Menge": st.column_config.NumberColumn("Menge"),
            },
            key=f"pick_check_{pickliste_id}",
        )

        anzahl = len(bearbeitet)
        anzahl_erledigt = int(bearbeitet["Erledigt"].sum()) if anzahl > 0 else 0
        alle_abgehakt = anzahl > 0 and anzahl_erledigt == anzahl

        st.caption(f"{anzahl_erledigt} von {anzahl} Artikeln abgehakt.")

        # --- Status ändern ---
        st.subheader("Status ändern")

        # 1) Grobe Berechtigung: Darf diese Rolle den Pickstatus überhaupt ändern?
        if not can(level, "change_pickliste_status"):
            st.info("Ihre Rolle darf den Pickstatus nicht ändern (nur Ansicht).")
            return

        # 2) Feine Prüfung aus der DB: erlaubte Folgestatus (nach Level gefiltert).
        erlaubte = get_erlaubte_pickliste_status(pickliste_id, level)

        if erlaubte.empty:
            st.info(
                "Für diese Pickliste gibt es aktuell keinen erlaubten Folgestatus "
                "(oder Ihr Level reicht für die möglichen Übergänge nicht aus)."
            )
            return

        erlaubte = erlaubte.copy()
        erlaubte["Anzeige"] = (
            erlaubte["CODE_NEXT_ID"].astype(str) + " - " + erlaubte["STATUS_NEXT"]
        )

        neuer_status_label = st.selectbox(
            "Neuer Status",
            list(erlaubte["Anzeige"]),
            key=f"status_pickliste_{pickliste_id}"
        )

        zeile = erlaubte[erlaubte["Anzeige"] == neuer_status_label]
        neuer_status_id = int(zeile["CODE_NEXT_ID"].iloc[0])

        # PICKED (171) erst erlauben, wenn ALLE Artikel abgehakt sind.
        speichern_gesperrt = (neuer_status_id == PICK_PICKED and not alle_abgehakt)
        if speichern_gesperrt:
            st.warning(
                "Bitte zuerst alle Artikel abhaken. Erst dann kann die Pickliste "
                "auf PICKED gesetzt werden."
            )

        if st.button(
            "Status speichern",
            key=f"btn_status_pickliste_{pickliste_id}",
            disabled=speichern_gesperrt,
        ):
            try:
                pickliste_status_aendern(
                    pickliste_id=pickliste_id,
                    neuer_status_id=neuer_status_id,
                    benutzer=benutzer
                )
                st.toast(f"Status wurde auf {neuer_status_label} geändert.")
                st.rerun()
            except Exception as fehler:
                st.error("Der Status konnte nicht geändert werden.")
                st.exception(fehler)

    except Exception as fehler:
        st.error("Die Picklisten konnten nicht geladen werden.")
        st.exception(fehler)