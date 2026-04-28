import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np

# --- CONFIGURATION ---
st.set_page_config(page_title="1313 Poker Dashboard", page_icon="🃏", layout="wide", initial_sidebar_state="expanded")

# --- DATA LOADING ---
DATA_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vRNrlI9B6sz9BIMmG2l_ego6Zno6js1V5zxVlNps7Lzb--Mvt-EsIFwBXFO_cp4Aw/pub?gid=367894725&single=true&output=csv" 

@st.cache_data(ttl=300)
def load_data(url):
    df = pd.read_csv(url)
    
    df['Game #'] = pd.to_numeric(df['Game #'], errors='coerce')
    df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
    df = df.dropna(subset=['Game #', 'Date'])
    
    player_cols = [col for col in df.columns if col not in ['Game #', 'Date']]
    df_long = df.melt(id_vars=['Game #', 'Date'], value_vars=player_cols, 
                        var_name='Player', value_name='Profit')
    
    df_long['Profit'] = df_long['Profit'].astype(str)
    df_long['Profit'] = df_long['Profit'].str.replace(',', '', regex=False)
    df_long['Profit'] = df_long['Profit'].str.replace('₹', '', regex=False)
    df_long['Profit'] = df_long['Profit'].str.replace('$', '', regex=False)
    df_long['Profit'] = df_long['Profit'].str.strip()
    
    df_long['Profit'] = pd.to_numeric(df_long['Profit'], errors='coerce')
    df_long = df_long.dropna(subset=['Profit'])
    df_long = df_long.sort_values(['Player', 'Date'])
    df_long['Cumulative Profit'] = df_long.groupby('Player')['Profit'].cumsum()
    
    return df, df_long

try:
    df_raw, df_long = load_data(DATA_URL)
except Exception as e:
    st.error(f"Error loading data. Check your URL. Details: {e}")
    st.stop()

# --- SIDEBAR NAVIGATION & FILTERS ---
st.sidebar.markdown(
    """
    <div style='text-align: center; font-size: 36px; letter-spacing: 15px; margin-bottom: -15px;'>
        <span style='color: white;'>♠️</span>
        <span style='color: #ff4b4b;'>♥️</span>
        <span style='color: #ff4b4b;'>♦️</span>
        <span style='color: white;'>♣️</span>
    </div>
    """, 
    unsafe_allow_html=True
)
st.sidebar.title("1313 Poker")

view_selection = st.sidebar.radio(
    "Go To View:",
    ["🌍 Global Overview", "🎯 Player Deep-Dive", "⚔️ Head-to-Head Rivalry", "🎲 Single Game Analysis", "📓 Game Ledger"]
)

st.sidebar.divider()
st.sidebar.header("Global Filters")
all_players = sorted(df_long['Player'].unique())

if view_selection in ["🌍 Global Overview", "📓 Game Ledger"]:
    selected_players = st.sidebar.multiselect("Select Players", all_players, default=all_players)
    filtered_df = df_long[df_long['Player'].isin(selected_players)]
else:
    filtered_df = df_long 

