import math
from pathlib import Path
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

st.set_page_config(
    page_title="Championship Analytics | Opta Trajectories",
    page_icon="⚽",
    layout="wide",
)

# Custom CSS to shrink metric values so team names fit without truncating
st.markdown(
    """
    <style>
    div[data-testid="stMetricValue"] {
        font-size: 16px !important;
        font-weight: 600 !important;
        line-height: 1.3 !important;
    }
    div[data-testid="stMetricLabel"] {
        font-size: 13px !important;
        color: #475569 !important;
    }
    </style>
""",
    unsafe_allow_html=True,
)

TEAM_COLORS = {
    "West Ham": "#7A263A",
    "Millwall": "#002F6C",
    "Wolves": "#FDB913",
    "Middlesbrough": "#E00000",
    "Southampton": "#D10022",
    "West Brom": "#00175A",
    "Burnley": "#6C1D45",
    "Sheff Utd": "#EE2737",
    "Swansea": "#111111",
    "Wrexham": "#E30613",
    "Birmingham": "#0000FF",
    "Norwich": "#D4B000",
    "Derby": "#231F20",
    "Blackburn": "#009EE0",
    "Portsmouth": "#001489",
    "QPR": "#0054A6",
    "Charlton": "#D4001A",
    "Watford": "#E6B800",
    "Bolton": "#1B2A4A",
    "Cardiff": "#0070B8",
    "Bristol C": "#E21B23",
    "Lincoln": "#D91C24",
    "Preston": "#4A5568",
    "Stoke": "#E03A3E",
}

BASE_DIR = Path(__file__).resolve().parent
DATA_PATH = BASE_DIR / "data" / "expected_positions.csv"


@st.cache_data(ttl=60)
def load_data():
  if not DATA_PATH.exists():
    return pd.DataFrame()
  try:
    data = pd.read_csv(DATA_PATH)
    if len(data.columns) <= 1:
      data = pd.read_csv(DATA_PATH, sep="\t")
  except Exception:
    return pd.DataFrame()

  data.columns = data.columns.str.strip()
  if "team" in data.columns:
    data["team"] = data["team"].astype(str).str.strip()

  pct_cols = ["Title", "Promotion", "Promotion P/O", "REL"]
  for col in pct_cols:
    if col in data.columns:
      data[col] = (
          data[col]
          .astype(str)
          .str.replace("%", "", regex=False)
          .str.strip()
      )
      data[col] = pd.to_numeric(data[col], errors="coerce") / 100.0

  data["xpos"] = pd.to_numeric(data["xpos"], errors="coerce")
  data["xpts"] = pd.to_numeric(data["xpts"], errors="coerce")

  if "date" in data.columns:
    data["date_dt"] = pd.to_datetime(
        data["date"], format="%d-%b-%y", errors="coerce"
    )
    data = data.sort_values(by="date_dt")

  return data


df = load_data()

if df.empty or "team" not in df.columns:
  st.error("⚠️ Unable to load dataset.")
  st.stop()

# Dates & Snapshots
unique_dates = df["date"].dropna().unique()
latest_date = unique_dates[-1] if len(unique_dates) > 0 else "N/A"
prev_date = unique_dates[-2] if len(unique_dates) > 1 else None

# Header Section with small date timestamp
st.title("⚽ EFL Championship Trajectories")
st.caption(
    f"Opta Expected Metrics & Season Outcome Probabilities  |  **Last"
    f" Updated:** {latest_date}"
)

latest_df = df[df["date"] == latest_date].sort_values(by="xpos")

# Calculate KPI Groups
if not latest_df.empty:
  auto_promo_teams = ", ".join(latest_df.iloc[0:2]["team"].tolist())
  playoff_teams = ", ".join(latest_df.iloc[2:6]["team"].tolist())
  relegation_teams = ", ".join(latest_df.iloc[-3:]["team"].tolist())

  # Calculate Biggest Mover
  mover_text = "N/A"
  mover_delta = 0
  if prev_date:
    prev_df = df[df["date"] == prev_date][["team", "xpos"]].rename(
        columns={"xpos": "prev_xpos"}
    )
    merged = pd.merge(latest_df, prev_df, on="team")
    merged["pos_change"] = merged["prev_xpos"] - merged["xpos"]
    top_mover = merged.sort_values(by="pos_change", ascending=False).iloc[0]
    mover_delta = int(top_mover["pos_change"])
    if mover_delta > 0:
      mover_text = f"{top_mover['team']} (+{mover_delta} places)"
    elif mover_delta < 0:
      mover_text = f"{top_mover['team']} ({mover_delta} places)"
    else:
      mover_text = "No change across league"
  else:
    top_xpts = latest_df.sort_values(by="xpts", ascending=False).iloc[0]
    mover_text = f"{top_xpts['team']} ({top_xpts['xpts']:.1f} xPts)"

  # Render 4 KPI Columns
  k1, k2, k3, k4 = st.columns(4)
  k1.metric("Auto Promotion (1st & 2nd)", auto_promo_teams)
  k2.metric("Play-off Spots (3rd - 6th)", playoff_teams)
  k3.metric("Relegation Zone (22nd - 24th)", relegation_teams)
  k4.metric(
      "Biggest Mover (Last Update)",
      mover_text,
      f"{mover_delta} places" if prev_date else "Baseline",
  )

