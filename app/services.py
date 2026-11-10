"""Règles métier. Fonctions simples qui reçoivent `now` en paramètre : faciles à tester."""
import datetime as dt
import re

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .models import (STATUT_ANNULE, STATUT_CONFIRME, STATUT_EN_ATTENTE, STATUT_TERMINE,
                     STATUTS_ACTIFS, Dentiste, RendezVous, Soin)

MESSAGE_INTROUVABLE = "Rendez-vous introuvable. Vérifiez votre numéro et votre téléphone."
MESSAGE_CRENEAU_PRIS = "Ce créneau vient d'être pris, choisissez-en un autre"


class ErreurMetier(Exception):
    """Erreur de règle métier, transformée en réponse HTTP par main.py."""

    def __init__(self, status_code: int, message: str):
        self.status_code = status_code
        self.message = message
        super().__init__(message)

HEURE_DEBUT = dt.time(8, 0)
HEURE_FIN = dt.time(17, 0)          # fin de journée
DUREE_MIN = 30                      # durée d'un créneau
MAX_JOURS = 31                      # période maximale demandée à /creneaux


def maintenant() -> dt.datetime:
    """Heure actuelle (le Sénégal est en UTC, comme les conteneurs Docker)."""
    return dt.datetime.now()


def heures_de_la_journee() -> list[dt.time]:
    """08:00, 08:30, ... 16:30 (le dernier créneau finit à 17:00)."""
    heures = []
    courant = dt.datetime.combine(dt.date.today(), HEURE_DEBUT)
    fin = dt.datetime.combine(dt.date.today(), HEURE_FIN)
    while courant < fin:
        heures.append(courant.time())
        courant += dt.timedelta(minutes=DUREE_MIN)
    return heures


def est_jour_ouvre(jour: dt.date) -> bool:
    return jour.weekday() < 5  # 0 = lundi ... 4 = vendredi


def erreur_creneau(jour: dt.date, heure: dt.time, now: dt.datetime) -> str | None:
    """Renvoie le message d'erreur si le créneau est invalide, sinon None."""
    if not est_jour_ouvre(jour):
        return "Pas de rendez-vous le week-end (ouvert du lundi au vendredi)"
    if heure not in heures_de_la_journee():
        return "Heure invalide : créneaux de 30 minutes entre 08h00 et 17h00 (dernier à 16h30)"
    if dt.datetime.combine(jour, heure) <= now:
        return "Impossible de réserver un créneau dans le passé"
    return None


def creneau_valide(jour: dt.date, heure: dt.time, now: dt.datetime) -> bool:
    """Vrai si : jour ouvré, heure dans la grille, et pas dans le passé."""
    return erreur_creneau(jour, heure, now) is None


def normaliser_telephone(tel: str) -> str:
    """Accepte '77 123 45 67', '+221 77 123 45 67'... Renvoie 9 chiffres : '771234567'."""
    chiffres = re.sub(r"[\s.\-()]", "", tel)
    for prefixe in ("+221", "00221", "221"):
        if chiffres.startswith(prefixe) and len(chiffres) > 9:
            chiffres = chiffres[len(prefixe):]
            break
    if not re.fullmatch(r"[37]\d{8}", chiffres):
        raise ValueError("Numéro de téléphone invalide (exemple : 77 123 45 67)")
    return chiffres


def creneaux_libres(db: Session, dentiste_id: int, du: dt.date, au: dt.date,
                    now: dt.datetime) -> list[tuple[dt.date, dt.time]]:
    """Créneaux valides du dentiste entre `du` et `au` non occupés par un RDV actif."""
    pris = {(r.date, r.heure) for r in db.scalars(
        select(RendezVous).where(RendezVous.dentiste_id == dentiste_id,
                                 RendezVous.date >= du, RendezVous.date <= au,
                                 RendezVous.statut.in_(STATUTS_ACTIFS)))}
    libres = []
    jour = du
    while jour <= au:
        for h in heures_de_la_journee():
            if creneau_valide(jour, h, now) and (jour, h) not in pris:
                libres.append((jour, h))
        jour += dt.timedelta(days=1)
    return libres


