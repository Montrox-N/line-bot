# helper.py
def get_auto_reply(message: str):
    if not message:
        return None
    msg = message.strip().lower()

    if msg in ("صباح الخير", "صباح الخير 🌅"):
        return "صباح النور ☀️"
    if msg in ("مساء الخير", "مساء الخير 🌙"):
        return "مساء النور 🌌"
    if msg in ("السلام عليكم", "السلام عليكم ورحمة الله"):
        return "وعليكم السلام ورحمة الله وبركاته 🤍"
    if msg == ".":
        return "نقطة وصلت ✔️"
    return None
