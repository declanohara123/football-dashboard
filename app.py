from pathlib import Path
import pandas as pd
import plotly.express as px
import streamlit as st

# Page Configuration
st.set_page_config(
    page_title="Championship Analytics | Opta Trajectories",
    page_icon="⚽",
    layout="wide",
)

# Custom Championship Team Color Map
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
    "Norwich": "#FFF200",
    "Derby": "#231F20",
    "Blackburn": "#009EE0",
    "Portsmouth": "#001489",
    "QPR": "#0054A6",
    "Charlton": "#D4001A",
    "Watford": "#FBEE23",
    "Bolton": "#1B2A4A",
    "Cardiff": "#0070B8",
    "Bristol C": "#E21B23",
    "Lincoln": "#E31B23",
    "Preston": "#FFFFFF",
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

if df.empty:
  st.error("⚠️ Unable to load dataset. Please check CSV file.")
  st.stop()

# Header Section
st.title("⚽ EFL Championship Trajectories")
st.caption("Opta Expected Metrics & Season Outcome Probabilities")

# Top KPI Summary Cards
latest_date = df["date"].iloc[-1]
latest_df = df[df["date"] == latest_date]

top_title = latest_df.sort_values(by="Title", ascending=False).iloc[0]
top_xpts = latest_df.sort_values(by="xpts", ascending=False).iloc[0]

kpi1, kpi2, kpi3 = st.columns(3)
kpi1.metric(
    "Title Favorite",
    f"{top_title['team']}",
    f"{top_title['Title'] * 100:.1f}% Prob",
)
kpi2.metric(
    "Expected Points Leader",
    f"{top_xpts['team']}",
    f"{top_xpts['xpts']:.1f} xPts",
)
kpi3.metric("Latest Snapshot", f"{latest_date}")

st.markdown("---")

# Sidebar Filters
st.sidebar.header("Dashboard Controls")
all_teams = sorted(df["team"].unique())
selected_teams = st.sidebar.multiselect(
    "Filter Teams:", all_teams, default=all_teams
)

if not selected_teams:
  selected_teams = all_teams

filtered_df = df[df["team"].isin(selected_teams)]


# Chart Builder
def create_chart(
    df_data, y_col, title, invert_y=False, is_percent=False, add_thresholds=False
):
  fig = px.line(
      df_data,
      x="date",
      y=y_col,
      color="team",
      color_discrete_map=TEAM_COLORS,
      line_shape="spline",
      title=f"<b>{title}</b>",
      labels={"date": "Matchday Date", y_col: title, "team": "Club"},
  )

  fig.update_traces(line=dict(width=2.5), hovertemplate="%{y}")

  fig.update_layout(
      height=360,
      margin=dict(l=20, r=20, t=50, b=20),
      showlegend=False,
      hovermode="x unified",
      paper_bgcolor="rgba(0,0,0,0)",
      plot_bgcolor="rgba(248,249,250,0.8)",
      font=dict(family="Arial, sans-serif", size=12),
      title_font=dict(size=15),
  )

  if invert_y:
    fig.update_yaxes(autorange="reversed", dtick=2, range=[24.5, 0.5])

  if add_thresholds:
    # Add Promotion / Relegation threshold lines for expected position
    fig.add_hline(
        y=2.5,
        line_dash="dot",
        line_color="green",
        annotation_text="Auto Promotion (2nd)",
    )
    fig.add_hline(
        y=6.5, line_dash="dot", line_color="blue", annotation_text="Play-offs (6th)"
    )
    fig.add_hline(
        y=21.5, line_dash="dot", line_color="red", annotation_text="Relegation (22nd)"
    )

  if is_percent:
    fig.update_yaxes(tickformat=".1p")

  return fig


# 3x2 Visual Grid
col1, col2, col3 = st.columns(3)
col4, col5, col6 = st.columns(3)

with col1:
  st.plotly_chart(
      create_chart(
          filtered_df,
          "xpos",
          "Expected Position",
          invert_y=True,
          add_thresholds=True,
      ),
      use_container_width=True,
  )

with col2:
  st.plotly_chart(
      create_chart(filtered_df, "xpts", "Expected Points (xPts)"),
      use_container_width=True,
  )

with col3:
  st.plotly_chart(
      create_chart(filtered_df, "Title", "Title Win Probability", is_percent=True),
      use_container_width=True,
  )

with col4:
  st.plotly_chart(
      create_chart(
          filtered_df, "Promotion", "Automatic Promotion %", is_percent=True
      ),
      use_container_width=True,
  )

with col5:
  st.plotly_chart(
      create_chart(
          filtered_df, "Promotion P/O", "Play-off Probability %", is_percent=True
      ),
      use_container_width=True,
  )

with col6:
  st.plotly_chart(
      create_chart(
          filtered_df, "REL", "Relegation Probability %", is_percent=True
      ),
      use_container_width=True,
  )
