import os
import threading
import google.generativeai as genai
from flask import Flask
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes
from supabase import create_client, Client

# --- تنظیمات سرور برای زنده نگه داشتن در رندر ---
app = Flask(__name__)
@app.route('/')
def home(): return "ROXANA ONLINE", 200

def run_flask():
    app.run(host='0.0.0.0', port=10000)

# --- دریافت اطلاعات از Environment Variables ---
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

# اتصال به دیتابیس Supabase
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# تابعی که جایگزین دیتای ثابت قبلی شده است
def get_inventory():
    try:
        res = supabase.table("products").select("*").eq("is_available", True).execute()
        if not res.data:
            return "در حال حاضر لیست محصولات خالی است."
        
        inventory_text = "لیست موجودی طلا و محصولات زیبایی:\n"
        for p in res.data:
            inventory_text += f"- {p['name']}: قیمت {p['price_dhs']} درهم\n"
        return inventory_text
    except Exception as e:
        print(f"Error fetching data: {e}")
        return "خطا در دریافت موجودی لحظه‌ای."

# پردازش پیام‌های تلگرام (دقیقاً با همان منطق برنامه قبلی شما)
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text
    if not user_text: return
    
    status_msg = await update.message.reply_text("⏳ رکسانا در حال بررسی...")
    
    # دریافت موجودی زنده از دیتابیس
    inventory = get_inventory()
    
    # دستورالعمل سیستم
    system_instruction = f"You are Roxana, a professional store assistant for jewelry and beauty products. Use this inventory to help customers: {inventory}. Always answer in Persian with a friendly tone."
    
    # لیست مدل‌ها برای تست (همان لیستی که قبلاً استفاده می‌کردی)
    target_models = ['gemini-1.5-flash', 'gemini-1.5-pro', 'gemini-pro']
    genai.configure(api_key=GEMINI_API_KEY)
    
    # اجرای حلقه روی مدل‌ها (دقیقاً مثل کد قبلی خودت)
    for model_name in target_models:
        try:
            model = genai.GenerativeModel(model_name)
            response = model.generate_content(f"{system_instruction}\n\nسوال کاربر: {user_text}")
            
            if response and response.text:
                await status_msg.edit_text(response.text)
                return 
        except Exception as e:
            print(f"Model {model_name} failed: {e}")
            continue
            
    await status_msg.edit_text("❌ متأسفانه در حال حاضر سیستم هوشمند با ترافیک بالایی روبروست. لطفاً دقایقی دیگر پیام دهید.")

# نقطه شروع برنامه
if __name__ == '__main__':
    # اجرای Flask در یک Thread جداگانه
    threading.Thread(target=run_flask, daemon=True).start()
    
    # راه اندازی ربات تلگرام
    application = Application.builder().token(TELEGRAM_TOKEN).build()
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    print("Roxana is running...")
    # پارامتر drop_pending_updates=True برای جلوگیری از خطای Conflict اضافه شد
    application.run_polling(drop_pending_updates=True)
