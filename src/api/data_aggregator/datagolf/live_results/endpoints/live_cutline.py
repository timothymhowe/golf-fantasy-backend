from functools import lru_cache
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

@lru_cache(maxsize=1)
def fetch_cutline_cached():
    """
    Fetches cut line data from DataGolf using Playwright with caching.
    Returns a dictionary of cut line predictions and their probabilities.
    """
    
    return {'predictions': {}}
    
    # TODO: Fix this nonsense later
    try:
        with sync_playwright() as p:
            # Launch browser with minimal overhead
            browser = p.chromium.launch(
                headless=True,
                args=['--disable-gpu', '--no-sandbox', '--disable-dev-shm-usage']
            )
            
            # Create context with tight timeouts
            context = browser.new_context(
                viewport={'width': 1280, 'height': 720},
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            )
            
            page = context.new_page()
            page.set_default_timeout(10000)  # 10 second timeout
            
            # Navigate and wait for content
            page.goto("https://datagolf.com/live-model/pga-tour")
            page.wait_for_selector(".the-val-1:not(:empty)", timeout=10000)
            
            predictions = {}
            for i in range(1, 4):
                try:
                    value = page.locator(f".the-val-{i}").inner_text()
                    prob = page.locator(f".cut-per-{i}").inner_text().rstrip('%')
                    if value and prob:
                        predictions[value] = float(prob)
                except Exception as e:
                    logger.warning(f"Failed to parse cut line {i}: {str(e)}")
                    continue
            
            return {'predictions': predictions}
            
    except Exception as e:
        logger.error(f"Error in fetch_cutline_cached: {str(e)}")
        return {'predictions': {}}

def fetch_cutline():
    """
    Wrapper function that handles cache invalidation and returns the latest cut line data.
    Cache is invalidated every 5 minutes.
    """
    try:
        # Clear cache if it's older than 5 minutes
        if hasattr(fetch_cutline_cached, 'cache_time'):
            cache_time = getattr(fetch_cutline_cached, 'cache_time')
            if datetime.now() - cache_time > timedelta(minutes=5):
                fetch_cutline_cached.cache_clear()
                logger.debug("Cache cleared due to age")
        
        # Fetch new data
        result = fetch_cutline_cached()
        
        # Update cache timestamp
        fetch_cutline_cached.cache_time = datetime.now()
        
        if not result['predictions']:
            logger.warning("No cut line predictions found")
        else:
            logger.debug(f"Successfully fetched {len(result['predictions'])} cut line predictions")
            
        return result
        
    except Exception as e:
        logger.error(f"Error in fetch_cutline wrapper: {str(e)}")
        return {'predictions': {}}

