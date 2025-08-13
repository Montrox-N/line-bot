import os
from flask import Flask, request, abort

from linebot.v3 import WebhookHandler
from linebot.v3.exceptions import InvalidSignatureError
from linebot.v3.messaging import (
    Configuration, ApiClient, MessagingApi,
    ReplyMessageRequest, TextMessage
)
from linebot.v3.webhooks import MessageEvent, TextMessageContent, MemberJoinedEvent

# (اختياري) لو عندك helper.py للردود الجاهزة
try:
    from helper import get_auto_reply
except Exception:
    def get_auto_reply(_): return None

app = Flask(__name__)

# ✅ اقرأ القيم من المتغيرات البيئية (آمن للنشر على Render)
CHANNEL_SECRET = os.getenv("LINE_CHANNEL_SECRET")
CHANNEL_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")

if not CHANNEL_SECRET or not CHANNEL_ACCESS_TOKEN:
    # لو تشغل محليًا تقدر تطبع رسالة بدل raise
    raise RuntimeError("ضبط المتغيرات البيئية LINE_CHANNEL_SECRET و LINE_CHANNEL_ACCESS_TOKEN مطلوب قبل التشغيل.")

handler = WebhookHandler(CHANNEL_SECRET)
configuration = Configuration(access_token=CHANNEL_ACCESS_TOKEN)

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

@handler.add(MessageEvent, message=TextMessageContent)
def handle_text(event: MessageEvent):
    text = (event.message.text or "").strip()
    reply = get_auto_reply(text)
    if not reply:
        return
    with ApiClient(configuration) as api_client:
        MessagingApi(api_client).reply_message_with_http_info(
            ReplyMessageRequest(
                reply_token=event.reply_token,
                messages=[TextMessage(text=reply)]
            )
        )

@handler.add(MemberJoinedEvent)
def on_member_joined(event: MemberJoinedEvent):
    with ApiClient(configuration) as api_client:
        MessagingApi(api_client).reply_message_with_http_info(
            ReplyMessageRequest(
                reply_token=event.reply_token,
                messages=[TextMessage(text="مرحبًا 👋 نورتوا القروب! ✨")]
            )
        )

if __name__ == "__main__":
    # Render يمرّر PORT تلقائيًا
    port = int(os.getenv("PORT", "8000"))
    app.run(host="0.0.0.0", port=port)
