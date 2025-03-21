import requests
import os
from dotenv import load_dotenv
import logging

load_dotenv()
logger = logging.getLogger(__name__)

DATAGOLF_API_KEY = os.getenv('DATAGOLFAPI_KEY')
DATAGOLF_BASE_URL = 'https://feeds.datagolf.com'

def get_rankings():
    """
    Fetch DataGolf and world rankings
    
    Returns:
        dict: Rankings data or None on error
    """
    try:
        response = requests.get(
            f'{DATAGOLF_BASE_URL}/preds/get-dg-rankings',
            params={
                'file_format': 'json',
                'key': DATAGOLF_API_KEY
            }
        )
        response.raise_for_status()
        return response.json()
        
    except Exception as e:
        logger.error(f"Error fetching rankings: {e}")
        return None