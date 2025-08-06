from flask import Flask, request, abort
from linebot.v3.messaging import MessagingApi, Configuration, ApiClient
from linebot.v3.webhook import WebhookHandler, MessageEvent
from linebot.v3.webhooks import TextMessageContent
from linebot.v3.messaging.models import TextMessage

app = Flask(__name__)

# بيانات التوكن والسر
channel_access_token = '89Y1MT+M1f8klkwrepigjHQ3HOjdOcIKjvkFD73cRjYBk+FG9Yb30oFdFAPZ7yyOVaRUNfMhJbX53MEf1Ya9+gNNRh/dhOCXAV6kviej/TvJN837BKV46LrRrVgMmQvcYLVekBdpUNIt1i2E4k8NwgdB04t89/1O/w1cDnyilFU='
channel_secret = '32986ab5b3de87960ddd19c4a96df383'

configuration = Configuration(access_token=channel_access_token)
handler = WebhookHandler(channel_secret)

@app.route("/callback", methods=["POST"])
def callback():
    signature = request.headers.get("X-Line-Signature")
    body = request.get_data(as_text=True)

    try:
        handler.handle(body, signature)
    except Exception as e:
        print("❌ حدث خطأ في webhook:", e)
        abort(400)

    return "OK", 200  # ✅ هذا السطر يضمن رجوع 200 للـ LINE

@handler.add(MessageEvent)
def handle_message(event):
    if isinstance(event.message, TextMessageContent):
        user_message = event.message.text.lower()

        if user_message == "ping":
            reply = "pong!"
        else:
            reply = f"أنت قلت: {user_message}"

        with ApiClient(configuration) as api_client:
            messaging_api = MessagingApi(api_client)
            messaging_api.reply_message(
                reply_token=event.reply_token,
                messages=[TextMessage(text=reply)]
            )

if __name__ == "__main__":
    app.run(port=8000)
