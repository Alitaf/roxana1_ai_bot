import os
import threading
import google.generativeai as genai
from flask import Flask
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes
from supabase import create_client, Client

app = Flask(__name__)
@app.route('/')
def home(): return "ROXANA ONLINE", 200

def run_flask():
    app.run(host='0.0.0.0', port=10000)

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

try:
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
except:
    supabase = None

def get_inventory():
    if not supabase: return "انبار فعلا در دسترس نیست."
    try:
        res = supabase.table("products").select("*").eq("is_available", True).execute()
        return "\n".join([f"- {p['name']}: {p['price_dhs']} درهم" for p in res.data]) if res.data else "موجودی خالی است."
    except: return "خطا در دریافت لیست محصولات."

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text
    if not user_text: return
    status_msg = await update.message.reply_text("⏳ رکسانا در حال فکر کردن...")

    inventory = get_inventory()
    # ساده‌سازی دستورالعمل برای کاهش حجم توکن
    system_instruction = f"Role: Roxana (Assistant). Inventory: {inventory}. Response: Persian, Friendly."
    
    genai.configure(api_key=GEMINI_API_KEY)
    
    # تست مدل‌ها به ترتیب پایداری
    for model_name in ['gemini-1.5-flash', 'gemini-pro']:
        try:
            model = genai.GenerativeModel(model_name)
            response = model.generate_content(f"{system_instruction}\nCustomer: {user_text}")
            if response and response.text:
                await status_msg.edit_text(response.text)
                return
        except Exception as e:
            print(f"Error with {model_name}: {e}")
            continue
            
    await status_msg.edit_text("❌ گوگل فعلاً اجازه پاسخگویی نمی‌دهد. ۱۰ دقیقه دیگر امتحان کنید.")

if __name__ == '__main__':
    threading.Thread(target=run_flask, daemon=True).start()
    application = Application.builder().token(TELEGRAM_TOKEN).build()
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.run_polling(drop_pending_updates=True)
