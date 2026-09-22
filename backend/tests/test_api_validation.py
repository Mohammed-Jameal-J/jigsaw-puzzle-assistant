from fastapi.testclient import TestClient

from main import app


client = TestClient(app)


def test_invalid_puzzle_id_is_rejected_with_400():
    response = client.get("/api/puzzle/not-a-valid-id")

    assert response.status_code == 400
    assert "puzzle_id" in response.json()["detail"].lower()


def test_invalid_piece_id_is_rejected_with_400():
    response = client.get("/api/puzzle/0123456789ab/pieces/abc")

    assert response.status_code == 400
    assert "piece_id" in response.json()["detail"].lower()
