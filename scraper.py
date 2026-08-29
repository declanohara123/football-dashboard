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

      # Wait specifically for table rows containing data cells to render
      page.wait_for_selector("table tbody tr td", timeout=45000)
      page.wait_for_timeout(3000)  # Buffer to allow all 24 teams to render

      html_content = page.content()
    except Exception as e:
      print(f"Scraper error during page load: {e}")
      browser.close()
      sys.exit(1)

    browser.close()

  soup = BeautifulSoup(html_content, "html.parser")
  table = soup.find("table")

  if not table:
    print("Error: Could not find table element on page.")
    sys.exit(1)

  rows = []
  tbody = table.find("tbody") or table
  for tr in tbody.find_all("tr"):
    cells = [td.get_text(strip=True) for td in tr.find_all(["td", "th"])]
    if len(cells) >= 3:
      rows.append(cells)

  if not rows:
    print("Error: No populated data rows extracted from table.")
    sys.exit(1)

  parsed_data = []
  for idx, r in enumerate(rows, start=1):
    # Detect position column vs team name column dynamically
    first_col = r[0]
    if first_col.isdigit():
      pos_val = first_col
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
