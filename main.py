from flask import Flask, request, abort
from linebot.v3 import WebhookHandler
from linebot.v3.messaging import MessagingApiClient, ReplyMessageRequest, TextMessage
from linebot.v3.webhook import MessageEvent, TextMessageContent

app = Flask(__name__)

# ضع التوكن والسر الخاص بك هنا
channel_access_token = '89Y1MT+M1f8klkwrepigjHQ3HOjdOcIKjvkFD73cRjYBk+FG9Yb30oFdFAPZ7yyOVaRUNfMhJbX53MEf1Ya9+gNNRh/dhOCXAV6kviej/TvJN837BKV46LrRrVgMmQvcYLVekBdpUNIt1i2E4k8NwgdB04t89/1O/w1cDnyilFU='
channel_secret = '32986ab5b3de87960ddd19c4a96df383'

handler = WebhookHandler(channel_secret)
messaging_api = MessagingApiClient(channel_access_token)

@app.route("/callback", methods=['POST'])
def callback():
    signature = request.headers['X-Line-Signature']
    body = request.get_data(as_text=True)

    try:
        handler.handle(body, signature)
    except Exception as e:
        abort(400)

    return 'OK'

@handler.add(MessageEvent, message=TextMessageContent)
def handle_message(event):
    reply_token = event.reply_token
    user_message = event.message.text
    reply = TextMessage(text="تم استلام رسالتك: " + user_message)
    messaging_api.reply_message(ReplyMessageRequest(reply_token, messages=[reply]))

if __name__ == "__main__":
    app.run(port=8000)
