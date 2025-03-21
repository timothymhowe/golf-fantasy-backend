from sqlalchemy.ext.hybrid import hybrid_property

# TODO: This is a hack to get the DB migration to work.  Fix this. when running the migration scripts, imports need to be relative to the root, so src.api.etc.etc.etc
# TODO: Is it though?  Or does it just work.  when 
from utils.db_connector import db
from datetime import datetime, time
from sqlalchemy import DateTime
from pytz import timezone, utc


class User(db.Model):
    """
    Represents a user in the system.

    Attributes:
        id (int): The unique identifier for the user.
        firebase_id (str): The Firebase UID associated with the user.
        display_name (str): The display name of the user.
        first_name (str): The first name of the user.
        last_name (str): The last name of the user.
        email (str): The email address of the user.
        avatar_url (str): The URL of the user's avatar.
    """

    id = db.Column(db.Integer, primary_key=True)
    firebase_id = db.Column(db.String(255), unique=True, nullable=False)
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
        is_active (bool): Indicates whether the league is active or not.
    """

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    scoring_format = db.Column(db.String(100), nullable=False, default="STANDARD")
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    schedule_id = db.Column(db.Integer, nullable=True)


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
        timestamp_utc (datetime): The timestamp when the pick was made.
        player_name (str): The name of the player picked.
        year (int): The year of the tournament.
        tournament_id (int): The ID of the tournament for which the pick was made.
        is_most_recent (bool): Whether this pick is the most recent pick for the league member.
    """

    # TODO: optimize how we keep track of most recent picks.  For now, this is ok.
    id = db.Column(db.Integer, primary_key=True)
    league_member_id = db.Column(
        db.Integer, db.ForeignKey("league_member.id"), nullable=False
    )
    timestamp_utc = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    golfer_id = db.Column(db.String(9), db.ForeignKey("golfer.id"), nullable=False)
    year = db.Column(db.Integer, nullable=False)
    tournament_id = db.Column(db.Integer, db.ForeignKey("tournament.id"))
    is_most_recent = db.Column(db.Boolean, nullable=False, default=True)
    # is_locked = db.Column(db.Boolean, nullable=False, default=False)
    
    # TODO: Determine if this is actually best practice, weird copilot suggestion/hallucination potentially...
    def to_dict(self):
        return {
            'id': self.id,
            'league_member_id': self.league_member_id,
            'tournament_id': self.tournament_id,
            'golfer_id': self.golfer_id,
            'year': self.year,
            'is_most_recent': self.is_most_recent,
            # Add any other fields you want to include in the dictionary
        }


class Tournament(db.Model):
    """
    A class that represents a golf tournament in the system.

    Attributes:
        id (int): The unique identifier for the tournament (primary key).
        sportcontent_api_id (int): The unique identifier for the tournament in the SportContent API.
        sportcontent_api_tour_id (int): The unique identifier for the tour in the SportContent API.
        datagolf_id (int): The unique identifier for the tournament in the DataGolf API.
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
        latitude (str): The latitude of the tournament.
        longitude (str): The longitude of the tournament.
        is_major (bool): Whether the tournament is a major.
        has_cut (bool): Whether the tournament has a cut.
    """

    id = db.Column(db.Integer, primary_key=True)
    sportcontent_api_id = db.Column(db.Integer, unique=True)
    sportcontent_api_tour_id = db.Column(db.Integer, unique=False, default=2)
    datagolf_id = db.Column(db.Integer, unique=True)
    year = db.Column(db.Integer, nullable=False)
    tournament_name = db.Column(db.String(100), nullable=False)
    tournament_format = db.Column(db.String(100), nullable=False, default="stroke")
    start_date = db.Column(db.Date, nullable=False)
    start_time = db.Column(db.Time, nullable=False, default=time(7, 00))
    time_zone = db.Column(db.String(50), nullable=False, default="America/New_York")
    location_raw = db.Column(db.String(100), nullable=True)
    end_date = db.Column(db.Date, nullable=False)
    course_name = db.Column(db.String(100))
    city = db.Column(db.String(50), nullable=True)
    state = db.Column(db.String(50), nullable=True)
    latitude = db.Column(db.String(10), nullable=True)
    longitude = db.Column(db.String(10), nullable=True)
    is_major = db.Column(db.Boolean, nullable=False, default=False)
    has_cut = db.Column(db.Boolean, nullable=False, default=False)


    # TODO: Does this make sense to do?  I'm not sure if this is the best way to do this.
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
        id (String): The unique identifier for the golfer, uses the golf_id function in src/api/utils/functions/golf_id.py to generate. (Primary Key)
        sportcontent_api_id (int): The unique identifier for the golfer in the SportContent API.
        datagolf_id (int): The unique identifier for the golfer in the DataGolf API.
        first_name (str): The first name of the golfer.
        last_name (str): The last name of the golfer.
        full_name (str): The full name of the golfer.
        country_name (str): The name of the country the golfer is from.
        country_code (str): The 3 letter ISO country code of the country the golfer is from.
        photo_url (str): The URL of the photo of the golfer.
        is_amateur (bool): Whether the golfer is an amateur.
    """

    id = db.Column(db.String(9), primary_key=True)
    sportcontent_api_id = db.Column(db.Integer, unique=True)
    datagolf_id = db.Column(db.Integer, unique=True)
    first_name = db.Column(db.String(50), nullable=False)
    last_name = db.Column(db.String(50), nullable=False)
    full_name = db.Column(db.String(100), nullable=False)
    country_name=db.Column(db.String(60), nullable=True)
    country_code = db.Column(db.String(10), nullable=True)
    photo_url = db.Column(db.String(512), nullable=True)
    is_amateur= db.Column(db.Boolean, default=False)
    


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
        timestamp (datetime): The timestamp when this record was most recently updated.
        is_most_recent (bool): Whether this record is the most recent record for the golfer in the entry list.
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
    timestamp_utc = db.Column(DateTime, default=datetime.utcnow)
    is_most_recent = db.Column(db.Boolean, default=True, nullable=False)

    def to_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}


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
    Represents the scoring rule entry for a golf fantasy league.

    Attributes:
        id (int): The unique identifier for the scoring rule.
        scoring_ruleset_id (int): The ID of the scoring ruleset that this rule belongs to.
        start_position (int): The starting position for the rule.
        end_position (int): The ending position for the rule.
        points (int): The number of points awarded for the rule.
    """

    id = db.Column(db.Integer, primary_key=True)
    scoring_ruleset_id = db.Column(
        db.Integer, db.ForeignKey("scoring_ruleset.id"), nullable=False
    )
    start_position = db.Column(db.Integer, nullable=False)
    end_position = db.Column(db.Integer, nullable=False)
    points = db.Column(db.Integer, nullable=False)


