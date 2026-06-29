import math
import streamlit as st

SEITENGROESSE = 10   # Einträge pro Seite


def anzahl_seiten(gesamt):
    """Wie viele Seiten ergeben sich aus der Gesamtzahl der Einträge?"""
    return max(1, math.ceil(gesamt / SEITENGROESSE))


def aktuelle_seite(seite_key, seiten_gesamt):
    """
    Liest die aktuelle Seite aus dem Session State und begrenzt sie
    auf einen gültigen Bereich (1 .. seiten_gesamt).
    """
    seite = st.session_state.get(seite_key, 1)
    if seite < 1:
        seite = 1
    if seite > seiten_gesamt:
        seite = seiten_gesamt
    return seite


def navigation(seite_key, seite, seiten_gesamt):
    """
    Zeigt unten die Seiten-Navigation: Zurück, Seitenzahlen, Weiter.
    Beim Klick wird die neue Seite gespeichert und die Seite neu geladen.
    """
    st.write(f"Seite {seite} von {seiten_gesamt}")

    # Ein Fenster von höchstens 5 Seitenzahlen rund um die aktuelle Seite
    von = max(1, seite - 2)
    bis = min(seiten_gesamt, von + 4)
    von = max(1, bis - 4)
    zahlen = list(range(von, bis + 1))

    spalten = st.columns(len(zahlen) + 2)

    # Zurück
    if spalten[0].button("◀", key=f"{seite_key}_prev", disabled=(seite <= 1)):
        st.session_state[seite_key] = seite - 1
        st.rerun()

    # Seitenzahlen (die aktuelle Seite ist als Knopf deaktiviert = hervorgehoben)
    for i, nummer in enumerate(zahlen):
        if spalten[i + 1].button(
            str(nummer),
            key=f"{seite_key}_p{nummer}",
            disabled=(nummer == seite)
        ):
            st.session_state[seite_key] = nummer
            st.rerun()

    # Weiter
    if spalten[-1].button("▶", key=f"{seite_key}_next", disabled=(seite >= seiten_gesamt)):
        st.session_state[seite_key] = seite + 1
        st.rerun()