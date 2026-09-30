import os

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

load_dotenv()

from api import router as api_router  # noqa: E402
from database import init_db  # noqa: E402

app = FastAPI(title="HumanTwin AI", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ORIGINS", "*").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)


@app.on_event("startup")
def _startup():
    init_db()


@app.get("/")
def root():
    return {"name": "HumanTwin AI", "docs": "/docs", "health": "/api/health"}
