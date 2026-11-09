import datetime as dt

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import or_, select
from sqlalchemy.orm import Session, selectinload

from .. import services
from ..database import get_db
from ..models import Dentiste, Soin
from ..schemas import CreneauOut, DentisteOut, SoinOut

router = APIRouter(tags=["Public"])


def _dentiste_ou_404(db: Session, dentiste_id: int) -> Dentiste:
    dentiste = db.get(Dentiste, dentiste_id)
    if not dentiste:
        raise HTTPException(404, "Dentiste introuvable")
    return dentiste


@router.get("/dentistes", response_model=list[DentisteOut],
            summary="Liste des dentistes avec leurs motifs")
def lister_dentistes(
        q: str | None = Query(None, description="Recherche par nom de dentiste ou de motif"),
        soin_id: int | None = Query(None, description="Ne garder que les dentistes proposant ce motif"),
        db: Session = Depends(get_db)):
    requete = select(Dentiste).options(selectinload(Dentiste.soins)).order_by(Dentiste.nom)
    if soin_id is not None:
        requete = requete.where(Dentiste.soins.any(Soin.id == soin_id))
    if q:
        motif = f"%{q.strip()}%"
        requete = requete.where(or_(Dentiste.nom.ilike(motif),
                                    Dentiste.soins.any(Soin.libelle.ilike(motif))))
    return db.scalars(requete).all()


@router.get("/soins", response_model=list[SoinOut],
            summary="Liste des motifs de consultation")
def lister_soins(
        dentiste_id: int | None = Query(None, description="Ne garder que les motifs de ce dentiste"),
        db: Session = Depends(get_db)):
    requete = select(Soin).order_by(Soin.id)
    if dentiste_id is not None:
        requete = requete.where(Soin.id.in_(
            select(Soin.id).join(Dentiste.soins).where(Dentiste.id == dentiste_id)))
    return db.scalars(requete).all()


@router.get("/dentistes/{dentiste_id}/soins", response_model=list[SoinOut],
            summary="Motifs de consultation proposés par un dentiste")
def soins_du_dentiste(dentiste_id: int, db: Session = Depends(get_db)):
    return _dentiste_ou_404(db, dentiste_id).soins


@router.get("/creneaux", response_model=list[CreneauOut],
            summary="Créneaux libres d'un dentiste sur une période")
def lister_creneaux(
        dentiste_id: int = Query(..., description="Identifiant du dentiste"),
        du: dt.date = Query(..., description="Premier jour (AAAA-MM-JJ)"),
        au: dt.date = Query(..., description="Dernier jour (AAAA-MM-JJ), égal à `du` pour un seul jour"),
        db: Session = Depends(get_db),
        now: dt.datetime = Depends(services.maintenant)):
    if au < du:
        raise HTTPException(422, "`au` doit être postérieur ou égal à `du`")
    if (au - du).days >= services.MAX_JOURS:
        raise HTTPException(422, f"Période limitée à {services.MAX_JOURS} jours")
    _dentiste_ou_404(db, dentiste_id)
    return [CreneauOut(date=d, heure=h)
            for d, h in services.creneaux_libres(db, dentiste_id, du, au, now)]
