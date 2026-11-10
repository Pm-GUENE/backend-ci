import datetime as dt
import re

from pydantic import BaseModel, ConfigDict, Field, field_validator

from .services import normaliser_telephone


class SoinOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    libelle: str


class DentisteOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    nom: str
    specialite: str
    soins: list[SoinOut]


class CreneauOut(BaseModel):
    date: dt.date
    heure: dt.time


class RendezVousCreate(BaseModel):
    patient_nom: str = Field(..., min_length=2, max_length=100,
                             description="Prénom(s) et nom du patient")
    patient_tel: str = Field(..., description="Téléphone sénégalais, ex. 77 123 45 67")
    dentiste_id: int
    soin_id: int
    date: dt.date = Field(..., description="AAAA-MM-JJ")
    heure: dt.time = Field(..., description="HH:MM")

    @field_validator("patient_nom")
    @classmethod
    def verifier_nom(cls, v: str) -> str:
        v = re.sub(r"\s+", " ", v.strip())
        if not re.fullmatch(r"[^\W\d_]+(?:[ '\-][^\W\d_]+)*", v):
            raise ValueError("Le nom ne doit contenir que des lettres")
        return v

    @field_validator("patient_tel")
    @classmethod
    def verifier_tel(cls, v: str) -> str:
        return normaliser_telephone(v)


class RendezVousOut(BaseModel):
    """`id` est le numéro de rendez-vous à donner au patient."""
    model_config = ConfigDict(from_attributes=True)
    id: int
    patient_nom: str
    patient_tel: str
    date: dt.date
    heure: dt.time
    statut: str
    dentiste: "DentisteResume"
    soin: SoinOut


class DentisteResume(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    nom: str
    specialite: str


class SuiviOut(RendezVousOut):
    """Réponse du suivi patient. `annulable` indique si le bouton « Annuler » doit s'afficher."""
    annulable: bool


RendezVousOut.model_rebuild()
SuiviOut.model_rebuild()


class ConnexionIn(BaseModel):
    identifiant: str = Field(..., min_length=1, max_length=100)
    mot_de_passe: str = Field(..., min_length=1, max_length=128)


class JetonOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str = Field(..., description="`dentiste` ou `admin`")
    nom: str
    doit_changer_mdp: bool = Field(..., description="Si vrai, afficher la page « Changer votre mot de passe »")


class MotDePasseIn(BaseModel):
    nouveau_mot_de_passe: str = Field(..., min_length=8, max_length=72)
    confirmation: str | None = Field(None, description="Facultatif : si fourni, doit être identique")


class MessageOut(BaseModel):
    message: str
    doit_changer_mdp: bool
