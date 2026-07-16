"""Unit tests for the health check endpoint."""


def test_health_check_endpoint(client):
    """Test that the health check endpoint returns 200 and UP status."""
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    json_data = response.get_json()
    assert json_data is not None
    assert json_data["status"] == "UP"
    assert "version" in json_data
