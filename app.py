import os, json, re
from flask import Flask, request, abort, redirect, url_for, render_template_string, session
from dotenv import load_dotenv

# === إعدادات عامة ===
load_dotenv()  # محليًا فقط، آمن تجاهلها على Render
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "change-me")  # ضعها في Render
FLASK_SECRET   = os.getenv("FLASK_SECRET",   "please-change")  # ضعها في Render
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
        <inp
