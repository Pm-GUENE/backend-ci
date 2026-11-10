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


RendezVousOut.model_rebuild()
