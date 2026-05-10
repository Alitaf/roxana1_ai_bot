import os
import threading
import google.generativeai as genai
from flask import Flask
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from supabase import create_client, Client

# --- تنظیمات Flask برای زنده نگه داشتن سرور در Render ---
app = Flask(__name__)

@app.route('/')
def health_check():
    return "OK", 200

def run_flask():
    app.run(host='0.0.0.0', port=10000)

# --- دریافت متغیرها ---
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

# --- اتصال به سرویس‌ها ---
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
genai.configure(api_key=GEMINI_API_KEY)

# --- توابع ربات ---
def get_inventory():
    try:
        response = supabase.table("products").select("*").eq("is_available", True).execute()
        items = response.data
        if not items: return "محصولی موجود نیست."
        
        text = "موجودی فروشگاه:\n"
        for p in items:
            text += f"- {p['name']}: {p['price_dhs']} درهم\n"
        return text
    except:
        return "خطا در استعلام دیتابیس."

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text
    # ارسال پیام موقت
    temp_msg = await update.message.reply_text("⏳ در حال بررسی...")
    
    try:
        inventory = get_inventory()
        model = genai.GenerativeModel("gemini-1.5-flash")
        
        prompt = f"You are Roxana Store assistant. Inventory:\n{inventory}\nUser: {user_text}"
        response = model.generate_content(prompt)
        
        await temp_msg.edit_text(response.text)
    except Exception as e:
        await temp_msg.edit_text(f"خطای فنی: {str(e)}")

# --- اجرای اصلی ---
if __name__ == '__main__':
    # ۱. اجرای Flask در پس‌زمینه
    threading.Thread(target=run_flask, daemon=True).start()
    
    # ۲. اجرای ربات تلگرام
    print("Starting Telegram Bot...")
    application = Application.builder().token(TELEGRAM_TOKEN).build()
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.run_polling()
