# LINE Bot (Flask + line-bot-sdk v3) — تنبيه انضمام عضو جديد

## المتطلبات
- قناة Messaging API من LINE Developers
- المتغيرات البيئية:
  - `LINE_CHANNEL_SECRET`
  - `LINE_CHANNEL_ACCESS_TOKEN`

## تشغيل محليًا
1) تثبيت الاعتمادات:
```
pip install -r requirements.txt
```
2) ضبط المتغيرات البيئية (Windows CMD مثالًا):
```
setx LINE_CHANNEL_SECRET "YOUR_SECRET"
setx LINE_CHANNEL_ACCESS_TOKEN "YOUR_ACCESS_TOKEN"
```
> بعد setx افتح نافذة CMD جديدة.

3) تشغيل التطبيق:
```
python main.py
```
4) للتجربة عبر الإنترنت مؤقتًا:
```
ngrok http 8000
```
ثم ضع رابط ngrok منتهيًا بـ `/callback` في Webhook URL واضغط Verify.

## النشر على Render
- ارفع المشروع إلى GitHub.
- أنشئ Web Service:
  - Build: `pip install -r requirements.txt`
  - Start: `python main.py` (أو استخدم `render.yaml`)
- أضف المتغيرات البيئية في Render.
- استخدم رابط الخدمة مع `/callback` في Webhook URL.

## ما الذي يفعله البوت؟
- يرد على الرسائل النصية بـ: "أنت قلت: ..."
- يرحّب تلقائيًا عند انضمام عضو جديد للمجموعة (MemberJoinedEvent).
