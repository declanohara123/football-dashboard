import os
import sys
import traceback
from pathlib import Path
import pandas as pd
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

  extracted_rows = []

  with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    context = browser.new_context(
        user_agent=(
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        ),
        viewport={"width": 1440, "height": 900},
    )
    page = context.new_page()

    try:
      print(f"Navigating to {URL}...")
      page.goto(URL, wait_until="networkidle", timeout=60000)
      page.mouse.wheel(0, 1000)
      page.wait_for_timeout(6000)

      # Evaluate JS directly in browser DOM to pull all table rows (including shadow roots)
      extracted_rows = page.evaluate("""() => {
                const allTables = Array.from(document.querySelectorAll('table'));
                let targetTable = null;
                
                for (const tbl of allTables) {
                    if (tbl.innerText.includes('%') || tbl.innerText.toLowerCase().includes('xpts')) {
                        targetTable = tbl;
                        break;
                    }
                }
                
                if (!targetTable && allTables.length > 0) {
                    targetTable = allTables.length > 1 ? allTables[1] : allTables[0];
                }
                
                if (!targetTable) return [];
                
                const trs = Array.from(targetTable.querySelectorAll('tr'));
                return trs.map(tr => {
                    const cells = Array.from(tr.querySelectorAll('td, th'));
                    return cells.map(c => c.innerText.trim());
                }).filter(r => r.length >= 3);
            }""")

    except Exception:
      print("Error evaluating browser DOM:")
      traceback.print_exc()
      browser.close()
      sys.exit(1)

    browser.close()

  if not extracted_rows:
    print("Error: Could not extract table rows using DOM evaluation.")
    sys.exit(1)

  parsed_data = []
  for idx, r in enumerate(extracted_rows, start=1):
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

  new_df = pd.DataFrame(parsed_data).drop_duplicates(subset=["team"])
  date_str = pd.Timestamp.now().strftime("%d-%b-%y")
  new_df["date"] = date_str

  if not existing_df.empty and "date" in existing_df.columns:
    existing_df = existing_df[existing_df["date"] != date_str]
    updated_df = pd.concat([existing_df, new_df], ignore_index=True)
  else:
    updated_df = new_df

  updated_df.to_csv(CSV_PATH, index=False)
  print(
      f"Successfully scraped {len(new_df)} predicted team entries for date:"
      f" '{date_str}'."
  )


if __name__ == "__main__":
  try:
    run_scraper()
  except Exception:
    print("Fatal exception encountered during scraper run:")
    traceback.print_exc()
    sys.exit(1)
