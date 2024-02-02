from sqlalchemy.ext.hybrid import hybrid_property

from src.api.utils.db_connector import db
from datetime import time
from sqlalchemy import DateTime
from pytz import timezone, utc
class User(db.Model):
    """
    Represents a user in the system.

    Attributes:
        id (int): The unique identifier for the user.
        firebase_uid (str): The Firebase UID associated with the user.
        display_name (str): The display name of the user.
        first_name (str): The first name of the user.
        last_name (str): The last name of the user.
        email (str): The email address of the user.
        avatar_url (str): The URL of the user's avatar.
    """

    id = db.Column(db.Integer, primary_key=True)
    firebase_uid = db.Column(db.String(255), unique=True, nullable=False)
    display_name = db.Column(db.String(40), nullable=False)
    first_name = db.Column(db.String(40), nullable=False)
    last_name = db.Column(db.String(40), nullable=False)
    email = db.Column(db.String(40), unique=True, nullable=False)
    avatar_url = db.Column(db.String(512))  # new field for avatar URL


class League(db.Model):
    """
    Represents a league in the system.

    Attributes:
        id (int): The unique identifier for the league.
        name (str): The name of the league.
        scoring_format (str): The scoring format used in the league.
        commissioner_id (int): The ID of the user who is the commissioner of the league.
    """

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    scoring_format = db.Column(db.String(100), nullable=False)
    commissioner_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)


class LeagueMember(db.Model):
    """
    Represents a member of a league in the system.

    Attributes:
        id (int): The unique identifier for the league-member.
        league_id (int): The ID of the league the member belongs to.
        user_id (int): The ID of the user associated with the member.
        role_id (int): The ID of the role assigned to the member.
    """

    id = db.Column(db.Integer, primary_key=True)
    league_id = db.Column(db.Integer, db.ForeignKey("league.id"), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    role_id = db.Column(db.Integer, db.ForeignKey("role.id"), nullable=False, default=0)


class Pick(db.Model):
    """
    Represents a pick made by a league member for a tournament.

    Attributes:
        id (int): The unique identifier for the pick.
        league_member_id (int): The ID of the league member who made the pick.
        timestamp (datetime): The timestamp when the pick was made.
        player_name (str): The name of the player picked.
        year (int): The year of the tournament.
        tournament_id (int): The ID of the tournament for which the pick was made.
    """

    id = db.Column(db.Integer, primary_key=True)
    league_member_id = db.Column(
        db.Integer, db.ForeignKey("league_member.id"), nullable=False
    )
    timestamp = db.Column(
        db.DateTime, nullable=False, default=db.func.current_timestamp()
    )
    player_name = db.Column(db.String(100), nullable=False)
    year = db.Column(db.Integer, nullable=False)
    tournament_id = db.Column(db.Integer, db.ForeignKey("tournament.id"))


class Tournament(db.Model):
    """
    A class that represents a golf tournament in the system.

    Attributes:
        id (int): The unique identifier for the tournament (primary key).
        sportcontent_api_id (int): The unique identifier for the tournament in the SportContent API.
        year (int): The year of the tournament.
        tournament_name (str): The name of the tournament.
        tournament_format (str): The format of the tournament (stroke, match, etc.).
        start_date (date): The start date of the tournament.
        start_time (time): The start time of the tournament.
        time_zone (str): The time zone of the tournament.
        location_raw (str): The raw location information of the tournament.
        end_date (date): The end date of the tournament.
        course_name (str): The name of the course where the tournament is played.
        city (str): The city where the tournament is played.
        state (str): The state where the tournament is played.
    """

    id = db.Column(db.Integer, primary_key=True)
    sportcontent_api_id = db.Column(db.Integer, unique=True)
    sportcontent_api_tour_id = db.Column(db.Integer, unique=False, default=2)
    year = db.Column(db.Integer, nullable=False)
    tournament_name = db.Column(db.String(100), nullable=False)
    tournament_format = db.Column(db.String(100), nullable=False, default="stroke")
    start_date = db.Column(db.Date, nullable=False)
    start_time = db.Column(db.Time, nullable=False, default=time(8,30))
    time_zone = db.Column(db.String(50), nullable=False, default="America/New_York")
    location_raw = db.Column(db.String(100), nullable=True)
    end_date = db.Column(db.Date, nullable=False)
    course_name = db.Column(db.String(100))
    city = db.Column(db.String(50), nullable=True)
    state = db.Column(db.String(50), nullable=True)
    is_major = db.Column(db.Boolean, nullable=False, default=False)
    


    @hybrid_property
    def start_date_tz(self):
        return utc.localize(self.start_date).astimezone(timezone(self.time_zone))

    @hybrid_property
    def end_date_tz(self):
        return utc.localize(self.end_date).astimezone(timezone(self.time_zone))

class Golfer(db.Model):
    """
    Represents a golfer in the system.

    Attributes:
        id (int): The unique identifier for the golfer. (Primary Key)
        sportcontent_api_id (int): The unique identifier for the golfer in the SportContent API.
        first_name (str): The first name of the golfer.
        last_name (str): The last name of the golfer.
        photo_url (str): The URL of the photo of the golfer.
    """

    id = db.Column(db.String(9), primary_key=True)
    sportcontent_api_id = db.Column(db.Integer, unique=True)
    first_name = db.Column(db.String(50), nullable=False)
    last_name = db.Column(db.String(50), nullable=False)
    full_name = db.Column(db.String(100), nullable=False)
    photo_url = db.Column(db.String(512))


class TournamentGolfer(db.Model):
    """
    Represents a golfer's appearance in a tournament.

    Attributes:
        id (int): The unique identifier for the tournament golfer. Primary Key.
        tournament_id (int): The unique identifier for the tournament.
        golfer_id (int): The unique identifier for the golfer.
        year (int): The year of the tournament.
        is_active (bool): Whether the golfer is active in the tournament.
        is_alternate (bool): Whether the golfer is an alternate in the tournament.
        is_injured (bool): Whether the golfer is injured in the tournament.
    """

    id = db.Column(db.Integer, primary_key=True)
    tournament_id = db.Column(
        db.Integer, db.ForeignKey("tournament.id"), nullable=False
    )
    golfer_id = db.Column(db.String(9), db.ForeignKey("golfer.id"), nullable=False)
    year = db.Column(db.Integer, nullable=False)
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    is_alternate = db.Column(db.Boolean, nullable=False, default=False)
    is_injured = db.Column(db.Boolean, nullable=False, default=False)


class Role(db.Model):
    """
    Represents a role in the system.
    
    Attributes:
        id (int): The unique identifier for the role.
        name (str): The name of the role.
    """

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)


