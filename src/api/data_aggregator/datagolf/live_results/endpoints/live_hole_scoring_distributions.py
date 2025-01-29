import requests
import os

DATAGOLF_API_KEY = os.getenv('DATAGOLFAPI_KEY')
DATAGOLF_API_URL = f"https://feeds.datagolf.com/preds/live-hole-stats?tour=pga&file_format=json&key={DATAGOLF_API_KEY}"

def fetch_hole_scoring_distributions():
    """Fetch the latest tournament state from the DataGolf API."""
    response = requests.get(DATAGOLF_API_URL)
    response.raise_for_status()
    return response.json()

