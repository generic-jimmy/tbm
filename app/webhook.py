"""Shared helper for deriving a per-bot Telegram webhook secret.

No new DB column needed: the secret is deterministic — HMAC(SECRET_KEY, bot_hash).
Both the worker (when calling setWebhook) and the incoming route (when
verifying X-Telegram-Bot-Api-Secret-Token) recompute it the same way.
"""
import hashlib
import hmac


def webhook_secret_for(bot_hash: str, secret_key: str) -> str:
    return hmac.new(
        secret_key.encode(), bot_hash.encode(), hashlib.sha256
    ).hexdigest()


def webhook_path(bot_hash: str) -> str:
    return f"/webhook/{bot_hash}"
