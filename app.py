import streamlit as st
import sqlite3
import pandas as pd
import random
import io
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
    demo_players = ["Clay", "Henry", "Thomas", "Monica", "Clarence", "James", 
                    "Pappa", "Tassy", "Wes", "Kat", "Ingrid", "Ansel"]
    demo_games = ["Catan", "Magic", "Mario Kart", "Monopoly", "Poker", "Go Fish"]
    for p in demo_players: c.execute("INSERT INTO players VALUES (?)", (p,))
    for g in demo_games: c.execute("INSERT INTO games VALUES (?)", (g,))
    for _ in range(200):
        g = random.choice(demo_games)
        p_sample = random.sample(demo_players, random.randint(2, 6))
        winner = random.choice(p_sample)
        losers = [p for p in p_sample if p != winner]
        d = (datetime.now() - timedelta(days=random.randint(0, 180))).strftime("%Y-%m-%d")
        c.execute('''INSERT INTO matches (game, date, time, winners, losers) VALUES (?,?,?,?,?)''',
                  (g, d, "20:00", winner, ", ".join(losers)))
    conn.commit()

create_tables()

# --- 2. THEME & UI STATE ---
if 'theme' not in st.session_state:
    st.session_state.theme = "dark"

t = {
    "dark": {"bg": "#0B0E14", "card": "#1C2128", "text": "#FFFFFF", "accent": "#00FFAA", "sub": "#8B949E", "border": "rgba(255,255,255,0.1)"},
    "light": {"bg": "#F0F2F5", "card": "#FFFFFF", "text": "#1C1E21", "accent": "#007AFF", "sub": "#65676B", "border": "rgba(0,0,0,0.05)"}
}[st.session_state.theme]

st.set_page_config(page_title="Arena Vault", layout="wide")

st.markdown(f"""
    <style>
    .stApp {{ background-color: {t['bg']}; color: {t['text']}; }}
    h1, h2, h3 {{ color: {t['accent']} !important; font-weight: 800 !important; }}
    .glass-card {{
        background: {t['card']}; padding: 20px; border-radius: 20px;
        border: 1px solid {t['border']}; margin-bottom: 15px;
    }}
    .streak-val {{ font-size: 26px; font-weight: 800; color: #FF4B2B; }}
    .stButton>button {{ border-radius: 12px; font-weight: 700; background: {t['accent']}; color: black; border: none; }}
    </style>
    """, unsafe_allow_html=True)

# --- 3. ANALYTICS HELPERS ---
def get_top_streaks():
    df = pd.read_sql_query("SELECT game, winners, date FROM matches ORDER BY date ASC", conn)
    if df.empty: return []
    streaks = []
    for game in df['game'].unique():
        g_df = df[df['game'] == game]
        curr_p, count, start_d = None, 0, None
        for _, row in g_df.iterrows():
            if row['winners'] == curr_p: count += 1
            else:
                if curr_p and count >= 2:
                    streaks.append({"p": curr_p, "g": game, "c": count})
                curr_p, count, start_d = row['winners'], 1, row['date']
        if curr_p and count >= 2: streaks.append({"p": curr_p, "g": game, "c": count})
    return sorted(streaks, key=lambda x: x['c'], reverse=True)[:3]

# --- 4. NAVIGATION ---
tabs = st.tabs(["🏠 HOME", "📝 RECORD", "📋 ALL LOGS", "➕ REGISTER", "⚙️ SETTINGS"])

