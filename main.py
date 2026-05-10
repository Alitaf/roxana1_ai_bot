import os
import threading
import google.generativeai as genai
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes
from http.server import BaseHTTPRequestHandler, HTTPServer
from supabase import create_client, Client

# ۱. تنظیمات اتصال (دریافت از محیط رندر)
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
GEMINI_KEY = os.environ.get("GEMINI_KEY")

# اتصال به دیتابیس Supabase
try:
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
except Exception as e:
    print(f"Supabase Connection Error: {e}")
    supabase = None

# ۲. تابع خواندن محصولات (جایگزین لیست ثابت قبلی)
def get_live_inventory():
    if not supabase:
        return "Inventory is currently unavailable."
    try:
        res = supabase.table("products").select("name, price_dhs, link, description").eq("is_available", True).execute()
        if not res.data:
            return "No products are currently available."
        
        inventory_text = ""
        for p in res.data:
            inventory_text += f"Product: {p['name']} | Price: {p['price_dhs']} Dhs | URL: {p.get('link', '')} | Features: {p.get('description', '')}\n"
        return inventory_text
    except Exception:
        return "Error fetching product list."
        
# ۳. سرور سلامت برای رندر
class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Roxana Shop Bot is Active")

def run_health_check():
    server = HTTPServer(('0.0.0.0', int(os.environ.get("PORT", 10000))), HealthCheckHandler)
    server.serve_forever()

# ۴. تنظیمات Gemini (دقیقاً مثل کد قبلی شما)
genai.configure(api_key=GEMINI_KEY)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text: return
    user_text = update.message.text
    
    # مدل‌های دقیق برنامه قبلی شما
    target_models = ['models/gemini-3.1-flash-lite', 'models/gemini-2.0-flash', 'models/gemini-1.5-flash']
    
    # گرفتن موجودی زنده
    # در داخل تابع handle_message
    current_inventory = get_live_inventory()
    
    system_instruction = f"""
    You are 'Roxana', a professional and friendly beauty consultant for Roxana Online Shop.
    
    HOW TO RESPOND:
    1. DO NOT use bullet points or a "label: value" format (like Name: Price:). 
    2. Write in a flowy, conversational, and consulting tone (like your previous version). 
    3. Explain the benefits of the product based on the 'Features' provided.
    4. Mention the price naturally within the text.
    5. Place the link only ONCE at the end of the description or naturally in the sentence.
    6. ALWAYS match the user's language (Persian or English).

    PRODUCT DATA:
    {current_inventory}
    """
    for model_name in target_models:
        try:
            model = genai.GenerativeModel(model_name)
            response = model.generate_content(f"{system_instruction}\n\nسوال کاربر: {user_text}")
            
            if response and response.text:
                await update.message.reply_text(response.text)
                return 
        except Exception as e:
            print(f"Model {model_name} failed: {e}")
            continue

    await update.message.reply_text("🔴 مشکلی در پردازش پیش آمد، لطفاً دوباره بپرسید.")

if __name__ == '__main__':
    threading.Thread(target=run_health_check, daemon=True).start()
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))
    print("Roxana is starting with Supabase...")
    app.run_polling(drop_pending_updates=True)
