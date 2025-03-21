import os
import json
from datetime import datetime, timedelta
import firebase_admin
from firebase_admin import credentials, firestore
from dotenv import load_dotenv

from data_aggregator.datagolf.rankings.endpoints.rankings import get_rankings
from data_aggregator.datagolf.rankings.endpoints.skill_ratings import get_skill_ratings
from data_aggregator.datagolf.rankings.endpoints.skill_decompositions import get_player_decompositions
from data_aggregator.datagolf.rankings.endpoints.pre_tournament_predictions import get_pretournament_predictions

import logging

# Load environment variables
load_dotenv()
logger = logging.getLogger(__name__)

# Initialize Firebase if not already initialized
if not firebase_admin._apps:
    firebase_admin_sdk_key = os.getenv('FIREBASE_ADMIN_SDK_KEY')
    firebase_admin_sdk_key_dict = json.loads(firebase_admin_sdk_key)
    cred = credentials.Certificate(firebase_admin_sdk_key_dict)
    firebase_admin.initialize_app(cred)

db = firestore.client()

CACHE_EXPIRY_HOURS = 6  # Cache for 24 hours
CACHE_FILE_PATH = 'data_aggregator/datagolf/cache/rankings_cache.json'

def is_cache_stale(last_updated):
    """Check if the cache is stale based on the last updated timestamp."""
    last_updated_time = datetime.fromisoformat(last_updated)
    return datetime.utcnow() - last_updated_time > timedelta(hours=CACHE_EXPIRY_HOURS)

def save_to_firestore(endpoint: str, data: dict):
    """Save raw API response to Firestore"""
    try:
        timestamp = datetime.utcnow().isoformat()
        doc_ref = db.collection('datagolf_rankings_archive').document(timestamp)
        doc_ref.set({
            'endpoint': endpoint,
            'data': data,
            'timestamp': timestamp
        })
    except Exception as e:
        logger.error(f"Error saving to Firestore: {e}")

