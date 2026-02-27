import streamlit as st
import sqlite3
import pandas as pd
import random
from datetime import datetime, timedelta

# --- 1. DATABASE SETUP ---
conn = sqlite3.connect('arena_vault.db', check_same_thread=False)
c = conn.cursor()

def create_tables(force_rebuild=False):
    if force_rebuild:
        c.execute('DROP TABLE IF EXISTS matches')
        c.execute('DROP TABLE IF EXISTS players')
        c.execute('DROP TABLE IF EXISTS games')
    c.execute('CREATE TABLE IF NOT EXISTS players (name TEXT PRIMARY KEY)')
    c.execute('CREATE TABLE IF NOT EXISTS games (title TEXT PRIMARY KEY)')
    c.execute('''CREATE TABLE IF NOT EXISTS matches (
                 id INTEGER PRIMARY KEY AUTOINCREMENT,
                 game TEXT, date TEXT, time TEXT, 
                 winners TEXT, losers TEXT, ties TEXT, quitters TEXT, 
                 scores TEXT, notes TEXT)''')
    conn.commit()

def run_bootstrap():
    create_tables(force_rebuild=True)
    # Your Specific Roster
    demo_players = ["Clay", "Henry", "Thomas", "Monica", "Clarence", "James", 
                    "Pappa", "Tassy", "Wes", "Kat", "Ingrid", "Ansel"]
    # Your Specific Games
    demo_games = ["Catan", "Magic", "Mario Kart", "Monopoly", "Poker", "Go Fish"]
    
    for p in demo_players: c.execute("INSERT INTO players VALUES (?)", (p,))
    for g in demo_games: c.execute("INSERT INTO games VALUES (?)", (g,))
    
    # Generate 200 Matches
    for _ in range(200):
        g = random.choice(demo_games)
        # Randomize participant count (2 to 6)
        num_p = random.randint(2, 6)
        p_sample = random.sample(demo_players, num_p)
        winner = random.choice(p_sample)
        losers = [p for p in p_sample if p != winner]
        
        # Random date within the last 6 months
        d = (datetime.now() - timedelta(days=random.randint(0, 180))).strftime("%Y-%m-%d")
        c.execute('''INSERT INTO matches (game, date, time, winners, losers) VALUES (?,?,?,?,?)''',
                  (g, d, "20:00", winner, ", ".join(losers)))
    conn.commit()

create_tables()

# --- 2. THEME & UI STATE ---
if 'theme' not in st.session_state:
    st.session_state.theme = "dark"

t = {
    "dark": {
        "bg": "#0B0E14", "card": "#1C2128", "text": "#FFFFFF", 
        "accent": "#00FFAA", "sub": "#8B949E", "border": "rgba(255,255,255,0.1)",
        "table_text": "#FFFFFF"
    },
    "light": {
        "bg": "#F0F2F5", "card": "#FFFFFF", "text": "#1C1E21", 
        "accent": "#007AFF", "sub": "#65676B", "border": "rgba(0,0,0,0.05)",
        "table_text": "#1C1E21"
    }
}[st.session_state.theme]

st.set_page_config(page_title="Arena Vault", layout="wide")

st.markdown(f"""
    <style>
    .stApp {{ background-color: {t['bg']}; color: {t['text']}; }}
    
    /* Global Text Styles */
    h1, h2, h3 {{ color: {t['accent']} !important; font-weight: 800 !important; }}
    .stMarkdown p {{ color: {t['text']}; font-weight: 500; }}
    
    /* Card Styles */
    .glass-card {{
        background: {t['card']};
        padding: 20px;
        border-radius: 20px;
        border: 1px solid {t['border']};
        margin-bottom: 15px;
    }}
    
    /* Table/Dataframe Overrides for Readability */
    [data-testid="stDataFrame"] {{ color: {t['table_text']} !important; }}
    .st-expander {{ border: 1px solid {t['border']}; border-radius: 12px; background: {t['card']}; }}

    /* Streak Card Specifics */
    .streak-val {{ font-size: 26px; font-weight: 800; color: #FF4B2B; margin: 5px 0; }}
    .streak-game {{ font-size: 11px; color: {t['sub']}; text-transform: uppercase; font-weight: bold; letter-spacing: 1px; }}
    
    .stButton>button {{ border-radius: 12px; font-weight: 700; background: {t['accent']}; color: black; border: none; }}
    </style>
    """, unsafe_allow_html=True)

# --- 3. ANALYTICS ---
def get_top_streaks():
    df = pd.read_sql_query("SELECT game, winners, date FROM matches ORDER BY date ASC", conn)
    if df.empty: return []
    streaks = []
    for game in df['game'].unique():
        g_df = df[df['game'] == game]
        curr_winner, count, start_date = None, 0, None
        for _, row in g_df.iterrows():
            if row['winners'] == curr_winner:
                count += 1
            else:
                if curr_winner and count >= 2:
                    dur = (datetime.strptime(row['date'], "%Y-%m-%d") - datetime.strptime(start_date, "%Y-%m-%d")).days
                    streaks.append({"p": curr_winner, "g": game, "c": count, "d": dur})
                curr_winner, count, start_date = row['winners'], 1, row['date']
        if curr_winner and count >= 2:
            dur = (datetime.now() - datetime.strptime(start_date, "%Y-%m-%d")).days
            streaks.append({"p": curr_winner, "g": game, "c": count, "d": dur})
    return sorted(streaks, key=lambda x: x['c'], reverse=True)[:3]

