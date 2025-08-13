import json, re, os, time, datetime

_ARABIC_DIACRITICS = re.compile(r"[\u0610-\u061A\u064B-\u065F\u0670\u06D6-\u06ED]")
def normalize_ar(text: str) -> str:
    if not text:
        return ""
    t = text.strip()
    t = _ARABIC_DIACRITICS.sub("", t)
    t = t.replace("ـ", "")
    t = t.replace("أ","ا").replace("إ","ا").replace("آ","ا")
    t = t.replace("ى","ي").replace("ئ","ي").replace("ؤ","و")
    return t.lower()

_REPLIES_PATH = os.getenv("REPLIES_PATH", "replies.json")
_REPLIES = None
_R_MTIME = 0

def _load_replies():
    global _REPLIES, _R_MTIME
    if not os.path.exists(_REPLIES_PATH):
        _REPLIES = {"exact":{}, "contains":{}, "regex":{}, "fallback": None}
        _R_MTIME = 0
        return
    m = os.path.getmtime(_REPLIES_PATH)
    if _REPLIES is not None and m == _R_MTIME:
        return
    with open(_REPLIES_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    exact = {normalize_ar(k): v for k, v in data.get("exact", {}).items()}
    contains = {normalize_ar(k): v for k, v in data.get("contains", {}).items()}
    _REPLIES = {
        "exact": exact,
        "contains": contains,
        "regex": data.get("regex", {}),
        "fallback": data.get("fallback")
    }
    _R_MTIME = m

_MOD_PATH = os.getenv("MODERATION_PATH", "moderation.json")
_MOD = None
_M_MTIME = 0

def _load_mod():
    global _MOD, _M_MTIME
    if not os.path.exists(_MOD_PATH):
        _MOD = {"forbidden": [], "warning": "⚠️ الرجاء عدم استخدام الكلمات المخالفة.", "notify_admin": False}
        _M_MTIME = 0
        return
    m = os.path.getmtime(_MOD_PATH)
    if _MOD is not None and m == _M_MTIME:
        return
    with open(_MOD_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    forb = [normalize_ar(x) for x in data.get("forbidden", [])]
    _MOD = {"forbidden": forb, "warning": data.get("warning") or "⚠️ الرجاء عدم استخدام الكلمات المخالفة.", "notify_admin": bool(data.get("notify_admin", False))}
    _M_MTIME = m

def check_forbidden(text: str) -> bool:
    _load_mod()
    t = normalize_ar(text or "")
    for bad in _MOD["forbidden"]:
        if bad and bad in t:
            return True
    return False

def get_warning_message() -> str:
    _load_mod()
    return _MOD["warning"]

def get_auto_reply(message: str):
    if not message:
        return None
    _load_replies()
    raw = message.strip()
    text = normalize_ar(raw)

    if text == "!time" or raw.strip() == "!time":
        now = datetime.datetime.utcnow() + datetime.timedelta(hours=3)
        return f"الوقت الآن: {now.strftime('%H:%M:%S')} ⏱"
    if text == "!date" or raw.strip() == "!date":
        today = datetime.datetime.utcnow() + datetime.timedelta(hours=3)
        return f"تاريخ اليوم: {today.strftime('%Y-%m-%d')} 📅"

    if text in _REPLIES.get("exact", {}):
        return _REPLIES["exact"][text]
    for key, resp in _REPLIES.get("contains", {}).items():
        if key in text:
            return resp
    import re as _re
    for pattern, resp in _REPLIES.get("regex", {}).items():
        if _re.search(pattern, raw, flags=_re.IGNORECASE):
            return resp
    return _REPLIES.get("fallback") or None
