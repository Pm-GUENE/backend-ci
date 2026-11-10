"""Dépendances d'authentification : qui est connecté, et a-t-il le droit ?"""
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from .database import get_db
from .models import Administrateur, Dentiste
from .security import lire_jeton

schema_bearer = HTTPBearer(auto_error=False, description="Jeton obtenu avec POST /connexion")

ROLE_DENTISTE = "dentiste"
ROLE_ADMIN = "admin"


def utilisateur_courant(creds: HTTPAuthorizationCredentials | None = Depends(schema_bearer),
                        db: Session = Depends(get_db)) -> tuple[str, Dentiste | Administrateur]:
    """Renvoie (role, compte). 401 si le jeton est absent, invalide ou expiré."""
    non_authentifie = HTTPException(401, "Authentification requise",
                                    headers={"WWW-Authenticate": "Bearer"})
    if creds is None:
        raise non_authentifie
    contenu = lire_jeton(creds.credentials)
    if not contenu:
        raise non_authentifie
    role = contenu.get("role")
    modele = {ROLE_DENTISTE: Dentiste, ROLE_ADMIN: Administrateur}.get(role)
    compte = db.get(modele, contenu.get("uid")) if modele else None
    if compte is None or compte.identifiant != contenu.get("sub"):
        raise non_authentifie
    return role, compte


def get_current_dentiste(utilisateur=Depends(utilisateur_courant)) -> Dentiste:
    """Réservé aux dentistes ayant déjà changé leur mot de passe temporaire."""
    role, compte = utilisateur
    if role != ROLE_DENTISTE:
        raise HTTPException(403, "Accès réservé aux dentistes")
    if compte.doit_changer_mdp:
        raise HTTPException(403, "Vous devez d'abord changer votre mot de passe")
    return compte


def require_admin(utilisateur=Depends(utilisateur_courant)) -> Administrateur:
    role, compte = utilisateur
    if role != ROLE_ADMIN:
        raise HTTPException(403, "Accès réservé à l'administrateur")
    return compte