class ScoringRuleset(db.Model):
    """
    Represents a scoring ruleset for a golf tournament.

    Attributes:
        id (int): The unique identifier for the scoring ruleset.
        name (str): The name of the scoring ruleset.
        description (str): The description of the scoring ruleset.
        major_multiplier (float): The multiplier applied to scores for major tournaments.
        mdf_points (int): The points awarded for making the cut in a tournament.
        mc_points (int): The points awarded for missing the cut in a tournament.
        no_pick_points (int): The points deducted for not making any picks in a tournament.
    """

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.String(255))
    major_multiplier = db.Column(db.Float, nullable=False, default=1)
    mdf_points = db.Column(db.Integer, nullable=False, default=5)
    mc_points = db.Column(db.Integer, nullable=False, default=0)
    no_pick_points = db.Column(db.Integer, nullable=False, default=-10)


class LeagueMemberTournamentScore(db.Model):
    """
    Represents the score of a league member in a tournament.

    Attributes:
        id (int): The unique identifier for the score
        league_member_id (int): The foreign key referencing the league member's ID
        tournament_id (int): The foreign key referencing the tournament's ID
        tournament_golfer_result_id (int): The foreign key referencing the tournament golfer result
        score (int): The score of the member in the tournament
        is_no_pick (bool): Whether this score was from not making a pick
        is_duplicate_pick (bool): Whether this score was from making a duplicate pick
    """

    id = db.Column(db.Integer, primary_key=True)
    league_member_id = db.Column(db.Integer, db.ForeignKey("league_member.id"), nullable=False)
    tournament_id = db.Column(db.Integer, db.ForeignKey("tournament.id"), nullable=False)
    tournament_golfer_result_id = db.Column(
        db.Integer, 
        db.ForeignKey("tournament_golfer_result.id"), 
        nullable=True  # Nullable because of no-pick scenarios
    )
    score = db.Column(db.Integer, nullable=False, default=0)
    is_no_pick = db.Column(db.Boolean, nullable=False, default=False)
    is_duplicate_pick = db.Column(db.Boolean, nullable=False, default=False)

    # Add relationship to access result directly
    result = db.relationship("TournamentGolferResult")


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
    user_name = db.Column(db.String(100), unique=True, nullable=False)
    display_name = db.Column(db.String(100))
    nickname = db.Column(db.String(100))
    first_name = db.Column(db.String(50))
    last_name = db.Column(db.String(50))
    league_id = db.Column(db.Integer, db.ForeignKey("league.id"), nullable=False)


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
    legacy_member_id = db.Column(db.Integer, db.ForeignKey("legacy_member.id"))
    week = db.Column(db.Integer)
    tournament_id = db.Column(db.Integer, db.ForeignKey("tournament.id"))
    golfer_name = db.Column(db.String(100))
    golfer_id = db.Column(db.String(9), db.ForeignKey("golfer.id"))
    no_pick = db.Column(db.Boolean, default=False, nullable=False)


class LeagueCommisioner(db.Model):
    """
    Represents a league commissioner in the system.

    Attributes:
        id (int): The unique identifier for the league commissioner relation.
        league_id (int): The ID of the league the commissioner belongs to.
        user_id (int): The ID of the user associated with the commissioner.
    """

    id = db.Column(db.Integer, primary_key=True)
    league_id = db.Column(db.Integer, db.ForeignKey("league.id"), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)