def creer_rendez_vous(db: Session, *, patient_nom: str, patient_tel: str, dentiste_id: int,
                      soin_id: int, jour: dt.date, heure: dt.time,
                      now: dt.datetime) -> RendezVous:
    """Crée un rendez-vous 'en_attente' après avoir vérifié toutes les règles."""
    dentiste = db.get(Dentiste, dentiste_id)
    if not dentiste:
        raise ErreurMetier(404, "Dentiste introuvable")
    soin = db.get(Soin, soin_id)
    if not soin:
        raise ErreurMetier(404, "Motif de consultation introuvable")
    if soin not in dentiste.soins:
        raise ErreurMetier(422, "Ce dentiste ne propose pas ce motif de consultation")

    message = erreur_creneau(jour, heure, now)
    if message:
        raise ErreurMetier(422, message)

    deja_pris = db.scalar(select(RendezVous.id).where(
        RendezVous.dentiste_id == dentiste_id, RendezVous.date == jour,
        RendezVous.heure == heure, RendezVous.statut.in_(STATUTS_ACTIFS)))
    if deja_pris:
        raise ErreurMetier(409, MESSAGE_CRENEAU_PRIS)

    rdv = RendezVous(patient_nom=patient_nom, patient_tel=patient_tel,
                     dentiste_id=dentiste_id, soin_id=soin_id, date=jour, heure=heure)
    db.add(rdv)
    try:
        db.commit()  # l'index uq_creneau_actif protège si deux patients réservent en même temps
    except IntegrityError:
        db.rollback()
        raise ErreurMetier(409, MESSAGE_CRENEAU_PRIS)
    db.refresh(rdv)
    return rdv


# ---------- Statuts ----------
TRANSITIONS = {
    STATUT_EN_ATTENTE: {STATUT_CONFIRME, STATUT_ANNULE},
    STATUT_CONFIRME: {STATUT_TERMINE, STATUT_ANNULE},
    STATUT_TERMINE: set(),   # ne change plus
    STATUT_ANNULE: set(),    # ne change plus
}


def moment_du_rdv(rdv: RendezVous) -> dt.datetime:
    return dt.datetime.combine(rdv.date, rdv.heure)


def verifier_transition(rdv: RendezVous, nouveau: str, now: dt.datetime) -> None:
    """Lève ErreurMetier(409) si le changement de statut est interdit."""
    if nouveau not in TRANSITIONS.get(rdv.statut, set()):
        raise ErreurMetier(409, f"Changement de statut impossible : "
                                f"{rdv.statut} -> {nouveau}")
    if nouveau == STATUT_TERMINE and moment_du_rdv(rdv) > now:
        raise ErreurMetier(409, "Un rendez-vous ne peut être terminé qu'après son heure")


def est_annulable_par_patient(rdv: RendezVous, now: dt.datetime) -> bool:
    return rdv.statut in STATUTS_ACTIFS and moment_du_rdv(rdv) > now


# ---------- Suivi par le patient ----------
def trouver_rdv_patient(db: Session, rdv_id: int, tel: str) -> RendezVous:
    """Le couple numéro + téléphone doit correspondre, sinon 404 sans dire lequel est faux."""
    try:
        tel_normalise = normaliser_telephone(tel)
    except ValueError:
        raise ErreurMetier(404, MESSAGE_INTROUVABLE)
    rdv = db.get(RendezVous, rdv_id)
    if not rdv or rdv.patient_tel != tel_normalise:
        raise ErreurMetier(404, MESSAGE_INTROUVABLE)
    return rdv


def annuler_par_patient(db: Session, rdv_id: int, tel: str, now: dt.datetime) -> RendezVous:
    rdv = trouver_rdv_patient(db, rdv_id, tel)
    if rdv.statut not in STATUTS_ACTIFS:
        raise ErreurMetier(409, "Ce rendez-vous ne peut plus être annulé (déjà terminé ou annulé)")
    verifier_transition(rdv, STATUT_ANNULE, now)
    if moment_du_rdv(rdv) <= now:
        raise ErreurMetier(409, "Ce rendez-vous est déjà passé, il ne peut plus être annulé")
    rdv.statut = STATUT_ANNULE  # le créneau redevient libre (l'index ne concerne que les actifs)
    db.commit()
    db.refresh(rdv)
    return rdv
