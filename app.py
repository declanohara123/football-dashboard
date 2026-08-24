from pathlib import Path
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

st.set_page_config(
    page_title="Championship Analytics | Opta Trajectories",
    page_icon="⚽",
    layout="wide",
)

# Club Color Map
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

st.title("⚽ EFL Championship Trajectories")
st.caption("Opta Expected Metrics & Season Outcome Probabilities")

# Top KPI Section
latest_date = df["date"].dropna().iloc[-1] if not df["date"].dropna().empty else "N/A"
latest_df = df[df["date"] == latest_date]

if not latest_df.empty and "Title" in latest_df.columns:
  top_title = latest_df.sort_values(by="Title", ascending=False).iloc[0]
  top_xpts = latest_df.sort_values(by="xpts", ascending=False).iloc[0]

  k1, k2, k3 = st.columns(3)
  k1.metric(
      "Title Favorite",
      f"{top_title['team']}",
      f"{top_title['Title']*100:.1f}% Prob",
  )
  k2.metric(
      "Expected Points Leader",
      f"{top_xpts['team']}",
      f"{top_xpts['xpts']:.1f} xPts",
  )
  k3.metric("Latest Snapshot", f"{latest_date}")

st.markdown("---")

# Sidebar Controls
all_teams = sorted(df["team"].dropna().unique())
st.sidebar.header("Dashboard Controls")

selected_teams = st.sidebar.multiselect(
    "Highlight Teams:", all_teams, default=["Swansea"]
)

show_background = st.sidebar.checkbox("Show rest of league in background", value=True)


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

  # Draw background faint gray lines for non-selected teams
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

  # Draw bold highlighted lines for selected teams
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

  # Configure Layout & Axis Range Constraints
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

  # Fixed Y-Axis limits to preserve scale context
  if y_range:
    fig.update_yaxes(range=y_range)

  if invert_y:
    fig.update_yaxes(autorange="reversed", dtick=2)

  if is_percent:
    fig.update_yaxes(tickformat=".0%")

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


# Render 3x2 Grid with Strict Range Constraints
col1, col2, col3 = st.columns(3)
col4, col5, col6 = st.columns(3)

with col1:
  st.plotly_chart(
      create_context_chart(
          df,
          selected_teams,
          "xpos",
          "Expected Position",
          y_range=[24.5, 0.5],
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
          y_range=[30, 90],
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
          y_range=[-0.02, 1.02],
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
          y_range=[-0.02, 1.02],
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
          y_range=[-0.02, 1.02],
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
          y_range=[-0.02, 1.02],
          is_percent=True,
      ),
      use_container_width=True,
  )
