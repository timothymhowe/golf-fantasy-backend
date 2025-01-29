import json
import os
from datetime import datetime, timedelta

CACHE_FILE = 'data_aggregator/data_golf/cache/live_results_cache.json'

def load_cache():
    """Load cache from a file."""
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, 'r') as f:
            return json.load(f)
    return {'tournament_state': None, 'last_updated': None}

def save_cache(data):
    """Save cache to a file."""
    with open(CACHE_FILE, 'w') as f:
        json.dump(data, f)

def is_cache_stale(last_updated, max_age_minutes=10):
    """Check if the cache is stale."""
    if last_updated is None:
        return True
    last_updated_time = datetime.fromisoformat(last_updated)
    return (datetime.utcnow() - last_updated_time) > timedelta(minutes=max_age_minutes)
