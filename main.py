import os
from flask import Flask, request, abort

from linebot.v3 import WebhookHandler
from linebot.v3.exceptions import InvalidSignatureError
from linebot.v3.messaging import (
    Configuration, ApiClient, MessagingApi,
    ReplyMessageRequest, TextMessage
)
from linebot.v3.webhooks import MessageEvent, TextMessageContent, MemberJoinedEvent

app = Flask(__name__)

# مفاتيحك
CHANNEL_ACCESS_TOKEN = "89Y1MT+M1f8klkwrepigjHQ3HOjdOcIKjvkFD73cRjYBk+FG9Yb30oFdFAPZ7yyOVaRUNfMhJbX53MEf1Ya9+gNNRh/dhOCXAV6kviej/TvJN837BKV46LrRrVgMmQvcYLVekBdpUNIt1i2E4k8NwgdB04t89/1O/w1cDnyilFU="
CHANNEL_SECRET = "32986ab5b3de87960ddd19c4a96df383"

handler = WebhookHandler(CHANNEL_SECRET)
configuration = Configuration(access_token=CHANNEL_ACCESS_TOKEN)

@app.route("/callback", methods=["POST"])
def callback():
    signature = request.headers.get("X-Line-Signature", "")
    body = request.get_data(as_text=True)
    print("📩 Webhook body:", body)  # للتشخيص
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        print("❌ Invalid signature")
        abort(400)
    except Exception as e:
        print("❌ Handler error:", e)
        abort(400)
    return "OK", 200

# ردودك المخصصة
@handler.add(MessageEvent, message=TextMessageContent)
def handle_message(event: MessageEvent):
    text = (event.message.text or "").strip()
    print("👀 Received text:", text)

    reply = None
    if text == "صباح الخير":
        reply = "صباح النور"
    elif text == "مساء الخير":
        reply = "مساء النور"
    elif text == "السلام عليكم":
        reply = "وعليكم السلام"

    if reply:
        with ApiClient(configuration) as api_client:
            api = MessagingApi(api_client)
            api.reply_message_with_http_info(
                ReplyMessageRequest(
                    reply_token=event.reply_token,
                    messages=[TextMessage(text=reply)]
                )
            )
            print("✅ Replied:", reply)

# ترحيب عند انضمام عضو جديد
@handler.add(MemberJoinedEvent)
def on_member_joined(event: MemberJoinedEvent):
    welcome = "مرحبًا 👋 نورتوا القروب! ✨"
    with ApiClient(configuration) as api_client:
        api = MessagingApi(api_client)
        api.reply_message_with_http_info(
            ReplyMessageRequest(
                reply_token=event.reply_token,
                messages=[TextMessage(text=welcome)]
            )
        )
    print("🎉 Member joined -> sent welcome")

if __name__ == "__main__":
    port = int(os.getenv("PORT", "8000"))
    app.run(host="0.0.0.0", port=port)
