"""Parse a Telegram update dict into a flat DB-ready row."""
import time
from datetime import datetime, timezone
from typing import Optional


def parse_update(upd: dict, bot_hash: str) -> Optional[dict]:
    msg = (upd.get("message")
           or upd.get("edited_message")
           or upd.get("channel_post")
           or upd.get("edited_channel_post"))
    if not msg:
        return None

    is_edited = "edited_message" in upd or "edited_channel_post" in upd
    sender    = msg.get("from") or {}
    chat      = msg.get("chat") or {}

    kind  = "text"
    fid   = None
    fname = None
    fsize = None
    mime  = None
    body  = ""
    w = h = dur = lat = lon = None
    cap       = msg.get("caption", "") or ""
    fwd_from  = None
    reply_to  = None

    if is_edited:
        kind = "edited"
        body = msg.get("text") or msg.get("caption") or ""

    elif "text" in msg:
        kind = "text"
        body = msg["text"]

    elif "document" in msg:
        d     = msg["document"]
        kind  = "document"
        fid   = d["file_id"]
        fname = d.get("file_name", "unknown")
        fsize = d.get("file_size")
        mime  = d.get("mime_type")
        body  = f"File: {fname}  ({fsize or '?'} bytes)"

    elif "photo" in msg:
        ph   = msg["photo"][-1]
        kind = "photo"
        fid  = ph["file_id"]
        w, h = ph.get("width"), ph.get("height")
        body = f"Photo {w}×{h}"

    elif "video" in msg:
        vd   = msg["video"]
        kind = "video"
        fid  = vd["file_id"]
        dur  = vd.get("duration")
        w, h = vd.get("width"), vd.get("height")
        mime = vd.get("mime_type")
        body = f"Video {dur}s  {w}×{h}"

    elif "audio" in msg:
        au   = msg["audio"]
        kind = "audio"
        fid  = au["file_id"]
        dur  = au.get("duration")
        fname = au.get("title") or au.get("file_name")
        mime = au.get("mime_type")
        body = f"Audio: {fname or 'unknown'}  {dur}s"

    elif "voice" in msg:
        vo   = msg["voice"]
        kind = "voice"
        fid  = vo["file_id"]
        dur  = vo.get("duration")
        mime = vo.get("mime_type")
        body = f"Voice {dur}s"

    elif "video_note" in msg:
        vn   = msg["video_note"]
        kind = "voice"
        fid  = vn["file_id"]
        dur  = vn.get("duration")
        body = f"Video note {dur}s"

    elif "sticker" in msg:
        st   = msg["sticker"]
        kind = "sticker"
        fid  = st.get("file_id")
        body = f"Sticker {st.get('emoji', '')} ({st.get('set_name', '')})"

    elif "location" in msg:
        kind = "location"
        lat  = msg["location"]["latitude"]
        lon  = msg["location"]["longitude"]
        body = f"Location: {lat}, {lon}"

    elif "contact" in msg:
        ct   = msg["contact"]
        kind = "contact"
        body = (f"{ct.get('first_name', '')} {ct.get('last_name', '')}"
                f"\n{ct.get('phone_number', '')}")

    elif "poll" in msg:
        kind = "text"
        body = f"Poll: {msg['poll'].get('question', '')}"

    else:
        body = "Unsupported message type"

    if cap:
        body += f"\n📝 {cap}"

    # Forwarded?
    if "forward_from" in msg:
        fwd_from = (msg["forward_from"].get("first_name", "")
                    + " " + msg["forward_from"].get("last_name", "")).strip()
    elif "forward_from_chat" in msg:
        fwd_from = msg["forward_from_chat"].get("title", "")
    elif "forward_sender_name" in msg:
        fwd_from = msg["forward_sender_name"]

    if "reply_to_message" in msg:
        reply_to = msg["reply_to_message"].get("message_id")

    raw_ts = msg.get("date") or msg.get("edit_date") or int(time.time())
    ts = datetime.fromtimestamp(raw_ts, tz=timezone.utc)

    return {
        "msg_id":        msg.get("message_id"),
        "bot_hash":      bot_hash,
        "update_id":     upd["update_id"],
        "kind":          kind,
        "sender_id":     sender.get("id"),
        "sender_name":   sender.get("first_name") or chat.get("title") or "system",
        "chat_id":       chat.get("id"),
        "chat_title":    chat.get("title") or sender.get("first_name") or "",
        "chat_type":     chat.get("type", ""),
        "chat_username": chat.get("username"),
        "content":       body,
        "caption":       cap or None,
        "file_id":       fid,
        "file_name":     fname,
        "file_size":     fsize,
        "mime_type":     mime,
        "is_forwarded":  fwd_from is not None,
        "fwd_from":      fwd_from,
        "reply_to_id":   reply_to,
        "is_edited":     is_edited,
        "is_deleted":    False,
        "width":   w,   "height": h, "duration": dur,
        "latitude": lat, "longitude": lon,
        "raw_json":  upd,
        "ts":        ts,
        # extra context for callers
        "_sender":  sender,
        "_chat":    chat,
    }
