from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routers.chat import router as chat_router

app = FastAPI(title="Aceh News RAG API")

# Sesuaikan origins ini nanti dengan domain frontend Next.js kamu pas deploy.
# "*" hanya buat development lokal.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://tanyaaceh.vercel.app", "http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chat_router)


@app.get("/")
def health_check():
    return {"status": "ok", "service": "Aceh News RAG API"}