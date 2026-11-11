from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from .config import settings
from .database import engine
from .routers import admin, auth, dentiste, public, rendez_vous
from .services import ErreurMetier
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
app.include_router(auth.router)
app.include_router(admin.router)
app.include_router(dentiste.router)
app.include_router(rendez_vous.router)


@app.exception_handler(ErreurMetier)
def erreur_metier(request: Request, exc: ErreurMetier):
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.message})


@app.get("/health", tags=["Système"], summary="État du service")
def health():
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))
    return {"status": "ok"}
