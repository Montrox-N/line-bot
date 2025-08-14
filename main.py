import os
import json
import shutil
from pathlib import Path

from flask import (
    Flask, request, render_template_string,
    redirect, url_for, session, abort, send_file
)

# LINE SDK v3
from linebot.v3 import WebhookHandler
from linebot.v3.exceptions import InvalidSignatureError
from linebot.v3.messaging import (
    Configuration, ApiClient, MessagingApi,
    ReplyMessageRequest, TextMessage
)
from linebot.v3.webhooks import (
    MessageEvent, TextMessageContent, MemberJoinedEvent
)

# الهلبر: الردود + المنع (تأكد من وجود helper.py بنفس الدوال)
from helper import get_auto_reply, check_forbidden, get_warning_message

# =============================
# تهيئة Flask + مفاتيح البيئة
# =============================
app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "please-change-this")

CHANNEL_SECRET = os.getenv("LINE_CHANNEL_SECRET")
CHANNEL_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")
if not CHANNEL_SECRET or not CHANNEL_ACCESS_TOKEN:
    raise RuntimeError("ضبط المتغيرات البيئية LINE_CHANNEL_SECRET و LINE_CHANNEL_ACCESS_TOKEN مطلوب قبل التشغيل.")

handler = WebhookHandler(CHANNEL_SECRET)
configuration = Configuration(access_token=CHANNEL_ACCESS_TOKEN)

# كلمة مرور لوحة الإدارة
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "")

# =============================
# إعداد ملف الكلمات (يدعم قرص دائم)
# =============================
# إذا فعّلت Persistent Disk في Render:
#   Settings → Disks → Add Disk (mount path=/data)
# ثم ضع في Environment:
#   WORDS_FILE=/data/words.json
WORDS_FILE = os.getenv("WORDS_FILE", "words.json")
SOURCE_WORDS_FILE = "words.json"  # نسخة أولية من الريبو (تُنسخ عند أول تشغيل لو الملف الدائم غير موجود)

def _ensure_parent_dir(path_str: str):
    p = Path(path_str).expanduser()
    if p.parent and not p.parent.exists():
        p.parent.mkdir(parents=True, exist_ok=True)
    return p

def _bootstrap_words_if_needed():
    """إنشاء النسخة الأولى على القرص الدائم إن لم تكن موجودة."""
    target = Path(WORDS_FILE)
    if not target.exists() and Path(SOURCE_WORDS_FILE).exists():
        _ensure_parent_dir(WORDS_FILE)
        shutil.copy2(SOURCE_WORDS_FILE, WORDS_FILE)

def load_words() -> dict:
    _bootstrap_words_if_needed()
    try:
        with open(WORDS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, dict) else {}
    except Exception:
        return {}

def save_words(data: dict):
    _ensure_parent_dir(WORDS_FILE)
    tmp_path = f"{WORDS_FILE}.tmp"
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    Path(tmp_path).replace(WORDS_FILE)

# =============================
# مسارات عامة
# =============================
@app.route("/health")
def health():
    return "OK", 200

@app.route("/callback", methods=["POST"])
def callback():
    signature = request.headers.get("X-Line-Signature", "")
    body = request.get_data(as_text=True)
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        return "invalid signature", 400
    except Exception:
        return "error", 400
    return "OK", 200

# =============================
# لوحة الإدارة (جلسات + كلمة مرور)
# =============================
ADMIN_TEMPLATE = """
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
  <meta charset="utf-8">
  <title>لوحة تحكم البوت</title>
  <style>
    body { font-family: sans-serif; max-width: 900px; margin: 24px auto; }
    table { border-collapse: collapse; width: 100%; }
    th, td { border: 1px solid #ddd; padding: 8px; }
    th { background: #f7f7f7; }
    input[type=text] { width: 100%; padding: 6px; }
    .box { border: 1px solid #ddd; border-radius: 12px; padding: 16px; margin-bottom: 16px; }
    code { background:#f5f5f5; padding:2px 6px; border-radius:6px; }
    .muted { color:#666; }
    button { padding:8px 14px; cursor:pointer; }
  </style>
</head>
<body>
  <h2>لوحة تحكم البوت</h2>

  <div class="box">
    <div>حالة الخدمة: <b>تشغيل ✅</b></div>
    <div>مسار الصحّة: <code>/health</code></div>
    <div>الويبهوك: <code>/callback</code></div>
    <div class="muted">الردود من الملف: <code>{{ words_file }}</code> — قائمة المنع من: <code>moderation.json</code></div>
  </div>

  <div class="box">
    <h3>الردود الحالية</h3>
    {% if words %}
    <table>
      <tr><th>الكلمة</th><th>الرد</th><th style="width:110px">حذف</th></tr>
      {% for key, value in words.items() %}
      <tr>
        <td>{{ key }}</td>
        <td>{{ value }}</td>
        <td>
          <form method="post" action="{{ url_for('admin_delete') }}" style="display:inline">
            <input type="hidden" name="word" value="{{ key }}">
            <button type="submit">حذف</button>
          </form>
        </td>
      </tr>
      {% endfor %}
    </table>
    {% else %}
      <div>🚫 لا توجد ردود حالياً.</div>
    {% endif %}
  </div>

  <div class="box">
    <h3>إضافة رد جديد</h3>
    <form method="post" action="{{ url_for('admin_add') }}">
      <div style="display:grid; grid-template-columns: 1fr 2fr 140px; gap:10px; align-items:center;">
        <div>
          <label>الكلمة/العبارة</label>
          <input type="text" name="word" required>
        </div>
        <div>
          <label>الرد</label>
          <input type="text" name="reply" required>
        </div>
        <div style="margin-top:22px;">
          <button type="submit" style="width:100%;">إضافة</button>
        </div>
      </div>
    </form>
  </div>

  <div class="box">
    <h3>ملفات البيانات</h3>
    <p>
      <a href="{{ url_for('download_words') }}">⤓ تحميل نسخة من words.json</a>
    </p>
  </div>

  <form method="post" action="{{ url_for('admin_logout') }}">
    <button type="submit">تسجيل الخروج</button>
  </form>
</body>
</html>
"""

