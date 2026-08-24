from datetime import datetime
from io import StringIO
from pathlib import Path
import pandas as pd
from playwright.sync_api import sync_playwright

BASE_DIR = Path(__file__).resolve().parent
DATA_PATH = BASE_DIR / "data" / "expected_positions.csv"


def scrape_predicted_table():
  """Uses Playwright to click the 'PREDICTED' tab on The Analyst and grab Opta metrics."""
  url = "https://theanalyst.com/competition/english-championship/table"
  today_str = datetime.now().strftime("%d-%b-%y")

  with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()

    page.goto(url, wait_until="networkidle")
    page.click("text=PREDICTED")
    page.wait_for_timeout(2500)

    content = page.content()
    browser.close()

  tables = pd.read_html(StringIO(content))

  target_df = None
  for df in tables:
    df.columns = [str(c).strip() for c in df.columns]
    if any(k in df.columns for k in ["XPOS", "xpos", "XPTS", "xpts", "Title"]):
      target_df = df
      break

  if target_df is None and tables:
    target_df = tables[0]

  if target_df is not None:
    # Standardise column names
    col_map = {
        "XPOS": "xpos",
        "TEAM": "team",
        "XPTS": "xpts",
        "TITLE": "Title",
        "PROMOTION": "Promotion",
        "PROMOTION P/O": "Promotion P/O",
        "RELEGATION": "REL",
    }
    target_df = target_df.rename(
        columns={
            c: col_map[c]
            for c in target_df.columns
            if c in col_map or c.upper() in col_map
        }
    )
    target_df["date"] = today_str

  return target_df


def main():
  today_str = datetime.now().strftime("%d-%b-%y")

  # Avoid duplicate entries for the same day
  if DATA_PATH.exists():
    try:
      existing = pd.read_csv(DATA_PATH)
      if (
          "date" in existing.columns
          and today_str in existing["date"].astype(str).values
      ):
        print(
            f"Data for {today_str} already recorded in CSV. Exiting scraper."
        )
        return
    except Exception as e:
      print(f"Notice reading existing file: {e}")

  try:
    df = scrape_predicted_table()
    if df is not None and not df.empty:
      file_exists = DATA_PATH.exists()
      df.to_csv(DATA_PATH, mode="a", index=False, header=not file_exists)
      print(f"Successfully scraped and appended 24 teams for {today_str}!")
    else:
      print("Scraper ran but returned an empty dataset.")
  except Exception as e:
    print(f"Scraper error: {e}")


if __name__ == "__main__":
  main()