# ==========================================
# VIEW 1: GLOBAL OVERVIEW
# ==========================================
if view_selection == "🌍 Global Overview":
    st.title("🌍 Global Overview")
    
    leaderboard = filtered_df.groupby('Player')['Profit'].sum().sort_values(ascending=False)
    
    if not leaderboard.empty:
        col1, col2, col3, col4, col5 = st.columns(5)
        total_valid_games = len(df_raw['Game #'].unique())
        
        col1.metric("Total Games", total_valid_games)
        col2.metric(f"🏆 Top Winner ({leaderboard.index[0]})", f"₹{leaderboard.iloc[0]:,.0f}")
        col3.metric(f"📉 Underdog ({leaderboard.index[-1]})", f"₹{leaderboard.iloc[-1]:,.0f}")
        
        max_loss_row = filtered_df.loc[filtered_df['Profit'].idxmin()]
        col4.metric(f"💀 Max Loss ({max_loss_row['Player']})", f"₹{max_loss_row['Profit']:,.0f}")
        col5.metric("💰 Total Pool", f"₹{leaderboard[leaderboard > 0].sum():,.0f}")

    st.divider()
    
    c1, c2 = st.columns([2, 1])
    with c1:
        st.subheader("Group Performance Over Time")
        plot_df = filtered_df.sort_values(['Player', 'Date'])
        fig_line = px.line(plot_df, x='Date', y='Cumulative Profit', color='Player',
                          markers=True, template="plotly_dark")
        st.plotly_chart(fig_line, use_container_width=True)

    with c2:
        st.subheader("Total Standings")
        lb_df = leaderboard.reset_index().sort_values('Profit', ascending=True)
        fig_bar = px.bar(lb_df, y='Player', x='Profit', orientation='h',
                        color='Profit', color_continuous_scale='RdYlGn', template="plotly_dark")
        fig_bar.update_layout(xaxis_title="Total Profit", yaxis_title="")
        st.plotly_chart(fig_bar, use_container_width=True)
        
    st.divider()
    
    # NEW FEATURE: VARIANCE & SWING ANALYSIS
    st.subheader("🌪️ Player Variance & Swing Analysis")
    st.markdown("Identifies the 'Grinders' (steady profit/loss) vs. the 'Wildcards' (huge swings). Players top-right win big and swing big.")
    
    variance_df = filtered_df.groupby('Player').agg(
        Avg_Profit=('Profit', 'mean'),
        Volatility=('Profit', 'std'), # Standard deviation = Variance/Swings
        Games=('Profit', 'count')
    ).dropna().reset_index()
    
    # Only plot players with at least 2 games (needed to calculate volatility)
    variance_df = variance_df[variance_df['Games'] > 1] 
    
    if not variance_df.empty:
        fig_var = px.scatter(variance_df, x='Volatility', y='Avg_Profit', 
                             text='Player', size='Games', color='Avg_Profit',
                             color_continuous_scale='RdYlGn', template="plotly_dark")
        fig_var.update_traces(textposition='top center')
        fig_var.update_layout(xaxis_title="Volatility (Standard Deviation of Swings)", 
                              yaxis_title="Average Profit per Game (₹)")
        
        # Add quadrants lines (Zero profit line)
        fig_var.add_hline(y=0, line_dash="dash", line_color="white", opacity=0.5)
        st.plotly_chart(fig_var, use_container_width=True)

# ==========================================
# VIEW 2: PLAYER DEEP-DIVE
# ==========================================
elif view_selection == "🎯 Player Deep-Dive":
    st.title("🎯 Player Deep-Dive")
    
    target_player = st.selectbox("Select a Player to Analyze", all_players)
    player_data = df_long[df_long['Player'] == target_player].sort_values('Date').copy()
    
    if not player_data.empty:
        total_p = player_data['Profit'].sum()
        avg_p = player_data['Profit'].mean()
        win_rate = (player_data['Profit'] > 0).sum() / len(player_data) * 100
        
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Total Net Profit", f"₹{total_p:,.0f}")
        c2.metric("Avg Profit / Game", f"₹{avg_p:,.0f}")
        c3.metric("Win Rate", f"{win_rate:.1f}%")
        c4.metric("Games Played", len(player_data))
        
        # NEW FEATURE: FORM & STREAKS
        st.divider()
        st.subheader("🔥 Form & Streaks")
        
        profits = player_data['Profit'].tolist()
        
        # 1. Last 5 Games Form
        last_5 = profits[-5:] if len(profits) >= 5 else profits
        form_str = " ".join(["🟩" if x > 0 else ("🟥" if x < 0 else "⬜") for x in last_5])
        
        # 2. Current Streak
        current_streak = 0
        if profits:
            is_winning = profits[-1] > 0
            for p in reversed(profits):
                if (p > 0) == is_winning and p != 0:
                    current_streak += 1
                elif p == 0:
                    continue # Ignore exact zero break-evens in streaks
                else:
                    break
            streak_display = f"🔥 Won last {current_streak}" if is_winning else f"🧊 Lost last {current_streak}"
        else:
            streak_display = "N/A"
            
        # 3. Max Win Streak Logic
        wins_mask = player_data['Profit'] > 0
        streak_groups = wins_mask.ne(wins_mask.shift()).cumsum()
        max_win_streak = wins_mask.groupby(streak_groups).sum().max()
        
        sc1, sc2, sc3 = st.columns(3)
        sc1.metric("Recent Form (Last 5)", form_str)
        sc2.metric("Current Streak", streak_display)
        sc3.metric("Longest Win Streak", int(max_win_streak))
        
        st.divider()
        
        col_chart1, col_chart2 = st.columns(2)
        with col_chart1:
            st.subheader("Personal Bankroll Trend")
            fig_p_line = px.line(player_data, x='Date', y='Cumulative Profit', 
                                 markers=True, template="plotly_dark", line_shape='spline')
            fig_p_line.update_traces(line_color='#00FF00' if total_p >= 0 else '#FF0000')
            st.plotly_chart(fig_p_line, use_container_width=True)
            
        with col_chart2:
            st.subheader("Session Results Distribution")
            fig_hist = px.histogram(player_data, x='Profit', nbins=10, 
                                    template="plotly_dark", color_discrete_sequence=['#1E90FF'])
            st.plotly_chart(fig_hist, use_container_width=True)

