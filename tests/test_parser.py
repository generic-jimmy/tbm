"""Parser — all supported Telegram message types."""
import pytest
from app.parser import parse_update

BH = "testhash"   # bot_hash required by parse_update signature


def _upd(msg: dict, uid: int = 1, key: str = "message") -> dict:
    return {"update_id": uid, key: msg}


def _base(extra: dict | None = None) -> dict:
    m = {
        "message_id": 42,
        "date":       1_700_000_000,
        "from":       {"id": 99, "first_name": "Alice"},
        "chat":       {"id": 100, "type": "private", "first_name": "Alice"},
    }
    if extra:
        m.update(extra)
    return m


def test_text():
    row = parse_update(_upd({**_base(), "text": "Hello world"}), BH)
    assert row["kind"] == "text"
    assert row["content"] == "Hello world"
    assert row["sender_id"] == 99
    assert row["chat_id"] == 100


def test_photo():
    msg = {**_base(), "photo": [{"file_id": "ph1", "width": 320, "height": 240}]}
    row = parse_update(_upd(msg, 2), BH)
    assert row["kind"] == "photo"
    assert row["file_id"] == "ph1"


def test_document():
    msg = {**_base(), "document": {
        "file_id": "doc1", "file_name": "report.pdf",
        "file_size": 2048, "mime_type": "application/pdf",
    }}
    row = parse_update(_upd(msg, 3), BH)
    assert row["kind"] == "document"
    assert row["file_name"] == "report.pdf"
    assert row["file_size"] == 2048
    assert row["mime_type"] == "application/pdf"


def test_video():
    msg = {**_base(), "video": {
        "file_id": "vid1", "duration": 30,
        "width": 1280, "height": 720, "mime_type": "video/mp4",
    }}
    row = parse_update(_upd(msg, 4), BH)
    assert row["kind"] == "video"
    assert row["duration"] == 30


def test_audio():
    msg = {**_base(), "audio": {
        "file_id": "aud1", "duration": 180,
        "title": "My Song", "mime_type": "audio/mpeg",
    }}
    row = parse_update(_upd(msg, 5), BH)
    assert row["kind"] == "audio"
    assert row["file_name"] == "My Song"


def test_voice():
    msg = {**_base(), "voice": {"file_id": "voi1", "duration": 5, "mime_type": "audio/ogg"}}
    row = parse_update(_upd(msg, 6), BH)
    assert row["kind"] == "voice"


def test_sticker():
    msg = {**_base(), "sticker": {"file_id": "stk1", "emoji": "👍", "set_name": "MyPack"}}
    row = parse_update(_upd(msg, 7), BH)
    assert row["kind"] == "sticker"
    assert row["file_id"] == "stk1"


def test_location():
    msg = {**_base(), "location": {"latitude": 40.7128, "longitude": -74.0060}}
    row = parse_update(_upd(msg, 8), BH)
    assert row["kind"] == "location"
    assert abs(row["latitude"]  - 40.7128) < 1e-4
    assert abs(row["longitude"] - (-74.0060)) < 1e-4


def test_contact():
    msg = {**_base(), "contact": {
        "first_name": "Bob", "last_name": "Smith", "phone_number": "+1234567890",
    }}
    row = parse_update(_upd(msg, 9), BH)
    assert row["kind"] == "contact"
    assert "+1234567890" in row["content"]


def test_edited_message():
    msg = {**_base(), "text": "Edited content"}
    row = parse_update(_upd(msg, 10, key="edited_message"), BH)
    assert row["is_edited"] is True


def test_channel_post():
    msg = {
        "message_id": 77, "date": 1_700_001_000,
        "chat": {"id": -200, "type": "channel", "title": "My Channel"},
        "text": "Channel broadcast",
    }
    row = parse_update({"update_id": 11, "channel_post": msg}, BH)
    assert row is not None
    assert row["kind"] == "text"
    assert row["chat_id"] == -200
    assert row["chat_title"] == "My Channel"


def test_no_message_returns_none():
    row = parse_update({"update_id": 12, "inline_query": {"id": "abc", "query": "test"}}, BH)
    assert row is None


def test_forwarded_flag():
    msg = {
        **_base(), "text": "Forwarded!",
        "forward_from": {"id": 55, "first_name": "Charlie", "last_name": "Brown"},
    }
    row = parse_update(_upd(msg, 13), BH)
    assert row["is_forwarded"] is True
    assert "Charlie" in (row["fwd_from"] or "")


def test_reply_to():
    msg = {**_base(), "text": "Reply!", "reply_to_message": {"message_id": 41}}
    row = parse_update(_upd(msg, 14), BH)
    assert row["reply_to_id"] == 41


def test_caption_appended():
    msg = {
        **_base(),
        "photo": [{"file_id": "ph2", "width": 100, "height": 100}],
        "caption": "Nice photo!",
    }
    row = parse_update(_upd(msg, 15), BH)
    assert "Nice photo!" in row["content"]
    assert row["caption"] == "Nice photo!"
