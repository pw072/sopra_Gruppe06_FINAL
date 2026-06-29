import streamlit as st


def apply_design():
    """
    Lädt das gemeinsame, moderne Design (Apple-/SaaS-orientiert).

    WICHTIG: Hier wird ausschließlich das Aussehen angepasst (Farben, Abstände,
    Schrift, Karten, abgerundete Ecken). Es wird KEINE Funktionalität verändert.
    Diese Funktion wird einmal in app.py aufgerufen und gilt für alle Seiten.

    Zentrale Stellschrauben weiter unten:
      --accent  (Akzentfarbe)   --canvas (Hintergrund)   --radius (Eckenrundung)
    """
    st.markdown(
        """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

        /* =====================================================================
           Design-Variablen – hier zentral anpassbar
           ===================================================================== */
        :root {
            --accent: #2563EB;
            --accent-hover: #1D4FD7;
            --accent-soft: #EEF2FF;
            --canvas: #F4F5F7;
            --card: #FFFFFF;
            --line: #ECECEE;
            --text: #1D1D1F;
            --muted: #6B7280;
            --radius: 14px;
            --radius-sm: 10px;
            --font: 'Inter', -apple-system, BlinkMacSystemFont, "Segoe UI",
                    Roboto, Helvetica, Arial, sans-serif;
        }

        /* ---- Schrift überall ---- */
        html, body, [data-testid="stAppViewContainer"], [data-testid="stSidebar"],
        input, button, select, textarea {
            font-family: var(--font) !important;
            -webkit-font-smoothing: antialiased;
        }

        /* ---- Canvas-Hintergrund + transparenter Header ---- */
        section.main, [data-testid="stMain"] { background-color: var(--canvas); }
        [data-testid="stHeader"] { background: transparent; }

        /* ---- Inhalt als weiße Karte auf dem Canvas ---- */
        /* margin-top zieht die Karte nach oben auf Höhe der Sidebar/Navigation.
           Wenn die Karte zu hoch/zu tief sitzt, einfach diesen Wert anpassen. */
        [data-testid="stMain"] .block-container {
            max-width: 1180px;
            background: var(--card);
            border: 1px solid var(--line);
            border-radius: 20px;
            padding: 1.75rem 2.75rem 3rem;
            margin-top: -2.5rem;
            box-shadow: 0 1px 2px rgba(16,24,40,.04), 0 12px 28px rgba(16,24,40,.05);
        }

        /* Deploy- und Optionen-Button (drei Punkte) etwas weiter nach unten,
           damit sie nicht in die hochgezogene Karte ragen.
           Höhe über translateY anpassbar. */
        [data-testid="stToolbar"] { transform: translateY(0.9rem); }

        /* dünne farbige Linie ganz oben ausblenden (aufgeräumter) */
        [data-testid="stDecoration"] { display: none; }

        /* ---- Überschriften ---- */
        h1, h2, h3, h4 { color: var(--text); font-weight: 600; letter-spacing: -0.02em; }
        h1 { font-size: 1.9rem; }
        h2 { font-size: 1.4rem; margin-top: 1.4rem; }
        h3 { font-size: 1.12rem; margin-top: 1.1rem; }

        /* =====================================================================
           Sidebar: Marke, Benutzer-Karte, Navigation
           ===================================================================== */
        [data-testid="stSidebar"] {
            background: var(--card);
            border-right: 1px solid var(--line);
        }
        [data-testid="stSidebar"] .block-container,
        [data-testid="stSidebar"] > div { background: var(--card); }

        .app-brand { display:flex; align-items:center; gap:11px; padding:6px 2px 16px; }
        .app-brand-icon {
            font-size:1.35rem; background:var(--accent-soft); color:var(--accent);
            width:38px; height:38px; border-radius:11px;
            display:flex; align-items:center; justify-content:center;
        }
        .app-brand-text { font-weight:700; font-size:1.02rem; line-height:1.2; color:var(--text); }
        .app-brand-text small { display:block; font-weight:500; font-size:.72rem; color:#9499A0; margin-top:1px; }

        .user-card {
            background:var(--canvas); border:1px solid var(--line);
            border-radius:12px; padding:11px 13px; margin:2px 0 18px;
        }
        .user-name { font-weight:600; font-size:.95rem; color:var(--text); }
        .user-role {
            display:inline-block; margin-top:5px; font-size:.72rem; font-weight:600;
            color:var(--accent); background:var(--accent-soft);
            padding:2px 9px; border-radius:999px;
        }

        /* Navigations-Radio als Menü (Sidebar) */
        [data-testid="stSidebar"] [role="radiogroup"] { gap:3px; }
        [data-testid="stSidebar"] [role="radiogroup"] label {
            display:flex; align-items:center; width:100%;
            padding:9px 12px; border-radius:10px; cursor:pointer;
            transition:background .15s ease, color .15s ease;
            font-size:.94rem; color:#3A3A3C;
        }
        [data-testid="stSidebar"] [role="radiogroup"] label:hover { background:var(--canvas); }
        [data-testid="stSidebar"] [role="radiogroup"] label > div:first-child { display:none; } /* Radio-Punkt aus */
        [data-testid="stSidebar"] [role="radiogroup"] label:has(input:checked) {
            background:var(--accent-soft); color:var(--accent); font-weight:600;
        }

        /* =====================================================================
           Buttons
           ===================================================================== */
        .stButton > button {
            border-radius: var(--radius-sm);
            border: 1px solid #E2E2E5;
            background: var(--card);
            color: var(--text);
            font-weight: 500;
            padding: 0.5rem 1.15rem;
            transition: all .15s ease;
            box-shadow: none;
        }
        .stButton > button:hover { border-color:#C9C9CE; background:#FAFAFB; }
        .stButton > button:active { transform: scale(0.98); }

        .stButton > button[kind="primary"], [data-testid="stBaseButton-primary"] {
            background: var(--accent); border-color: var(--accent); color:#fff;
            box-shadow: 0 1px 2px rgba(37,99,235,.30);
        }
        .stButton > button[kind="primary"]:hover, [data-testid="stBaseButton-primary"]:hover {
            background: var(--accent-hover); border-color: var(--accent-hover); color:#fff;
        }

        /* =====================================================================
           Eingabefelder & Auswahllisten
           ===================================================================== */
        .stTextInput input, .stNumberInput input, .stDateInput input,
        [data-baseweb="select"] > div {
            border-radius: var(--radius-sm) !important;
            border: 1px solid #E2E2E5 !important;
            background: var(--card) !important;
        }
        .stTextInput input:focus, .stNumberInput input:focus,
        [data-baseweb="select"] > div:focus-within {
            border-color: var(--accent) !important;
            box-shadow: 0 0 0 3px rgba(37,99,235,.12) !important;
        }
        /* Feld-Beschriftungen dezent */
        [data-testid="stWidgetLabel"] p { font-size:.82rem; color:var(--muted); font-weight:500; }

        /* =====================================================================
           In-Page Umschalter (horizontale Radios) als Segmented Control
           ===================================================================== */
        [data-testid="stMain"] [role="radiogroup"] {
            background:#EFEFF2; padding:4px; border-radius:11px; gap:2px; width:fit-content;
        }
        [data-testid="stMain"] [role="radiogroup"] label {
            padding:5px 16px; border-radius:8px; cursor:pointer; transition:all .15s ease;
            color:#4A4A4F; font-size:.9rem; font-weight:500;
        }
        [data-testid="stMain"] [role="radiogroup"] label > div:first-child { display:none; }
        [data-testid="stMain"] [role="radiogroup"] label:has(input:checked) {
            background:var(--card); box-shadow:0 1px 2px rgba(16,24,40,.10);
            color:var(--accent); font-weight:600;
        }

        /* =====================================================================
           Tabellen, Meldungen, Dialog
           ===================================================================== */
        [data-testid="stDataFrame"] {
            border-radius: 12px; overflow: hidden; border: 1px solid var(--line);
        }
        [data-testid="stAlert"] { border-radius: 12px; border: none; }
        [data-testid="stDialog"] > div { border-radius: 18px; }

        [data-testid="stCaptionContainer"] { color: var(--muted); }
        hr { border-color: var(--line); }
        footer { visibility: hidden; }

        /* Toast etwas weicher */
        [data-testid="stToast"] { border-radius: 12px; }
        </style>
        """,
        unsafe_allow_html=True,
    )