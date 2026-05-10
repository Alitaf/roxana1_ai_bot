import os
import threading
import google.generativeai as genai
from flask import Flask
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from supabase import create_client, Client

# --- تنظیمات اولیه ---
app = Flask('')

@app.route('/')
def home():
    return "Roxana Bot is Live!"

def run_flask():
    app.run(host='0.0.0.0', port=10000)

# --- اتصال به سرویس‌ها ---
# دریافت متغیرهای محیطی از Render
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

# بررسی وجود متغیرها برای جلوگیری از کرش کردن
if not all([SUPABASE_URL, SUPABASE_KEY, TELEGRAM_TOKEN, GEMINI_API_KEY]):
    print("ERROR: One or more Environment Variables are missing!")

# اتصال به سوپابیس
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# تنظیمات جمنای
genai.configure(api_key=GEMINI_API_KEY)
system_instruction = """
You are Roxana, a professional and friendly assistant for 'Roxana Store'.
Your task is to help customers based on the available inventory provided to you.
- Always be polite and speak in Persian (Farsi).
- Use the provided inventory to answer questions about price, availability, and details.
- If a product is not in the inventory, kindly say we don't have it yet.
"""

# --- توابع کمکی ---
def get_current_inventory():
    try:
        # دریافت محصولاتی که موجود هستند
        response = supabase.table("products").select("*").eq("is_available", True).execute()
        items = response.data
        print(f"DEBUG: Found {len(items)} products in database.")
        
        if not items:
            return "در حال حاضر محصولی در لیست موجودی یافت نشد."
        
        inventory_text = "لیست محصولات موجود در فروشگاه رکسانا:\n"
        for p in items:
            inventory_text += f"- {p['name']}: {p['description']} | قیمت: {p['price_dhs']} درهم | لینک: {p['link']}\n"
        return inventory_text
    except Exception as e:
        print(f"Database Error: {e}")
        return "خطا در دریافت اطلاعات از دیتابیس."

# --- هندلرهای تلگرام ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("سلام! من رکسانا هستم، دستیار هوشمند فروشگاه شما. چطور می‌تونم کمکتون کنم؟")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text
    if not user_text: return

    # ارسال پیام وضعیت اولیه
    status_msg = await update.message.reply_text("⏳ در حال بررسی موجودی و پاسخگویی...")

    try:
        # ۱. دریافت موجودی لحظه‌ای
        inventory = get_current_inventory()
        
        # ۲. تلاش برای تولید پاسخ با مدل Flash (پایدارترین مدل برای Render)
        model = genai.GenerativeModel("gemini-1.5-flash")
        full_prompt = f"{system_instruction}\n\nInventory:\n{inventory}\n\nCustomer Question: {user_text}"
        
        response = model.generate_content(full_prompt)
        
        if response and response.text:
            # حذف پیام "در حال بررسی" و ارسال پاسخ اصلی
            await status_msg.delete()
            await update.message.reply_text(response.text)
        else:
            await status_msg.edit_text("❌ متأسفانه پاسخی دریافت نشد. لطفا دوباره سوال کنید.")
            
    except Exception as e:
        print(f"General Error: {e}")
        await status_msg.edit_text(f"❌ پوزش می‌طلبم، مشکلی پیش آمده: {str(e)}")

# --- اجرای برنامه ---
if __name__ == '__main__':
    # اجرای Flask در یک ترد جداگانه برای Health Check رندر
    threading.Thread(target=run_flask).start()
    
    # اجرای ربات تلگرام
    print("Bot is starting...")
    application = Application.builder().token(TELEGRAM_TOKEN).build()
    
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    application.run_polling()
