import requests
from utils.db_connector import db, init_db
from flask import Flask
from models import Golfer
import logging
from fuzzywuzzy import fuzz
import os
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

DATAGOLF_API_KEY = os.getenv('DATAGOLFAPI_KEY')
DATAGOLF_BASE_URL = 'https://feeds.datagolf.com'

def get_datagolf_players():
    """Get list of all players from DataGolf API"""
    try:
        response = requests.get(
            f'{DATAGOLF_BASE_URL}/get-player-list',
            params={
                'file-format': 'json',
                'key': DATAGOLF_API_KEY
            }
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        logger.error(f"Error fetching DataGolf players: {e}")
        return None

def parse_datagolf_name(player_name: str) -> tuple[str, str]:
    """Parse DataGolf player name format (Last, First) into first and last names"""
    parts = player_name.split(', ', 1)
    if len(parts) == 2:
        return parts[1].strip(), parts[0].strip()  # first_name, last_name
    return '', player_name.strip()

def find_best_match(golfer, datagolf_players):
    """Find best matching DataGolf player for a golfer using multiple matching strategies"""
    best_match = None
    best_score = 0
    perfect_match = False
    
    # Clean and prepare golfer names
    golfer_first = golfer.first_name.lower().strip()
    golfer_last = golfer.last_name.lower().strip()
    golfer_full = f"{golfer_first} {golfer_last}".strip()
    golfer_full_reversed = f"{golfer_last} {golfer_first}".strip()
    golfer_combined = f"{golfer_first}{golfer_last}".strip()
    
    for dg_player in datagolf_players:
        dg_first, dg_last = parse_datagolf_name(dg_player['player_name'])
        
        # Clean and prepare DataGolf names
        dg_first = dg_first.lower().strip()
        dg_last = dg_last.lower().strip()
        dg_full = f"{dg_first} {dg_last}".strip()
        dg_full_reversed = f"{dg_last} {dg_first}".strip()
        dg_combined = f"{dg_first}{dg_last}".strip()
        
        # Calculate various matching scores
        scores = [
            # Exact matches (case insensitive)
            1000 if golfer_full == dg_full else 0,
            1000 if golfer_full == dg_full_reversed else 0,
            1000 if golfer_full_reversed == dg_full else 0,
            1000 if golfer_combined == dg_combined else 0,
            
            # Individual name part matches
            fuzz.ratio(golfer_first, dg_first),
            fuzz.ratio(golfer_last, dg_last),
            fuzz.ratio(golfer_first, dg_last),  # Handle reversed names
            fuzz.ratio(golfer_last, dg_first),  # Handle reversed names
            
            # Full name matches with different arrangements
            fuzz.ratio(golfer_full, dg_full),
            fuzz.ratio(golfer_full, dg_full_reversed),
            fuzz.ratio(golfer_full_reversed, dg_full),
            
            # Token sort ratio (handles word order differences)
            fuzz.token_sort_ratio(golfer_full, dg_full),
            
            # Token set ratio (handles partial matches and extra words)
            fuzz.token_set_ratio(golfer_full, dg_full)
        ]
        
        # Get highest score from all matching strategies
        max_score = max(scores)
        
        # Perfect match found
        if max_score == 1000:
            return dg_player, 100, True
            
        # Update best match if this score is higher
        if max_score > best_score:
            weighted_score = (
                max_score * 0.7 +  # Main score
                fuzz.ratio(golfer_combined, dg_combined) * 0.3  # Combined name similarity as verification
            )
            
            if weighted_score > best_score and weighted_score > 85:
                best_score = weighted_score
                best_match = dg_player
                
                # Log match details for debugging
                print(f"\nMatch details for {golfer_full}:")
                print(f"DataGolf name: {dg_full}")
                print(f"Max score: {max_score}")
                print(f"Weighted score: {weighted_score}")
                print(f"Individual scores: {scores}")
    
    return best_match, best_score, False

def match_golfer_ids():
    """Match golfers in database with their DataGolf IDs"""
    # Get golfers without DataGolf IDs
    unmatched_golfers = Golfer.query.filter(
        (Golfer.datagolf_id.is_(None)) |
        (Golfer.datagolf_id == '')
    ).all()
    
    if not unmatched_golfers:
        print("No unmatched golfers found!")
        return
        
    print(f"Found {len(unmatched_golfers)} golfers without DataGolf IDs")
    
    # Get DataGolf player list
    datagolf_players = get_datagolf_players()
    if not datagolf_players:
        print("Failed to fetch DataGolf players")
        return
        
    print(f"Retrieved {len(datagolf_players)} players from DataGolf")
    
    # Process each unmatched golfer
    for golfer in unmatched_golfers:
        print(f"\nProcessing: {golfer.first_name} {golfer.last_name}")
        
        best_match, match_score, is_perfect = find_best_match(golfer, datagolf_players)
        
        if best_match:
            dg_first, dg_last = parse_datagolf_name(best_match['player_name'])
            print(f"Found match: {dg_first} {dg_last}")
            print(f"Score: {match_score:.1f}")
            print(f"DataGolf ID: {best_match['dg_id']}")
            print(f"Country: {best_match['country']} ({best_match['country_code']})")
            print(f"Amateur: {'Yes' if best_match['amateur'] else 'No'}")
            
            if is_perfect:
                print(f"Perfect match found - automatically accepting")
                confirm = 'y'
            else:
                confirm = input("Accept this match? (y/n/s=skip): ").lower()
            
            if confirm == 'y':
                golfer.first_name = dg_first
                golfer.last_name = dg_last
                golfer.datagolf_id = best_match['dg_id']
                golfer.country = best_match['country']
                golfer.country_code = best_match['country_code']
                golfer.full_name = best_match['player_name']  # Keep DataGolf format
                db.session.commit()
                print("Updated golfer with DataGolf info")
            elif confirm == 's':
                print("Skipping this golfer")
            else:
                print("Match rejected")
        else:
            print("No match found")
            
        print("-" * 50)

if __name__ == "__main__":
    app = Flask(__name__)
    init_db(app)
    
    with app.app_context():
        match_golfer_ids()