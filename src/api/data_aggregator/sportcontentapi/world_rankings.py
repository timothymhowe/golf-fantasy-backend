import requests
from data_aggregator.sportcontentapi.headers import sportcontentapi_headers

url = "https://golf-leaderboard-data.p.rapidapi.com/world-rankings"

def get_world_rankings():
    """
    Retrieves the current world rankings for golfers.

    Returns:
        dict: The world rankings data in JSON format.
    """
    
    response = requests.get(url, headers=sportcontentapi_headers)
    return response.json()

if __name__ == "__main__":
    print (get_world_rankings())