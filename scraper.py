import sys
import traceback
import pandas as pd
from pathlib import Path
from playwright.sync_api import sync_playwright

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
CSV_PATH = DATA_DIR / "expected_positions.csv"

# Target the standalone widget to bypass main-site anti-bot and iframe nesting
URL = "https://dataviz.theanalyst.com/opta-football-predictions/?competition=al48ooi8acoibema226051250"

def run_scraper():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    
    existing_df = pd.DataFrame()
    if CSV_PATH.exists():
        try:
            existing_df = pd.read_csv(CSV_PATH)
            if len(existing_df.columns) <= 1:
                existing_df = pd.read_csv(CSV_PATH, sep="\t")
        except Exception:
            pass

    scraped_rows = {}

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True) 
        context = browser.new_context(
            viewport={"width": 1440, "height": 900},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = context.new_page()

        try:
            print(f"Navigating to {URL}...")
            page.goto(URL, wait_until="networkidle", timeout=60000)
            page.wait_for_timeout(5000)

            print("Hunting for the Predictions tab...")
            # Aggressive JS clicker: scans all elements for exact text match
            clicked = page.evaluate("""() => {
                const elements = Array.from(document.querySelectorAll('*'));
                const btn = elements.find(el => {
                    const text = el.innerText ? el.innerText.trim() : '';
                    // Match "Prediction" or "Predictions" exactly, ignore large container elements
                    return (text === 'Prediction' || text === 'Predictions') && el.children.length === 0;
                });
                
                if (btn) {
                    btn.click();
                    return true;
                }
                return false;
            }""")

            if not clicked:
                print("Could not locate the Predictions tab.")
                sys.exit(1)
                
            print("Successfully clicked Predictions tab.")
            page.wait_for_timeout(3000)
            
            # Click centre to ensure keyboard focus
            page.mouse.click(720, 500)

            print("Scrolling and extracting data...")
            for i in range(20):
                rows = page.evaluate("""() => {
                    const tables = Array.from(document.querySelectorAll('table'));
                    let target = tables.find(t => t.innerText.includes('%') || t.innerText.toLowerCase().includes('xpts'));
                    if (!target && tables.length > 0) target = tables[0];
                    if (!target) return [];
                    return Array.from(target.querySelectorAll('tr')).map(tr => 
                        Array.from(tr.querySelectorAll('td, th')).map(c => c.innerText.trim())
                    );
                }""")
                
                for r in rows:
                    if len(r) >= 4 and any('%' in str(c) for c in r):
                        if str(r[0]).replace('.', '', 1).isdigit():
                            team = r[1]
                            if team.lower() not in ["team", "pr", "win", "draw", "real madrid", "málaga", ""]:
                                scraped_rows[team] = r
                
                print(f"Scroll {i+1}: Found {len(scraped_rows)}/24 teams...")
                if len(scraped_rows) >= 24:
                    print("All 24 Championship teams successfully extracted!")
                    break
                
                page.keyboard.press("PageDown")
                page.wait_for_timeout(600)

        except Exception as e:
            print("Error during scraping:")
            traceback.print_exc()
        finally:
            browser.close()

    if not scraped_rows:
        print("Error: Could not extract simulation entries.")
        sys.exit(1)

    parsed_data = []
    for team_val, r in scraped_rows.items():
        parsed_data.append({
            "xpos": str(r[0]),
            "team": str(team_val),
            "xpts": str(r[2]) if len(r) > 2 else "0",
            "Title": str(r[3]) if len(r) > 3 else "0%",
            "Promotion": str(r[4]) if len(r) > 4 else "0%",
            "Promotion P/O": str(r[5]) if len(r) > 5 else "0%",
            "REL": str(r[6]) if len(r) > 6 else "0%"
        })

    new_df = pd.DataFrame(parsed_data).sort_values(by="xpos")
    date_str = pd.Timestamp.now().strftime("%d-%b-%y")
    new_df["date"] = date_str

    if not existing_df.empty and "date" in existing_df.columns:
        existing_df = existing_df[existing_df["date"] != date_str]
        updated_df = pd.concat([existing_df, new_df], ignore_index=True)
    else:
        updated_df = new_df

    updated_df.to_csv(CSV_PATH, index=False)
    print(f"Successfully saved {len(new_df)} predicted team entries for date: '{date_str}'.")

if __name__ == "__main__":
    try:
        run_scraper()
    except Exception:
        print("Fatal exception encountered during scraper run:")
        traceback.print_exc()
        sys.exit(1)
