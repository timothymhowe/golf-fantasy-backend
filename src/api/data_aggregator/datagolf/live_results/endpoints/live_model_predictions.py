import requests
import os



DATAGOLF_API_KEY = os.getenv('DATAGOLFAPI_KEY')
DATAGOLF_API_URL = f"https://feeds.datagolf.com/preds/in-play?tour=pga&dead_heat=no&odds_format=decimal&file_format=json&key={DATAGOLF_API_KEY}"

def fetch_model_predictions():
    """Fetch the latest tournament state from the DataGolf API."""
    response = requests.get(DATAGOLF_API_URL)
    response.raise_for_status()
    return response.json()
