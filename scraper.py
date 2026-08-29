import os
import sys
import traceback
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
      page.goto(URL, wait_until="domcontentloaded", timeout=60000)

      # Wait for table elements to fully mount into DOM
      page.wait_for_selector("table", timeout=45000)
      page.wait_for_timeout(4000)

      html_content = page.content()
    except Exception:
      print("Scraper error during page navigation:")
      traceback.print_exc()
      browser.close()
      sys.exit(1)

    browser.close()

  soup = BeautifulSoup(html_content, "html.parser")
  tables = soup.find_all("table")

  if not tables:
    print("Error: Could not find any table element on the page.")
    sys.exit(1)

  # Target specifically the table containing Opta prediction headers (xPts / Title / Promotion / REL)
  predicted_table = None
  for tbl in tables:
    header_text = tbl.get_text().lower()
    if any(k in header_text for k in ["xpts", "title", "promotion", "rel"]):
      predicted_table = tbl
      break

  # Fallback to the widest table if explicit headers aren't in <thead>
  if not predicted_table:
    predicted_table = max(tables, key=lambda t: len(t.find_all("tr")))

  tbody = predicted_table.find("tbody") or predicted_table
  rows = []
  for tr in tbody.find_all("tr"):
    cells = [td.get_text(strip=True) for td in tr.find_all(["td", "th"])]
    if len(cells) >= 3:
      rows.append(cells)

  if not rows:
    print("Error: No data rows extracted from predicted table.")
    sys.exit(1)

  parsed_data = []
  for idx, r in enumerate(rows, start=1):
    # Skip header row if present in tbody
    if r[0].lower() in ["pos", "position", "#", "rank", "team"]:
      continue

    if r[0].isdigit():
      pos_val = r[0]
      team_val = r[1]
      pts_val = r[2] if len(r) > 2 else "0"
      title_val = r[3] if len(r) > 3 else "0%"
      promo_val = r[4] if len(r) > 4 else "0%"
      po_val = r[5] if len(r) > 5 else "0%"
      rel_val = r[6] if len(r) > 6 else "0%"
    else:
      pos_val = str(idx)
      team_val = r[0]
      pts_val = r[1] if len(r) > 1 else "0"
      title_val = r[2] if len(r) > 2 else "0%"
      promo_val = r[3] if len(r) > 3 else "0%"
      po_val = r[4] if len(r) > 4 else "0%"
      rel_val = r[5] if len(r) > 5 else "0%"

    parsed_data.append({
        "xpos": pos_val,
        "team": team_val,
        "xpts": pts_val,
        "Title": title_val,
        "Promotion": promo_val,
        "Promotion P/O": po_val,
        "REL": rel_val,
    })

  if not parsed_data:
    print("Error: Parsed data empty after processing rows.")
    sys.exit(1)

  new_df = pd.DataFrame(parsed_data)

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
      print(f"Data for date '{date_str}' is already recorded in CSV. Exiting.")
      sys.exit(0)
    updated_df = pd.concat([existing_df, new_df], ignore_index=True)
  else:
    updated_df = new_df

  updated_df.to_csv(CSV_PATH, index=False)
  print(
      f"Successfully scraped and appended {len(new_df)} team entries for predicted table date: '{date_str}'."
  )


if __name__ == "__main__":
  try:
    run_scraper()
  except Exception:
    print("Fatal exception encountered during scraper run:")
    traceback.print_exc()
    sys.exit(1)
