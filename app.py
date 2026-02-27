import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime

# --- 1. DATABASE CONNECTION ---
def get_db_connection():
    return sqlite3.connect('arena_vault.db', check_same_thread=False)

conn = get_db_connection()
c = conn.cursor()
c.execute('CREATE TABLE IF NOT EXISTS players (name TEXT PRIMARY KEY)')
c.execute('CREATE TABLE IF NOT EXISTS games (title TEXT PRIMARY KEY)')
c.execute('''CREATE TABLE IF NOT EXISTS matches (
             id INTEGER PRIMARY KEY AUTOINCREMENT,
             game TEXT, date TEXT, time TEXT, winners TEXT, losers TEXT, ties TEXT, 
             scores TEXT, concluded BOOLEAN, counts BOOLEAN, quitters TEXT, duration TEXT, notes TEXT)''')
conn.commit()

# --- 2. THE "NO-FAIL" READABILITY STYLING ---
st.set_page_config(page_title="Arena Vault", layout="wide")
st.markdown("""
    <style>
    /* Absolute Black Background */
    .stApp { background-color: #000000 !important; }

    /* High-Contrast Player Header */
    .player-row {
        background-color: #FFFFFF;
        padding: 10px;
        border-radius: 5px 5px 0 0;
        margin-top: 15px;
    }
    .player-text {
        color: #000000 !important;
        font-size: 1.5rem !important;
        font-weight: 900 !important;
        text-transform: uppercase;
    }

    /* Checkbox Label Fix - This forces the text next to boxes to be WHITE and LARGE */
    div[data-testid="stCheckbox"] label p {
        color: #FFFFFF !important;
        font-size: 1.3rem !important;
        font-weight: 800 !important;
        background-color: #333333;
        padding: 5px 10px;
        border-radius: 5px;
    }

    /* Section Headers */
    .section-header {
        color: #00FFAA !important;
        font-size: 1.4rem !important;
        font-weight: 900;
        margin-top: 20px;
        border-bottom: 2px solid #00FFAA;
    }

    /* Big Green Button */
    .stButton>button {
        background: #00FFAA !important;
        color: #000000 !important;
        font-size: 1.5rem !important;
        font-weight: 900 !important;
        height: 4em;
        border: 4px solid white;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 3. LOGIC ---
menu = st.tabs(["➕ LOG MATCH", "⚙️ MANAGE", "📊 HISTORY"])

with menu[1]: # MANAGE
    st.markdown('<p class="section-header">ADD NEW ENTRIES</p>', unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    with c1:
        np = st.text_input("PLAYER NAME")
        if st.button("SAVE PLAYER") and np:
            c.execute("INSERT OR IGNORE INTO players VALUES (?)", (np.strip(),))
            conn.commit()
            st.rerun()
    with c2:
        ng = st.text_input("GAME TITLE")
        if st.button("SAVE GAME") and ng:
            c.execute("INSERT OR IGNORE INTO games VALUES (?)", (ng.strip(),))
            conn.commit()
            st.rerun()

with menu[0]: # LOG MATCH
    p_list = [r[0] for r in c.execute("SELECT name FROM players ORDER BY name").fetchall()]
    g_list = [r[0] for r in c.execute("SELECT title FROM games ORDER BY title").fetchall()]

    if not p_list or not g_list:
        st.warning("Go to MANAGE and add Players/Games first!")
    else:
        st.markdown('<p class="section-header">1. GAME & PLAYERS</p>', unsafe_allow_html=True)
        game = st.selectbox("CHOOSE GAME", g_list)
        participants = st.multiselect("CHOOSE PLAYERS", p_list)

        if participants:
            st.markdown('<p class="section-header">2. ASSIGN RESULTS</p>', unsafe_allow_html=True)
            wins, losses, ties, quits, score_map = [], [], [], [], {}

            for p in participants:
                # Player Name Header (High Contrast)
                st.markdown(f'<div class="player-row"><span class="player-text">{p}</span></div>', unsafe_allow_html=True)
                
                # Result Checkboxes with forced-color labels
                c1, c2, c3, c4 = st.columns(4)
                with c1: w = st.checkbox("WIN", key=f"w_{p}")
                with c2: l = st.checkbox("LOSS", key=f"l_{p}", disabled=w)
                with c3: t = st.checkbox("TIE", key=f"t_{p}", disabled=(w or l))
                with c4: q = st.checkbox("QUIT", key=f"q_{p}")
                
                if w: wins.append(p)
                if l: losses.append(p)
                if t: ties.append(p)
                if q: quits.append(p)
                
            st.markdown('<p class="section-header">3. TIME & DATE</p>', unsafe_allow_html=True)
            cd, ct = st.columns(2)
            m_date = cd.date_input("DATE", datetime.now())
            m_time = ct.time_input("TIME", datetime.now().time())

            with st.expander("OPTIONAL: SCORES & NOTES"):
                for p in participants:
                    score_map[p] = st.text_input(f"Score for {p}", key=f"s_{p}")
                concluded = st.toggle("FINISHED?", value=True)
                notes = st.text_area("NOTES")

            if st.button("🚀 SAVE VICTORY"):
                scores_str = ", ".join([f"{k}:{v}" for k, v in score_map.items() if v])
                c.execute('''INSERT INTO matches 
                             (game, date, time, winners, losers, ties, scores, concluded, counts, quitters, duration, notes) 
                             VALUES (?,?,?,?,?,?,?,?,?,?,?,?)''',
                          (game, str(m_date), str(m_time), ", ".join(wins), ", ".join(losses), 
                           ", ".join(ties), scores_str, concluded, True, ", ".join(quits), "", notes))
                conn.commit()
                st.success("SAVED!")
                st.rerun()

with menu[2]: # HISTORY
    st.markdown('<p class="section-header">MATCH HISTORY</p>', unsafe_allow_html=True)
    df = pd.read_sql_query("SELECT * FROM matches ORDER BY id DESC", conn)
    st.dataframe(df, use_container_width=True)