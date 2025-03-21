import requests
from dotenv import load_dotenv
import os
load_dotenv()

def get_datagolf_rankings():
    """
    Fetches the top 500 players from the DataGolf rankings API endpoint.
    
    Returns:
        list: A list of player IDs from the DataGolf rankings
    """
    url = "https://feeds.datagolf.com/preds/get-dg-rankings"
    params = {
        "file_format": "json",
        "key": os.getenv('DATAGOLFAPI_KEY')
    }

    try:
        response = requests.get(url, params=params)
        response.raise_for_status()  # Raises an HTTPError for bad responses
        
        data = response.json()
        
        # Extract player IDs from the rankings data
        player_ids = []
        if 'rankings' in data:
            for player in data['rankings']:
                if 'dg_id' in player:
                    player_ids.append(player['dg_id'])
                    
        return player_ids
        
    except requests.RequestException as e:
        print(f"Error fetching DataGolf rankings: {e}")
        return []

def get_datagolf_rankings_with_names():
    """
    Fetches the top 500 players from the DataGolf rankings API endpoint.
    
    Returns:
        list: A list of dictionaries containing player IDs and names from the DataGolf rankings
    """
    url = "https://feeds.datagolf.com/preds/get-dg-rankings"
    params = {
        "file_format": "json",
        "key": os.getenv('DATAGOLF_API_KEY')
    }

    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        
        data = response.json()
        
        # Extract player IDs and names from the rankings data
        players = []
        if 'rankings' in data:
            for player in data['rankings']:
                if 'dg_id' in player and 'player_name' in player:
                    players.append({
                        'id': player['dg_id'],
                        'name': player['player_name']
                    })
                    
        return players
        
    except requests.RequestException as e:
        print(f"Error fetching DataGolf rankings: {e}")
        return []




def get_player_image_url(player_id):
    """
    Scrapes a player's profile page to get their headshot image URL.
    
    Args:
        player_id (str): The DataGolf ID of the player
        
    Returns:
        str: URL of the player's headshot image, or None if not found
    """
    import requests
    from bs4 import BeautifulSoup

    profile_url = f"https://datagolf.com/player-profiles?dg_id={player_id}"
    
    try:
        # Request the profile page
        response = requests.get(profile_url)
        response.raise_for_status()
        
        # Parse the HTML
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Find the player image
        img_element = soup.find('img', class_='player-pic')
        if img_element and 'src' in img_element.attrs:
            image_url = img_element['src']
            
            # If URL is relative, make it absolute
            if image_url.startswith('/'):
                image_url = f"https://datagolf.com{image_url}"
            
            return image_url
                
    except requests.RequestException as e:
        print(f"Error fetching profile page for player {player_id}: {e}")
    except Exception as e:
        print(f"Error processing player {player_id}: {e}")
    
    return None

def download_top_10_player_images(output_dir='headshots'):
    """
    Downloads player headshot images from DataGolf for just the top 10 ranked players.
    Converts player names to ASCII to handle special characters.
    Saves to 'headshots' directory in project root.
    
    Args:
        output_dir (str): Directory where images will be saved. Default is 'headshots'
    """
    import os
    import requests
    from pathlib import Path
    import unicodedata
    import time

    def strip_accents(text):
        """
        Strips accents from text, converting to ASCII.
        Example: 'Séb' -> 'Seb'
        """
        return ''.join(c for c in unicodedata.normalize('NFKD', text)
            if unicodedata.category(c) != 'Mn')

    # Create output directory in project root if it doesn't exist
    root_dir = Path(__file__).parents[3]  # Go up 3 levels to reach project root
    output_path = root_dir / output_dir
    output_path.mkdir(parents=True, exist_ok=True)
    
    # Get list of players with IDs and take first 10
    players = get_datagolf_rankings_with_names()[250:]
    
    for player in players:
        player_id = player['id']
        player_name = strip_accents(player['name'])
        
        # Get the image URL for this player
        image_url = get_player_image_url(player_id)
        
        if image_url:
            try:
                # Request the image
                img_response = requests.get(image_url)
                img_response.raise_for_status()
                
                if img_response.status_code == 200:
                    # Create filename using player ID and normalized name
                    filename = f"{player_id}_headshot.png"
                    filepath = output_path / filename
                    
                    # Write image to file
                    with open(filepath, 'wb') as f:
                        f.write(img_response.content)
                    print(f"Downloaded image for {player_name}")
                else:
                    print(f"Failed to download image for {player_name}")
                    
            except requests.RequestException as e:
                print(f"Error downloading image for {player_name}: {e}")
                
            # Add a small delay to be polite
            time.sleep(1)
        else:
            print(f"No image URL found for {player_name}")





if __name__ == "__main__":
    # print(get_datagolf_rankings())
    # print(get_datagolf_rankings_with_names())
    download_top_10_player_images()