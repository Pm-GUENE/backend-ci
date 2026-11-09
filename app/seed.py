"""Initialisation idempotente : tables, soins, administrateur, dentistes de démo."""
import logging
import time

from sqlalchemy import select, text
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from .config import settings
from .database import Base, engine
from .models import Administrateur, Dentiste, Soin
from .security import hash_password

log = logging.getLogger("seed")

SOINS = ["détartrage", "soin de carie", "extraction", "appareil dentaire",
         "contrôle d'appareil", "consultation de contrôle"]

DENTISTES_DEMO = [
    ("Moustapha Diaw", "Chirurgien-dentiste", "moustapha.diaw",
     ["détartrage", "soin de carie", "extraction"]),
    ("Awa Ndiaye", "Orthodontiste", "awa.ndiaye",
     ["appareil dentaire", "contrôle d'appareil", "consultation de contrôle"]),
    ("Cheikh Fall", "Dentiste généraliste", "cheikh.fall",
     ["consultation de contrôle", "détartrage", "soin de carie"]),
]


def seed(db: Session) -> None:
    existants = {s.libelle: s for s in db.scalars(select(Soin))}
    for libelle in SOINS:
        if libelle not in existants:
            existants[libelle] = Soin(libelle=libelle)
            db.add(existants[libelle])

    if not db.scalar(select(Administrateur).where(
            Administrateur.identifiant == settings.ADMIN_IDENTIFIANT)):
        db.add(Administrateur(identifiant=settings.ADMIN_IDENTIFIANT,
                              mot_de_passe_hash=hash_password(settings.ADMIN_PASSWORD)))

    for nom, spec, ident, motifs in DENTISTES_DEMO:
        if not db.scalar(select(Dentiste).where(Dentiste.identifiant == ident)):
            db.add(Dentiste(nom=nom, specialite=spec, identifiant=ident,
                            mot_de_passe_hash=hash_password(settings.DEMO_PASSWORD),
                            doit_changer_mdp=False,  # comptes de démo
                            soins=[existants[m] for m in motifs]))
    db.flush()


def init_db(retries: int = 30, delay: float = 2.0) -> None:
    """Attend la base, crée les tables et le seed. Sûr avec 2 instances (verrou PostgreSQL)."""
    for tentative in range(1, retries + 1):
        try:
            with engine.begin() as conn:
                if engine.dialect.name == "postgresql":
                    conn.execute(text("SELECT pg_advisory_xact_lock(424242)"))
                Base.metadata.create_all(conn)
                with Session(bind=conn) as db:
                    seed(db)
            log.info("Base initialisée")
            return
        except OperationalError:
            log.warning("Base indisponible (%s/%s)", tentative, retries)
            time.sleep(delay)
    raise RuntimeError("Impossible de se connecter à la base de données")
