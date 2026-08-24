from pathlib import Path
import pandas as pd
import plotly.express as px
import streamlit as st

# Page Configuration
st.set_page_config(
    page_title="Championship Multi-Metric Dashboard", layout="wide"
)
st.title("⚽ Championship Season Progression Dashboard")

# File Path
BASE_DIR = Path(__file__).resolve().parent
DATA_PATH = BASE_DIR / "data" / "expected_positions.csv"


@st.cache_data(ttl=60)
def load_data():
  try:
    data = pd.read_csv(DATA_PATH)
    if len(data.columns) <= 1:
      data = pd.read_csv(DATA_PATH, sep="\t")
  except Exception:
    data = pd.read_csv(DATA_PATH, sep="\t")

  # Clean spaces from columns and text
  data.columns = data.columns.str.strip()
  data["team"] = data["team"].astype(str).str.strip()

  # Clean percentage strings to numeric decimals (e.g., '17.80%' -> 0.178)
  pct_cols = ["Title", "Promotion", "Promotion P/O", "REL"]
  for col in pct_cols:
    if col in data.columns:
      data[col] = (
          data[col]
          .astype(str)
          .str.rstrip("%")
          .astype("float", errors="ignore")
          / 100.0
      )

  # Numeric columns
  data["xpos"] = pd.to_numeric(data["xpos"], errors="coerce")
  data["xpts"] = pd.to_numeric(data["xpts"], errors="coerce")

  # Parse dates and sort chronologically
  data["date_dt"] = pd.to_datetime(data["date"], format="%d-%b-%y")
  data = data.sort_values(by="date_dt")

  return data


df = load_data()

# Team Selector in Sidebar
st.sidebar.header("Filter Options")
all_teams = sorted(df["team"].unique())
selected_teams = st.sidebar.multiselect(
    "Select Teams (Default: All Teams):", all_teams, default=all_teams
)

if not selected_teams:
  selected_teams = all_teams

filtered_df = df[df["team"].isin(selected_teams)]


# Helper function to generate clean line plots for the grid
def create_metric_chart(
    df_data, y_col, title, invert_y=False, is_percent=False
):
  fig = px.line(
      df_data,
      x="date",
      y=y_col,
      color="team",
      line_shape="spline",  # Smooth curved lines matching your image
      title=title,
      labels={
          "date": "Date",
          y_col: title,
          "team": "Team",
      },
  )

  # Remove chart clutter to match sleek dashboard style
  fig.update_layout(
      height=350,
      margin=dict(l=20, r=20, t=40, b=20),
      showlegend=False,  # Keep clean without 24 legend items per subchart
      hovermode="x unified",
      paper_bgcolor="rgba(0,0,0,0)",
      plot_bgcolor="rgba(245,245,245,0.5)",
  )

  if invert_y:
    fig.update_yaxes(autorange="reversed", dtick=2, range=[24.5, 0.5])

  if is_percent:
    fig.update_yaxes(tickformat=".2p")

  return fig


# Build the 3x2 Grid Layout
row1_col1, row1_col2, row1_col3 = st.columns(3)
row2_col1, row2_col2, row2_col3 = st.columns(3)

with row1_col1:
  st.plotly_chart(
      create_metric_chart(
          filtered_df, "Title", "Average of Title", is_percent=True
      ),
      use_container_width=True,
  )

with row1_col2:
  st.plotly_chart(
      create_metric_chart(
          filtered_df, "xpos", "Expected Position", invert_y=True
      ),
      use_container_width=True,
  )

with row1_col3:
  st.plotly_chart(
      create_metric_chart(filtered_df, "xpts", "Sum of xpts"),
      use_container_width=True,
  )

with row2_col1:
  st.plotly_chart(
      create_metric_chart(
          filtered_df, "Promotion P/O", "Sum of Promotion P/O", is_percent=True
      ),
      use_container_width=True,
  )

with row2_col2:
  st.plotly_chart(
      create_metric_chart(
          filtered_df, "REL", "Sum of REL", is_percent=True
      ),
      use_container_width=True,
  )

with row2_col3:
  st.plotly_chart(
      create_metric_chart(
          filtered_df, "Promotion", "Sum of Promotion", is_percent=True
      ),
      use_container_width=True,
  )
