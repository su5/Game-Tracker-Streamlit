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
                 winners TEXT, losers TEXT, scores TEXT, notes TEXT)''')
    conn.commit()

def run_bootstrap():
    """Wipes everything and generates the 'Papa' roster with sample matches."""
    create_tables(force_rebuild=True)
    demo_players = ["Clay", "Henry", "Thomas", "Monica", "Clarence", "James", 
                    "Papa", "Tassy", "Wes", "Kat", "Ingrid", "Ansel"]
    demo_games = ["Catan", "Magic", "Mario Kart", "Monopoly", "Poker", "Go Fish"]
    
    for p in demo_players: c.execute("INSERT INTO players VALUES (?)", (p,))
    for g in demo_games: c.execute("INSERT INTO games VALUES (?)", (g,))
    
    for _ in range(40):
        g = random.choice(demo_games)
        p_sample = random.sample(demo_players, random.randint(2, 4))
        winner = p_sample[0]
        losers = p_sample[1:]
        d = (datetime.now() - timedelta(days=random.randint(0, 30))).strftime("%Y-%m-%d")
        c.execute("INSERT INTO matches (game, date, time, winners, losers, notes) VALUES (?,?,?,?,?,?)",
                  (g, d, "12:00", winner, ", ".join(losers), "Bootstrap Data"))
    conn.commit()

create_tables()

# --- 2. UI THEME ---
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
    .stMarkdown p, label, .stText, .stSelectbox p, .stMultiSelect p {{ 
        color: {t['text']} !important; font-weight: 600 !important; 
    }}
    .glass-card {{
        background: {t['card']}; padding: 20px; border-radius: 20px;
        border: 1px solid {t['border']}; margin-bottom: 15px;
    }}
    .inventory-list {{
        max-height: 200px; overflow-y: auto; background: rgba(0,0,0,0.2); 
        border-radius: 10px; padding: 10px; border: 1px solid {t['border']};
        color: {t['accent']}; font-family: monospace;
    }}
    .stButton>button {{
        border-radius: 12px; font-weight: 700; background: {t['accent']}; color: black; border: none; width: 100%;
    }}
    .session-pill {{
        background: rgba(0, 255, 170, 0.1); border: 1px solid {t['accent']};
        padding: 5px 15px; border-radius: 50px; display: inline-block; margin-right: 10px; font-size: 0.85rem;
    }}
    </style>
    """, unsafe_allow_html=True)

# --- 3. SESSION LOGIC ---
def get_session_stats():
    """Calculates consecutive matches with same game and player group."""
    all_m = pd.read_sql_query("SELECT * FROM matches ORDER BY id DESC", conn)
    if all_m.empty: return None, [], {}
    
    last_m = all_m.iloc[0]
    target_game = last_m['game']
    target_players = set([p.strip() for p in (last_m['winners'] + "," + last_m['losers']).split(",") if p.strip()])
    
    session_matches = []
    for _, row in all_m.iterrows():
        row_players = set([p.strip() for p in (row['winners'] + "," + row['losers']).split(",") if p.strip()])
        if row['game'] == target_game and row_players == target_players:
            session_matches.append(row)
        else:
            break 
            
    stats = {p: 0 for p in target_players}
    for m in session_matches:
        for w in m['winners'].split(","):
            w_strip = w.strip()
            if w_strip in stats: stats[w_strip] += 1
            
    return target_game, sorted(list(target_players)), stats

# --- 4. TABS ---
tabs = st.tabs(["🏠 HOME", "📝 RECORD", "📋 LOG ARCHIVE", "➕ REGISTER", "⚙️ SETTINGS"])

with tabs[0]: # HOME
    st.header("Dashboard")
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
                    st.dataframe(pd.DataFrame(res).sort_values("W", ascending=False), use_container_width=True, hide_index=True)
    with col_r:
        st.subheader("Recent History")
        recent = pd.read_sql_query("SELECT game, winners, date FROM matches ORDER BY id DESC LIMIT 10", conn)
        for _, row in recent.iterrows():
            st.markdown(f'<div class="glass-card"><b>{row["game"]}</b><br><small>{row["date"]}</small><br><span style="color:{t["accent"]}">Winner: {row["winners"]}</span></div>', unsafe_allow_html=True)

with tabs[1]: # RECORD (Centralized)
    st.header("Record Match Results")
    
    # --- QUICK LOG SECTION ---
    s_game, s_players, s_stats = get_session_stats()
    if s_game:
        st.markdown('<div class="glass-card" style="border: 1px solid #00FFAA44;">', unsafe_allow_html=True)
        col_q1, col_q2 = st.columns([2, 1])
        with col_q1:
            st.subheader(f"⚡ Quick Log: {s_game}")
            st.write("One-click record for current round:")
        with col_q2:
            st.markdown(" ".join([f'<div class="session-pill"><b>{k}:</b> {v}</div>' for k, v in s_stats.items()]), unsafe_allow_html=True)
        
        q_cols = st.columns(len(s_players))
        for i, p in enumerate(s_players):
            if q_cols[i].button(p, key=f"ql_{p}"):
                new_losers = [player for player in s_players if player != p]
                c.execute("INSERT INTO matches (game, date, time, winners, losers, notes) VALUES (?,?,?,?,?,?)",
                          (s_game, datetime.now().strftime("%Y-%m-%d"), "Quick Log", p, ", ".join(new_losers), "Round Rematch"))
                conn.commit()
                st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

    # --- MANUAL ENTRY SECTION ---
    st.markdown('<div class="glass-card">', unsafe_allow_html=True)
    st.subheader("📝 New Session / Manual Entry")
    all_p = [r[0] for r in c.execute("SELECT name FROM players ORDER BY name").fetchall()]
    all_g = [r[0] for r in c.execute("SELECT title FROM games ORDER BY title").fetchall()]
    
    c1, c2 = st.columns(2)
    with c1: rg_game = st.selectbox("Select Game", all_g)
    with c2: rg_date = st.date_input("Match Date", datetime.now())
    
    players_in = st.multiselect("Who participated?", all_p)
    if players_in:
        st.divider()
        winners, losers = [], []
        for p in players_in:
            col_p1, col_p2 = st.columns(2)
            with col_p1: st.write(f"**{p}**")
            with col_p2:
                if st.checkbox("Winner", key=f"win_check_{p}"): winners.append(p)
                else: losers.append(p)
        
        if st.button("ARCHIVE BATTLE"):
            if not winners: st.error("Select at least one winner.")
            else:
                c.execute("INSERT INTO matches (game, date, time, winners, losers) VALUES (?,?,?,?,?)",
                          (rg_game, str(rg_date), "20:00", ", ".join(winners), ", ".join(losers)))
                conn.commit(); st.toast("Logged!"); st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

with tabs[2]: # LOG ARCHIVE
    st.header("History & Modifications")
    logs = pd.read_sql_query("SELECT * FROM matches ORDER BY id DESC", conn)
    edit_id = st.selectbox("Select Match ID to Modify", logs['id'].tolist())
    if edit_id:
        row = logs[logs['id'] == edit_id].iloc[0]
        with st.form("edit_match"):
            f_win = st.text_input("Winners", row['winners'])
            f_loss = st.text_input("Losers", row['losers'])
            c_e1, c_e2 = st.columns(2)
            if c_e1.form_submit_button("Update Match"):
                c.execute("UPDATE matches SET winners=?, losers=? WHERE id=?", (f_win, f_loss, edit_id))
                conn.commit(); st.rerun()
            if c_e2.form_submit_button("🗑️ Delete Match"):
                c.execute("DELETE FROM matches WHERE id=?", (edit_id,))
                conn.commit(); st.rerun()
    st.dataframe(logs, use_container_width=True, hide_index=True)

with tabs[3]: # REGISTER
    st.header("Expand Roster & Library")
    cur_p = [r[0] for r in c.execute("SELECT name FROM players ORDER BY name").fetchall()]
    cur_g = [r[0] for r in c.execute("SELECT title FROM games ORDER BY title").fetchall()]
    
    col_reg1, col_reg2 = st.columns(2)
    with col_reg1:
        st.markdown('<div class="glass-card">', unsafe_allow_html=True)
        st.subheader("👤 New Player")
        p_in = st.text_input("Name", key="reg_p")
        if p_in:
            if p_in.lower() in [x.lower() for x in cur_p]: st.error("❌ Already Registered")
            else:
                if st.button("Register Player"):
                    c.execute("INSERT INTO players VALUES (?)", (p_in.strip(),)); conn.commit(); st.rerun()
        st.write("---")
        st.write(f"**Players ({len(cur_p)})**")
        st.markdown(f'<div class="inventory-list">{"<br>".join(cur_p)}</div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)
        
    with col_reg2:
        st.markdown('<div class="glass-card">', unsafe_allow_html=True)
        st.subheader("🎮 New Game")
        g_in = st.text_input("Title", key="reg_g")
        if g_in:
            if g_in.lower() in [x.lower() for x in cur_g]: st.error("❌ Already Registered")
            else:
                if st.button("Register Game"):
                    c.execute("INSERT INTO games VALUES (?)", (g_in.strip(),)); conn.commit(); st.rerun()
        st.write("---")
        st.write(f"**Library ({len(cur_g)})**")
        st.markdown(f'<div class="inventory-list">{"<br>".join(cur_g)}</div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

with tabs[4]: # SETTINGS
    st.header("Vault Settings")
    st.markdown('<div class="glass-card">', unsafe_allow_html=True)
    if st.button("🌓 Toggle Dark/Light Mode"):
        st.session_state.theme = "dark" if st.session_state.theme == "light" else "light"
        st.rerun()
    st.divider()

    st.subheader("Surgical Purge")
    p_purge = st.multiselect("Select Players to Purge", cur_p)
    g_purge = st.multiselect("Select Games to Purge", cur_g)
    
    if p_purge or g_purge:
        all_m = pd.read_sql_query("SELECT * FROM matches", conn)
        impact = 0
        for p in p_purge: impact += len(all_m[all_m['winners'].str.contains(p, na=False) | all_m['losers'].str.contains(p, na=False)])
        for g in g_purge: impact += len(all_m[all_m['game'] == g])
        
        st.warning(f"⚠️ **DATA DELETION:** This will remove **{impact} match records**.")
        if st.checkbox("Confirm surgical deletion of selected records."):
            if st.button("EXECUTE PURGE"):
                for p in p_purge:
                    c.execute("DELETE FROM matches WHERE winners LIKE ? OR losers LIKE ?", (f'%{p}%', f'%{p}%'))
                    c.execute("DELETE FROM players WHERE name=?", (p,))
                for g in g_purge:
                    c.execute("DELETE FROM matches WHERE game=?", (g,))
                    c.execute("DELETE FROM games WHERE title=?", (g,))
                conn.commit(); st.rerun()

    st.divider()
    if st.button("🚨 DEBUG: BOOTSTRAP DATA", type="primary"):
        run_bootstrap(); st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)