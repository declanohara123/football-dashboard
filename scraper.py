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
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            viewport={"width": 1440, "height": 900}
        )
        page = context.new_page()

        try:
            print(f"Navigating to {URL}...")
            page.goto(URL, wait_until="networkidle", timeout=60000)
            page.mouse.wheel(0, 1000)
            
            # Check if there is a 'Predictions' or 'Expected' tab button to click
            try:
                pred_tab = page.locator("button, a, div").filter(has_text="Prediction").first
                if pred_tab.is_visible():
                    print("Found 'Prediction' toggle tab. Clicking...")
                    pred_tab.click()
                    page.wait_for_timeout(3000)
            except Exception:
                pass

            # Wait explicitly for percentage symbols in the widget
            page.wait_for_selector("text='%'", timeout=15000)
            page.wait_for_timeout(3000)

            # Pull rows directly from the table containing % values
            rows = page.evaluate("""() => {
                const allTables = Array.from(document.querySelectorAll('table'));
                let targetTable = allTables.find(t => t.innerText.includes('%') || t.innerText.toLowerCase().includes('xpts'));
                
                if (!targetTable) {
                    // Search inside Shadow DOM elements if top-level table search fails
                    const allNodes = Array.from(document.querySelectorAll('*'));
                    for (const node of allNodes) {
                        if (node.shadowRoot) {
                            const shadowTables = Array.from(node.shadowRoot.querySelectorAll('table'));
                            const found = shadowTables.find(t => t.innerText.includes('%'));
                            if (found) {
                                targetTable = found;
                                break;
                            }
                        }
                    }
                }

                if (!targetTable) return [];

                return Array.from(targetTable.querySelectorAll('tr')).map(tr => {
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
                    "REL": rel_val
                })

        except Exception:
            print("Error during DOM extraction:")
            traceback.print_exc()
            browser.close()
            sys.exit(1)

        browser.close()

    if not parsed_data:
        print("Error: Could not find prediction table with percentage metrics.")
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
    print(f"Successfully scraped {len(new_df)} predicted team entries for date: '{date_str}'.")


if __name__ == "__main__":
    try:
        run_scraper()
    except Exception:
        print("Fatal exception encountered during scraper run:")
        traceback.print_exc()
        sys.exit(1)
