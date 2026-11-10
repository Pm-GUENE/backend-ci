import datetime as dt

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from .. import services
from ..database import get_db
from ..schemas import RendezVousCreate, RendezVousOut

router = APIRouter(tags=["Patient"])


@router.post("/rendez-vous", response_model=RendezVousOut, status_code=201,
             summary="Réserver un rendez-vous",
             responses={404: {"description": "Dentiste ou motif introuvable"},
                        409: {"description": "Créneau déjà pris"},
                        422: {"description": "Données ou créneau invalides"}})
def creer_rendez_vous(donnees: RendezVousCreate, db: Session = Depends(get_db),
                      now: dt.datetime = Depends(services.maintenant)):
    """Crée un rendez-vous au statut `en_attente`. Le champ `id` de la réponse est le
    **numéro de rendez-vous** que le patient utilisera, avec son téléphone, pour le suivre."""
    return services.creer_rendez_vous(
        db, patient_nom=donnees.patient_nom, patient_tel=donnees.patient_tel,
        dentiste_id=donnees.dentiste_id, soin_id=donnees.soin_id,
        jour=donnees.date, heure=donnees.heure, now=now)
