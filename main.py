import os
import threading
import requests
from flask import Flask
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes
from supabase import create_client, Client

# --- تنظیمات سرور برای Render ---
app = Flask(__name__)
@app.route('/')
def home(): return "OK", 200

def run_flask():
    app.run(host='0.0.0.0', port=10000)

# --- متغیرها ---
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# --- توابع ---
def get_inventory():
    try:
        res = supabase.table("products").select("*").eq("is_available", True).execute()
        if not res.data: return "موجودی خالی است."
        return "\n".join([f"- {p['name']}: {p['price_dhs']} AED" for p in res.data])
    except: return "خطا در دیتابیس"

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text
    # حذف پیام‌های میانی برای جلوگیری از شلوغی و خطا
    try:
        inventory = get_inventory()
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}"
        payload = {
            "contents": [{"parts": [{"text": f"You are Roxana, a store assistant. Inventory: {inventory}. Answer in Persian: {user_text}"}]}]
        }
        response = requests.post(url, json=payload, timeout=10)
        answer = response.json()['candidates'][0]['content']['parts'][0]['text']
        await update.message.reply_text(answer)
    except Exception as e:
        print(f"Error: {e}")
        await update.message.reply_text("در حال حاضر مشکلی پیش آمده، لطفا دوباره تلاش کنید.")

# --- اجرا ---
if __name__ == '__main__':
    threading.Thread(target=run_flask, daemon=True).start()
    print("Bot is starting...")
    application = Application.builder().token(TELEGRAM_TOKEN).build()
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.run_polling()