# ==========================================
# VIEW 3: HEAD-TO-HEAD RIVALRY
# ==========================================
elif view_selection == "⚔️ Head-to-Head Rivalry":
    st.title("⚔️ Head-to-Head Rivalry")
    st.markdown("Analyze performance specifically for games where **both** players sat at the same table.")
    
    col_sel1, col_sel2 = st.columns(2)
    player_A = col_sel1.selectbox("Select Player A", all_players, index=0)
    # Default Player B to the second person in the list to avoid them being the same immediately
    default_b_index = 1 if len(all_players) > 1 else 0
    player_B = col_sel2.selectbox("Select Player B", all_players, index=default_b_index)
    
    if player_A == player_B:
        st.warning("Please select two different players to compare.")
    else:
        # Find games where BOTH played
        games_A = set(df_long[df_long['Player'] == player_A]['Game #'])
        games_B = set(df_long[df_long['Player'] == player_B]['Game #'])
        common_games = list(games_A.intersection(games_B))
        
        if not common_games:
            st.info(f"{player_A} and {player_B} have never played in the same game.")
        else:
            # Filter data for only these common games and these two players
            rivalry_df = df_long[(df_long['Game #'].isin(common_games)) & 
                                 (df_long['Player'].isin([player_A, player_B]))].copy()
            
            rivalry_df = rivalry_df.sort_values(['Player', 'Date'])
            
            # Calculate their isolated profits for just these games
            stats_A = rivalry_df[rivalry_df['Player'] == player_A]['Profit']
            stats_B = rivalry_df[rivalry_df['Player'] == player_B]['Profit']
            
            tot_A = stats_A.sum()
            tot_B = stats_B.sum()
            
            # Determine who "won" the rivalry
            winner = player_A if tot_A > tot_B else (player_B if tot_B > tot_A else "Tie")
            
            st.divider()
            
            c1, c2, c3 = st.columns(3)
            c1.metric("Games Played Together", len(common_games))
            c2.metric(f"Rivalry Leader", winner)
            c3.metric("Profit Difference", f"₹{abs(tot_A - tot_B):,.0f}")
            
            st.divider()
            
            rc1, rc2 = st.columns(2)
            
            with rc1:
                st.subheader(f"Total Profit (Common Games Only)")
                # Bar chart for total
                bar_data = pd.DataFrame({
                    'Player': [player_A, player_B],
                    'Profit': [tot_A, tot_B]
                })
                fig_r_bar = px.bar(bar_data, x='Player', y='Profit', color='Player', 
                                   template="plotly_dark", 
                                   color_discrete_sequence=['#1E90FF', '#FF4500'])
                st.plotly_chart(fig_r_bar, use_container_width=True)
                
            with rc2:
                st.subheader("Head-to-Head Trend")
                # Calculate cumulative profit for JUST these common games
                rivalry_df['H2H Cumulative'] = rivalry_df.groupby('Player')['Profit'].cumsum()
                
                fig_r_line = px.line(rivalry_df, x='Date', y='H2H Cumulative', color='Player',
                                     markers=True, template="plotly_dark",
                                     color_discrete_sequence=['#1E90FF', '#FF4500'])
                st.plotly_chart(fig_r_line, use_container_width=True)

