import json
import re
import requests
import pandas as pd
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
CSV_PATH = DATA_DIR / "expected_positions.csv"

# The direct API feed for the Championship simulations
URL = "https://api.performfeeds.com/soccerdata/seasonandtournamentsimulations/1mjq6w6ezkxe611ykkj8rgz7f1?tmcl=al48ooi8acoibema226051250&_fmt=jsonp&_rt=c&_clbk=TM18_al48ooi8acoibema226051250_d12663cef142438da97f0d0278a0d168"

headers = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Referer": "https://theanalyst.com/",
    "Origin": "https://theanalyst.com",
    "Accept": "*/*"
}

def run_scraper():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    
    print("Fetching raw JSON feed from Opta API...")
    response = requests.get(URL, headers=headers)
    if response.status_code != 200:
        print(f"Failed to fetch data. API returned status code: {response.status_code}")
        return
        
    # Strip the JSONP callback wrapper to get clean JSON
    json_str = re.sub(r'^[^(]*\(|\);?$', '', response.text)
    data = json.loads(json_str)
    
    parsed_data = []
    
    # Extract the team array from the Opta schema
    try:
        teams = data['stages']['stage'][0]['teams']['team']
    except KeyError:
        print("Error: Could not locate the 'teams' array in the JSON payload.")
        return

    for team_info in teams:
        team_name = team_info.get("name", "Unknown")
        xpts = 0.0
        ranks = {}
        
        # Predictions array contains both Average Points (type 3) and Rank Distribution (type 5)
        for pred in team_info.get("predictions", {}).get("prediction", []):
            if str(pred.get("type")) == "3":
                xpts = float(pred.get("value", 0))
            
            elif str(pred.get("type")) == "5":
                for r in pred.get("ranks", {}).get("rank", []):
                    # ranks are formatted as floats (e.g. 15.48)
                    ranks[int(r["id"])] = float(r["value"])
        
        # Calculate Championship probabilities based on rank positions
        title_pct = ranks.get(1, 0.0)
        promo_pct = ranks.get(1, 0.0) + ranks.get(2, 0.0)
        playoff_pct = sum(ranks.get(i, 0.0) for i in range(3, 7))
        rel_pct = sum(ranks.get(i, 0.0) for i in range(22, 25))
        
        parsed_data.append({
            "team": team_name,
            "xpts": f"{xpts:.2f}",
            "Title": f"{title_pct:.2f}%",
            "Promotion": f"{promo_pct:.2f}%",
            "Promotion P/O": f"{playoff_pct:.2f}%",
            "REL": f"{rel_pct:.2f}%"
        })

    # Load into DataFrame to calculate expected positions based on xPts
    df = pd.DataFrame(parsed_data)
    df["xpts_num"] = df["xpts"].astype(float)
    df["xpos"] = df["xpts_num"].rank(ascending=False, method="min").astype(int)
    
    # Reorder columns to exactly match your existing CSV format
    df = df[["xpos", "team", "xpts", "Title", "Promotion", "Promotion P/O", "REL"]]
    df = df.sort_values(by="xpos")
    
    date_str = pd.Timestamp.now().strftime("%d-%b-%y")
    df["date"] = date_str
    
    # Merge with the historical CSV to keep the time-series data intact
    if CSV_PATH.exists():
        existing_df = pd.read_csv(CSV_PATH)
        if not existing_df.empty and "date" in existing_df.columns:
            # Overwrite today's data if it already exists to prevent duplication
            existing_df = existing_df[existing_df["date"] != date_str]
            df = pd.concat([existing_df, df], ignore_index=True)
            
    df.to_csv(CSV_PATH, index=False)
    print(f"Successfully processed and saved {len(parsed_data)} Championship teams for date: '{date_str}'.")

if __name__ == "__main__":
    run_scraper()
