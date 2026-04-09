import pytest
from fixtures.data import create_pick


class TestSubmitPick:
    def test_submit_for_future_tournament(self, client, auth_headers, seeded_db):
        member = seeded_db['members'][0]
        future_tournament = seeded_db['tournaments'][1]
        golfer = seeded_db['golfers'][0]
        response = client.post('/pick/submit', headers=auth_headers, json={
            'league_member_id': member.id,
            'tournament_id': future_tournament.id,
            'golfer_id': golfer.id,
        })
        assert response.status_code == 201
        data = response.get_json()
        assert data['tournament_id'] == future_tournament.id
        assert data['golfer_id'] == golfer.id

    def test_submit_replaces_previous_pick(self, client, auth_headers, seeded_db, db_session):
        member = seeded_db['members'][0]
        future_tournament = seeded_db['tournaments'][1]
        golfer1 = seeded_db['golfers'][0]
        golfer2 = seeded_db['golfers'][1]

        # First pick
        client.post('/pick/submit', headers=auth_headers, json={
            'league_member_id': member.id,
            'tournament_id': future_tournament.id,
            'golfer_id': golfer1.id,
        })
        # Second pick for same tournament
        response = client.post('/pick/submit', headers=auth_headers, json={
            'league_member_id': member.id,
            'tournament_id': future_tournament.id,
            'golfer_id': golfer2.id,
        })
        assert response.status_code == 201
        data = response.get_json()
        assert data['golfer_id'] == golfer2.id

    def test_submit_for_past_tournament_raises(self, client, auth_headers, seeded_db):
        member = seeded_db['members'][0]
        past_tournament = seeded_db['tournaments'][0]
        golfer = seeded_db['golfers'][0]
        # submit_pick raises ValueError for started tournaments and the route
        # doesn't catch it, so Flask propagates the exception in test mode
        with pytest.raises(ValueError, match='Tournament has already started'):
            client.post('/pick/submit', headers=auth_headers, json={
                'league_member_id': member.id,
                'tournament_id': past_tournament.id,
                'golfer_id': golfer.id,
            })

    def test_requires_auth(self, client):
        response = client.post('/pick/submit', json={
            'league_member_id': 1,
            'tournament_id': 1,
            'golfer_id': 'SCOSC0001',
        })
        assert response.status_code == 401


class TestGetCurrentPick:
    def test_existing_pick(self, client, auth_headers, seeded_db):
        member = seeded_db['members'][0]
        tournament = seeded_db['tournaments'][0]
        response = client.get(
            f'/pick/current/{member.id}?tournament_id={tournament.id}',
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data['has_pick'] is True
        assert data['golfer_id'] == seeded_db['golfers'][0].id

    def test_no_pick_returns_200_with_false(self, client, auth_headers, seeded_db):
        member = seeded_db['members'][0]
        future_tournament = seeded_db['tournaments'][1]
        response = client.get(
            f'/pick/current/{member.id}?tournament_id={future_tournament.id}',
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data['has_pick'] is False

    def test_missing_tournament_id_returns_400(self, client, auth_headers, seeded_db):
        member = seeded_db['members'][0]
        response = client.get(f'/pick/current/{member.id}', headers=auth_headers)
        assert response.status_code == 400

    def test_requires_auth(self, client):
        response = client.get('/pick/current/1?tournament_id=1')
        assert response.status_code == 401
