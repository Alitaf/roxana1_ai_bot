import os
from supabase import create_client, Client

# جایگزین بخش قبلی کنید
supabase_url = os.environ.get("SUPABASE_URL")
supabase_key = os.environ.get("SUPABASE_KEY")

print(f"DEBUG: URL found: {supabase_url is not None}")
print(f"DEBUG: KEY found: {supabase_key is not None}")

if not supabase_url or not supabase_key:
    print("ERROR: Supabase variables are missing in Environment!")
    # این خط باعث می‌شود برنامه با پیام شفاف‌تری متوقف شود
    raise ValueError("Missing SUPABASE_URL or SUPABASE_KEY in Render Environment Variables")

supabase: Client = create_client(supabase_url, supabase_key)
