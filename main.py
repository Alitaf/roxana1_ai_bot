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
        res = supabase.table("products").select("*").eq("is_available", True).execute()
        if not res.data:
            return "No products are currently available in the catalog."
        
        inventory_text = "List of available products in Roxana Store:\n"
        for p in res.data:
            inventory_text += f"- {p['name']} - Price: {p['price_dhs']} Dhs\n"
        return inventory_text
    except Exception as e:
        print(f"Fetch Error: {e}")
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
    current_inventory = get_live_inventory()
    
    # دستورالعمل هوشمند شما (بدون تغییر در ساختار موفق)
    system_instruction = f"""
    You are 'Roxana', the EXCLUSIVE beauty consultant for Roxana Online Shop.
    
    STRICT RULES:
    1. ONLY use the product information provided in the list below. Do not invent products.
    2. LANGUAGE MATCHING: Always respond in the SAME language that the user uses.
    3. If a product is NOT in the list, politely inform the user.
    4. Keep the tone professional and friendly.

    PRODUCT LIST:
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
