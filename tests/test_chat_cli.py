from unittest.mock import MagicMock, patch

import chat


def test_request_chat_success():
    fake_response = MagicMock()
    fake_response.status_code = 200
    fake_response.json.return_value = {
        "message": {"role": "assistant", "content": "hello from model"}
    }

    with patch("chat.httpx.Client") as client_cls:
        client_instance = client_cls.return_value.__enter__.return_value
        client_instance.post.return_value = fake_response

        out = chat.request_chat(
            api_base="http://127.0.0.1:8000",
            model="llama3.1:8b",
            messages=[{"role": "user", "content": "hi"}],
            temperature=0.7,
            max_tokens=64,
        )

    assert out == "hello from model"


def test_request_chat_error_message_uses_detail_when_available():
    fake_response = MagicMock()
    fake_response.status_code = 400
    fake_response.json.return_value = {"detail": "bad request"}

    with patch("chat.httpx.Client") as client_cls:
        client_instance = client_cls.return_value.__enter__.return_value
        client_instance.post.return_value = fake_response

        try:
            chat.request_chat(
                api_base="http://127.0.0.1:8000",
                model="llama3.1:8b",
                messages=[{"role": "user", "content": "hi"}],
                temperature=0.7,
                max_tokens=64,
            )
            assert False, "Expected RuntimeError"
        except RuntimeError as exc:
            assert "bad request" in str(exc)


def test_request_chat_retries_on_5xx_then_succeeds():
    first = MagicMock()
    first.status_code = 502
    first.json.return_value = {"detail": "temporary"}

    second = MagicMock()
    second.status_code = 200
    second.json.return_value = {
        "message": {"role": "assistant", "content": "recovered"}
    }

    with patch("chat.httpx.Client") as client_cls:
        client_instance = client_cls.return_value.__enter__.return_value
        client_instance.post.side_effect = [first, second]

        out = chat.request_chat(
            api_base="http://127.0.0.1:8000",
            model="llama3.1:8b",
            messages=[{"role": "user", "content": "hi"}],
            temperature=0.7,
            max_tokens=64,
            retries=1,
        )

    assert out == "recovered"


def test_request_chat_does_not_retry_on_4xx():
    bad = MagicMock()
    bad.status_code = 400
    bad.json.return_value = {"detail": "invalid input"}

    with patch("chat.httpx.Client") as client_cls:
        client_instance = client_cls.return_value.__enter__.return_value
        client_instance.post.return_value = bad

        try:
            chat.request_chat(
                api_base="http://127.0.0.1:8000",
                model="llama3.1:8b",
                messages=[{"role": "user", "content": "hi"}],
                temperature=0.7,
                max_tokens=64,
                retries=3,
            )
            assert False, "Expected RuntimeError"
        except RuntimeError as exc:
            assert "invalid input" in str(exc)

    assert client_instance.post.call_count == 1


def test_request_chat_sends_api_key_header_when_provided():
    ok = MagicMock()
    ok.status_code = 200
    ok.json.return_value = {
        "message": {"role": "assistant", "content": "auth ok"}
    }

    with patch("chat.httpx.Client") as client_cls:
        client_instance = client_cls.return_value.__enter__.return_value
        client_instance.post.return_value = ok

        out = chat.request_chat(
            api_base="http://127.0.0.1:8000",
            model="llama3.1:8b",
            messages=[{"role": "user", "content": "hi"}],
            temperature=0.7,
            max_tokens=64,
            api_key="secret",
        )

    assert out == "auth ok"
    _, kwargs = client_instance.post.call_args
    assert kwargs["headers"] == {"X-API-Key": "secret"}
