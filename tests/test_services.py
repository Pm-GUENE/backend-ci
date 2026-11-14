import datetime as dt
from types import SimpleNamespace

import pytest

from app import services
from app.models import (
    STATUT_EN_ATTENTE,
    STATUT_CONFIRME,
    STATUT_TERMINE,
    STATUT_ANNULE,
)


# ---------- Horaires et créneaux ----------

def test_heures_de_la_journee():
    heures = services.heures_de_la_journee()

    assert len(heures) == 18
    assert heures[0] == dt.time(8, 0)
    assert heures[-1] == dt.time(16, 30)


def test_jour_ouvre():
    assert services.est_jour_ouvre(dt.date(2026, 11, 16)) is True


def test_weekend_non_ouvrable():
    assert services.est_jour_ouvre(dt.date(2026, 11, 14)) is False


def test_creneau_valide():
    now = dt.datetime(2026, 11, 16, 7, 0)

    assert services.creneau_valide(
        dt.date(2026, 11, 16), dt.time(8, 0), now
    ) is True


def test_creneau_weekend_refuse():
    now = dt.datetime(2026, 11, 13, 7, 0)

    message = services.erreur_creneau(
        dt.date(2026, 11, 14), dt.time(8, 0), now
    )

    assert message is not None
    assert "week-end" in message


def test_creneau_apres_heure_limite_refuse():
    now = dt.datetime(2026, 11, 16, 7, 0)

    assert services.creneau_valide(
        dt.date(2026, 11, 16), dt.time(17, 0), now
    ) is False


def test_creneau_dans_le_passe_refuse():
    now = dt.datetime(2026, 11, 16, 9, 0)

    assert services.creneau_valide(
        dt.date(2026, 11, 16), dt.time(8, 0), now
    ) is False


# ---------- Téléphone ----------

@pytest.mark.parametrize(
    "telephone",
    [
        "77 123 45 67",
        "+221 77 123 45 67",
        "00221 77 123 45 67",
        "221771234567",
    ],
)
def test_normaliser_telephone_formats_valides(telephone):
    assert services.normaliser_telephone(telephone) == "771234567"


@pytest.mark.parametrize(
    "telephone",
    [
        "12 345 67 89",
        "77123456",
        "77123456789",
        "telephone invalide",
    ],
)
def test_normaliser_telephone_formats_invalides(telephone):
    with pytest.raises(ValueError):
        services.normaliser_telephone(telephone)


# ---------- Statuts des rendez-vous ----------

def test_normaliser_statut_avec_accent():
    assert services.normaliser_statut(" Confirmé ") == STATUT_CONFIRME


def test_transition_en_attente_vers_confirme():
    rdv = SimpleNamespace(
        statut=STATUT_EN_ATTENTE,
        date=dt.date(2026, 11, 16),
        heure=dt.time(10, 0),
    )
    now = dt.datetime(2026, 11, 16, 9, 0)

    services.verifier_transition(rdv, STATUT_CONFIRME, now)


def test_transition_depuis_statut_termine_interdite():
    rdv = SimpleNamespace(
        statut=STATUT_TERMINE,
        date=dt.date(2026, 11, 16),
        heure=dt.time(8, 0),
    )

    with pytest.raises(services.ErreurMetier) as erreur:
        services.verifier_transition(
            rdv,
            STATUT_CONFIRME,
            dt.datetime(2026, 11, 16, 12, 0),
        )

    assert erreur.value.status_code == 409


def test_rendez_vous_ne_peut_pas_etre_termine_a_l_avance():
    rdv = SimpleNamespace(
        statut=STATUT_CONFIRME,
        date=dt.date(2026, 11, 16),
        heure=dt.time(10, 0),
    )

    with pytest.raises(services.ErreurMetier) as erreur:
        services.verifier_transition(
            rdv,
            STATUT_TERMINE,
            dt.datetime(2026, 11, 16, 9, 0),
        )

    assert erreur.value.status_code == 409


