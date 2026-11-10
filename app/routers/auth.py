from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import ROLE_ADMIN, ROLE_DENTISTE, utilisateur_courant
from ..models import Administrateur, Dentiste
from ..schemas import ConnexionIn, JetonOut, MessageOut, MotDePasseIn
from ..security import FAUX_HASH, creer_jeton, hash_password, verify_password

router = APIRouter(tags=["Authentification"])

MESSAGE_CONNEXION = "Identifiant ou mot de passe incorrect"


@router.post("/connexion", response_model=JetonOut, summary="Connexion (dentiste ou administrateur)",
             responses={401: {"description": "Identifiant ou mot de passe incorrect"}})
def connexion(donnees: ConnexionIn, db: Session = Depends(get_db)):
    """Page de connexion commune. Renvoie un jeton à envoyer ensuite dans l'en-tête
    `Authorization: Bearer <jeton>`. Si `doit_changer_mdp` est vrai (première connexion
    d'un dentiste), le dentiste doit d'abord appeler `PATCH /mot-de-passe`."""
    identifiant = donnees.identifiant.strip().lower()
    role, compte = ROLE_DENTISTE, db.scalar(select(Dentiste).where(Dentiste.identifiant == identifiant))
    if compte is None:
        role, compte = ROLE_ADMIN, db.scalar(
            select(Administrateur).where(Administrateur.identifiant == identifiant))

    # Même temps de calcul que l'identifiant existe ou non, et même message d'erreur
    hash_a_verifier = compte.mot_de_passe_hash if compte else FAUX_HASH
    if not verify_password(donnees.mot_de_passe, hash_a_verifier) or compte is None:
        raise HTTPException(401, MESSAGE_CONNEXION)

    return JetonOut(
        access_token=creer_jeton(identifiant=compte.identifiant, role=role, user_id=compte.id),
        role=role,
        nom=compte.nom if role == ROLE_DENTISTE else "Administrateur",
        doit_changer_mdp=compte.doit_changer_mdp if role == ROLE_DENTISTE else False)


@router.patch("/mot-de-passe", response_model=MessageOut, summary="Changer son mot de passe",
              responses={401: {"description": "Non connecté"},
                         422: {"description": "Mot de passe trop court, identique à l'actuel ou confirmation différente"}})
def changer_mot_de_passe(donnees: MotDePasseIn, utilisateur=Depends(utilisateur_courant),
                         db: Session = Depends(get_db)):
    """Obligatoire à la première connexion d'un dentiste (mot de passe temporaire).
    Le nouveau mot de passe doit faire au moins 8 caractères et différer de l'actuel."""
    role, compte = utilisateur
    if donnees.confirmation is not None and donnees.confirmation != donnees.nouveau_mot_de_passe:
        raise HTTPException(422, "Les deux mots de passe ne sont pas identiques")
    if verify_password(donnees.nouveau_mot_de_passe, compte.mot_de_passe_hash):
        raise HTTPException(422, "Le nouveau mot de passe doit être différent du mot de passe actuel")
    compte.mot_de_passe_hash = hash_password(donnees.nouveau_mot_de_passe)
    if role == ROLE_DENTISTE:
        compte.doit_changer_mdp = False
    db.commit()
    return MessageOut(message="Mot de passe modifié", doit_changer_mdp=False)
