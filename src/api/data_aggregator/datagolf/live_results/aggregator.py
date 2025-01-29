import os
import json
from datetime import datetime, timedelta
import firebase_admin
from firebase_admin import credentials, firestore
from dotenv import load_dotenv

# Import the endpoint functions
from data_aggregator.datagolf.live_results.endpoints.live_hole_scoring_distributions import fetch_hole_scoring_distributions
from data_aggregator.datagolf.live_results.endpoints.live_model_predictions import fetch_model_predictions
from data_aggregator.datagolf.live_results.endpoints.live_tournament_stats import fetch_live_stats
from data_aggregator.datagolf.live_results.endpoints.live_cutline import fetch_cutline

# Load environment variables from .env file
load_dotenv()

# Parse the Firebase Admin SDK key from the environment variable
firebase_admin_sdk_key = os.getenv('FIREBASE_ADMIN_SDK_KEY')
firebase_admin_sdk_key_dict = json.loads(firebase_admin_sdk_key)

# Initialize Firebase Admin SDK if not already initialized
if not firebase_admin._apps:
    cred = credentials.Certificate(firebase_admin_sdk_key_dict)
    firebase_admin.initialize_app(cred)

db = firestore.client()

CACHE_EXPIRY_MINUTES = 10  # Define cache expiry time
CACHE_FILE_PATH = 'data_aggregator/datagolf/cache/mega_cache.json'  # Path to cache file

def is_cache_stale(last_updated):
    """Check if the cache is stale based on the last updated timestamp."""
    print("Checking if cache is stale:")
    last_updated_time = datetime.fromisoformat(last_updated)
    is_stale = datetime.utcnow() - last_updated_time > timedelta(minutes=CACHE_EXPIRY_MINUTES)
    
    if is_stale:
        print("Cache is stale, last updated:", last_updated_time)
    else:
        print("Cache is not stale, last updated:", last_updated_time)
    return is_stale

def load_cache():
    """Load cache from a local JSON file."""
    print("Loading cache from:", CACHE_FILE_PATH)
    if os.path.exists(CACHE_FILE_PATH):
        try:
            with open(CACHE_FILE_PATH, 'r') as cache_file:
                # Add debug logging
                content = cache_file.read()
                print(f"Cache file size: {len(content)} bytes")
                try:
                    return json.loads(content)
                except json.JSONDecodeError as e:
                    print(f"Error parsing cache JSON at position {e.pos}: {e.msg}")
                    print(f"Context: {content[max(0, e.pos-50):min(len(content), e.pos+50)]}")
                    # If cache is corrupted, delete it
                    os.remove(CACHE_FILE_PATH)
                    return None
        except Exception as e:
            print(f"Error reading cache file: {e}")
            return None
    return None

def save_cache(data):
    """Save cache to a local JSON file."""
    with open(CACHE_FILE_PATH, 'w') as cache_file:
        json.dump(data, cache_file)

def fetch_combined_data():
    # Load cache with fallback to fresh data
    try:
        cache = load_cache()
        if cache and not is_cache_stale(cache['last_updated']):
            print("Using cached data.")
            return cache
    except Exception as e:
        print(f"Cache error: {e}, fetching fresh data...")
        cache = None

    # Fetch fresh data from endpoints
    print("Fetching new data from endpoints.")
    hole_scoring_distributions = fetch_hole_scoring_distributions()
    model_predictions = fetch_model_predictions()
    tournament_stats = fetch_live_stats()
    cutline_predictions = fetch_cutline()  # Now synchronous
    
    combined_data = {
        'last_updated': datetime.utcnow().isoformat(),
        'hole_scoring_distributions': hole_scoring_distributions,
        'model_predictions': model_predictions,
        'tournament_stats': tournament_stats,
        'cutline_predictions': cutline_predictions
    }

    # Try to save cache, but don't fail if we can't
    try:
        save_cache(combined_data)
    except Exception as e:
        print(f"Error saving cache: {e}")

    return combined_data


def archive_data_to_firebase(data):
    """Archive data to Firebase for historical records."""
    timestamp = datetime.utcnow().isoformat()
    doc_ref = db.collection('datagolf_archive').document(timestamp)
    doc_ref.set(data)

# This module is intended to be imported and used by API endpoints until we implement serverless functions that schedule this process
