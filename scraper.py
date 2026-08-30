import requests
import json

URL = "https://api.performfeeds.com/soccerdata/seasonandtournamentsimulations/1mjq6w6ezkxe611ykkj8rgz7f1?tmcl=al48ooi8acoibema226051250&_fmt=json"

def test_api():
    print("Fetching raw data from Opta API...")
    response = requests.get(URL)
    
    if response.status_code == 200:
        data = response.json()
        # Print the structure for just the first team in the feed
        print("\n--- JSON STRUCTURE ---")
        
        # We need to find the nested list containing the teams.
        # This dumps the first 1500 characters so we can see the exact keys.
        print(json.dumps(data, indent=2)[:1500])
    else:
        print(f"Failed to fetch. Status code: {response.status_code}")

if __name__ == "__main__":
    test_api()
