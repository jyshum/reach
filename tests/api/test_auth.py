import pytest
from unittest.mock import patch, MagicMock
from fastapi import HTTPException

from backend.auth import get_current_user, get_optional_user


def test_get_current_user_valid_token():
    mock_request = MagicMock()
    mock_request.headers.get.return_value = "Bearer valid.jwt.token"

    with patch("backend.auth._decode_token") as mock_decode:
        mock_decode.return_value = {"sub": "user-uuid-123", "email": "test@example.com"}
        user_id = get_current_user(mock_request)

    assert user_id == "user-uuid-123"
    mock_decode.assert_called_once_with("valid.jwt.token")


def test_get_current_user_missing_header():
    mock_request = MagicMock()
    mock_request.headers.get.return_value = None

    with pytest.raises(HTTPException) as exc_info:
        get_current_user(mock_request)
    assert exc_info.value.status_code == 401


def test_get_current_user_invalid_token():
    mock_request = MagicMock()
    mock_request.headers.get.return_value = "Bearer bad.token"

    with patch("backend.auth._decode_token") as mock_decode:
        mock_decode.side_effect = Exception("Invalid token")
        with pytest.raises(HTTPException) as exc_info:
            get_current_user(mock_request)
    assert exc_info.value.status_code == 401


def test_get_current_user_no_bearer_prefix():
    mock_request = MagicMock()
    mock_request.headers.get.return_value = "just.a.token"

    with pytest.raises(HTTPException) as exc_info:
        get_current_user(mock_request)
    assert exc_info.value.status_code == 401


def test_get_optional_user_valid_token():
    mock_request = MagicMock()
    mock_request.headers.get.return_value = "Bearer valid.jwt.token"

    with patch("backend.auth._decode_token") as mock_decode:
        mock_decode.return_value = {"sub": "user-uuid-123", "email": "test@example.com"}
        user_id = get_optional_user(mock_request)

    assert user_id == "user-uuid-123"


def test_get_optional_user_no_token():
    mock_request = MagicMock()
    mock_request.headers.get.return_value = None

    user_id = get_optional_user(mock_request)
    assert user_id is None


def test_get_optional_user_invalid_token():
    mock_request = MagicMock()
    mock_request.headers.get.return_value = "Bearer bad.token"

    with patch("backend.auth._decode_token") as mock_decode:
        mock_decode.side_effect = Exception("Invalid token")
        user_id = get_optional_user(mock_request)

    assert user_id is None