def get_aggregated_stats():
    """
    Aggregate stats from all DataGolf endpoints into a unified tournament data structure.

    Returns:
        dict: Tournament and player data in the following format:
        {
            "event_name": str,
            "course_name": str,
            "last_updated": str,
            "players": {
                "dg_id": {
                    "bio": {
                        "name": str,
                        "datagolf_rank": int,
                        "owgr_rank": int,
                        "country_code":str
                    },
                    "course_fit": None | {
                        "age": int,
                        "baseline_pred": float,
                        "final_pred": float,
                        "course_history_adjustment": float,
                        "course_fit_adjustment": float
                    },
                    "predictions": None | {
                        "baseline": {
                            "win": float,
                            "top_2": float,
                            ... # top_3 through top_50
                            "make_cut": float
                        },
                        "baseline_history_fit": {
                            # same structure as baseline
                        }
                    },
                    "skill_ratings": None | {
                        "ranks": {
                            "sg_total": int,
                            "sg_ott": int,
                            "sg_app": int,
                            "sg_arg": int,
                            "sg_putt": int
                        },
                        "values": {
                            "sg_total": float,
                            "sg_ott": float,
                            "sg_app": float,
                            "sg_arg": float,
                            "sg_putt": float,
                            "driving_dist": float,
                            "driving_acc": float
                        }
                    }
                }
                # ... more players
            }
        }
        
        Note: Top-level sections (course_fit, predictions, skill_ratings) will be None if 
        data is not available for that player.
    """
    try:
        # Check cache first
        if os.path.exists(CACHE_FILE_PATH):
            with open(CACHE_FILE_PATH, 'r') as f:
                cache = json.load(f)
                if not is_cache_stale(cache['last_updated']):
                    logger.info("Returning cached rankings data")
                    return cache['data']

        # Fetch fresh data
        predictions_data = get_pretournament_predictions()
        values_data, ranks_data = get_skill_ratings()
        rankings_data = get_rankings()
        decomp_data = get_player_decompositions()

        # Save raw responses to Firestore
        if values_data:
            save_to_firestore('skill_ratings_values', values_data)
        if ranks_data:
            save_to_firestore('skill_ratings_ranks', ranks_data)
        if rankings_data:
            save_to_firestore('rankings', rankings_data)
        if decomp_data:
            save_to_firestore('decompositions', decomp_data)
        print("attempting to save predictions data")
        if predictions_data:
            print("got predictions data!")
            save_to_firestore('predictions', predictions_data)

        if not all([values_data, ranks_data, rankings_data, decomp_data, predictions_data]):
            logger.error("Failed to fetch all required data")
            return None
            
        # Create tournament-level structure
        tournament_data = {
            'event_name': decomp_data.get('event_name'),
            'course_name': decomp_data.get('course_name'),
            'last_updated': decomp_data.get('last_updated'),
            'players': {}
        }
        
        # Process player data
        if 'rankings' in rankings_data:
            for player in rankings_data['rankings']:
                dg_id = player['dg_id']
                tournament_data['players'][dg_id] = {
                    'bio': {
                        'name': player.get('player_name'),
                        'datagolf_rank': player.get('datagolf_rank'),
                        'owgr_rank': player.get('owgr_rank'),
                        'country_code': player.get('country')
                    }
                }

          
        # Initialize basic structure for all players
        for dg_id in tournament_data['players']:
            tournament_data['players'][dg_id].update({
                'course_fit': None,
                'predictions': None,
                'skill_ratings': None
            })

        # Add pre-tournament predictions
        if 'baseline' in predictions_data:
            print("Found baseline predictions, attempting to process...")
            print(f"Number of players in baseline: {len(predictions_data['baseline'])}")
            for player in predictions_data['baseline']:
                dg_id = player['dg_id']
                print(f"Processing predictions for player {dg_id}")
                if dg_id in tournament_data['players']:
                    print(f"Found matching player in tournament data, adding predictions")
                    tournament_data['players'][dg_id]['predictions'] = {
                        'baseline': {
                            'win': player.get('win'),
                            'top_2': player.get('top_2'),
                            'top_3': player.get('top_3'),
                            'top_4': player.get('top_4'),
                            'top_5': player.get('top_5'),
                            'top_10': player.get('top_10'),
                            'top_15': player.get('top_15'),
                            'top_20': player.get('top_20'),
                            'top_30': player.get('top_30'),
                            'top_40': player.get('top_40'),
                            'top_50': player.get('top_50'),
                            'make_cut': player.get('make_cut')
                        },
                        'baseline_history_fit': {
                            'win': player.get('win'),
                            'top_2': player.get('top_2'),
                            'top_3': player.get('top_3'),
                            'top_4': player.get('top_4'),
                            'top_5': player.get('top_5'),
                            'top_10': player.get('top_10'),
                            'top_15': player.get('top_15'),
                            'top_20': player.get('top_20'),
                            'top_30': player.get('top_30'),
                            'top_40': player.get('top_40'),
                            'top_50': player.get('top_50'),
                            'make_cut': player.get('make_cut')
                        }
                    }
                else:
                    print(f"Player {dg_id} not found in tournament data")

        # Add skill ratings
        for player in values_data['players']:
            dg_id = player['dg_id']
            if dg_id in tournament_data['players']:
                tournament_data['players'][dg_id]['skill_ratings'] = {
                    'values': {
                        'sg_total': player['sg_total'],
                        'sg_ott': player['sg_ott'],
                        'sg_app': player['sg_app'],
                        'sg_arg': player['sg_arg'],
                        'sg_putt': player['sg_putt'],
                        'driving_dist': player['driving_dist'],
                        'driving_acc': player['driving_acc']
                    }
                }

        # Add skill rating ranks
        for player in ranks_data['players']:
            dg_id = player['dg_id']
            if dg_id in tournament_data['players']:
                tournament_data['players'][dg_id]['skill_ratings']['ranks'] = {
                    'sg_total': player['sg_total'],
                    'sg_ott': player['sg_ott'],
                    'sg_app': player['sg_app'],
                    'sg_arg': player['sg_arg'],
                    'sg_putt': player['sg_putt']
                }
                    
        # Add decompositions
        if 'players' in decomp_data:
            for player in decomp_data['players']:
                dg_id = player['dg_id']
                if dg_id in tournament_data['players']:
                    tournament_data['players'][dg_id]['course_fit'] = {
                        'baseline_pred': player['baseline_pred'],
                        'final_pred': player['final_pred'],
                        'course_history_adjustment': player['course_history_adjustment'],
                        'course_fit_adjustment': player.get('total_fit_adjustment'),
                        'age': player.get('age')
                    }
      

        # Save to cache
        cache_data = {
            'data': tournament_data,
            'last_updated': datetime.utcnow().isoformat()
        }
        os.makedirs(os.path.dirname(CACHE_FILE_PATH), exist_ok=True)
        with open(CACHE_FILE_PATH, 'w') as f:
            json.dump(cache_data, f)

        return tournament_data
        
    except Exception as e:
        logger.error(f"Error aggregating stats: {e}")
        return None