# ---------- Annulation et rappels ----------

def test_rendez_vous_futur_annulable():
    rdv = SimpleNamespace(
        statut=STATUT_CONFIRME,
        date=dt.date(2026, 11, 16),
        heure=dt.time(10, 0),
    )

    assert services.est_annulable_par_patient(
        rdv, dt.datetime(2026, 11, 16, 9, 0)
    ) is True


def test_rappel_dans_les_15_minutes():
    rdv = SimpleNamespace(
        statut=STATUT_CONFIRME,
        date=dt.date(2026, 11, 16),
        heure=dt.time(10, 15),
    )

    assert services.est_rappel(
        rdv, dt.datetime(2026, 11, 16, 10, 0)
    ) is True


def test_rappel_hors_delai():
    rdv = SimpleNamespace(
        statut=STATUT_CONFIRME,
        date=dt.date(2026, 11, 16),
        heure=dt.time(10, 16),
    )

    assert services.est_rappel(
        rdv, dt.datetime(2026, 11, 16, 10, 0)
    ) is False


def test_rendez_vous_en_attente_ne_declenche_pas_de_rappel():
    rdv = SimpleNamespace(
        statut=STATUT_EN_ATTENTE,
        date=dt.date(2026, 11, 16),
        heure=dt.time(10, 10),
    )

    assert services.est_rappel(
        rdv, dt.datetime(2026, 11, 16, 10, 0)
    ) is False




# ---------- Tests métier avec SQLite ----------

from sqlalchemy import select

from app.database import Base, engine, SessionLocal
from app.seed import init_db
from app.models import Dentiste, Soin
from app.security import verify_password


@pytest.fixture
def db():
    # Réinitialiser la base de test avant chaque test métier
    Base.metadata.drop_all(bind=engine)
    init_db(retries=1, delay=0)

    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


def obtenir_dentiste_et_soin(db):
    dentiste = db.scalar(
        select(Dentiste).where(Dentiste.identifiant == "moustapha.diaw")
    )
    assert dentiste is not None
    assert dentiste.soins
    return dentiste, dentiste.soins[0]


def test_creer_rendez_vous_valide(db):
    dentiste, soin = obtenir_dentiste_et_soin(db)

    rdv = services.creer_rendez_vous(
        db,
        patient_nom="Test Patient",
        patient_tel="771234567",
        dentiste_id=dentiste.id,
        soin_id=soin.id,
        jour=dt.date(2027, 1, 4),
        heure=dt.time(10, 0),
        now=dt.datetime(2027, 1, 4, 8, 0),
    )

    assert rdv.id is not None
    assert rdv.statut == STATUT_EN_ATTENTE
    assert rdv.patient_tel == "771234567"


def test_creer_rendez_vous_dentiste_inexistant(db):
    soin = db.scalar(select(Soin))

    with pytest.raises(services.ErreurMetier) as erreur:
        services.creer_rendez_vous(
            db,
            patient_nom="Test",
            patient_tel="771234567",
            dentiste_id=999999,
            soin_id=soin.id,
            jour=dt.date(2027, 1, 5),
            heure=dt.time(10, 0),
            now=dt.datetime(2027, 1, 5, 8, 0),
        )

    assert erreur.value.status_code == 404


def test_creer_rendez_vous_soin_inexistant(db):
    dentiste, _ = obtenir_dentiste_et_soin(db)

    with pytest.raises(services.ErreurMetier) as erreur:
        services.creer_rendez_vous(
            db,
            patient_nom="Test",
            patient_tel="771234567",
            dentiste_id=dentiste.id,
            soin_id=999999,
            jour=dt.date(2027, 1, 6),
            heure=dt.time(10, 0),
            now=dt.datetime(2027, 1, 6, 8, 0),
        )

    assert erreur.value.status_code == 404


