"""Crypto module — Fernet encrypt/decrypt/hash roundtrip tests."""
import pytest
from app.crypto import decrypt_token, encrypt_token, hash_token

KEY = "test-secret-key-exactly-32bytes!!"


def test_roundtrip():
    token = "1234567890:AAHdqTcvCH1vGWJxfSeofSAs0K5PALDsaw"
    assert decrypt_token(encrypt_token(token, KEY), KEY) == token


def test_fernet_random_iv():
    """Same plaintext → different ciphertext every call (Fernet uses random IV)."""
    token = "my-bot-token"
    c1 = encrypt_token(token, KEY)
    c2 = encrypt_token(token, KEY)
    assert c1 != c2
    assert decrypt_token(c1, KEY) == decrypt_token(c2, KEY) == token


def test_hash_is_stable():
    h = hash_token("some-token")
    assert h == hash_token("some-token")


def test_hash_length():
    assert len(hash_token("x")) == 16


def test_different_tokens_different_hashes():
    assert hash_token("token-a") != hash_token("token-b")


def test_wrong_key_raises():
    ct = encrypt_token("secret", KEY)
    with pytest.raises(Exception):
        decrypt_token(ct, "wrong-key-entirely-different!!")
