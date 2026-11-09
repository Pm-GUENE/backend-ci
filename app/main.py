from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from .config import settings
from .database import engine
from .routers import public
from .seed import init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(title="DentaRDV API",
              description="Prise de rendez-vous pour une clinique dentaire au Sénégal",
              version="1.0.0", lifespan=lifespan)

app.add_middleware(CORSMiddleware, allow_origins=settings.CORS_ORIGINS,
                   allow_methods=["*"], allow_headers=["*"])

app.include_router(public.router)


@app.get("/health", tags=["Système"], summary="État du service")
def health():
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))
    return {"status": "ok"}
