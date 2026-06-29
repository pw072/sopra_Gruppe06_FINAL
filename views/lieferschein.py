import streamlit as st
import pandas as pd

import pagination
from delivery_service import (
    get_lieferscheine,
    get_lieferschein_details,
    get_erlaubte_lieferschein_status,
    lieferschein_status_aendern,
    material_nachbuchung,
)
from permissions import can


ANZEIGE_SPALTEN = [
    "LieferscheinID",
    "KundenauftragID",
    "Kundenfirma",
    "Lieferdatum",
    "Lieferstatus",
]

# Status-Codes (DELIVERYSTATUS)
DELIVERY_IN_TRANSIT = 52
DELIVERY_DELIVERED = 65
DELIVERY_CANCELED = 66
DELIVERY_RETOURNIERT = 68


# -----------------------------------------------------------------------------
# Spediteur-Popup (Modal)
# Wird ausgelöst, sobald ein Lieferschein auf IN TRANSIT gesetzt wurde.
# Simuliert den Spediteur: "Delivered" oder "Retoure".
# -----------------------------------------------------------------------------
@st.dialog("Spediteur")
def spediteur_dialog(delivery_id, benutzer):
    st.write("Konnte die Lieferung zugestellt werden?")

    spalte_links, spalte_rechts = st.columns(2)

    with spalte_links:
        if st.button("Delivered", key="sped_delivered", use_container_width=True):
            try:
                # IN TRANSIT -> DELIVERED (keine Bestands-/Reservierungsänderung)
                lieferschein_status_aendern(
                    delivery_id=delivery_id,
                    neuer_status_id=DELIVERY_DELIVERED,
                    benutzer=benutzer,
                )
                st.session_state.pop("spediteur_delivery_id", None)
                st.session_state["ls_bestaetigung"] = "Lieferung als zugestellt (DELIVERED) gebucht."
                st.rerun()
            except Exception as fehler:
                st.error("Konnte nicht auf DELIVERED gesetzt werden.")
                st.exception(fehler)

    with spalte_rechts:
        if st.button("Retoure", key="sped_retoure", use_container_width=True):
            try:
                # Retoure ist in der DB nur als DELIVERED -> RETOURNIERT erlaubt.
                # Daher zuerst auf DELIVERED, dann auf RETOURNIERT setzen.
                # Beim Schritt auf RETOURNIERT erhöht die Prozedur den Bestand wieder.
                lieferschein_status_aendern(
                    delivery_id=delivery_id,
                    neuer_status_id=DELIVERY_DELIVERED,
                    benutzer=benutzer,
                )
                lieferschein_status_aendern(
                    delivery_id=delivery_id,
                    neuer_status_id=DELIVERY_RETOURNIERT,
                    benutzer=benutzer,
                )
                # Bestätigung mit Bestandsbuchung (RETOURNIERT erhöht den Bestand)
                meldung = material_nachbuchung(delivery_id, DELIVERY_RETOURNIERT, benutzer)
                st.session_state.pop("spediteur_delivery_id", None)
                st.session_state["ls_bestaetigung"] = meldung or "Lieferung als Retoure (RETOURNIERT) gebucht."
                st.rerun()
            except Exception as fehler:
                st.error("Die Retoure konnte nicht gebucht werden.")
                st.exception(fehler)


