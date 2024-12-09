import requests
from data_aggregator.sportcontentapi.headers import sportcontentapi_headers

url = "https://golf-leaderboard-data.p.rapidapi.com/scorecard/"

def get_player_scorecard_raw(golfer_id:int, tournament_id:int):
    """
    Retrieves the scorecard for a specific golfer in a specific tournament.

    Args:
        golfer_id (int): The ID of the golfer. This is the id used by SPORTCONTENTAPI, which gets stored as golfer.sportcontentapi_id in the database.
        tournament_id (int): The ID of the tournament.  This is the id used by SPORTCONTENTAPI, which gets stored as tournament.sportcontentapi_id in the database.

    Returns:
        dict: The scorecard information in JSON format.
    """
    
    query_url = f"{url} + {tournament_id}/{golfer_id}"
    response = requests.get(query_url, headers=sportcontentapi_headers)
    return response.json()

if __name__ == "__main__":
    # TODO: for testing purposes.  Remove when done
    print(get_player_scorecard_raw(101017,220))