"""Règles métier. Fonctions simples qui reçoivent `now` en paramètre : faciles à tester."""
import datetime as dt

from sqlalchemy import select
from sqlalchemy.orm import Session

from .models import STATUTS_ACTIFS, RendezVous

HEURE_DEBUT = dt.time(8, 0)
HEURE_FIN = dt.time(17, 0)          # fin de journée
DUREE_MIN = 30                      # durée d'un créneau
MAX_JOURS = 31                      # période maximale demandée à /creneaux


def maintenant() -> dt.datetime:
    """Heure actuelle (le Sénégal est en UTC, comme les conteneurs Docker)."""
    return dt.datetime.now()


def heures_de_la_journee() -> list[dt.time]:
    """08:00, 08:30, ... 16:30 (le dernier créneau finit à 17:00)."""
    heures = []
    courant = dt.datetime.combine(dt.date.today(), HEURE_DEBUT)
    fin = dt.datetime.combine(dt.date.today(), HEURE_FIN)
    while courant < fin:
        heures.append(courant.time())
        courant += dt.timedelta(minutes=DUREE_MIN)
    return heures


def est_jour_ouvre(jour: dt.date) -> bool:
    return jour.weekday() < 5  # 0 = lundi ... 4 = vendredi


def creneau_valide(jour: dt.date, heure: dt.time, now: dt.datetime) -> bool:
    """Vrai si : jour ouvré, heure dans la grille, et pas dans le passé."""
    if not est_jour_ouvre(jour):
        return False
    if heure not in heures_de_la_journee():
        return False
    return dt.datetime.combine(jour, heure) > now


def creneaux_libres(db: Session, dentiste_id: int, du: dt.date, au: dt.date,
                    now: dt.datetime) -> list[tuple[dt.date, dt.time]]:
    """Créneaux valides du dentiste entre `du` et `au` non occupés par un RDV actif."""
    pris = {(r.date, r.heure) for r in db.scalars(
        select(RendezVous).where(RendezVous.dentiste_id == dentiste_id,
                                 RendezVous.date >= du, RendezVous.date <= au,
                                 RendezVous.statut.in_(STATUTS_ACTIFS)))}
    libres = []
    jour = du
    while jour <= au:
        for h in heures_de_la_journee():
            if creneau_valide(jour, h, now) and (jour, h) not in pris:
                libres.append((jour, h))
        jour += dt.timedelta(days=1)
    return libres
