from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Text, JSON
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

# SQLAlchemy Models untuk SQLite
class Registration(Base):
    """Model untuk menyimpan data pendaftaran pasien ke SQLite."""

    __tablename__ = "registrations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    nik_pasien = Column(String(50), nullable=False, index=True)
    patient_ihs_id = Column(String(100), nullable=False)
    patient_name = Column(String(255), nullable=True)
    nik_dokter = Column(String(50), nullable=True)
    practitioner_ihs_id = Column(String(100), nullable=False)
    practitioner_name = Column(String(255), nullable=True)
    location_id = Column(String(100), nullable=False)
    location_name = Column(String(255), nullable=True)
    encounter_id = Column(String(100), nullable=False, unique=True, index=True)
    status = Column(String(50), default="arrived")
    created_at = Column(DateTime, default=datetime.utcnow)
    fhir_response = Column(JSON, nullable=True)

    def to_dict(self):
        return {
            "id": self.id,
            "nik_pasien": self.nik_pasien,
            "patient_ihs_id": self.patient_ihs_id,
            "patient_name": self.patient_name,
            "nik_dokter": self.nik_dokter,
            "practitioner_ihs_id": self.practitioner_ihs_id,
            "practitioner_name": self.practitioner_name,
            "location_id": self.location_id,
            "location_name": self.location_name,
            "encounter_id": self.encounter_id,
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class Coding(BaseModel):
    system: str
    code: str
    display: Optional[str]


class Identifier(BaseModel):
    system: str
    value: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str
    expires_in: int


class PatientIHSResponse(BaseModel):
    ihs_number: str
    nik: str
    fullname: str

class LocationRequest(BaseModel):
    location_name: str
    nik_pasien: Optional[str] = None
    patient_ihs_id: Optional[str] = None
    practitioner_ihs_id: Optional[str] = None
    description: Optional[str] = None
    address: Optional[str] = None
    category: Optional[List[Coding]] = None


class LocationResponse(BaseModel):
    id: str
    active: bool
    name: str

class EncounterRequest(BaseModel):
    patient_ihs_id: str
    practitioner_ihs_id: str
    location_id: str
    nik_pasien: Optional[str] = None
    encounter_class: Optional[str] = "AMB"
    description: Optional[str] = "Kunjungan Rutin"


class EncounterResponse(BaseModel):
    id: str
    status: str
    subject: Dict[str, str]
    period: Dict[str, str]


class FullFlowResponse(BaseModel):
    status: str
    message: str
    data: Dict[str, Any]