# helper.py
import os, json, re, datetime

# ---------- تطبيع النص العربي ----------
_ARABIC_DIACRITICS = re.compile(r"[\u0610-\u061A\u064B-\u065F\u0670\u06D6-\u06ED]")
def normalize_ar(text: str) -> str:
    if not text:
        return ""
    t = text.strip()
    t = _ARABIC_DIACRITICS.sub("", t)     # إزالة التشكيل
    t = t.replace("ـ", "")                # إزالة التطويل
    t = t.replace("أ","ا").replace("إ","ا").replace("آ","ا")
    t = t.replace("ى","ي").replace("ئ","ي").replace("ؤ","و")
    return t.lower()

# ---------- مسارات الملفات (مُوحّدة) ----------
# نُفضّل قراءة المسار من WORDS_FILE (لو عندك /data/words.json على Render)
_WORDS_PATH = (
    os.getenv("WORDS_FILE")
    or os.getenv("WORDS_PATH")
    or "words.json"
)

# لقائمة المنع
_MOD_PATH = (
    os.getenv("MODERATION_FILE")
    or os.getenv("MODERATION_PATH")
    or "moderation.json"
)

# ---------- كاش خفيف بوقت التعديل ----------
_WORDS = None
_W_MTIME = None

_MOD = None
_M_MTIME = None

def _safe_load_json(path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None

# ----- تحميل الكلمات مع فحص mtime في كل نداء -----
def _load_words():
    global _WORDS, _W_MTIME
    try:
        mtime = os.path.getmtime(_WORDS_PATH)
    except Exception:
        # لو الملف غير موجود أو لا يمكن قراءته
        _WORDS, _W_MTIME = {}, None
        return

    if _WORDS is not None and _W_MTIME == mtime:
        # لا تغيير على الملف
        return

    data = _safe_load_json(_WORDS_PATH) or {}
    # طَبّع المفاتيح العربية
    normalized = {}
    for k, v in data.items():
        if not isinstance(k, str):
            continue
        normalized[normalize_ar(k)] = v
    _WORDS = normalized
    _W_MTIME = mtime

# ----- تحميل المنع مع فحص mtime في كل نداء -----
def _load_mod():
    global _MOD, _M_MTIME
    try:
        mtime = os.path.getmtime(_MOD_PATH)
    except Exception:
        _MOD, _M_MTIME = {"forbidden": [], "warning": "⚠️ الرجاء عدم استخدام الكلمات المخالفة.", "notify_admin": False}, None
        return

    if _MOD is not None and _M_MTIME == mtime:
        return

    data = _safe_load_json(_MOD_PATH) or {}
    forb = []
    for x in data.get("forbidden", []):
        if isinstance(x, str):
            forb.append(normalize_ar(x))
    _MOD = {
        "forbidden": forb,
        "warning": data.get("warning") or "⚠️ الرجاء عدم استخدام الكلمات المخالفة.",
        "notify_admin": bool(data.get("notify_admin", False))
    }
    _M_MTIME = mtime

# ---------- API المستخدمة في main.py ----------
def check_forbidden(text: str) -> bool:
    _load_mod()
    t = normalize_ar(text or "")
    for bad in _MOD.get("forbidden", []):
        if bad and bad in t:
            return True
    return False

def get_warning_message() -> str:
    _load_mod()
    return _MOD.get("warning", "⚠️ الرجاء عدم استخدام الكلمات المخالفة.")

def get_auto_reply(message: str):
    """
    يعيد الرد المناسب أو None.
    يعيد تحميل words.json تلقائيًا عند تغيّره.
    """
    if not message:
        return None

    _load_words()  # <-- هنا السحر: إعادة التحميل عند الحاجة
    raw = (message or "").strip()
    text = normalize_ar(raw)

    # أوامر سريعة
    if raw.strip() == "!time" or text == "!time":
        now = datetime.datetime.utcnow() + datetime.timedelta(hours=3)  # UTC+3
        return f"الوقت الآن: {now.strftime('%H:%M:%S')} ⏱"

    if raw.strip() == "!date" or text == "!date":
        today = datetime.datetime.utcnow() + datetime.timedelta(hours=3)
        return f"تاريخ اليوم: {today.strftime('%Y-%m-%d')} 📅"

    # مطابقة تامة من ملف الكلمات
    if text in (_WORDS or {}):
        return _WORDS[text]

    # (اختياري) contains خفيف لبعض الكلمات الشائعة
    # حتى لو ما فيه تطابق تام، جرّب وجود مفتاح قصير شائع داخل النص
    for key_norm, resp in (_WORDS or {}).items():
        if len(key_norm) >= 2 and key_norm in text:
            if key_norm in ("بوت", "مساعدة", "شكرا", "شكراً", "صباح", "مساء", "السلام"):
                return resp

    # لا يوجد رد
    return None
