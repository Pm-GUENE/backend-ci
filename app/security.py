import datetime as dt

import bcrypt
import jwt

from .config import settings

ALGORITHM = "HS256"


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(password: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode(), hashed.encode())
    except ValueError:
        return False


# Faux hachage : permet de dépenser le même temps de calcul quand l'identifiant n'existe pas
FAUX_HASH = hash_password("mot-de-passe-factice")


def creer_jeton(*, identifiant: str, role: str, user_id: int) -> str:
    expiration = dt.datetime.now(dt.timezone.utc) + dt.timedelta(minutes=settings.JWT_EXPIRE_MINUTES)
    return jwt.encode({"sub": identifiant, "role": role, "uid": user_id, "exp": expiration},
                      settings.JWT_SECRET, algorithm=ALGORITHM)


def lire_jeton(token: str) -> dict | None:
    """Renvoie le contenu du jeton, ou None s'il est invalide ou expiré."""
    try:
        return jwt.decode(token, settings.JWT_SECRET, algorithms=[ALGORITHM])
    except jwt.PyJWTError:
        return None
