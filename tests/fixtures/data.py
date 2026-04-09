"""
Test data factory functions.

Each function creates database records with sensible defaults.
seed_full_league() composes them into a complete test scenario.
"""

from datetime import date, time, datetime, timedelta
from models import (
    User, League, LeagueMember, Pick, Tournament, Golfer,
    TournamentGolfer, TournamentGolferResult, Role,
    LeagueMemberTournamentScore, Schedule, ScheduleTournament,
)


def create_roles(session):
    roles = [
        Role(id=1, name='Commissioner'),
        Role(id=2, name='Admin'),
        Role(id=3, name='Member'),
    ]
    for r in roles:
        session.add(r)
    session.flush()
    return roles


def create_user(session, firebase_id='test-firebase-uid', display_name='TestUser',
                first_name='Test', last_name='User', email='test@example.com',
                avatar_url=None):
    user = User(
        firebase_id=firebase_id,
        display_name=display_name,
        first_name=first_name,
        last_name=last_name,
        email=email,
        avatar_url=avatar_url,
    )
    session.add(user)
    session.flush()
    return user


def create_league(session, name='Test League', scoring_format='STANDARD',
                  schedule_id=None):
    league = League(
        name=name,
        scoring_format=scoring_format,
        is_active=True,
        schedule_id=schedule_id,
    )
    session.add(league)
    session.flush()
    return league


def create_league_member(session, league_id, user_id, role_id=3):
    member = LeagueMember(
        league_id=league_id,
        user_id=user_id,
        role_id=role_id,
    )
    session.add(member)
    session.flush()
    return member


def create_tournament(session, tournament_name='The Masters', year=2025,
                      start_date=None, end_date=None, start_time=None,
                      time_zone='America/New_York', is_major=False,
                      sportcontent_api_id=None, datagolf_id=None,
                      course_name='Augusta National'):
    if start_date is None:
        start_date = date(2025, 4, 10)
    if end_date is None:
        end_date = start_date + timedelta(days=3)
    if start_time is None:
        start_time = time(7, 0)

    tournament = Tournament(
        tournament_name=tournament_name,
        year=year,
        start_date=start_date,
        end_date=end_date,
        start_time=start_time,
        time_zone=time_zone,
        is_major=is_major,
        sportcontent_api_id=sportcontent_api_id,
        datagolf_id=datagolf_id,
        course_name=course_name,
    )
    session.add(tournament)
    session.flush()
    return tournament


def create_golfer(session, golfer_id='SCOSC0001', first_name='Scottie',
                  last_name='Scheffler', datagolf_id=18854):
    golfer = Golfer(
        id=golfer_id,
        first_name=first_name,
        last_name=last_name,
        full_name=f'{first_name} {last_name}',
        datagolf_id=datagolf_id,
        country_code='USA',
    )
    session.add(golfer)
    session.flush()
    return golfer


def create_schedule(session, year=2025, schedule_name='2025 PGA Tour'):
    schedule = Schedule(year=year, schedule_name=schedule_name)
    session.add(schedule)
    session.flush()
    return schedule


def create_schedule_tournament(session, schedule_id, tournament_id, week_number=1):
    st = ScheduleTournament(
        schedule_id=schedule_id,
        tournament_id=tournament_id,
        week_number=week_number,
    )
    session.add(st)
    session.flush()
    return st


def create_tournament_golfer(session, tournament_id, golfer_id, year=2025):
    tg = TournamentGolfer(
        tournament_id=tournament_id,
        golfer_id=golfer_id,
        year=year,
        is_most_recent=True,
    )
    session.add(tg)
    session.flush()
    return tg


def create_tournament_golfer_result(session, tournament_golfer_id, result='1',
                                     status='complete', score_to_par=-15):
    tgr = TournamentGolferResult(
        tournament_golfer_id=tournament_golfer_id,
        result=result,
        status=status,
        score_to_par=score_to_par,
    )
    session.add(tgr)
    session.flush()
    return tgr