def get_stats():
    df = pd.read_sql_query("SELECT game, winners, losers FROM matches", conn)
    if df.empty: return pd.DataFrame()
    res = []
    players = [r[0] for r in c.execute("SELECT name FROM players").fetchall()]
    for g in df['game'].unique():
        g_df = df[df['game'] == g]
        for p in players:
            w = len(g_df[g_df['winners'].str.contains(p, na=False)])
            l = len(g_df[g_df['losers'].str.contains(p, na=False)])
            if (w + l) > 0:
                res.append({"Game": g, "Player": p, "W": w, "L": l, "Total": w+l, "Ratio": f"{(w/(w+l))*100:.0f}%"})
    return pd.DataFrame(res)

# --- 4. NAVIGATION ---
tabs = st.tabs(["🏠 HOME", "📝 RECORD", "➕ REGISTER", "⚙️ SETTINGS"])

with tabs[0]: # HOME
    st.header("Dashboard")
    
    # Top Streaks
    streaks = get_top_streaks()
    if streaks:
        st.markdown(f"<p style='color:{t['sub']}; font-weight:700; margin-bottom:10px;'>🔥 TOP ACTIVE STREAKS</p>", unsafe_allow_html=True)
        s_cols = st.columns(3)
        for i, s in enumerate(streaks):
            with s_cols[i]:
                st.markdown(f"""
                <div class="glass-card" style="border: 1px solid #FF4B2B; text-align: center;">
                    <div class="streak-game">{s['g']}</div>
                    <div class="streak-val">{s['p']}</div>
                    <div style="font-weight: 800; font-size: 0.9rem;">{s['c']} CONSECUTIVE WINS</div>
                    <div style="font-size: 10px; color: {t['sub']}">{s['d']} DAYS ACTIVE</div>
                </div>
                """, unsafe_allow_html=True)

    col_l, col_r = st.columns([2, 1])
    with col_l:
        st.markdown(f"<p style='color:{t['sub']}; font-weight:700;'>🏆 STANDINGS</p>", unsafe_allow_html=True)
        s_df = get_stats()
        if not s_df.empty:
            for g in sorted(s_df['Game'].unique()):
                with st.expander(f"{g.upper()} LEADERBOARD", expanded=True):
                    g_table = s_df[s_df['Game'] == g].sort_values('W', ascending=False)
                    st.dataframe(g_table[['Player', 'W', 'L', 'Total', 'Ratio']], use_container_width=True, hide_index=True)

    with col_r:
        st.markdown(f"<p style='color:{t['sub']}; font-weight:700;'>📜 RECENT</p>", unsafe_allow_html=True)
        recent = pd.read_sql_query("SELECT date, game, winners FROM matches ORDER BY id DESC LIMIT 10", conn)
        for _, row in recent.iterrows():
            st.markdown(f"""
            <div class="glass-card" style="padding: 12px; margin-bottom: 8px;">
                <div style="font-weight: 800; color:{t['accent']}">{row['game']}</div>
                <div style="font-size: 0.8rem; color:{t['sub']}">{row['date']} • Winner: <b>{row['winners']}</b></div>
            </div>
            """, unsafe_allow_html=True)

with tabs[1]: # RECORD RESULT
    st.header("Log Result")
    st.markdown('<div class="glass-card">', unsafe_allow_html=True)
    all_g = [r[0] for r in c.execute("SELECT title FROM games ORDER BY title").fetchall()]
    all_p = [r[0] for r in c.execute("SELECT name FROM players ORDER BY name").fetchall()]
    
    c1, c2 = st.columns(2)
    with c1: g_sel = st.selectbox("Game Played", all_g)
    with c2: d_sel = st.date_input("Match Date", datetime.now())
    
    p_in = st.multiselect("Who played?", all_p)
    if p_in:
        st.divider()
        win_list, loss_list, scores = [], [], {}
        for p in p_in:
            st.markdown(f"**{p}**")
            col1, col2, col3 = st.columns([1, 1, 2])
            with col1: is_w = st.checkbox("Win", key=f"rec_w_{p}")
            with col2: is_l = st.checkbox("Loss", key=f"rec_l_{p}", value=not is_w)
            with col3: scores[p] = st.text_input("Score (Opt)", key=f"rec_s_{p}")
            if is_w: win_list.append(p)
            if is_l: loss_list.append(p)
        
        if st.button("ARCHIVE MATCH"):
            s_str = ", ".join([f"{k}:{v}" for k, v in scores.items() if v])
            c.execute('''INSERT INTO matches (game, date, time, winners, losers, scores) VALUES (?,?,?,?,?,?)''',
                      (g_sel, str(d_sel), "20:00", ", ".join(win_list), ", ".join(loss_list), s_str))
            conn.commit(); st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

with tabs[2]: # REGISTER NEW
    st.header("Expansion Pack")
    st.markdown('<div class="glass-card">', unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("👤 New Player")
        p_name = st.text_input("Player Name")
        if st.button("Add to Roster") and p_name:
            c.execute("INSERT OR IGNORE INTO players VALUES (?)", (p_name.strip(),))
            conn.commit(); st.success(f"{p_name} registered!"); st.rerun()
    with c2:
        st.subheader("🎮 New Game")
        g_name = st.text_input("Game Title")
        if st.button("Add to Library") and g_name:
            c.execute("INSERT OR IGNORE INTO games VALUES (?)", (g_name.strip(),))
            conn.commit(); st.success(f"{g_name} added!"); st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

with tabs[3]: # SETTINGS
    st.header("Settings")
    if st.button("🌙 Dark Mode" if st.session_state.theme == "light" else "☀️ Light Mode"):
        st.session_state.theme = "dark" if st.session_state.theme == "light" else "light"
        st.rerun()
    st.divider()
    if st.button("🚨 FACTORY RESET & BOOTSTRAP (200 MATCHES)", type="primary"):
        run_bootstrap()
        st.rerun()