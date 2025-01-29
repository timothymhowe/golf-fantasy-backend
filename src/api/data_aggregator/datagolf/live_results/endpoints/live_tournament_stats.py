import requests
import os

DATAGOLF_API_KEY = os.getenv('DATAGOLFAPI_KEY')
STATS = 'sg_putt,sg_arg,sg_app,sg_ott,sg_t2g,sg_bs,sg_total,distance,accuracy,gir,prox_fw,prox_rgh,scrambling'

DATAGOLF_LIVE_STATS_URL_VALUE = f"https://feeds.datagolf.com/preds/live-tournament-stats?stats={STATS}&round=event_avg&display=value&key={DATAGOLF_API_KEY}"
DATAGOLF_LIVE_STATS_URL_RANK = f"https://feeds.datagolf.com/preds/live-tournament-stats?stats={STATS}&round=event_avg&display=rank&key={DATAGOLF_API_KEY}"

def fetch_live_stats():
    """Fetch and combine value and rank stats from the DataGolf API."""
    try:
        # Fetch both endpoints
        value_response = requests.get(DATAGOLF_LIVE_STATS_URL_VALUE)
        rank_response = requests.get(DATAGOLF_LIVE_STATS_URL_RANK)
        
        value_response.raise_for_status()
        rank_response.raise_for_status()
        
        value_data = value_response.json()
        rank_data = rank_response.json()
        
        # Initialize combined stats dictionary
        combined_stats = {
            'event_info': value_data.get('event_info', {}),
            'course_name': value_data.get('course_name'),
            'event_name': value_data.get('event_name'),
            'last_updated': value_data.get('last_updated'),
            'field_size':144,
            'live_stats': {}
        }

        # Process all golfers
        for value_golfer in value_data.get('live_stats', []):
            dg_id = value_golfer.get('dg_id')
            if not dg_id:
                continue

            # Find matching rank data for this golfer
            rank_golfer = next(
                (g for g in rank_data.get('live_stats', []) if g.get('dg_id') == dg_id),
                {}
            )

            # Initialize golfer entry with info
            combined_stats['live_stats'][dg_id] = {
                'info': {
                    'player_name': value_golfer.get('player_name'),
                    'position': value_golfer.get('position'),
                    'thru': value_golfer.get('thru'),
                    'today': value_golfer.get('round'),  # 'round' in API is 'today' score
                    'total': value_golfer.get('total')
                }
            }

            # Add all stats with both value and rank
            for stat in STATS.split(','):
                combined_stats['live_stats'][dg_id][stat] = {
                    'value': value_golfer.get(stat),
                    'rank': rank_golfer.get(stat)
                }

        # Update field_size to only count active players
        active_players = sum(
            1 for golfer in combined_stats['live_stats'].values()
            if golfer['info']['position'] != 'CUT'
        )
        
        combined_stats['field_size'] = active_players
        return combined_stats
    except requests.exceptions.RequestException as e:
        print(f"Error fetching live stats: {e}")
        raise


