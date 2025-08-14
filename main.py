import os
from flask import Flask, request, render_template_string, redirect, url_for, session, abort

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

# الهلبر: ردود + منع كلمات القروب (تأكد وجود helper.py بنفس الدوال)
from helper import get_auto_reply, check_forbidden, get_warning_message

# =============================
# تهيئة Flask + المفاتيح
# =============================
app = Flask(__name__)
# مفتاح الجلسة للّوحة (ضَع FLASK_SECRET_KEY في Environment على Render)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "please-change-this")

CHANNEL_SECRET = os.getenv("LINE_CHANNEL_SECRET")
CHANNEL_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")
if not CHANNEL_SECRET or not CHANNEL_ACCESS_TOKEN:
    raise RuntimeError("ضبط المتغيرات البيئية LINE_CHANNEL_SECRET و LINE_CHANNEL_ACCESS_TOKEN مطلوب قبل التشغيل.")

handler = WebhookHandler(CHANNEL_SECRET)
configuration = Configuration(access_token=CHANNEL_ACCESS_TOKEN)

# كلمة مرور لوحة الإدارة (ADMIN_PASSWORD في Environment على Render)
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "")

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
<!doctype html>
<html lang="ar" dir="rtl">
<head>
  <meta charset="utf-8">
  <title>لوحة تحكم البوت</title>
  <style>
    body { font-family: sans-serif; max-width: 720px; margin: 24px auto; }
    .box { border: 1px solid #ddd; border-radius: 12px; padding: 16px; }
    .row { margin: 12px 0; }
    code { background:#f5f5f5; padding:2px 6px; border-radius:6px; }
    button { padding: 8px 16px; cursor: pointer; }
  </style>
</head>
<body>
  <h2>لوحة تحكم البوت</h2>
  <div class="box">
    <div class="row">حالة الخدمة: <b>تشغيل ✅</b></div>
    <div class="row">مسار الصحّة: <code>/health</code></div>
    <div class="row">الويبهوك: <code>/callback</code></div>
    <div class="row">الردود من الملف: <code>words.json</code></div>
    <div class="row">قائمة المنع من: <code>moderation.json</code></div>
  </div>
  <form method="post" action="{{ url_for('admin_logout') }}" style="margin-top:16px">
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

@app.route("/admin", methods=["GET"])
def admin_home():
    if not session.get("admin_ok"):
        return redirect(url_for("admin_login"))
    return render_template_string(ADMIN_TEMPLATE)

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
        return  # لا رد إذا ما في تطابق

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
