from fastapi import APIRouter, Depends, Response
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from .. import services
from ..database import get_db
from ..deps import require_admin
from ..models import Dentiste
from ..schemas import DentisteAdminOut, DentisteCreate, DentisteCreeOut

router = APIRouter(prefix="/admin", tags=["Administrateur"],
                   dependencies=[Depends(require_admin)],
                   responses={401: {"description": "Non connecté"},
                              403: {"description": "Réservé à l'administrateur"}})


@router.get("/dentistes", response_model=list[DentisteAdminOut],
            summary="Liste des dentistes (administrateur)")
def lister_dentistes(db: Session = Depends(get_db)):
    """Nom, spécialité, identifiant et motifs proposés. Le dentiste le plus récent est en premier."""
    requete = select(Dentiste).options(selectinload(Dentiste.soins)).order_by(Dentiste.id.desc())
    return db.scalars(requete).all()


@router.post("/dentistes", response_model=DentisteCreeOut, status_code=201,
             summary="Créer un dentiste (administrateur)",
             responses={422: {"description": "Nom invalide, aucun motif ou motif inconnu"}})
def creer_dentiste(donnees: DentisteCreate, reponse: Response, db: Session = Depends(get_db)):
    """Le système génère l'identifiant (`prenom.nom`, avec un numéro en cas de doublon) et un
    mot de passe temporaire. **Le mot de passe n'est renvoyé qu'une seule fois** : il n'est
    enregistré que sous forme hachée. Le dentiste devra le changer à sa première connexion."""
    dentiste, mot_de_passe = services.creer_dentiste(
        db, nom=donnees.nom, specialite=donnees.specialite, soin_ids=donnees.soin_ids)
    reponse.headers["Cache-Control"] = "no-store"
    return DentisteCreeOut(id=dentiste.id, nom=dentiste.nom, specialite=dentiste.specialite,
                           identifiant=dentiste.identifiant, soins=dentiste.soins,
                           mot_de_passe_temporaire=mot_de_passe)
