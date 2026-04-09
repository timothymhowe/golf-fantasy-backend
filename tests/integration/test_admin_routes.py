import pytest


class TestHealthCheck:
    def test_returns_200(self, client):
        response = client.get('/health/')
        assert response.status_code == 200
        data = response.get_json()
        assert data['status'] == 'healthy'
        assert data['message'] == 'API is running'

    def test_db_health_returns_200(self, client):
        response = client.get('/health/db-health')
        assert response.status_code == 200
        data = response.get_json()
        assert data['status'] == 'healthy'
        assert data['database'] == 'connected'