def create_pick(session, league_member_id, golfer_id, tournament_id, year=2025,
                is_most_recent=True):
    pick = Pick(
        league_member_id=league_member_id,
        golfer_id=golfer_id,
        tournament_id=tournament_id,
        year=year,
        is_most_recent=is_most_recent,
    )
    session.add(pick)
    session.flush()
    return pick


def create_score(session, league_member_id, tournament_id,
                 tournament_golfer_result_id=None, score=0,
                 is_no_pick=False, is_duplicate_pick=False):
    s = LeagueMemberTournamentScore(
        league_member_id=league_member_id,
        tournament_id=tournament_id,
        tournament_golfer_result_id=tournament_golfer_result_id,
        score=score,
        is_no_pick=is_no_pick,
        is_duplicate_pick=is_duplicate_pick,
    )
    session.add(s)
    session.flush()
    return s


def seed_full_league(session):
    """Create a complete test scenario.

    Returns a dict with all created objects:
        roles, users (list), league, schedule, members (list),
        tournaments (list: [past, future]), golfers (list),
        tournament_golfers (list), results (list), picks (list), scores (list)
    """
    roles = create_roles(session)

    user1 = create_user(session, firebase_id='test-firebase-uid',
                        display_name='Player1', first_name='Test', last_name='User',
                        email='p1@test.com')
    user2 = create_user(session, firebase_id='firebase-uid-2',
                        display_name='Player2', first_name='Jane', last_name='Doe',
                        email='p2@test.com')

    schedule = create_schedule(session)
    league = create_league(session, schedule_id=schedule.id)

    member1 = create_league_member(session, league.id, user1.id, role_id=3)
    member2 = create_league_member(session, league.id, user2.id, role_id=3)

    # Past tournament (already started)
    past_tournament = create_tournament(
        session, tournament_name='Past Open', year=2025,
        start_date=date(2025, 1, 9), is_major=False,
        sportcontent_api_id=100, datagolf_id=100,
    )
    # Future tournament (not yet started)
    future_tournament = create_tournament(
        session, tournament_name='Future Classic', year=2025,
        start_date=date(2027, 12, 1), is_major=True,
        sportcontent_api_id=200, datagolf_id=200,
    )

    create_schedule_tournament(session, schedule.id, past_tournament.id, week_number=1)
    create_schedule_tournament(session, schedule.id, future_tournament.id, week_number=2)

    golfer1 = create_golfer(session)
    golfer2 = create_golfer(session, golfer_id='RORMC0001', first_name='Rory',
                            last_name='McIlroy', datagolf_id=17592)

    tg1 = create_tournament_golfer(session, past_tournament.id, golfer1.id)
    tg2 = create_tournament_golfer(session, past_tournament.id, golfer2.id)

    # Also add golfers to the future tournament field
    tg3 = create_tournament_golfer(session, future_tournament.id, golfer1.id)
    tg4 = create_tournament_golfer(session, future_tournament.id, golfer2.id)

    result1 = create_tournament_golfer_result(session, tg1.id, result='1',
                                              status='complete', score_to_par=-15)
    result2 = create_tournament_golfer_result(session, tg2.id, result='T2',
                                              status='complete', score_to_par=-10)

    pick1 = create_pick(session, member1.id, golfer1.id, past_tournament.id)
    pick2 = create_pick(session, member2.id, golfer2.id, past_tournament.id)

    score1 = create_score(session, member1.id, past_tournament.id,
                          tournament_golfer_result_id=result1.id, score=15000)
    score2 = create_score(session, member2.id, past_tournament.id,
                          tournament_golfer_result_id=result2.id, score=750)

    session.commit()

    return {
        'roles': roles,
        'users': [user1, user2],
        'league': league,
        'schedule': schedule,
        'members': [member1, member2],
        'tournaments': [past_tournament, future_tournament],
        'golfers': [golfer1, golfer2],
        'tournament_golfers': [tg1, tg2, tg3, tg4],
        'results': [result1, result2],
        'picks': [pick1, pick2],
        'scores': [score1, score2],
    }
