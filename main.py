import os, threading, google.generativeai as genai
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes
from http.server import BaseHTTPRequestHandler, HTTPServer
from supabase import create_client, Client

# ۱. تنظیمات اولیه و اتصال به سرویس‌ها
genai.configure(api_key=os.getenv("GEMINI_KEY"))
supabase_url = os.getenv("SUPABASE_URL")
supabase_key = os.getenv("SUPABASE_KEY")
supabase: Client = create_client(supabase_url, supabase_key)

# ۲. سرور سلامت برای رندر
class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200); self.end_headers()
        self.wfile.write(b"Roxana Bot is Live")

def run_health_check():
    server = HTTPServer(('0.0.0.0', int(os.environ.get("PORT", 10000))), HealthCheckHandler)
    server.serve_forever()

# ۳. دریافت هوشمند لیست محصولات از دیتابیس
def get_current_inventory():
    try:
        response = supabase.table("products").select("*").eq("is_available", True).execute()
        items = response.data
        print(f"DEBUG: Found {len(items)} products in database.") # این خط مهم است
        
        if not items: 
            return "No products available in database."
        
        inventory_text = "Roxana Store Product List:\n"
        for p in items:
            inventory_text += f"- {p['name']}: {p['description']} | Price: {p['price_dhs']} AED | Link: {p['link']}\n"
        return inventory_text
    except Exception as e:
        print(f"Database Error: {e}")
        return "Error fetching inventory."

# ۴. پردازش پیام‌ها
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text: return

    user_text = update.message.text
    inventory = get_current_inventory()
    
    system_instruction = f"""
    You are 'Roxana', the exclusive beauty consultant for Roxana Online Shop in Dubai.
    
    STRICT RULES:
    1. USE ONLY this product list: {inventory}
    2. Respond in the SAME language as the user (Persian, English, or Arabic).
    3. If a product is not in the list, politely say we don't have it yet.
    4. Provide the product link for every recommendation.
    5. No general advice outside our products.
    """

    target_models = ['models/gemini-1.5-flash', 'models/gemini-2.0-flash']
    
    for model_name in target_models:
        try:
            model = genai.GenerativeModel(model_name)
            response = model.generate_content(f"{system_instruction}\n\nUser Question: {user_text}")
            if response and response.text:
                await update.message.reply_text(response.text)
                return 
        except Exception: continue

async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Please send your question in text format so I can assist you better.\nلطفاً سوال خود را به صورت متنی بفرستید.")

# ۵. اجرای اصلی
if __name__ == '__main__':
    threading.Thread(target=run_health_check, daemon=True).start()
    app = Application.builder().token(os.getenv("TELEGRAM_TOKEN")).build()
    
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))
    app.add_handler(MessageHandler(filters.VOICE, handle_voice))
    
    print("Bot is running...")
    app.run_polling(drop_pending_updates=True)
