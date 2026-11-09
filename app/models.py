from datetime import date as date_type, datetime, time as time_type

from sqlalchemy import (CheckConstraint, ForeignKey, Index, String, func, text)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base

# Valeurs stockées en base (sans accent). Le frontend affiche "confirmé", "terminé", "annulé".
STATUT_EN_ATTENTE = "en_attente"
STATUT_CONFIRME = "confirme"
STATUT_TERMINE = "termine"
STATUT_ANNULE = "annule"
STATUTS = (STATUT_EN_ATTENTE, STATUT_CONFIRME, STATUT_TERMINE, STATUT_ANNULE)
STATUTS_ACTIFS = (STATUT_EN_ATTENTE, STATUT_CONFIRME)


class DentisteSoin(Base):
    __tablename__ = "dentiste_soin"
    dentiste_id: Mapped[int] = mapped_column(
        ForeignKey("dentiste.id", ondelete="CASCADE"), primary_key=True)
    soin_id: Mapped[int] = mapped_column(
        ForeignKey("soin.id", ondelete="CASCADE"), primary_key=True)


class Soin(Base):
    __tablename__ = "soin"
    id: Mapped[int] = mapped_column(primary_key=True)
    libelle: Mapped[str] = mapped_column(String(100), unique=True)


class Dentiste(Base):
    __tablename__ = "dentiste"
    id: Mapped[int] = mapped_column(primary_key=True)
    nom: Mapped[str] = mapped_column(String(100))
    specialite: Mapped[str] = mapped_column(String(100))
    identifiant: Mapped[str] = mapped_column(String(100), unique=True)
    mot_de_passe_hash: Mapped[str] = mapped_column(String(255))
    doit_changer_mdp: Mapped[bool] = mapped_column(default=True)

    soins: Mapped[list[Soin]] = relationship(secondary="dentiste_soin", order_by=Soin.id)


class Administrateur(Base):
    __tablename__ = "administrateur"
    id: Mapped[int] = mapped_column(primary_key=True)
    identifiant: Mapped[str] = mapped_column(String(100), unique=True)
    mot_de_passe_hash: Mapped[str] = mapped_column(String(255))


class RendezVous(Base):
    __tablename__ = "rendez_vous"
    id: Mapped[int] = mapped_column(primary_key=True)  # numéro de RDV donné au patient
    patient_nom: Mapped[str] = mapped_column(String(100))
    patient_tel: Mapped[str] = mapped_column(String(20))
    dentiste_id: Mapped[int] = mapped_column(ForeignKey("dentiste.id", ondelete="RESTRICT"))
    soin_id: Mapped[int] = mapped_column(ForeignKey("soin.id", ondelete="RESTRICT"))
    date: Mapped[date_type]
    heure: Mapped[time_type]
    statut: Mapped[str] = mapped_column(String(20), default=STATUT_EN_ATTENTE,
                                        server_default=STATUT_EN_ATTENTE)
    cree_le: Mapped[datetime] = mapped_column(server_default=func.now())

    dentiste: Mapped[Dentiste] = relationship()
    soin: Mapped[Soin] = relationship()

    __table_args__ = (
        CheckConstraint("statut IN ('en_attente','confirme','termine','annule')",
                        name="ck_statut"),
        # Anti double réservation : un seul RDV actif par dentiste et par créneau.
        Index("uq_creneau_actif", "dentiste_id", "date", "heure", unique=True,
              postgresql_where=text("statut IN ('en_attente','confirme')"),
              sqlite_where=text("statut IN ('en_attente','confirme')")),
    )
