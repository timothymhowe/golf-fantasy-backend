import requests
import os
from dotenv import load_dotenv
import logging

load_dotenv()
logger = logging.getLogger(__name__)

DATAGOLF_API_KEY = os.getenv('DATAGOLFAPI_KEY')
DATAGOLF_BASE_URL = 'https://feeds.datagolf.com'

def get_skill_ratings():
    """
    Fetch skill ratings from DataGolf API for both value and ranks displays
    
    Returns:
        tuple: (values_data, ranks_data) or (None, None) on error
    """
    try:
        # Get values display
        values_response = requests.get(
            f'{DATAGOLF_BASE_URL}/preds/skill-ratings',
            params={
                'display': 'value',
                'file_format': 'json',
                'key': DATAGOLF_API_KEY
            }
        )
        values_response.raise_for_status()
        
        # Get ranks display
        ranks_response = requests.get(
            f'{DATAGOLF_BASE_URL}/preds/skill-ratings',
            params={
                'display': 'ranks',
                'file_format': 'json',
                'key': DATAGOLF_API_KEY
            }
        )
        ranks_response.raise_for_status()
        
        return values_response.json(), ranks_response.json()
        
    except Exception as e:
        logger.error(f"Error fetching skill ratings: {e}")
        return None, None