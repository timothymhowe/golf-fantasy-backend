import os
from dotenv import load_dotenv

load_dotenv()

sportcontentapi_key = os.getenv("SPORTCONTENTAPI_KEY3")
sportcontentapi_headers = {
    "X-RapidAPI-Key": sportcontentapi_key,
    "X-RapidAPI-Host": "golf-leaderboard-data.p.rapidapi.com"
}