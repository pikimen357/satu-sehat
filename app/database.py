"""
Database service untuk SQLite menggunakan SQLAlchemy.
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from app.models import Base
import os

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./satusehat.db")

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db():
    """Inisialisasi database - membuat tabel jika belum ada."""
    from app.models import Registration
    Base.metadata.create_all(bind=engine)


def get_db() -> Session:
    """Dependency untuk mendapatkan database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def save_registration(
    db: Session,
    nik_pasien: str,
    patient_ihs_id: str,
    patient_name: str,
    practitioner_ihs_id: str,
    practitioner_name: str,
    location_id: str,
    location_name: str,
    encounter_id: str,
    fhir_response: dict = None,
):
    """Simpan data pendaftaran ke database."""
    from app.models import Registration
    registration = Registration(
        nik_pasien=nik_pasien,
        patient_ihs_id=patient_ihs_id,
        patient_name=patient_name,
        practitioner_ihs_id=practitioner_ihs_id,
        practitioner_name=practitioner_name,
        location_id=location_id,
        location_name=location_name,
        encounter_id=encounter_id,
        fhir_response=fhir_response,
    )
    db.add(registration)
    db.commit()
    db.refresh(registration)
    return registration


def get_registration_by_encounter(db: Session, encounter_id: str):
    """Ambil data pendaftaran berdasarkan encounter ID."""
    from app.models import Registration
    return db.query(Registration).filter(Registration.encounter_id == encounter_id).first()


def get_all_registrations(db: Session, skip: int = 0, limit: int = 100):
    """Ambil semua data pendaftaran."""
    from app.models import Registration
    return db.query(Registration).offset(skip).limit(limit).all()