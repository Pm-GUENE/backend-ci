import datetime as dt

from pydantic import BaseModel, ConfigDict


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
