import datetime as dt

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from .. import services
from ..database import get_db
from ..deps import get_current_dentiste
from ..models import Dentiste, RendezVous
from ..schemas import (ChangementStatut, NotificationRdv, NotificationsOut,
                       RdvDentisteOut, SoinOut)

router = APIRouter(tags=["Dentiste"],
                   responses={401: {"description": "Non connecté"},
                              403: {"description": "Réservé aux dentistes (mot de passe temporaire déjà changé)"}})


def _sortie(rdv: RendezVous, now: dt.datetime) -> RdvDentisteOut:
    return RdvDentisteOut(
        id=rdv.id, patient_nom=rdv.patient_nom, patient_tel=rdv.patient_tel, date=rdv.date,
        heure=rdv.heure, statut=rdv.statut, soin=SoinOut.model_validate(rdv.soin),
        cree_le=rdv.cree_le, actions_possibles=services.actions_possibles(rdv, now))


def _notification(rdv: RendezVous) -> NotificationRdv:
    return NotificationRdv(id=rdv.id, date=rdv.date, heure=rdv.heure,
                           patient_nom=rdv.patient_nom, motif=rdv.soin.libelle)


@router.get("/mes-rendez-vous", response_model=list[RdvDentisteOut],
            summary="Rendez-vous du dentiste connecté")
def mes_rendez_vous(du: dt.date | None = Query(None, description="Date de début (AAAA-MM-JJ)"),
                    au: dt.date | None = Query(None, description="Date de fin (AAAA-MM-JJ)"),
                    soin_id: int | None = Query(None, description="Filtrer par motif"),
                    statut: str | None = Query(None, description="en_attente, confirme, termine ou annule"),
                    dentiste: Dentiste = Depends(get_current_dentiste),
                    db: Session = Depends(get_db),
                    now: dt.datetime = Depends(services.maintenant)):
    """Uniquement les rendez-vous du dentiste connecté, triés par date et heure.
    Sert à la grille du planning (`?du=&au=` sur la semaine) et à la liste filtrée."""
    return [_sortie(r, now) for r in services.lister_rdv_dentiste(db, dentiste.id, du, au, soin_id, statut)]


@router.get("/mes-notifications", response_model=NotificationsOut,
            summary="Notifications du dentiste connecté")
def mes_notifications(dentiste: Dentiste = Depends(get_current_dentiste),
                      db: Session = Depends(get_db),
                      now: dt.datetime = Depends(services.maintenant)):
    """Nouveaux rendez-vous (`en_attente`, tant qu'ils ne sont pas traités ni annulés) et rappels
    des rendez-vous confirmés dans 15 minutes ou moins (le rappel disparaît à l'heure du rendez-vous).
    Le frontend peut appeler cette route toutes les 30 secondes."""
    en_attente, rappels = services.notifications_dentiste(db, dentiste.id, now)
    return NotificationsOut(nombre=len(en_attente) + len(rappels),
                            nouveaux_rendez_vous=[_notification(r) for r in en_attente],
                            rappels=[_notification(r) for r in rappels])


@router.patch("/rendez-vous/{rdv_id}", response_model=RdvDentisteOut,
              summary="Changer le statut d'un rendez-vous (dentiste concerné)",
              responses={404: {"description": "Rendez-vous introuvable"},
                         409: {"description": "Changement de statut interdit"},
                         422: {"description": "Statut invalide"}})
def changer_statut(rdv_id: int, donnees: ChangementStatut,
                   dentiste: Dentiste = Depends(get_current_dentiste),
                   db: Session = Depends(get_db),
                   now: dt.datetime = Depends(services.maintenant)):
    """`en_attente` → `confirme` → `termine`. Annulation possible depuis `en_attente` ou
    `confirme` (le créneau redevient libre). `termine` n'est possible qu'après l'heure du rendez-vous.
    Un rendez-vous `annule` ou `termine` ne change plus."""
    return _sortie(services.changer_statut_dentiste(db, dentiste, rdv_id, donnees.statut, now), now)
