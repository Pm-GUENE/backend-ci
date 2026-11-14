import datetime as dt

import jwt

from app.config import settings
from app.security import (
    ALGORITHM,
    creer_jeton,
    hash_password,
    lire_jeton,
    verify_password,
)


def test_hash_password_ne_stocke_pas_le_mot_de_passe_en_clair():
    mot_de_passe = "Test-securite-2026"

    hashed = hash_password(mot_de_passe)

    assert hashed != mot_de_passe
    assert hashed.startswith("$2")


def test_hash_password_produit_des_hash_differents():
    mot_de_passe = "Test-securite-2026"

    hash_1 = hash_password(mot_de_passe)
    hash_2 = hash_password(mot_de_passe)

    assert hash_1 != hash_2
    assert verify_password(mot_de_passe, hash_1)
    assert verify_password(mot_de_passe, hash_2)


def test_verify_password_accepte_un_mot_de_passe_correct():
    hashed = hash_password("MotDePasse-123")

    assert verify_password("MotDePasse-123", hashed) is True


def test_verify_password_refuse_un_mot_de_passe_incorrect():
    hashed = hash_password("MotDePasse-123")

    assert verify_password("MauvaisMotDePasse", hashed) is False


def test_verify_password_refuse_un_hash_invalide():
    assert verify_password("MotDePasse-123", "hash-invalide") is False


def test_creer_jeton_et_lire_jeton():
    token = creer_jeton(
        identifiant="test.dentiste",
        role="dentiste",
        user_id=123,
    )

    contenu = lire_jeton(token)

    assert contenu is not None
    assert contenu["sub"] == "test.dentiste"
    assert contenu["role"] == "dentiste"
    assert contenu["uid"] == 123


def test_lire_jeton_refuse_un_token_invalide():
    assert lire_jeton("ceci-n-est-pas-un-token") is None


def test_lire_jeton_refuse_un_token_expire():
    expiration = dt.datetime.now(dt.timezone.utc) - dt.timedelta(minutes=5)

    token = jwt.encode(
        {
            "sub": "test.dentiste",
            "role": "dentiste",
            "uid": 123,
            "exp": expiration,
        },
        settings.JWT_SECRET,
        algorithm=ALGORITHM,
    )

    assert lire_jeton(token) is None
