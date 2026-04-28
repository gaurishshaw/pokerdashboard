import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# --- CONFIGURATION ---
st.set_page_config(page_title="1313 Poker Dashboard", layout="wide", initial_sidebar_state="expanded")

# --- DATA LOADING ---
DATA_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vRNrlI9B6sz9BIMmG2l_ego6Zno6js1V5zxVlNps7Lzb--Mvt-EsIFwBXFO_cp4Aw/pub?gid=367894725&single=true&output=csv" 

@st.cache_data(ttl=300)
def load_data(url):
    df = pd.read_csv(url)
    
    # 1. Force formatting for Game # and Date
    df['Game #'] = pd.to_numeric(df['Game #'], errors='coerce')
    df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
    
    # 2. STRICT FILTER: Keep only rows where BOTH Game # and Date are filled
    df = df.dropna(subset=['Game #', 'Date'])
    
    # 3. Process Player Data
    player_cols = [col for col in df.columns if col not in ['Game #', 'Date']]
    df_long = df.melt(id_vars=['Game #', 'Date'], value_vars=player_cols, 
                        var_name='Player', value_name='Profit')
    
    # Clean string artifacts (commas, currency symbols) before numeric conversion
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
st.sidebar.image("https://cdn-icons-png.flaticon.com/512/105/105220.png", width=50)
st.sidebar.title("1313 Poker")

view_selection = st.sidebar.radio(
    "Go To View:",
    ["🌍 Global Overview", "🎯 Player Deep-Dive", "📓 Game Ledger"]
)

st.sidebar.divider()

st.sidebar.header("Global Filters")
all_players = sorted(df_long['Player'].unique())

if view_selection == "🌍 Global Overview" or view_selection == "📓 Game Ledger":
    selected_players = st.sidebar.multiselect("Select Players", all_players, default=all_players)
    filtered_df = df_long[df_long['Player'].isin(selected_players)]
else:
    filtered_df = df_long 

# ==========================================
# VIEW 1: GLOBAL OVERVIEW
# ==========================================
if view_selection == "🌍 Global Overview":
    st.title("🌍 Global Overview")
    st.markdown("Top-level metrics and overall group performance.")
    
    leaderboard = filtered_df.groupby('Player')['Profit'].sum().sort_values(ascending=False)
    
    if not leaderboard.empty:
        col1, col2, col3, col4, col5 = st.columns(5)
        
        # FIXED: Count the actual number of valid game rows
        total_valid_games = len(df_raw['Game #'].unique())
        col1.metric("Total Games", total_valid_games)
        
        top_player = leaderboard.index[0]
        top_amt = leaderboard.iloc[0]
        col2.metric(f"🏆 Top Winner ({top_player})", f"₹{top_amt:,.0f}")
        
        bot_player = leaderboard.index[-1]
        bot_amt = leaderboard.iloc[-1]
        col3.metric(f"📉 Underdog ({bot_player})", f"₹{bot_amt:,.0f}")
        
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
        fig_line.update_layout(xaxis_title="", yaxis_title="Net Profit (₹)", legend_title="Player")
        st.plotly_chart(fig_line, use_container_width=True)

    with c2:
        st.subheader("Total Standings")
        lb_df = leaderboard.reset_index().sort_values('Profit', ascending=True)
        fig_bar = px.bar(lb_df, y='Player', x='Profit', orientation='h',
                        color='Profit', color_continuous_scale='RdYlGn',
                        template="plotly_dark")
        fig_bar.update_layout(xaxis_title="Total Profit (₹)", yaxis_title="")
        st.plotly_chart(fig_bar, use_container_width=True)

# ==========================================
# VIEW 2: PLAYER DEEP-DIVE
# ==========================================
elif view_selection == "🎯 Player Deep-Dive":
    st.title("🎯 Player Deep-Dive")
    
    target_player = st.selectbox("Select a Player to Analyze", all_players)
    player_data = df_long[df_long['Player'] == target_player].copy()
    
    if not player_data.empty:
        total_p = player_data['Profit'].sum()
        avg_p = player_data['Profit'].mean()
        win_rate = (player_data['Profit'] > 0).sum() / len(player_data) * 100
        
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Total Net Profit", f"₹{total_p:,.0f}")
        c2.metric("Avg Profit / Game", f"₹{avg_p:,.0f}")
        c3.metric("Win Rate", f"{win_rate:.1f}%")
        c4.metric("Total Games Played", len(player_data))
        
        st.divider()
        
        col_chart1, col_chart2 = st.columns(2)
        
        with col_chart1:
            st.subheader("Personal Bankroll Trend")
            fig_p_line = px.line(player_data, x='Date', y='Cumulative Profit', 
                                 markers=True, template="plotly_dark", 
                                 line_shape='spline')
            fig_p_line.update_traces(line_color='#00FF00' if total_p >= 0 else '#FF0000')
            st.plotly_chart(fig_p_line, use_container_width=True)
            
        with col_chart2:
            st.subheader("Session Results Distribution")
            fig_hist = px.histogram(player_data, x='Profit', nbins=10, 
                                    template="plotly_dark",
                                    color_discrete_sequence=['#1E90FF'])
            fig_hist.update_layout(xaxis_title="Session Profit/Loss (₹)", yaxis_title="Number of Games")
            st.plotly_chart(fig_hist, use_container_width=True)

# ==========================================
# VIEW 3: GAME Ledger (RAW DATA)
# ==========================================
elif view_selection == "📓 Game Ledger":
    st.title("📓 Game Ledger & Raw Data")
    st.markdown("Detailed breakdown of all sessions and individual player statistics.")
    
    st.subheader("Aggregated Player Statistics")
    stats = filtered_df.groupby('Player').agg(
        Games_Played=('Profit', 'count'),
        Total_Profit=('Profit', 'sum'),
        Avg_Per_Game=('Profit', 'mean'),
        Best_Session=('Profit', 'max'),
        Worst_Session=('Profit', 'min')
    ).sort_values('Total_Profit', ascending=False)
    
    st.dataframe(
        stats.style.format(precision=0)
        .background_gradient(subset=['Total_Profit', 'Avg_Per_Game'], cmap='RdYlGn'),
        use_container_width=True, height=400
    )
    
    st.divider()
    
    st.subheader("Raw Game History")
    
    # Format the date nicely for the raw history view
    df_raw_display = df_raw.copy()
    df_raw_display['Date'] = df_raw_display['Date'].dt.strftime('%Y-%m-%d')
    
    st.dataframe(df_raw_display, use_container_width=True)