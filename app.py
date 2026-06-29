import streamlit as st

from views import login
from views import offene_auftraege
from views import lieferschein
from views import pickliste
from views import eventlog
from permissions import level_name
from styles import apply_design


st.set_page_config(
    page_title="Lager & Versand – SoPra G06",
    page_icon="📦",
    layout="wide",
)

# Gemeinsames Design laden (rein optisch, ändert keine Funktion)
apply_design()


# -----------------------------------------------------------------------------
# Login-Schranke
# Wenn niemand angemeldet ist, zeigen wir nur die Login-Seite und stoppen hier.
# -----------------------------------------------------------------------------
if not st.session_state.get("eingeloggt", False):
    login.anzeigen()
    st.stop()


# Ab hier ist sicher jemand angemeldet.
benutzer = st.session_state["benutzer"]
level = st.session_state["level"]


# -----------------------------------------------------------------------------
# Seitenleiste: Marke, Benutzer, Navigation
# (rein gestalterisch – dieselbe Navigation und derselbe Logout wie zuvor)
# -----------------------------------------------------------------------------
with st.sidebar:
    st.markdown(
        "<div class='app-brand'>"
        "<span class='app-brand-icon'>📦</span>"
        "<span class='app-brand-text'>Lager &amp; Versand"
        "<small>SoPra · Gruppe 06</small></span>"
        "</div>",
        unsafe_allow_html=True,
    )
    st.markdown(
        f"<div class='user-card'>"
        f"<div class='user-name'>{benutzer}</div>"
        f"<div class='user-role'>{level_name(level)} · Level {level}</div>"
        f"</div>",
        unsafe_allow_html=True,
    )

ICONS = {
    "Aufträge": "📦",
    "Picklisten": "✅",
    "Lieferscheine": "🚚",
    "Eventlog": "🕓",
}

seite = st.sidebar.radio(
    "Navigation",
    ["Aufträge","Picklisten", "Lieferscheine", "Eventlog"],
    format_func=lambda s: f"{ICONS[s]}\u2002\u2002{s}",
    label_visibility="collapsed",
)

st.sidebar.markdown("<div style='height:14px'></div>", unsafe_allow_html=True)

# Logout: Session leeren und neu laden -> landet wieder auf der Login-Seite
if st.sidebar.button("Abmelden", use_container_width=True):
    st.session_state.clear()
    st.rerun()


# -----------------------------------------------------------------------------
# Hauptbereich
# -----------------------------------------------------------------------------
if seite == "Aufträge":
    offene_auftraege.anzeigen()

elif seite == "Picklisten":
    pickliste.anzeigen()

elif seite == "Lieferscheine":
    lieferschein.anzeigen()

elif seite == "Eventlog":
    eventlog.anzeigen()