import streamlit as st

from eventlog_service import get_eventlog


def anzeigen():
    st.header("Eventlog")
    st.write("Hier werden die letzten Änderungen im System angezeigt.")

    # Filter: nur Einträge einer bestimmten Tabelle anzeigen
    tabelle = st.selectbox(
        "Tabelle filtern",
        ["Alle", "T_DELIVERY", "T_PICKLISTE", "T_SALESORDER"]
    )

    try:
        eintraege = get_eventlog(tabelle)

        if eintraege.empty:
            st.info("Es sind keine Einträge vorhanden.")
            return

        st.dataframe(eintraege, use_container_width=True)

    except Exception as fehler:
        st.error("Das Eventlog konnte nicht geladen werden.")
        st.exception(fehler)