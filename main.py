import os
from flask import Flask, request

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

# الهلبر: الردود + المنع
from helper import get_auto_reply, check_forbidden, get_warning_message

app = Flask(__name__)

# مفاتيح القناة من المتغيرات البيئية (Render أو النظام)
CHANNEL_SECRET = os.getenv("LINE_CHANNEL_SECRET")
CHANNEL_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")
if not CHANNEL_SECRET or not CHANNEL_ACCESS_TOKEN:
    raise RuntimeError("ضبط المتغيرات البيئية LINE_CHANNEL_SECRET و LINE_CHANNEL_ACCESS_TOKEN مطلوب قبل التشغيل.")

# تهيئة LINE SDK
handler = WebhookHandler(CHANNEL_SECRET)
configuration = Configuration(access_token=CHANNEL_ACCESS_TOKEN)

# مسار فحص الصحة (اختياري)
@app.route("/health")
def health():
    return "OK", 200

# مسار الويب هوك
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

# معالج رسائل النص
@handler.add(MessageEvent, message=TextMessageContent)
def on_text(event: MessageEvent):
    txt = (event.message.text or "").strip()

    # 1) منع كلمات داخل القروبات/الغرف
    src_type = getattr(event.source, "type", None)  # "user" | "group" | "room"
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

    # 2) الردود الآلية من words.json عبر helper
    reply = get_auto_reply(txt)
    if not reply:
        return  # لا ترسل شيء إذا لا يوجد تطابق

    with ApiClient(configuration) as client:
        MessagingApi(client).reply_message_with_http_info(
            ReplyMessageRequest(
                reply_token=event.reply_token,
                messages=[TextMessage(text=reply)]
            )
        )

# ترحيب عند انضمام عضو للقروب (اختياري)
@handler.add(MemberJoinedEvent)
def on_member_joined(event: MemberJoinedEvent):
    with ApiClient(configuration) as client:
        MessagingApi(client).reply_message_with_http_info(
            ReplyMessageRequest(
                reply_token=event.reply_token,
                messages=[TextMessage(text="مرحبًا 👋 نورتوا القروب! ✨")]
            )
        )

if __name__ == "__main__":
    port = int(os.getenv("PORT", "8000"))
    app.run(host="0.0.0.0", port=port)