st.markdown("---")

# Sidebar Controls
all_teams = sorted(df["team"].dropna().unique())
st.sidebar.header("Dashboard Controls")

selected_teams = st.sidebar.multiselect(
    "Highlight Teams:", all_teams, default=["Swansea"]
)
show_background = st.sidebar.checkbox(
    "Show rest of league in background", value=True
)


def get_smart_percent_max(data_series):
  max_val = data_series.dropna().max()
  if pd.isna(max_val) or max_val <= 0:
    return 0.10
  smart_max = math.ceil(max_val * 10) / 10.0
  return min(1.0, max(0.10, smart_max + 0.02))


def get_smart_pts_range(data_series):
  min_val = data_series.dropna().min()
  max_val = data_series.dropna().max()
  if pd.isna(min_val):
    return [30, 90]
  return [math.floor(min_val - 3), math.ceil(max_val + 3)]


def create_context_chart(
    full_df,
    selected_list,
    y_col,
    title,
    y_range=None,
    invert_y=False,
    is_percent=False,
    add_thresholds=False,
):
  fig = go.Figure()

  if show_background:
    unselected_df = full_df[~full_df["team"].isin(selected_list)]
    for team, group in unselected_df.groupby("team"):
      fig.add_trace(
          go.Scatter(
              x=group["date"],
              y=group[y_col],
              mode="lines",
              line=dict(color="#CBD5E1", width=1),
              opacity=0.35,
              hoverinfo="skip",
              showlegend=False,
          )
      )

  highlight_df = full_df[full_df["team"].isin(selected_list)]
  for team in selected_list:
    team_data = highlight_df[highlight_df["team"] == team]
    if not team_data.empty:
      color = TEAM_COLORS.get(team, "#1E293B")
      fig.add_trace(
          go.Scatter(
              x=team_data["date"],
              y=team_data[y_col],
              mode="lines+markers",
              name=team,
              line=dict(color=color, width=3, shape="spline"),
              marker=dict(size=6),
              hovertemplate=f"<b>{team}</b>: %{{y}}<extra></extra>",
          )
      )

  fig.update_layout(
      height=360,
      margin=dict(l=25, r=25, t=50, b=25),
      title=f"<b>{title}</b>",
      showlegend=True if len(selected_list) > 1 else False,
      legend=dict(
          orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1
      ),
      hovermode="x unified",
      paper_bgcolor="rgba(0,0,0,0)",
      plot_bgcolor="rgba(248,249,250,0.8)",
      font=dict(family="Arial, sans-serif", size=11),
  )

  if y_range:
    fig.update_yaxes(range=y_range)

  if invert_y:
    fig.update_yaxes(autorange="reversed", tick0=1, dtick=2)

  if is_percent:
    fig.update_yaxes(tickformat=".0%", dtick=0.05 if y_range[1] <= 0.3 else 0.10)

  if add_thresholds:
    fig.add_hline(
        y=2.5,
        line_dash="dot",
        line_color="green",
        annotation_text="Auto Promo (2nd)",
        annotation_position="top right",
    )
    fig.add_hline(
        y=6.5,
        line_dash="dot",
        line_color="blue",
        annotation_text="Play-offs (6th)",
        annotation_position="top right",
    )
    fig.add_hline(
        y=21.5,
        line_dash="dot",
        line_color="red",
        annotation_text="Relegation (22nd)",
        annotation_position="top right",
    )

  return fig


# Smart Max Calculations
title_max = get_smart_percent_max(df["Title"])
promo_max = get_smart_percent_max(df["Promotion"])
po_max = get_smart_percent_max(df["Promotion P/O"])
rel_max = get_smart_percent_max(df["REL"])
xpts_range = get_smart_pts_range(df["xpts"])

col1, col2, col3 = st.columns(3)
col4, col5, col6 = st.columns(3)

with col1:
  st.plotly_chart(
      create_context_chart(
          df,
          selected_teams,
          "xpos",
          "Expected Position",
          y_range=[24.5, 0.8],
          invert_y=True,
          add_thresholds=True,
      ),
      use_container_width=True,
  )

with col2:
  st.plotly_chart(
      create_context_chart(
          df,
          selected_teams,
          "xpts",
          "Expected Points (xPts)",
          y_range=xpts_range,
      ),
      use_container_width=True,
  )

with col3:
  st.plotly_chart(
      create_context_chart(
          df,
          selected_teams,
          "Title",
          "Title Win Probability",
          y_range=[-0.01, title_max],
          is_percent=True,
      ),
      use_container_width=True,
  )

with col4:
  st.plotly_chart(
      create_context_chart(
          df,
          selected_teams,
          "Promotion",
          "Automatic Promotion %",
          y_range=[-0.01, promo_max],
          is_percent=True,
      ),
      use_container_width=True,
  )

with col5:
  st.plotly_chart(
      create_context_chart(
          df,
          selected_teams,
          "Promotion P/O",
          "Play-off Probability %",
          y_range=[-0.01, po_max],
          is_percent=True,
      ),
      use_container_width=True,
  )

with col6:
  st.plotly_chart(
      create_context_chart(
          df,
          selected_teams,
          "REL",
          "Relegation Probability %",
          y_range=[-0.01, rel_max],
          is_percent=True,
      ),
      use_container_width=True,
  )
