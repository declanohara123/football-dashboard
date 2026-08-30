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
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            viewport={"width": 1440, "height": 900}
        )
        page = context.new_page()

        try:
            print(f"Navigating to {URL}...")
            page.goto(URL, wait_until="networkidle", timeout=60000)
            page.wait_for_timeout(5000)

            # Check if prediction table is hosted inside an iframe
            frames = page.frames
            print(f"Found {len(frames)} frames on page.")
            for idx, frame in enumerate(frames):
                print(f"Frame {idx} URL: {frame.url}")

            html_content = page.content()
            
            # Search frames for target table
            target_html = html_content
            for frame in frames:
                try:
                    f_content = frame.content()
                    if "%" in f_content or "xpts" in f_content.lower():
                        print(f"Target prediction data located in frame index {idx}!")
                        target_html = f_content
                        break
                except Exception:
                    continue

        except Exception:
            print("Scraper error during navigation:")
            traceback.print_exc()
            browser.close()
            sys.exit(1)

        browser.close()

    soup = BeautifulSoup(target_html, "html.parser")
    tables = soup.find_all("table")

    print(f"Found {len(tables)} tables total.")
    
    predicted_table = None
    for idx, tbl in enumerate(tables):
        text = tbl.get_text().lower()
        print(f"--- Table {idx} snippet ---")
        print(text[:200])
        # Prediction table MUST contain percentages or xpts
        if "%" in text or "xpts" in text or "promotion" in text:
            predicted_table = tbl
            print(f"Selected prediction table at index {idx}.")
            break

    if not predicted_table:
        print("Error: Opta prediction table with percentage probabilities was not rendered in DOM.")
        sys.exit(1)

    rows = []
    tbody = predicted_table.find("tbody") or predicted_table
    for tr in tbody.find_all("tr"):
        cells = [td.get_text(strip=True) for td in tr.find_all(["td", "th"])]
        if len(cells) >= 3:
            rows.append(cells)

    parsed_data = []
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

    new_df = pd.DataFrame(parsed_data)
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
