import os
import threading
import requests
from flask import Flask
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from supabase import create_client, Client

# --- تنظیمات سرور برای Render ---
app = Flask(__name__)

@app.route('/')
def home():
    return "Roxana is Online", 200

def run_flask():
    app.run(host='0.0.0.0', port=10000)

# --- دریافت تنظیمات از Environment Variables ---
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

# اتصال به دیتابیس
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# --- توابع اصلی ---
def get_inventory():
    try:
        response = supabase.table("products").select("*").eq("is_available", True).execute()
        items = response.data
        if not items: return "محصول موجود نداریم."
        inventory = "لیست موجودی رکسانا:\n"
        for p in items:
            inventory += f"- {p['name']}: {p['price_dhs']} درهم\n"
        return inventory
    except:
        return "خطا در دسترسی به دیتابیس."

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text
    status_msg = await update.message.reply_text("⏳ در حال بررسی...")

    try:
        inventory = get_inventory()
        
        # فراخوانی مستقیم API جمنای (بدون پکیج اضافه)
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}"
        payload = {
            "contents": [{
                "parts": [{"text": f"You are Roxana assistant. Use this inventory: {inventory}. Answer in Persian: {user_text}"}]
            }]
        }
        
        response = requests.post(url, json=payload)
        result = response.json()
        
        answer = result['candidates'][0]['content']['parts'][0]['text']
        await status_msg.edit_text(answer)
        
    except Exception as e:
        await status_msg.edit_text(f"❌ خطای سیستم: {str(e)}")

# --- اجرای برنامه ---
if __name__ == '__main__':
    # اجرای Flask در پس‌زمینه
    threading.Thread(target=run_flask, daemon=True).start()
    
    # اجرای ربات
    print("Bot is starting...")
    application = Application.builder().token(TELEGRAM_TOKEN).build()
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.run_polling()
