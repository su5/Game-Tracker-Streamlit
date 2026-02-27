import streamlit as st
import sqlite3
import pandas as pd
import random
from datetime import datetime, timedelta

# --- 1. DATABASE CORE ---
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
    """Generates the 12-person roster and 200 matches."""
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
        c.execute("INSERT INTO matches (game, date, time, winners, losers, notes) VALUES (?,?,?,?,?,?)",
                  (g, d, "20:00", winner, ", ".join(losers), "Simulated Data"))
    conn.commit()

create_tables()

# --- 2. THEME & UI ---
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
    h1, h2, h3, h4 {{ color: {t['accent']} !important; font-weight: 800 !important; }}
    .stMarkdown p, label, .stText {{ color: {t['text']} !important; font-weight: 600; }}
    .glass-card {{
        background: {t['card']}; padding: 20px; border-radius: 20px;
        border: 1px solid {t['border']}; margin-bottom: 15px;
    }}
    .inventory-list {{
        max-height: 250px; overflow-y: auto; background: rgba(0,0,0,0.2); 
        border-radius: 10px; padding: 15px; border: 1px solid {t['border']};
        font-family: monospace; color: {t['accent']};
    }}
    .streak-val {{ font-size: 26px; font-weight: 800; color: #FF4B2B; }}
    .stButton>button {{
        border-radius: 12px; font-weight: 700; background: {t['accent']}; color: black; border: none;
    }}
    </style>
    """, unsafe_allow_html=True)

# --- 3. ANALYTICS ---
def get_top_streaks():
    df = pd.read_sql_query("SELECT game, winners, date FROM matches ORDER BY date ASC", conn)
    if df.empty: return []
    streaks = []
    for game in df['game'].unique():
        g_df = df[df['game'] == game]
        curr_p, count = None, 0
        for _, row in g_df.iterrows():
            if row['winners'] == curr_p: count += 1
            else:
                if curr_p and count >= 2: streaks.append({"p": curr_p, "g": game, "c": count})
                curr_p, count = row['winners'], 1
        if curr_p and count >= 2: streaks.append({"p": curr_p, "g": game, "c": count})
    return sorted(streaks, key=lambda x: x['c'], reverse=True)[:3]

# --- 4. NAVIGATION ---
tabs = st.tabs(["🏠 HOME", "📝 RECORD", "📋 LOG ARCHIVE", "➕ REGISTER", "⚙️ SETTINGS"])

with tabs[0]: # HOME
    st.header("Dashboard")
    streaks = get_top_streaks()
    if streaks:
        s_cols = st.columns(3)
        for i, s in enumerate(streaks):
            with s_cols[i]:
                st.markdown(f'<div class="glass-card" style="border:1px solid #FF4B2B; text-align:center;"><div style="font-size:11px; color:{t["sub"]}">{s["g"].upper()}</div><div class="streak-val">{s["p"]}</div><div style="font-weight:700;">{s["c"]} WIN STREAK</div></div>', unsafe_allow_html=True)

    col_l, col_r = st.columns([2, 1])
    with col_l:
        st.subheader("Leaderboards")
        df_stats = pd.read_sql_query("SELECT game, winners, losers FROM matches", conn)
        if not df_stats.empty:
            for g in sorted(df_stats['game'].unique()):
                with st.expander(f"🏆 {g.upper()}"):
                    players = [r[0] for r in c.execute("SELECT name FROM players").fetchall()]
                    g_m = df_stats[df_stats['game'] == g]
                    res = []
                    for p in players:
                        w = len(g_m[g_m['winners'].str.contains(p, na=False)])
                        l = len(g_m[g_m['losers'].str.contains(p, na=False)])
                        if (w+l) > 0: res.append({"Player": p, "W": w, "L": l, "Ratio": f"{(w/(w+l))*100:.0f}%"})
                    st.table(pd.DataFrame(res).sort_values("W", ascending=False))
    with col_r:
        st.subheader("Recent")
        recent = pd.read_sql_query("SELECT game, winners, losers, date FROM matches ORDER BY id DESC LIMIT 10", conn)
        for _, row in recent.iterrows():
            st.markdown(f'<div class="glass-card"><div style="display:flex; justify-content:space-between;"><b>{row["game"]}</b><small>{row["date"]}</small></div><div style="color:{t["accent"]}; margin: 5px 0;">Winner: {row["winners"]}</div><div style="font-size:0.75rem; color:{t["sub"]}">Played: {row["winners"]}, {row["losers"]}</div></div>', unsafe_allow_html=True)

with tabs[1]: # RECORD
    st.header("Record Result")
    st.markdown('<div class="glass-card">', unsafe_allow_html=True)
    all_g = [r[0] for r in c.execute("SELECT title FROM games ORDER BY title").fetchall()]
    all_p = [r[0] for r in c.execute("SELECT name FROM players ORDER BY name").fetchall()]
    c1, c2 = st.columns(2)
    with c1: rg_game = st.selectbox("Game", all_g)
    with c2: rg_date = st.date_input("Date", datetime.now())
    p_in = st.multiselect("Participants", all_p)
    if p_in:
        st.divider()
        win_p, loss_p, scores = [], [], {}
        for p in p_in:
            st.markdown(f"**{p}**")
            col1, col2, col3 = st.columns([1,1,2])
            with col1: is_w = st.checkbox("Win", key=f"win_{p}")
            with col2: is_l = st.checkbox("Loss", key=f"loss_{p}", value=not is_w)
            with col3: scores[p] = st.text_input("Score", key=f"scr_{p}")
            if is_w: win_p.append(p)
            if is_l: loss_p.append(p)
        if st.button("ARCHIVE BATTLE"):
            s_str = ", ".join([f"{k}:{v}" for k,v in scores.items() if v])
            c.execute("INSERT INTO matches (game, date, time, winners, losers, scores) VALUES (?,?,?,?,?,?)",
                      (rg_game, str(rg_date), "20:00", ", ".join(win_p), ", ".join(loss_p), s_str))
            conn.commit(); st.toast("Logged!", icon="⚔️"); st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

with tabs[2]: # ARCHIVE
    st.header("Match History")
    all_logs = pd.read_sql_query("SELECT * FROM matches ORDER BY id DESC", conn)
    edit_id = st.selectbox("Modify ID", all_logs['id'].tolist())
    if edit_id:
        row = all_logs[all_logs['id'] == edit_id].iloc[0]
        with st.form("edit_form"):
            e_win = st.text_input("Winners", row['winners'])
            e_loss = st.text_input("Losers", row['losers'])
            if st.form_submit_button("Update"):
                c.execute("UPDATE matches SET winners=?, losers=? WHERE id=?", (e_win, e_loss, edit_id))
                conn.commit(); st.rerun()
            if st.form_submit_button("🗑️ Delete Entry"):
                c.execute("DELETE FROM matches WHERE id=?", (edit_id,))
                conn.commit(); st.rerun()
    st.dataframe(all_logs, use_container_width=True, hide_index=True)

with tabs[3]: # REGISTER
    st.header("Expand Roster")
    cur_p = [r[0] for r in c.execute("SELECT name FROM players ORDER BY name").fetchall()]
    cur_g = [r[0] for r in c.execute("SELECT title FROM games ORDER BY title").fetchall()]
    
    col_a, col_b = st.columns(2)
    with col_a:
        st.markdown('<div class="glass-card">', unsafe_allow_html=True)
        st.subheader("👤 New Player")
        p_in = st.text_input("Player Name", key="p_reg")
        if p_in:
            if p_in.lower() in [x.lower() for x in cur_p]: st.error("❌ Already Registered")
            else:
                st.success("✅ Unique Name")
                if st.button("Add Player"):
                    c.execute("INSERT INTO players VALUES (?)", (p_in.strip(),))
                    conn.commit(); st.rerun()
        st.write("---")
        st.write(f"**Current Players ({len(cur_p)})**")
        st.markdown(f'<div class="inventory-list">{"<br>".join(cur_p)}</div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)
    with col_b:
        st.markdown('<div class="glass-card">', unsafe_allow_html=True)
        st.subheader("🎮 New Game")
        g_in = st.text_input("Game Title", key="g_reg")
        if g_in:
            if g_in.lower() in [x.lower() for x in cur_g]: st.error("❌ Already in Library")
            else:
                st.success("✅ New Game")
                if st.button("Add Game"):
                    c.execute("INSERT INTO games VALUES (?)", (g_in.strip(),))
                    conn.commit(); st.rerun()
        st.write("---")
        st.write(f"**Game Library ({len(cur_g)})**")
        st.markdown(f'<div class="inventory-list">{"<br>".join(cur_g)}</div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

with tabs[4]: # SETTINGS
    st.header("Vault Settings")
    st.markdown('<div class="glass-card">', unsafe_allow_html=True)
    if st.button("🌙 Toggle Light/Dark"):
        st.session_state.theme = "dark" if st.session_state.theme == "light" else "light"
        st.rerun()
    st.divider()
    exp_df = pd.read_sql_query("SELECT * FROM matches", conn)
    st.download_button("📥 Export CSV", data=exp_df.to_csv(index=False).encode('utf-8'), file_name="arena.csv")
    imp_f = st.file_uploader("📤 Import CSV", type="csv")
    if imp_f and st.button("Confirm Merge"):
        pd.read_csv(imp_f).to_sql('matches', conn, if_exists='append', index=False)
        st.success("Merged!"); st.rerun()
    st.divider()
    if st.button("🚨 FACTORY RESET", type="primary"):
        run_bootstrap(); st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)