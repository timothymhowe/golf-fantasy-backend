import requests
from data_aggregator.sportcontentapi.headers import sportcontentapi_headers

url = "https://golf-leaderboard-data.p.rapidapi.com/leaderboard/"

def get_tournament_leaderboard_raw(tournament_id:int):
    """
    Retrieves the leaderboard for a specific tournament as a JSON object.

    Args:
        tournament_id (int): The ID of the tournament. This is the id used by SPORTCONTENTAPI, 
        which gets stored as tournament.sportcontentapi_id in the database.

    Returns:
        dict: The leaderboard data in JSON format or None if request fails.
    """
    try:
        query_url = f"{url}{tournament_id}"
        response = requests.get(query_url, headers=sportcontentapi_headers)
        response.raise_for_status()
        raw_data = response.json()
        return raw_data
    except requests.exceptions.RequestException as e:
        print(f"Error fetching tournament leaderboard: {e}")
        return None

def get_tournament_leaderboard_clean(tournament_id:int):
    """
    Retrieves and cleans the leaderboard data for a specific tournament.

    Args:
        tournament_id (int): The ID of the tournament.

    Returns:
        list: The cleaned leaderboard results or None if no data available.
    """
    raw_data = get_tournament_leaderboard_raw(tournament_id)
    if not raw_data or 'results' not in raw_data:
        return None
    
    # Extract the leaderboard array from the nested structure
    return raw_data['results']['leaderboard']

if __name__ == "__main__":
    test_tournament_id = 25
    results = get_tournament_leaderboard_clean(test_tournament_id)
    if results:
        print(f"Found {len(results)} player results")
        # Print first result as sample
        print("\nSample result:")
        print(results[0])