with tabs[0]: # HOME
    st.header("Dashboard")
    streaks = get_top_streaks()
    if streaks:
        s_cols = st.columns(3)
        for i, s in enumerate(streaks):
            with s_cols[i]:
                st.markdown(f'<div class="glass-card" style="border:1px solid #FF4B2B; text-align:center;"><div style="font-size:11px; color:{t["sub"]}">{s["g"]}</div><div class="streak-val">{s["p"]}</div><div style="font-weight:700">{s["c"]} WINS</div></div>', unsafe_allow_html=True)

    col_l, col_r = st.columns([2, 1])
    with col_l:
        st.subheader("Leaderboards")
        df_stats = pd.read_sql_query("SELECT game, winners, losers FROM matches", conn)
        if not df_stats.empty:
            for g in sorted(df_stats['game'].unique()):
                with st.expander(f"{g.upper()}"):
                    players = [r[0] for r in c.execute("SELECT name FROM players").fetchall()]
                    g_df = df_stats[df_stats['game'] == g]
                    res = []
                    for p in players:
                        w = len(g_df[g_df['winners'].str.contains(p, na=False)])
                        l = len(g_df[g_df['losers'].str.contains(p, na=False)])
                        if (w+l)>0: res.append({"Player": p, "W": w, "L": l, "Ratio": f"{(w/(w+l))*100:.0f}%"})
                    st.table(pd.DataFrame(res).sort_values("W", ascending=False))

    with col_r:
        st.subheader("Recent")
        recent = pd.read_sql_query("SELECT game, winners, losers, date FROM matches ORDER BY id DESC LIMIT 10", conn)
        for _, row in recent.iterrows():
            participants = f"{row['winners']}, {row['losers']}"
            st.markdown(f"""<div class="glass-card"><b>{row['game']}</b><br><small>{row['date']}</small><br>
                <span style="color:{t['accent']}">Winner: {row['winners']}</span><br>
                <small style="color:{t['sub']}">Played: {participants}</small></div>""", unsafe_allow_html=True)

with tabs[2]: # ALL LOGS (VIEW & EDIT)
    st.header("Log Archive")
    all_logs = pd.read_sql_query("SELECT * FROM matches ORDER BY id DESC", conn)
    
    selected_id = st.selectbox("Select Match ID to Edit/Delete", all_logs['id'].tolist())
    if selected_id:
        match_data = all_logs[all_logs['id'] == selected_id].iloc[0]
        with st.form("edit_form"):
            new_g = st.selectbox("Game", [r[0] for r in c.execute("SELECT title FROM games").fetchall()], index=0)
            new_w = st.text_input("Winners", match_data['winners'])
            new_l = st.text_input("Losers", match_data['losers'])
            col_eb1, col_eb2 = st.columns(2)
            if col_eb1.form_submit_button("Update Match"):
                c.execute("UPDATE matches SET game=?, winners=?, losers=? WHERE id=?", (new_g, new_w, new_l, selected_id))
                conn.commit(); st.rerun()
            if col_eb2.form_submit_button("🗑️ Delete Match"):
                c.execute("DELETE FROM matches WHERE id=?", (selected_id,))
                conn.commit(); st.rerun()
    st.dataframe(all_logs, use_container_width=True)

with tabs[4]: # SETTINGS
    st.header("Settings")
    if st.button("Toggle Theme"):
        st.session_state.theme = "dark" if st.session_state.theme == "light" else "light"
        st.rerun()

    st.subheader("Data Export/Import")
    # EXPORT
    full_df = pd.read_sql_query("SELECT * FROM matches", conn)
    csv = full_df.to_csv(index=False).encode('utf-8')
    st.download_button("📥 Export Logs to CSV", data=csv, file_name=f"arena_logs_{datetime.now().strftime('%Y%m%d')}.csv", mime='text/csv')
    
    # IMPORT
    uploaded_file = st.file_uploader("📤 Import Logs from CSV", type="csv")
    if uploaded_file is not None:
        if st.button("Confirm Import"):
            import_df = pd.read_csv(uploaded_file)
            import_df.to_sql('matches', conn, if_exists='append', index=False)
            st.success("Data imported successfully!"); st.rerun()

    st.divider()
    if st.button("🚨 FACTORY RESET", type="primary"):
        run_bootstrap(); st.rerun()