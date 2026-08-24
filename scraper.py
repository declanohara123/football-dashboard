
from datetime import datetime
import json
from pathlib import Path
import re
import pandas as pd
import requests

BASE_DIR = Path(__file__).resolve().parent
DATA_PATH = BASE_DIR / "data" / "expected_positions.csv"


def scrape_the_analyst_table():
  """Scrapes the Championship predicted table probabilities from Opta/The Analyst."""
  url = "https://theanalyst.com/competition/english-championship/table"
  headers = {
      "User-Agent": (
          "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
          " (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
      )
  }

  response = requests.get(url, headers=headers)
  if response.status_code != 200:
    raise RuntimeError(
        f"Failed to load The Analyst page. Status: {response.status_code}"
    )

  html = response.text
  today_str = datetime.now().strftime("%d-%b-%y")

  # Search for Opta's embedded JSON state data within script tags
  json_match = re.search(
      r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>', html
  )

  extracted_rows = []

  if json_match:
    payload = json.loads(json_match.group(1))
    # Traverse Next.js props to find the predicted table dataset
    try:
      page_props = payload.get("props", {}).get("pageProps", {})
      table_data = (
          page_props.get("tableData", [])
          or page_props.get("predictionTable", [])
          or page_props.get("standings", [])
      )

      for item in table_data:
        extracted_rows.append({
            "xpos": item.get("rank") or item.get("position"),
            "team": item.get("teamName") or item.get("team", {}).get("name"),
            "xpts": item.get("pts") or item.get("expectedPoints"),
            "Title": f"{item.get('titleProb', 0):.2f}%",
            "Promotion": f"{item.get('promoProb', 0):.2f}%",
            "Promotion P/O": f"{item.get('playoffProb', 0):.2f}%",
            "REL": f"{item.get('relegationProb', 0):.2f}%",
            "date": today_str,
        })
    except Exception as e:
      print(f"JSON parsing notice: {e}")

  # Fallback: Parse via Pandas HTML reader if script tag parsing varies
  if not extracted_rows:
    dfs = pd.read_html(html)
    for df_table in dfs:
      if "Team" in df_table.columns or "team" in df_table.columns:
        df_table.columns = df_table.columns.str.strip()
        df_table["date"] = today_str
        return df_table

  df_out = pd.DataFrame(extracted_rows)
  return df_out


def main():
  try:
    today_str = datetime.now().strftime("%d-%b-%y")

    # Avoid duplicate scrapes for the same date
    if DATA_PATH.exists():
      existing = pd.read_csv(DATA_PATH)
      if (
          "date" in existing.columns
          and today_str in existing["date"].astype(str).values
      ):
        print(f"Data for {today_str} already recorded. Exiting scraper.")
        return

    new_data = scrape_the_analyst_table()

    if not new_data.empty:
      file_exists = DATA_PATH.exists()
      new_data.to_csv(DATA_PATH, mode="a", index=False, header=not file_exists)
      print(f"Successfully scraped and appended data for {today_str}")
    else:
      print("Scraper ran but returned no new rows.")

  except Exception as err:
    print(f"Error executing scraper: {err}")


if __name__ == "__main__":
  main()
