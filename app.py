import os, json, re
from flask import Flask, request, abort, redirect, url_for, render_template_string, session
from dotenv import load_dotenv

# === إعدادات عامة ===
load_dotenv()
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "change-me")
FLASK_SECRET   = os.getenv("FLASK_SECRET",   "please-change")
WORDS_FILE     = os.getenv("WORDS_FILE", "words.json")

# === LINE SDK ===
from linebot import LineBotApi, WebhookHandler
from linebot.models import MessageEvent, TextMessage, TextSendMessage
from linebot.exceptions import InvalidSignatureError

LINE_CHANNEL_SECRET = os.getenv("LINE_CHANNEL_SECRET")
LINE_CHANNEL_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")
if not LINE_CHANNEL_SECRET or not LINE_CHANNEL_ACCESS_TOKEN:
    raise RuntimeError("الرجاء ضبط LINE_CHANNEL_SECRET و LINE_CHANNEL_ACCESS_TOKEN في Environment")

line_bot_api = LineBotApi(LINE_CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(LINE_CHANNEL_SECRET)

app = Flask(__name__)
app.secret_key = FLASK_SECRET

# === أدوات عربية بسيطة ===
ARABIC_DIACRITICS = re.compile(r"[\u0617-\u061A\u064B-\u0652\u0670\u06D6-\u06ED]")
def normalize_ar(text: str) -> str:
    if not text: return ""
    text = text.replace("أ","ا").replace("إ","ا").replace("آ","ا").replace("ة","ه")
    text = ARABIC_DIACRITICS.sub("", text).replace("ـ","")
    return re.sub(r"\s+"," ", text).strip().lower()

# === تحميل/حفظ الكلمات ===
def load_words():
    if not os.path.exists(WORDS_FILE):
        return {}
    with open(WORDS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_words(data: dict):
    with open(WORDS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def find_reply(user_text: str) -> str | None:
    t = normalize_ar(user_text)
    words = load_words()
    for key, val in words.items():
        if normalize_ar(key) in t:
            return val
    return None

# === LINE Webhook ===
@app.post("/callback")
def callback():
    signature = request.headers.get("X-Line-Signature", "")
    body = request.get_data(as_text=True)
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)
    return "OK"

@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    incoming = event.message.text or ""
    reply = find_reply(incoming)
    if reply is None:
        reply = "ما فهمت، جرّب كلمة مفتاحية أو ادخل لوحة الإدارة لتضيف كلمات."
    line_bot_api.reply_message(event.reply_token, TextSendMessage(text=reply))

# === لوحة التحكم ===
ADMIN_TEMPLATE = """
<!doctype html>
<html lang="ar" dir="rtl">
<head>
  <meta charset="utf-8">
  <title>لوحة كلمات البوت</title>
  <style>
    body{font-family:sans-serif; max-width:780px; margin:24px auto}
    table{width:100%; border-collapse:collapse}
    th,td{border:1px solid #ddd; padding:8px}
    form{margin:16px 0}
    input[type=text]{width:100%; padding:8px}
    .row{display:grid; grid-template-columns:1fr 1fr; gap:12px}
    .topbar{display:flex; justify-content:space-between; align-items:center}
    .btn{padding:8px 12px; border:1px solid #555; background:#f5f5f5; cursor:pointer}
    .small{font-size:12px; color:#666}
  </style>
</head>
<body>
  <div class="topbar">
    <h2>لوحة كلمات البوت</h2>
    <form method="post" action="{{ url_for('admin_logout') }}">
      <button class="btn">تسجيل خروج</button>
    </form>
  </div>

  <p class="small">ملف التخزين: {{ words_file }}</p>

  <h3>إضافة/تعديل كلمة</h3>
  <form method="post" action="{{ url_for('admin_add') }}">
    <div class="row">
      <div>
        <label>الكلمة/المفتاح:</label>
        <input type="text" name="key" required>
      </div>
      <div>
        <label>الرد:</label>
        <input type="text" name="val" required>
      </div>
    </div>
    <button class="btn" style="margin-top:10px">حفظ</button>
  </form>

  <h3>القائمة الحالية</h3>
  <table>
    <thead><tr><th>الكلمة</th><th>الرد</th><th>إجراء</th></tr></thead>
    <tbody>
      {% for k, v in words.items() %}
      <tr>
        <td>{{ k }}</td>
        <td>{{ v }}</td>
        <td>
          <form method="post" action="{{ url_for('admin_delete') }}" style="display:inline">
            <input type="hidden" name="key" value="{{ k }}">
            <button class="btn">حذف</button>
          </form>
        </td>
      </tr>
      {% endfor %}
      {% if not words %}
      <tr><td colspan="3" style="text-align:center">لا توجد كلمات بعد</td></tr>
      {% endif %}
    </tbody>
  </table>
</body>
</html>
"""

LOGIN_TEMPLATE = """
<!doctype html>
<html lang="ar" dir="rtl">
<head>
  <meta charset="utf-8">
  <title>تسجيل الدخول للوحة الإدارة</title>
  <style>
    body{font-family:sans-serif; max-width:420px; margin:48px auto}
    label{display:block; margin-bottom:6px}
    input{width:100%; padding:8px; margin-bottom:10px; box-sizing:border-box}
    .btn{padding:8px 12px; border:1px solid #555; background:#f5f5f5; cursor:pointer}
    .error{color:#b00; margin-top:8px}
  </style>
</head>
<body>
  <h2 style="text-align:center">تسجيل الدخول للوحة الإدارة</h2>
  <form method="post">
    <label>كلمة المرور:</label>
    <input type="password" name="password" required>
    <button class="btn">دخول</button>
  </form>
  {% if error %}
  <p class="error">{{ error }}</p>
  {% endif %}
</body>
</html>
"""

def require_login(fn):
    from functools import wraps
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not session.get("admin_ok"):
            return redirect(url_for("admin_login"))
        return fn(*args, **kwargs)
    return wrapper

@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        if request.form.get("password") == ADMIN_PASSWORD:
            session["admin_ok"] = True
            return redirect(url_for("admin_home"))
        return render_template_string(LOGIN_TEMPLATE, error="كلمة المرور غير صحيحة")
    return render_template_string(LOGIN_TEMPLATE, error=None)

@app.post("/admin/logout")
def admin_logout():
    session.clear()
    return redirect(url_for("admin_login"))

@app.get("/admin")
@require_login
def admin_home():
    words = load_words()
    return render_template_string(ADMIN_TEMPLATE, words=words, words_file=WORDS_FILE)

@app.post("/admin/add")
@require_login
def admin_add():
    key = (request.form.get("key") or "").strip()
    val = (request.form.get("val") or "").strip()
    if key and val:
        words = load_words()
        words[key] = val
        save_words(words)
    return redirect(url_for("admin_home"))

@app.post("/admin/delete")
@require_login
def admin_delete():
    key = (request.form.get("key") or "").strip()
    words = load_words()
    if key in words:
        words.pop(key)
        save_words(words)
    return redirect(url_for("admin_home"))

@app.get("/")
def health():
    return "OK"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 5000)))
