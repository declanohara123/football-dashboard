import json
import re
import requests

# Use the exact callback URL you extracted from the Network tab
URL = "https://api.performfeeds.com/soccerdata/seasonandtournamentsimulations/1mjq6w6ezkxe611ykkj8rgz7f1?tmcl=al48ooi8acoibema226051250&_fmt=jsonp&_rt=c&_clbk=TM18_al48ooi8acoibema226051250_d12663cef142438da97f0d0278a0d168"

headers = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Referer": "https://theanalyst.com/",
    "Origin": "https://theanalyst.com",
    "Accept": "*/*"
}

def test_api():
    print("Fetching raw data with browser headers...")
    response = requests.get(URL, headers=headers)
    
    if response.status_code == 200:
        raw_text = response.text
        print("Success! Extracting JSON payload...")
        
        # Strip the JSONP callback wrapper TM18_...(...) to leave clean JSON
        json_str = re.sub(r'^[^(]*\(|\);?$', '', raw_text)
        data = json.loads(json_str)
        
        print("\n--- JSON KEYS AVAILABLE ---")
        print(data.keys())
        print("\n--- FIRST 1200 CHARACTERS OF PAYLOAD ---")
        print(json.dumps(data, indent=2)[:1200])
    else:
        print(f"Failed to fetch. Status code: {response.status_code}")

if __name__ == "__main__":
    test_api()