# ==========================================
# VIEW 4: SINGLE GAME ANALYSIS
# ==========================================
elif view_selection == "🎲 Single Game Analysis":
    st.title("🎲 Single Game Analysis")
    st.markdown("Breakdown of performance for a specific session.")
    
    df_dates = df_raw[['Game #', 'Date']].drop_duplicates().sort_values('Game #', ascending=False)
    game_options = [f"Game {int(row['Game #'])} - {row['Date'].strftime('%b %d, %Y')}" for _, row in df_dates.iterrows()]
        
    if game_options:
        selected_game_str = st.selectbox("Select a Session", game_options)
        selected_game_num = int(selected_game_str.split(" ")[1])
        
        game_data = df_long[df_long['Game #'] == selected_game_num].sort_values('Profit', ascending=False)
        
        if not game_data.empty:
            st.divider()
            top_winner = game_data.iloc[0]
            biggest_loser = game_data.iloc[-1]
            total_pot = game_data[game_data['Profit'] > 0]['Profit'].sum()
            
            c1, c2, c3, c4 = st.columns(4)
            c1.metric(f"🏆 Winner ({top_winner['Player']})", f"₹{top_winner['Profit']:,.0f}")
            c2.metric(f"📉 Loser ({biggest_loser['Player']})", f"₹{biggest_loser['Profit']:,.0f}")
            c3.metric("💰 Total Pot Exchanged", f"₹{total_pot:,.0f}")
            c4.metric("👥 Players Present", len(game_data))
            
            st.divider()
            
            col_bar, col_table = st.columns([2, 1])
            with col_bar:
                st.subheader(f"Results Chart")
                fig_game_bar = px.bar(game_data, x='Player', y='Profit', color='Profit', 
                                      color_continuous_scale='RdYlGn', template="plotly_dark")
                st.plotly_chart(fig_game_bar, use_container_width=True)
                
            with col_table:
                st.subheader("Leaderboard")
                display_table = game_data[['Player', 'Profit']].reset_index(drop=True)
                st.dataframe(display_table.style.format({'Profit': "{:,.0f}"}).background_gradient(cmap='RdYlGn', subset=['Profit']),
                             use_container_width=True, height=400)

# ==========================================
# VIEW 5: GAME LEDGER (RAW DATA)
# ==========================================
elif view_selection == "📓 Game Ledger":
    st.title("📓 Game Ledger & Raw Data")
    
    st.subheader("Aggregated Player Statistics")
    stats = filtered_df.groupby('Player').agg(
        Games=('Profit', 'count'), Total_Profit=('Profit', 'sum'),
        Avg_Per_Game=('Profit', 'mean'), Best=('Profit', 'max'), Worst=('Profit', 'min')
    ).sort_values('Total_Profit', ascending=False)
    
    st.dataframe(stats.style.format(precision=0).background_gradient(subset=['Total_Profit', 'Avg_Per_Game'], cmap='RdYlGn'),
                 use_container_width=True, height=400)
    
    st.divider()
    st.subheader("Raw Game History")
    df_raw_display = df_raw.copy()
    df_raw_display['Date'] = df_raw_display['Date'].dt.strftime('%Y-%m-%d')
    st.dataframe(df_raw_display, use_container_width=True)