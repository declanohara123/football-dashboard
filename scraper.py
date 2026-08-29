import os
import sys
from pathlib import Path
import pandas as pd
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
CSV_PATH = DATA_DIR / "expected_positions.csv"

URL = "https://theanalyst.com/competition/english-championship/table"


def run_scraper():
  DATA_DIR.mkdir(parents=True, exist_ok=True)

  existing_df = pd.DataFrame()
  if CSV_PATH.exists():
    try:
      existing_df = pd.read_csv(CSV_PATH)
      if len(existing_df.columns) <= 1:
        existing_df = pd.read_csv(CSV_PATH, sep="\t")
    except Exception as e:
      print(f"Warning reading existing CSV: {e}")

  with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    # Custom User-Agent to prevent bot blocking
    context = browser.new_context(
        user_agent=(
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        )
    )
    page = context.new_page()

    try:
      print(f"Navigating to {URL}...")
      # Use domcontentloaded instead of networkidle to prevent 30s timeouts
      page.goto(URL, wait_until="domcontentloaded", timeout=60000)

      # Wait specifically for the table element to load into the DOM
      page.wait_for_selector("table", timeout=30000)
      page.wait_for_timeout(3000)  # Short buffer for dynamic JS rendering

      html_content = page.content()
    except Exception as e:
      print(f"Scraper error during page load: {e}")
      browser.close()
      sys.exit(1)

    browser.close()

  soup = BeautifulSoup(html_content, "html.parser")
  table = soup.find("table")

  if not table:
    print("Error: Could not find any table element on the page.")
    sys.exit(1)

  # Parse table headers
  headers = [
      th.get_text(strip=True)
      for th in table.find_all("th")
      if th.get_text(strip=True)
  ]

  rows = []
  for tr in table.find_all("tr"):
    cells = [td.get_text(strip=True) for td in tr.find_all("td")]
    if len(cells) >= 6:
      rows.append(cells)

  if not rows:
    print("Error: No data rows extracted from table.")
    sys.exit(1)

  # Map extracted table rows into standard DataFrame
  parsed_data = []
  for r in rows:
    # Expected table format: Pos, Team, xPts, Title %, Promo %, PO %, Rel %
    parsed_data.append({
        "xpos": r[0],
        "team": r[1],
        "xpts": r[2],
        "Title": r[3] if len(r) > 3 else "0%",
        "Promotion": r[4] if len(r) > 4 else "0%",
        "Promotion P/O": r[5] if len(r) > 5 else "0%",
        "REL": r[6] if len(r) > 6 else "0%",
    })

  new_df = pd.DataFrame(parsed_data)

  # Grab date stamp from webpage header if available, otherwise use today's date
  date_heading = soup.find(
      lambda tag: tag.name in ["h2", "h3", "p", "div", "span"]
      and "Updated" in tag.text
  )
  if date_heading:
    date_str = date_heading.text.replace("Updated", "").strip()
  else:
    date_str = pd.Timestamp.now().strftime("%d-%b-%y")

  new_df["date"] = date_str

  if not existing_df.empty and "date" in existing_df.columns:
    if date_str in existing_df["date"].values:
      print(f"Data for date '{date_str}' is already recorded. Exiting.")
      sys.exit(0)
    updated_df = pd.concat([existing_df, new_df], ignore_index=True)
  else:
    updated_df = new_df

  updated_df.to_csv(CSV_PATH, index=False)
  print(
      f"Successfully scraped and appended {len(new_df)} team entries for date:"
      f" '{date_str}'."
  )


if __name__ == "__main__":
  run_scraper()
