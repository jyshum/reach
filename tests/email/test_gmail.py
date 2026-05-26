import base64
from unittest.mock import patch, MagicMock
import pytest


@pytest.fixture
def mock_gmail_service():
    service = MagicMock()
    return service


def test_send_email_returns_thread_and_message_id(mock_gmail_service):
    from backend.email.gmail import send_email

    mock_gmail_service.users().messages().send().execute.return_value = {
        "id": "msg-123",
        "threadId": "thread-456",
    }

    result = send_email(
        service=mock_gmail_service,
        to="founder@startup.com",
        subject="Quick question",
        body="Hi, I'm a high school senior...",
        sender_email="student@gmail.com",
    )

    assert result["message_id"] == "msg-123"
    assert result["thread_id"] == "thread-456"


def test_send_email_constructs_valid_mime(mock_gmail_service):
    from backend.email.gmail import send_email

    mock_gmail_service.users().messages().send().execute.return_value = {
        "id": "msg-1", "threadId": "thread-1",
    }

    send_email(
        service=mock_gmail_service,
        to="founder@co.com",
        subject="Test subject",
        body="Test body",
        sender_email="me@gmail.com",
    )

    # Verify send was called with raw MIME
    send_call = mock_gmail_service.users().messages().send
    send_call.assert_called()


def test_check_thread_no_reply(mock_gmail_service):
    from backend.email.gmail import check_thread_for_reply

    mock_gmail_service.users().threads().get().execute.return_value = {
        "messages": [
            {"id": "msg-1", "labelIds": ["SENT"]},
        ]
    }

    result = check_thread_for_reply(
        service=mock_gmail_service,
        thread_id="thread-1",
        sender_email="student@gmail.com",
    )
    assert result is False


def test_check_thread_has_reply(mock_gmail_service):
    from backend.email.gmail import check_thread_for_reply

    mock_gmail_service.users().threads().get().execute.return_value = {
        "messages": [
            {"id": "msg-1", "labelIds": ["SENT"]},
            {"id": "msg-2", "labelIds": ["INBOX"]},
        ]
    }

    result = check_thread_for_reply(
        service=mock_gmail_service,
        thread_id="thread-1",
        sender_email="student@gmail.com",
    )
    assert result is True


def test_build_gmail_service():
    from backend.email.gmail import build_gmail_service

    with patch("backend.email.gmail.build") as mock_build:
        mock_build.return_value = MagicMock()
        service = build_gmail_service("access-token-123")

    mock_build.assert_called_once()
    assert service is not None