def anzeigen():
    st.header("Lieferscheine")

    benutzer = st.session_state.get("benutzer", "UNKNOWN")
    level = st.session_state.get("level", 0)

    # Bestätigungsmeldung nach einem Statuswechsel (übersteht das st.rerun)
    if "ls_bestaetigung" in st.session_state:
        st.success(st.session_state.pop("ls_bestaetigung"))

    # Spediteur-Popup anzeigen, falls eine Lieferung gerade auf IN TRANSIT
    # gesetzt wurde. Die ID steht im Session State; das Popup bleibt offen,
    # bis "Delivered" oder "Retoure" gewählt wurde.
    if "spediteur_delivery_id" in st.session_state:
        spediteur_dialog(st.session_state["spediteur_delivery_id"], benutzer)

    try:
        lieferscheine = get_lieferscheine()

        if lieferscheine.empty:
            st.info("Es gibt aktuell keine Lieferscheine.")
            return

        # =====================================================================
        # Übersicht: Suche + Sortierung + Tabelle (mit Seiten) + Zeilenauswahl
        # =====================================================================
        st.subheader("Übersicht")

        such_spalte1, such_spalte2, such_spalte3 = st.columns(3)
        with such_spalte1:
            such_kunde = st.text_input("Kundenname", key="ls_f_kunde")
        with such_spalte2:
            such_auftrag = st.text_input("KundenauftragID", key="ls_f_auftrag")
        with such_spalte3:
            such_lieferschein = st.text_input("LieferscheinID", key="ls_f_lieferschein")

        sort_spalte, richtung_spalte = st.columns(2)
        with sort_spalte:
            sortieren_nach = st.selectbox(
                "Sortieren nach",
                ["LieferscheinID", "KundenauftragID", "Kundenfirma", "Lieferdatum", "Lieferstatus"]
            )
        with richtung_spalte:
            reihenfolge = st.radio(
                "Reihenfolge",
                ["Aufsteigend", "Absteigend"],
                horizontal=True
            )

        gefiltert = lieferscheine.copy()
        if such_kunde:
            gefiltert = gefiltert[gefiltert["Kundenfirma"].str.contains(such_kunde, case=False, na=False)]
        if such_auftrag:
            gefiltert = gefiltert[gefiltert["KundenauftragID"].astype(str).str.contains(such_auftrag, na=False)]
        if such_lieferschein:
            gefiltert = gefiltert[gefiltert["LieferscheinID"].astype(str).str.contains(such_lieferschein, na=False)]

        aufsteigend = (reihenfolge == "Aufsteigend")
        gefiltert = gefiltert.sort_values(by=sortieren_nach, ascending=aufsteigend)

        if gefiltert.empty:
            st.info("Kein Lieferschein gefunden. Bitte Suche anpassen.")
            return

        seiten_gesamt = pagination.anzahl_seiten(len(gefiltert))
        seite = pagination.aktuelle_seite("seite_lieferschein", seiten_gesamt)
        start = (seite - 1) * pagination.SEITENGROESSE
        seiten_daten = gefiltert.iloc[start:start + pagination.SEITENGROESSE]

        tabellen_key = f"tab_ls_s{seite}_{such_kunde}_{such_auftrag}_{such_lieferschein}_{sortieren_nach}_{reihenfolge}"
        auswahl = st.dataframe(
            seiten_daten[ANZEIGE_SPALTEN],
            use_container_width=True,
            hide_index=True,
            on_select="rerun",
            selection_mode="single-row",
            key=tabellen_key
        )

        pagination.navigation("seite_lieferschein", seite, seiten_gesamt)

        # =====================================================================
        # Detailansicht: zeigt den in der Tabelle ausgewählten Lieferschein
        # =====================================================================
        st.subheader("Detailansicht")

        if not auswahl.selection["rows"]:
            st.info("Bitte in der Tabelle eine Zeile anklicken, um den Lieferschein zu öffnen.")
            return

        position = auswahl.selection["rows"][0]
        gewaehlt = seiten_daten.iloc[position]

        details = get_lieferschein_details(int(gewaehlt["LieferscheinID"]))
        kopf_daten = details.iloc[0]

        spalte_links, spalte_rechts = st.columns(2)

        with spalte_links:
            st.write(f"**Lieferschein:** {kopf_daten['LieferscheinID']}")
            st.write(f"**Kundenauftrag:** {kopf_daten['KundenauftragID']}")
            st.write(f"**Kunde:** {kopf_daten['Kundenfirma']}")
            st.write(f"**Ansprechpartner:** {kopf_daten['Ansprechpartner']}")
            st.write(f"**Status:** {kopf_daten['Lieferstatus']}")
            st.write(f"**Lieferdatum:** {kopf_daten['Lieferdatum']}")

        with spalte_rechts:
            st.write("**Lieferadresse:**")
            st.write(kopf_daten["Lieferadresse_Strasse"])
            st.write(f"{kopf_daten['Lieferadresse_PLZ']} {kopf_daten['Lieferadresse_Ort']}")
            st.write(kopf_daten["Lieferadresse_Bundesland"])
            st.write("**Absenderadresse:**")
            st.write(kopf_daten["Absenderadresse"])

        st.write("**Positionen:**")
        st.dataframe(
            details[["Artikelnummer", "Artikelbezeichnung", "Menge"]],
            use_container_width=True
        )

        # --- Status ändern ---
        st.subheader("Status ändern")

        # 1) Grobe Berechtigung: Darf diese Rolle Lieferstatus überhaupt ändern?
        if not can(level, "change_delivery_status"):
            st.info("Ihre Rolle darf den Lieferstatus nicht ändern (nur Ansicht).")
            return

        # 2) Feine Prüfung aus der DB: erlaubte Folgestatus (LOV_STATUS_FOLGE),
        #    bereits nach dem SecurityLevel des Benutzers gefiltert.
        erlaubte = get_erlaubte_lieferschein_status(
            int(kopf_daten["LieferscheinID"]), level
        )

        if erlaubte.empty:
            st.info(
                "Für diesen Lieferschein gibt es aktuell keinen erlaubten Folgestatus "
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
            key=f"status_lieferschein_{kopf_daten['LieferscheinID']}"
        )

        if st.button(
            "Status speichern",
            key=f"btn_status_lieferschein_{kopf_daten['LieferscheinID']}"
        ):
            zeile = erlaubte[erlaubte["Anzeige"] == neuer_status_label]
            neuer_status_id = int(zeile["CODE_NEXT_ID"].iloc[0])

            try:
                delivery_id = int(kopf_daten["LieferscheinID"])

                # 1) Statuswechsel (die G06-Prozedur bucht den Bestand selbst)
                lieferschein_status_aendern(
                    delivery_id=delivery_id,
                    neuer_status_id=neuer_status_id,
                    benutzer=benutzer
                )

                # 2) Material-Nachbuchung (Reservierung) + Bestätigungstext
                meldung = material_nachbuchung(delivery_id, neuer_status_id, benutzer)
                if meldung:
                    st.session_state["ls_bestaetigung"] = meldung
                else:
                    st.session_state["ls_bestaetigung"] = f"Status wurde auf {neuer_status_label} geändert."

                # 3) Bei IN TRANSIT zusätzlich das Spediteur-Popup auslösen
                if neuer_status_id == DELIVERY_IN_TRANSIT:
                    st.session_state["spediteur_delivery_id"] = delivery_id

                st.rerun()
            except Exception as fehler:
                st.error("Der Status konnte nicht geändert werden.")
                st.exception(fehler)

    except Exception as fehler:
        st.error("Die Lieferscheine konnten nicht geladen werden.")
        st.exception(fehler)