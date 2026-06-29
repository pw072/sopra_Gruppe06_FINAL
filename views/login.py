import streamlit as st

from auth_service import pruefe_login
from permissions import level_fuer_benutzer


def anzeigen():
    st.header("Anmeldung")
    st.write("Bitte mit Benutzername und Passwort anmelden.")

    username = st.text_input("Benutzername")
    passwort = st.text_input("Passwort", type="password")

    if st.button("Anmelden"):
        try:
            if pruefe_login(username, passwort):
                # Anmeldung erfolgreich -> Benutzer und Level merken.
                # Das Level kommt aus berechtigungen.json:
                #   - Benutzer in "benutzer_level" -> dort eingetragenes Level
                #   - sonst "standard_level" (Standard: 1 = Sachbearbeiter)
                st.session_state["eingeloggt"] = True
                st.session_state["benutzer"] = username
                st.session_state["level"] = level_fuer_benutzer(username)

                # Alternative, falls ihr das Level direkt aus der Datenbank
                # (T_USER.SECURITYLEVEL) nehmen wollt -- dann diese Zeile statt
                # der oberen verwenden (benötigt keine JSON-Pflege):
                #   from auth_service import get_user_level
                #   st.session_state["level"] = get_user_level(username)

                st.rerun()
            else:
                st.error("Benutzername oder Passwort ist falsch.")
        except Exception as fehler:
            st.error("Die Anmeldung konnte nicht geprüft werden.")
            st.exception(fehler)