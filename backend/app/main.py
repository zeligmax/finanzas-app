from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import auth, expenses, invoices, taxes
from app.core.config import settings

app = FastAPI(title=settings.PROJECT_NAME)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # frontend Vite en local
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(invoices.router)
app.include_router(expenses.router)
app.include_router(taxes.router)


@app.get("/api/health")
def health():
    return {"status": "ok"}
