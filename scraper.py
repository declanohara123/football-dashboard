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

  parsed_data = []

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

      # Scroll down to trigger Opta widget hydration
      page.mouse.wheel(0, 1200)
      page.wait_for_timeout(6000)

      # Search across all frame contexts (including Opta embed frames)
      target_frame = None
      for frame in page.frames:
        try:
          # Check for prediction markers in frame
          txt = frame.inner_text("body").lower()
          if "%" in txt or "xpts" in txt or "title" in txt:
            target_frame = frame
            print(f"Found prediction widget inside frame: {frame.url}")
            break
        except Exception:
          continue

      if not target_frame:
        target_frame = page

      # Extract table rows using JS DOM query across shadow root boundaries
      rows = target_frame.evaluate("""() => {
                const tables = Array.from(document.querySelectorAll('table'));
                let predTable = null;
                for (const t of tables) {
                    if (t.innerText.includes('%') || t.innerText.toLowerCase().includes('xpts')) {
                        predTable = t;
                        break;
                    }
                }
                if (!predTable && tables.length > 1) predTable = tables[1];
                if (!predTable && tables.length > 0) predTable = tables[0];
                if (!predTable) return [];

                return Array.from(predTable.querySelectorAll('tr')).map(tr => {
                    return Array.from(tr.querySelectorAll('td, th')).map(c => c.innerText.trim());
                }).filter(r => r.length >= 3);
            }""")

      for idx, r in enumerate(rows, start=1):
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

    except Exception:
      print("Error during page processing:")
      traceback.print_exc()
      browser.close()
      sys.exit(1)

    browser.close()

  if not parsed_data:
    print("Error: Could not extract predicted team entries.")
    sys.exit(1)

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