LOGIN_TEMPLATE = """
<!doctype html>
<html lang="ar" dir="rtl">
<head>
  <meta charset="utf-8">
  <title>تسجيل دخول الإدارة</title>
  <style>
    body { font-family: sans-serif; max-width: 420px; margin: 48px auto; }
    .box { border: 1px solid #ddd; border-radius: 12px; padding: 16px; }
    .row { margin: 12px 0; }
    .err { color: crimson; }
    input[type=password]{ width:100%; padding:8px; }
    button { padding: 8px 16px; cursor: pointer; }
  </style>
</head>
<body>
  <h2>تسجيل دخول الإدارة</h2>
  {% if error %}<div class="err">{{ error }}</div>{% endif %}
  <form class="box" method="post">
    <div class="row"><label>كلمة المرور</label></div>
    <div class="row"><input type="password" name="password" autofocus></div>
    <div class="row"><button type="submit">دخول</button></div>
  </form>
</body>
</html>
"""

# -----------------------------
# دوال/مسارات الإدارة
# -----------------------------
@app.route("/admin", methods=["GET"])
def admin_home():
    if not session.get("admin_ok"):
        return redirect(url_for("admin_login"))
    words = load_words()
    return render_template_string(ADMIN_TEMPLATE, words=words, words_file=WORDS_FILE)

@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    if request.method == "GET":
        return render_template_string(LOGIN_TEMPLATE, error=None)
    pwd = request.form.get("password", "")
    if not ADMIN_PASSWORD:
        return render_template_string(LOGIN_TEMPLATE, error="ADMIN_PASSWORD غير مضبوط في بيئة Render"), 500
    if pwd == ADMIN_PASSWORD:
        session["admin_ok"] = True
        return redirect(url_for("admin_home"))
    return render_template_string(LOGIN_TEMPLATE, error="كلمة المرور غير صحيحة"), 403

@app.post("/admin/logout")
def admin_logout():
    session.pop("admin_ok", None)
    return redirect(url_for("admin_login"))

@app.post("/admin/add")
def admin_add():
    if not session.get("admin_ok"):
        return redirect(url_for("admin_login"))
    word = (request.form.get("word") or "").strip()
    reply = (request.form.get("reply") or "").strip()
    if not word or not reply:
        return redirect(url_for("admin_home"))
    words = load_words()
    words[word] = reply
    save_words(words)
    return redirect(url_for("admin_home"))

@app.post("/admin/delete")
def admin_delete():
    if not session.get("admin_ok"):
        return redirect(url_for("admin_login"))
    word = (request.form.get("word") or "").strip()
    words = load_words()
    if word in words:
        del words[word]
        save_words(words)
    return redirect(url_for("admin_home"))

@app.get("/admin/download-words")
def download_words():
    if not session.get("admin_ok"):
        return redirect(url_for("admin_login"))
    p = Path(WORDS_FILE)
    if not p.exists():
        return "الملف غير موجود على السيرفر.", 404
    return send_file(
        str(p),
        as_attachment=True,
        download_name="words.json",
        mimetype="application/json; charset=utf-8"
    )

# =============================
# معالجات LINE
# =============================
@handler.add(MessageEvent, message=TextMessageContent)
def on_text(event: MessageEvent):
    txt = (event.message.text or "").strip()

    # تنبيه داخل القروبات/الغرف عند كلمات ممنوعة
    src_type = getattr(event.source, "type", None)
    if src_type in ("group", "room"):
        if check_forbidden(txt):
            warn = get_warning_message()
            with ApiClient(configuration) as client:
                MessagingApi(client).reply_message_with_http_info(
                    ReplyMessageRequest(
                        reply_token=event.reply_token,
                        messages=[TextMessage(text=warn)]
                    )
                )
            return  # لا تكمل ردود أخرى

    # ردود تلقائية من words.json عبر helper
    reply = get_auto_reply(txt)
    if not reply:
        return  # لا رد إذا لا يوجد تطابق

    with ApiClient(configuration) as client:
        MessagingApi(client).reply_message_with_http_info(
            ReplyMessageRequest(
                reply_token=event.reply_token,
                messages=[TextMessage(text=reply)]
            )
        )

@handler.add(MemberJoinedEvent)
def on_member_joined(event: MemberJoinedEvent):
    with ApiClient(configuration) as client:
        MessagingApi(client).reply_message_with_http_info(
            ReplyMessageRequest(
                reply_token=event.reply_token,
                messages=[TextMessage(text="مرحبًا 👋 نورتوا القروب! ✨")]
            )
        )

# =============================
# التشغيل المحلي
# =============================
if __name__ == "__main__":
    port = int(os.getenv("PORT", "8000"))
    app.run(host="0.0.0.0", port=port)
