def test_notifications_ws_rejects_missing_token(client):
    import pytest
    from starlette.websockets import WebSocketDisconnect

    # The server closes before accept()ing (see ws/notifications.py), so
    # TestClient raises as soon as the `with` block tries to connect, not
    # on a later receive() — the handshake itself fails.
    with pytest.raises(WebSocketDisconnect) as exc_info:
        with client.websocket_connect("/api/v1/ws/notifications"):
            pass

    assert exc_info.value.code == 4401


def test_notifications_ws_sends_session_init_first(client, access_token):
    with client.websocket_connect(f"/api/v1/ws/notifications?token={access_token}") as ws:
        first_message = ws.receive_json()

        assert first_message["type"] == "session.init"
        assert "session_id" in first_message
