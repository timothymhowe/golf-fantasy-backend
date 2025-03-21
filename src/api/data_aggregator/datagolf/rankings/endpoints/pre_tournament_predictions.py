import requests
import os
from dotenv import load_dotenv
import logging

load_dotenv()
logger = logging.getLogger(__name__)

DATAGOLF_API_KEY = os.getenv('DATAGOLFAPI_KEY')
DATAGOLF_BASE_URL = 'https://feeds.datagolf.com'



def get_pretournament_predictions(tour='pga'):
    """
    Fetch pre-tournament predictions including finish position probabilities
    
    Args:
        tour (str): Tour to get predictions for (default: 'pga')
    
    Returns:
        dict: Prediction data or None on error
    """
    try:
        response = requests.get(
            f'{DATAGOLF_BASE_URL}/preds/pre-tournament',
            params={
                'tour': tour,
                'add_position': '1,2,3,4,5,10,15,20,30,40,50',
                'dead_heat': 'no',
                'odds_format': 'decimal',
                'file_format': 'json',
                'key': DATAGOLF_API_KEY
            }
        )
        response.raise_for_status()
        return response.json()
        
    except Exception as e:
        logger.error(f"Error fetching pre-tournament predictions: {e}")
        return None