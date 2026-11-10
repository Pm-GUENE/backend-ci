import datetime as dt

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from .. import services
from ..database import get_db
from ..schemas import RendezVousCreate, RendezVousOut, SuiviOut

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


def _suivi(rdv, now: dt.datetime) -> SuiviOut:
    base = RendezVousOut.model_validate(rdv).model_dump()
    return SuiviOut(**base, annulable=services.est_annulable_par_patient(rdv, now))


@router.get("/rendez-vous/{rdv_id}", response_model=SuiviOut,
            summary="Suivre un rendez-vous (patient)",
            responses={404: {"description": "Numéro ou téléphone incorrect"}})
def suivre_rendez_vous(rdv_id: int,
                       tel: str = Query(..., description="Téléphone utilisé lors de la réservation"),
                       db: Session = Depends(get_db),
                       now: dt.datetime = Depends(services.maintenant)):
    """Le numéro de rendez-vous et le téléphone doivent correspondre, sinon 404
    (sans préciser lequel des deux est faux)."""
    return _suivi(services.trouver_rdv_patient(db, rdv_id, tel), now)


@router.patch("/rendez-vous/{rdv_id}/annulation", response_model=SuiviOut,
              summary="Annuler un rendez-vous (patient)",
              responses={404: {"description": "Numéro ou téléphone incorrect"},
                         409: {"description": "Rendez-vous non annulable (terminé, annulé ou passé)"}})
def annuler_rendez_vous(rdv_id: int,
                        tel: str = Query(..., description="Téléphone utilisé lors de la réservation"),
                        db: Session = Depends(get_db),
                        now: dt.datetime = Depends(services.maintenant)):
    """Passe le rendez-vous à `annule` et libère le créneau."""
    return _suivi(services.annuler_par_patient(db, rdv_id, tel, now), now)
