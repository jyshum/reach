"""FastAPI application."""

from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent / ".env")

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.routers import users, companies, outreach, email

app = FastAPI(title="REACH API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(users.router)
app.include_router(companies.router)
app.include_router(outreach.router)
app.include_router(email.router)


@app.get("/health")
def health():
    return {"status": "ok"}
