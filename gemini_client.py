from google import genai

from config import GEMINI_API_KEY

# SDK baru (google-genai) nggak pakai genai.configure() global lagi.
# Bikin satu client di sini, lalu di-import oleh modul lain.
client = genai.Client(api_key=GEMINI_API_KEY)