def test_creer_rendez_vous_soin_non_propose(db):
    dentiste, _ = obtenir_dentiste_et_soin(db)
    autre_soin = db.scalar(
        select(Soin).where(Soin.libelle == "appareil dentaire")
    )

    if autre_soin is None or autre_soin in dentiste.soins:
        pytest.skip("Aucun soin non proposé disponible pour ce dentiste")

    with pytest.raises(services.ErreurMetier) as erreur:
        services.creer_rendez_vous(
            db,
            patient_nom="Test",
            patient_tel="771234567",
            dentiste_id=dentiste.id,
            soin_id=autre_soin.id,
            jour=dt.date(2027, 1, 7),
            heure=dt.time(10, 0),
            now=dt.datetime(2027, 1, 7, 8, 0),
        )

    assert erreur.value.status_code == 422


def test_creer_deux_rendez_vous_sur_meme_creneau_refuse(db):
    dentiste, soin = obtenir_dentiste_et_soin(db)
    arguments = {
        "patient_nom": "Premier Patient",
        "patient_tel": "771234567",
        "dentiste_id": dentiste.id,
        "soin_id": soin.id,
        "jour": dt.date(2027, 1, 8),
        "heure": dt.time(10, 0),
        "now": dt.datetime(2027, 1, 8, 8, 0),
    }

    services.creer_rendez_vous(db, **arguments)

    arguments["patient_nom"] = "Deuxieme Patient"

    with pytest.raises(services.ErreurMetier) as erreur:
        services.creer_rendez_vous(db, **arguments)

    assert erreur.value.status_code == 409


def test_annuler_rendez_vous_par_patient(db):
    dentiste, soin = obtenir_dentiste_et_soin(db)

    rdv = services.creer_rendez_vous(
        db,
        patient_nom="Patient Annulation",
        patient_tel="771234567",
        dentiste_id=dentiste.id,
        soin_id=soin.id,
        jour=dt.date(2027, 1, 11),
        heure=dt.time(10, 0),
        now=dt.datetime(2027, 1, 11, 8, 0),
    )

    annule = services.annuler_par_patient(
        db, rdv.id, "77 123 45 67",
        dt.datetime(2027, 1, 11, 9, 0),
    )

    assert annule.statut == STATUT_ANNULE


def test_annulation_refuse_telephone_incorrect(db):
    dentiste, soin = obtenir_dentiste_et_soin(db)

    rdv = services.creer_rendez_vous(
        db,
        patient_nom="Patient Telephone",
        patient_tel="771234567",
        dentiste_id=dentiste.id,
        soin_id=soin.id,
        jour=dt.date(2027, 1, 12),
        heure=dt.time(10, 0),
        now=dt.datetime(2027, 1, 12, 8, 0),
    )

    with pytest.raises(services.ErreurMetier) as erreur:
        services.trouver_rdv_patient(db, rdv.id, "781234567")

    assert erreur.value.status_code == 404


def test_creer_dentiste_avec_identifiants_generes(db):
    soin = db.scalar(select(Soin))

    dentiste, mot_de_passe = services.creer_dentiste(
        db,
        nom="Fatou Diop",
        specialite="Orthodontiste",
        soin_ids=[soin.id],
    )

    assert dentiste.identifiant == "fatou.diop"
    assert dentiste.doit_changer_mdp is True
    assert len(mot_de_passe) == 12
    assert verify_password(mot_de_passe, dentiste.mot_de_passe_hash)


def test_identifiant_dentiste_doublon(db):
    soin = db.scalar(select(Soin))

    services.creer_dentiste(
        db,
        nom="Aminata Test",
        specialite="Dentiste",
        soin_ids=[soin.id],
    )

    second, _ = services.creer_dentiste(
        db,
        nom="Aminata Test",
        specialite="Dentiste",
        soin_ids=[soin.id],
    )

    assert second.identifiant == "aminata.test2"

