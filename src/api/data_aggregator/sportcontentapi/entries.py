import requests
from pytz import timezone
from data_aggregator.sportcontentapi.headers import sportcontentapi_headers
from modules.tournament.functions import get_upcoming_tournament


url = "https://golf-leaderboard-data.p.rapidapi.com/entry-list/"

# TODO: This needs to be updated every friday for the following week, and then more frequently  as the tournament approaches, ideally monday, tuesday, and wednesday.  Perhaps both wednesday morning and night.


def get_entry_list(tournament_id):
    """
    Retrieves the list of entries for a given tournament.

    Args:
        tournament_id (int): The ID of the tournament.  This is the id used by SPORTCONTENTAPI, which gets stored as sportcontentapi_id in the database.

    Returns:
        dict: The JSON response containing the list of entries.
    """
    response = requests.get(f"{url}{tournament_id}", headers=sportcontentapi_headers)
    return response.json()


def schedule_entry_list_update(scheduler):
    """
    Schedules the entry list update to occur at the appropriate times with appropriate values.

    Returns:
        None
    """
    
    scheduler.add_job(
        get_entry_list,
        "cron",
        day_of_week="fri",
        hour=12,
        timezone=timezone("America/New_York"),
        args=[get_upcoming_tournament()["sportcontent_api_id"]],
    )
    
    scheduler.add_job(
        get_entry_list,
        "cron",
        day_of_week="mon",
        hour=8,
        timezone=timezone("America/New_York"),
        args=[get_upcoming_tournament()["sportcontent_api_id"]],
    )
    
    scheduler.add_job(
        get_entry_list,
        "cron",
        day_of_week="tue",
        hour=8,
        timezone=timezone("America/New_York"),
        args=[get_upcoming_tournament()["sportcontent_api_id"]],
    )
   
    scheduler.add_job(
        get_entry_list,
        "cron",
        day_of_week="wed",
        hour=6,
        timezone=timezone("America/New_York"),
        args=[get_upcoming_tournament()["sportcontent_api_id"]],
    )
    
    scheduler.add_job(
        get_entry_list,
        "cron",
        day_of_week="wed",
        hour=12,
        timezone=timezone("America/New_York"),
        args=[get_upcoming_tournament()["sportcontent_api_id"]],
    )
    
    scheduler.add_job(
        get_entry_list,
        "cron",
        day_of_week="wed",
        hour=8,
        timezone=timezone("America/New_York"),
        args=[get_upcoming_tournament()["sportcontent_api_id"]],
    )
    
    scheduler.add_job(
        get_entry_list,
        "cron",
        day_of_week="thur",
        hour=0,
        timezone=timezone("America/New_York"),
        args=[get_upcoming_tournament()["sportcontent_api_id"]],
    )


