import pytest


class TestMostRecentTournament:
    def test_returns_past_tournament(self, client, seeded_db):
        league_id = seeded_db['league'].id
        response = client.get(f'/tournament/most-recent/{league_id}')
        assert response.status_code == 200
        data = response.get_json()
        assert data['tournament_name'] == 'Past Open'

    def test_no_tournaments_returns_404(self, client, db_session):
        from fixtures.data import create_roles, create_user, create_league, create_schedule
        create_roles(db_session)
        user = create_user(db_session)
        schedule = create_schedule(db_session)
        league = create_league(db_session, schedule_id=schedule.id)
        db_session.commit()
        response = client.get(f'/tournament/most-recent/{league.id}')
        assert response.status_code == 404


class TestUpcomingTournament:
    def test_returns_upcoming(self, client, seeded_db):
        league_id = seeded_db['league'].id
        response = client.get(f'/tournament/upcoming/{league_id}')
        assert response.status_code == 200
        data = response.get_json()
        assert data['tournament_name'] == 'Future Classic'

    def test_nonexistent_league_returns_404(self, client, seeded_db):
        response = client.get('/tournament/upcoming/99999')
        assert response.status_code == 404


class TestDropdownData:
    def test_returns_golfer_data(self, client, auth_headers, seeded_db):
        member = seeded_db['members'][0]
        tournament = seeded_db['tournaments'][0]
        response = client.get(
            f'/tournament/dd/{member.id}?tournament_id={tournament.id}',
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.get_json()
        assert 'golfers' in data
        assert len(data['golfers']) >= 2

    def test_missing_tournament_id_still_returns_data(self, client, auth_headers, seeded_db):
        member = seeded_db['members'][0]
        response = client.get(f'/tournament/dd/{member.id}', headers=auth_headers)
        # tournament_id defaults to None but the query still runs and returns golfers
        assert response.status_code == 200

    def test_requires_auth(self, client):
        response = client.get('/tournament/dd/1?tournament_id=1')
        assert response.status_code == 401