class TournamentGolferResult(db.Model):
    """
    Represents a golfer's result in a tournament.

    Attributes:
        id (int): The unique identifier for the result
        tournament_golfer_id (int): Foreign key to TournamentGolfer
        result (str): The finishing position (e.g., "1", "T2", "CUT", etc.)
        status (str): The player's status (e.g., "active", "complete", "cut", "wd", "dq")
        score_to_par (int): The player's score relative to par (can be null for CUT/WD/DQ)
    """

    id = db.Column(db.Integer, primary_key=True)
    tournament_golfer_id = db.Column(
        db.Integer, 
        db.ForeignKey("tournament_golfer.id"), 
        nullable=False
    )
    result = db.Column(db.String(9), nullable=False)
    status = db.Column(db.String(20), nullable=False, default='complete')
    score_to_par = db.Column(db.Integer, nullable=True)

    # Relationship to tournament_golfer
    tournament_golfer = db.relationship("TournamentGolfer", backref="results")


class GolferStats(db.Model):
    """
    Represents a record of stats of a golfer based on their performance in Tournaments, as well as pulled from apis.

    Args:
        db (_type_): _description_
    """

    #
    id = db.Column(db.Integer, primary_key=True)
    golfer_id = db.Column(db.String(9), db.ForeignKey("golfer.id"), nullable=False)

    # stats


class GolferRanking(db.Model):
    """
    Represents a record of stats of a golfer based on their performance in Tournaments, as well as pulled from apis.

    Args:
        db (_type_): _description_
    """

    #
    id = db.Column(db.Integer, primary_key=True)
    golfer_id = db.Column(db.String(9), db.ForeignKey("golfer.id"), nullable=False)

    # OWGR
    has_owgr = db.Column(db.Boolean, nullable=False, default=False)
    owgr = db.Column(db.Integer)
    is_most_recent = db.Column(db.Boolean, nullable=False, default=True)
    timestamp_utc = db.Column(DateTime, default=datetime.utcnow)



class Schedule(db.Model):
    """
    Represents a PGA Tour schedule for a given year.
    """
    __tablename__ = 'schedule'

    id = db.Column(db.Integer, primary_key=True)
    year = db.Column(db.Integer, nullable=False)
    schedule_name = db.Column(db.String(100), nullable=False)

    
    # Relationship to schedule tournaments
    tournaments = db.relationship('ScheduleTournament', back_populates='schedule')

class ScheduleTournament(db.Model):
    """
    Links tournaments to a schedule in chronological order.
    """
    __tablename__ = 'schedule_tournament'

    id = db.Column(db.Integer, primary_key=True)
    schedule_id = db.Column(db.Integer, db.ForeignKey('schedule.id'), nullable=False)
    tournament_id = db.Column(db.Integer, db.ForeignKey('tournament.id'), nullable=False)
    week_number = db.Column(db.Integer, nullable=False)
    allow_duplicate_picks = db.Column(db.Boolean, nullable=False, default=False)
    
    # Relationships
    schedule = db.relationship('Schedule', back_populates='tournaments')
    tournament = db.relationship('Tournament')
    
    # Unique constraint to ensure a tournament only appears once in a schedule
    __table_args__ = (
        db.UniqueConstraint('schedule_id', 'tournament_id', name='uix_schedule_tournament'),
    )

class LeagueInviteCode(db.Model):
    """
    Represents an invite code for joining a league.

    Attributes:
        id (int): The unique identifier for the invite code
        code (str): The actual invite code string
        league_id (int): The ID of the league this code is for
        created_by_id (int): The user ID who created this code
        created_at (datetime): When the code was created
        expires_at (datetime): When the code expires (nullable)
        is_active (bool): Whether this code can still be used
        max_uses (int): Maximum number of times this code can be used (nullable)
        usage_count (int): How many times this code has been used
        role_id (int): The role to assign to users who join with this code
    """
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(20), unique=True, nullable=False)
    league_id = db.Column(db.Integer, db.ForeignKey("league.id"), nullable=False)
    created_by_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    expires_at = db.Column(db.DateTime, nullable=True)
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    max_uses = db.Column(db.Integer, nullable=True)  # null means unlimited
    usage_count = db.Column(db.Integer, nullable=False, default=0)
    role_id = db.Column(db.Integer, db.ForeignKey("role.id"), nullable=False)

class InviteCodeUsage(db.Model):
    """
    Tracks the usage history of invite codes.

    Attributes:
        id (int): The unique identifier for the usage record
        invite_code_id (int): The ID of the invite code that was used
        user_id (int): The ID of the user who used the code
        used_at (datetime): When the code was used
    """
    id = db.Column(db.Integer, primary_key=True)
    invite_code_id = db.Column(db.Integer, db.ForeignKey("league_invite_code.id"), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    used_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    # Prevent double usage by same user
    __table_args__ = (
        db.UniqueConstraint('invite_code_id', 'user_id', name='uix_invite_code_usage'),
    )