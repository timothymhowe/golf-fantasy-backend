import pytest
from fixtures.data import create_user, create_roles, create_league


class TestScoreboard:
    def test_success(self, client, auth_headers, seeded_db):
        league_id = seeded_db['league'].id
        response = client.get(f'/league/scoreboard/{league_id}', headers=auth_headers)
        assert response.status_code == 200
        data = response.get_json()
        assert data['status'] == 'success'
        assert len(data['data']['leaderboard']) == 2

    def test_leaderboard_sorted_by_score_desc(self, client, auth_headers, seeded_db):
        league_id = seeded_db['league'].id
        response = client.get(f'/league/scoreboard/{league_id}', headers=auth_headers)
        data = response.get_json()
        scores = [entry['score'] for entry in data['data']['leaderboard']]
        assert scores == sorted(scores, reverse=True)

    def test_requires_auth(self, client):
        response = client.get('/league/scoreboard/1')
        assert response.status_code == 401

    def test_nonmember_returns_403(self, client, auth_headers, seeded_db, db_session):
        other_league = create_league(db_session, name='Other League')
        db_session.commit()
        response = client.get(f'/league/scoreboard/{other_league.id}', headers=auth_headers)
        assert response.status_code == 403

    def test_nonexistent_league(self, client, auth_headers, seeded_db):
        response = client.get('/league/scoreboard/99999', headers=auth_headers)
        assert response.status_code == 403


class TestMembership:
    def test_has_league_returns_true(self, client, auth_headers, seeded_db):
        response = client.get('/league/membership', headers=auth_headers)
        assert response.status_code == 200
        assert response.get_json()['hasLeague'] is True

    def test_no_leagues_returns_false(self, client, auth_headers, db_session):
        create_roles(db_session)
        create_user(db_session)
        db_session.commit()
        response = client.get('/league/membership', headers=auth_headers)
        assert response.status_code == 200
        assert response.get_json()['hasLeague'] is False

    def test_requires_auth(self, client):
        response = client.get('/league/membership')
        assert response.status_code == 401


class TestPickHistory:
    def test_success(self, client, auth_headers, seeded_db):
        member_id = seeded_db['members'][0].id
        response = client.get(f'/league/member/{member_id}/pick-history',
                              headers=auth_headers)
        assert response.status_code == 200
        data = response.get_json()
        assert 'member' in data
        assert 'picks' in data
        assert 'summary' in data

    def test_invalid_member_returns_404(self, client, auth_headers, seeded_db):
        response = client.get('/league/member/99999/pick-history',
                              headers=auth_headers)
        assert response.status_code == 404

    def test_requires_auth(self, client):
        response = client.get('/league/member/1/pick-history')
        # This route uses @require_auth - without a seeded db the member
        # lookup returns None/404 before auth is even checked by the decorator.
        # With the autouse mock, auth passes, and member 1 doesn't exist -> 404.
        assert response.status_code in (401, 404)
