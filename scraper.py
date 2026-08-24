from datetime import datetime
from pathlib import Path
import pandas as pd

# Paths
BASE_DIR = Path(__file__).resolve().parent
DATA_PATH = BASE_DIR / "data" / "expected_positions.csv"


def run_scraper():
  """Fetches latest data snapshot and appends new records to CSV."""
  today_str = datetime.now().strftime("%d-%b-%y")

  # Read existing data to avoid duplicate date entries
  if DATA_PATH.exists():
    try:
      existing_df = pd.read_csv(DATA_PATH)
      if len(existing_df.columns) <= 1:
        existing_df = pd.read_csv(DATA_PATH, sep="\t")
      existing_df.columns = existing_df.columns.str.strip()

      # Check if today's date has already been logged
      if "date" in existing_df.columns:
        existing_dates = existing_df["date"].astype(str).str.strip().tolist()
        if today_str in existing_dates:
          print(f"Data for {today_str} already exists in CSV. Skipping update.")
          return
    except Exception as e:
      print(f"Notice reading existing file: {e}")

  # --------------------------------------------------------------------------
  # PLACEHOLDER / SCRAPER LOGIC:
  # Replace this block with your live scraping code (e.g. requests / BeautifulSoup / Understat API)
  # --------------------------------------------------------------------------
  print(f"Fetching latest matchday expected points snapshot for {today_str}...")

  # Example structure matching your schema
  sample_teams = [
      "Millwall",
      "West Ham",
      "Wolves",
      "Middlesbrough",
      "Southampton",
  ]
  new_rows = []
  for idx, team in enumerate(sample_teams, start=1):
    new_rows.append({
        "xpos": idx,
        "team": team,
        "xpts": round(78.0 - (idx * 1.2), 2),
        "Title": f"{max(1, 18 - idx * 2):.2f}%",
        "Promotion": f"{max(1, 30 - idx * 3):.2f}%",
        "Promotion P/O": "40.00%",
        "REL": "1.00%",
        "date": today_str,
    })

  new_df = pd.DataFrame(new_rows)
  # --------------------------------------------------------------------------

  # Append new records to the CSV file
  file_exists = DATA_PATH.exists()
  new_df.to_csv(DATA_PATH, mode="a", index=False, header=not file_exists)
  print(f"Successfully appended {len(new_df)} new rows for {today_str}!")


if __name__ == "__main__":
  run_scraper()