class ScoringRule(db.Model):
    """
    Represents a scoring rule for a golf tournament.

    Attributes:
        id (int): The unique identifier for the scoring rule.
        start_position (int): The starting position for the rule.
        end_position (int): The ending position for the rule.
        points (int): The number of points awarded for the rule.
    """
 
    id = db.Column(db.Integer, primary_key=True)
    start_position = db.Column(db.Integer, nullable=False)
    end_position = db.Column(db.Integer, nullable=False)
    points = db.Column(db.Integer, nullable=False)


class UserScore(db.Model):
    """
    Represents the score of a user in a tournament.

    Attributes:
        id (int): The unique identifier for the user score.
        user_id (int): The foreign key referencing the user's ID.
        tournament_id (int): The foreign key referencing the tournament's ID.
        score (int): The score of the user in the tournament.
    """
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    tournament_id = db.Column(
        db.Integer, db.ForeignKey("tournament.id"), nullable=False
    )
    score = db.Column(db.Integer, nullable=False, default=0)


class LegacyMember(db.Model):
    """
    Represents a legacy member in the system.
    
    Attributes:
        id (int): The unique identifier for the legacy member.
        full_name (str): The full name of the legacy member.
        first_name (str): The first name of the legacy member.
        last_name (str): The last name of the legacy member.
    """
    
    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(100))
    first_name = db.Column(db.String(50))
    last_name = db.Column(db.String(50))


class LegacyMemberPick(db.Model):
    """
    Represents a pick made by a legacy member for a tournament.
    
    Attributes:
        id (int): The unique identifier for the pick.
        user_id (int): The ID of the legacy member who made the pick.
        week (int): The week number of the tournament.
        tournament_id (int): The ID of the tournament for which the pick is made.
        golfer_name (str): The name of the golfer chosen by the legacy member.
    """
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("legacy_member.id"))
    week = db.Column(db.Integer)
    tournament_id = db.Column(db.Integer, db.ForeignKey("tournament.id"))
    golfer_name = db.Column(db.String(100))
