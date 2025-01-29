import requests
import os
import asyncio
from data_aggregator.datagolf.live_results.live_results_cache import load_cache, save_cache, is_cache_stale
from datetime import datetime
from data_aggregator.datagolf.live_results.aggregator import fetch_combined_data as big_fetch

DATAGOLF_API_KEY = os.getenv('DATAGOLFAPI_KEY')
DATAGOLF_API_URL = f"https://feeds.datagolf.com/preds/live-tournament-stats?stats=sg_putt,sg_arg,sg_app,sg_ott,sg_t2g,sg_bs,sg_total,distance,accuracy,gir,prox_fw,prox_rgh,scrambling&round=event_avg&display=value&key={DATAGOLF_API_KEY}"

def fetch_tournament_state():
    """Fetch the latest tournament state from the DataGolf API."""
    response = requests.get(DATAGOLF_API_URL)
    response.raise_for_status()
    return response.json()

def get_latest_tournament_state():
    """Get the latest tournament state, updating if necessary."""
    cache = load_cache()
    if is_cache_stale(cache['last_updated']):
        # Fetch new data if cache is stale
        tournament_state = fetch_tournament_state()
        cache = {
            'tournament_state': tournament_state,
            'last_updated': datetime.utcnow().isoformat()
        }
        save_cache(cache)
    else:
        tournament_state = cache['tournament_state']

    return tournament_state

def a_big_fetch():
    print("passing big fetch to aggregator")
    return big_fetch()

def sync_big_fetch():
    return asyncio.run(a_big_fetch())