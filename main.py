import os
import threading
import google.generativeai as genai
from flask import Flask
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes
from supabase import create_client, Client

# --- Flask Server ---
app = Flask(__name__)
@app.route('/')
def home(): return "ROXANA ONLINE", 200

def run_flask():
    app.run(host='0.0.0.0', port=10000)

# --- Config ---
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

# اتصال ایمن به دیتابیس
try:
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
except Exception as e:
    print(f"Supabase Connection Error: {e}")
    supabase = None

def get_inventory():
    if not supabase: return "خطا در پیکربندی دیتابیس."
    try:
        res = supabase.table("products").select("*").eq("is_available", True).execute()
        if not res.data: return "موجودی فعلاً ثبت نشده است."
        return "\n".join([f"- {p['name']}: {p['price_dhs']} درهم" for p in res.data])
    except Exception as e:
        print(f"Fetch Error: {e}")
        return "خطا در خواندن لیست محصولات."

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text
    if not user_text: return
    
    status_msg = await update.message.reply_text("⏳ رکسانا در حال بررسی...")
    
    inventory = get_inventory()
    system_instruction = f"You are Roxana, a helpful assistant. Use this inventory: {inventory}. Answer in Persian."
    
    # دقیقاً همان ساختار حلقه که قبلاً جواب گرفته بودی
    target_models = ['gemini-1.5-flash', 'gemini-1.5-pro', 'gemini-pro']
    genai.configure(api_key=GEMINI_API_KEY)
    
    for model_name in target_models:
        try:
            model = genai.GenerativeModel(model_name)
            response = model.generate_content(f"{system_instruction}\n\nسوال کاربر: {user_text}")
            if response and response.text:
                await status_msg.edit_text(response.text)
                return 
        except:
            continue
            
    await status_msg.edit_text("❌ سیستم فعلاً پاسخگو نیست.")

if __name__ == '__main__':
    threading.Thread(target=run_flask, daemon=True).start()
    application = Application.builder().token(TELEGRAM_TOKEN).build()
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    # جلوگیری از تداخل (Conflict)
    application.run_polling(drop_pending_updates=True)
