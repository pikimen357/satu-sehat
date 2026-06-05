import logging
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from app.models import (
    TokenResponse, PatientIHSResponse, 
    LocationRequest, LocationResponse, 
    EncounterRequest, EncounterResponse, FullFlowResponse
)
from app.services.satusehat_service import SatuSehatService
from app.services.fhir_builder import build_location_payload, build_encounter_payload
from app.database import get_db, save_registration, init_db
from app.config import settings
from app.services.auth import get_access_token

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/registration", tags=["Pendaftaran Pasien"])

# Inisialisasi database saat startup
init_db()

service = SatuSehatService()

NIK_PASIEN_DUMMY = "9271060312000001"
IHS_DOKTER_DUMMY = "10006926841"

# ---------------------------------------------------------------------------
# STEP 1 – Token
# ---------------------------------------------------------------------------

@router.get("/token", summary="Step 1: Dapatkan Access Token", response_model=TokenResponse)
async def get_token():
    """
    Mendapatkan OAuth2 access token dari server SATUSEHAT.
    """
    try:
        return await service.get_token()
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {str(e)}")

# ---------------------------------------------------------------------------
# STEP 2 – Master Data
# ---------------------------------------------------------------------------

@router.get("/patient-ihs", summary="Step 2a: Cari IHS Number Pasien", response_model=PatientIHSResponse)
async def get_patient_ihs(nik: str = NIK_PASIEN_DUMMY):
    """
    Mencari IHS Number pasien berdasarkan NIK.
    Token diperoleh otomatis.
    """
    try:
        token = await get_access_token()
        patient_data = await service.get_patient_ihs(token, nik)
        # Transformasi FHIR Resource ke Simple Model
        return {
            "ihs_number": patient_data["id"],
            "nik": nik,
            "fullname": patient_data.get("name", [{}])[0].get("text", "Unknown")
        }
    except HTTPException as e:
        raise e

@router.get("/practitioner-ihs", summary="Step 2b: Cari IHS Number Dokter", response_model=PatientIHSResponse)
async def get_practitioner_ihs(nik: str):
    """
    Mencari IHS Number dokter berdasarkan NIK.
    Token diperoleh otomatis.
    """
    try:
        token = await get_access_token()
        prac_data = await service.get_practitioner_ihs(token, nik)
        return {
            "ihs_number": prac_data["id"],
            "nik": nik,
            "fullname": prac_data.get("name", [{}])[0].get("text", "Unknown")
        }
    except HTTPException as e:
        raise e


@router.get("/practitioner-by-ihs", summary="Step 2b (alt): Cari Dokter by IHS Number")
async def get_practitioner_by_ihs(ihs_id: str = IHS_DOKTER_DUMMY):
    """
    Mencari data dokter langsung berdasarkan IHS Number.
    Token diperoleh otomatis.
    """
    try:
        token = await get_access_token()
        prac_data = await service.get_practitioner_by_ihs(token, ihs_id)
        if prac_data.get("resourceType") != "Practitioner":
            raise HTTPException(status_code=404, detail="Practitioner tidak ditemukan")
        name_text = prac_data.get("name", [{}])[0].get("text", "Unknown") if prac_data.get("name") else "Unknown"
        return {
            "ihs_number": prac_data["id"],
            "nik": "-",
            "fullname": name_text
        }
    except HTTPException as e:
        raise e


# ---------------------------------------------------------------------------
# STEP 3 – POST Location
# ---------------------------------------------------------------------------

@router.post("/location", summary="Step 3: Buat Resource Location", response_model=LocationResponse)
async def create_location(payload: LocationRequest, db: Session = Depends(get_db)):
    """
    Membuat resource Location berdasarkan request body.
    Token diperoleh otomatis.
    Data otomatis disimpan ke SQLite (jika nik_pasien disediakan).
    """
    token = await get_access_token()
    fhir_payload = build_location_payload(
        org_id=settings.satusehat_org_id,
        location_name=payload.location_name,
    )
    
    try:
        result = await service.create_location(token, fhir_payload)
        location_id = result["id"]
        
        # Simpan ke SQLite jika nik_pasien disediakan
        if payload.nik_pasien:
            save_registration(
                db=db,
                nik_pasien=payload.nik_pasien,
                patient_ihs_id=payload.patient_ihs_id or "unknown",
                patient_name=None,
                practitioner_ihs_id=payload.practitioner_ihs_id or "unknown",
                practitioner_name=None,
                location_id=location_id,
                location_name=payload.location_name,
                encounter_id="pending",  # akan diupdate di encounter
                fhir_response=result
            )
        
        return {
            "id": location_id,
            "active": True,
            "name": result.get("name", payload.location_name)
        }
    except HTTPException as e:
        raise e

# ---------------------------------------------------------------------------
# STEP 4 – POST Encounter
# ---------------------------------------------------------------------------

@router.post("/encounter", summary="Step 4: Daftarkan Kunjungan (Encounter)", response_model=EncounterResponse)
async def create_encounter(payload: EncounterRequest, db: Session = Depends(get_db)):
    """
    Mendaftarkan kunjungan pasien ke SATUSEHAT.
    Token diperoleh otomatis.
    Data otomatis disimpan ke SQLite.
    """
    token = await get_access_token()
    # Gunakan builder yang sudah benar
    fhir_payload = build_encounter_payload(
        org_id=settings.satusehat_org_id,
        location_id=payload.location_id,
        patient_ihs_id=payload.patient_ihs_id,
        practitioner_ihs_id=payload.practitioner_ihs_id,
    )
    
    try:
        result = await service.create_encounter(token, fhir_payload)
        encounter_id = result["id"]
        
        # Simpan ke SQLite
        save_registration(
            db=db,
            nik_pasien=payload.nik_pasien or "unknown",
            patient_ihs_id=payload.patient_ihs_id,
            patient_name=None,
            practitioner_ihs_id=payload.practitioner_ihs_id,
            practitioner_name=None,
            location_id=payload.location_id,
            location_name=None,
            encounter_id=encounter_id,
            fhir_response=result
        )
        
        return {
            "id": encounter_id,
            "status": result.get("status", "arrived"),
            "subject": {"reference": f"Patient/{payload.patient_ihs_id}"},
            "period": result.get("period", {"start": "Not Set"})
        }
    except HTTPException as e:
        raise e

# ---------------------------------------------------------------------------
# FULL FLOW 
# ---------------------------------------------------------------------------

@router.post("/run-full-flow", summary="[ALL-IN-ONE] Full Registration Flow", response_model=FullFlowResponse)
async def run_full_registration_flow(
    nik_pasien: str = NIK_PASIEN_DUMMY,
    ihs_dokter: str = IHS_DOKTER_DUMMY,
    location_name: str = "Ruang Poli Umum",
    db: Session = Depends(get_db)
):
    """
    Menjalankan seluruh alur pendaftaran menggunakan service yang sudah ada.
    Data otomatis disimpan ke SQLite.
    """
    try:
        # 1. Token
        token = await get_access_token()
        
        # 2a. Patient IHS
        patient_res = await service.get_patient_ihs(token, nik_pasien)
        patient_ihs = patient_res["id"]
        patient_name = patient_res.get("name", [{}])[0].get("text", "Unknown")
        
        # 2b. Practitioner IHS (Directly using IHS Number for flow)
        # Kita asumsikan ihs_dokter adalah IHS Number valid
        practitioner_ihs = ihs_dokter 
        
        # 3. Location - gunakan builder yang sudah benar
        loc_fhir = build_location_payload(
            org_id=settings.satusehat_org_id,
            location_name=location_name
        )
        loc_res = await service.create_location(token, loc_fhir)
        location_id = loc_res["id"]
        
        # 4. Encounter - gunakan builder yang sudah benar
        enc_fhir = build_encounter_payload(
            org_id=settings.satusehat_org_id,
            location_id=location_id,
            patient_ihs_id=patient_ihs,
            practitioner_ihs_id=practitioner_ihs,
        )
        enc_res = await service.create_encounter(token, enc_fhir)
        encounter_id = enc_res["id"]
        
        # Simpan ke SQLite
        save_registration(
            db=db,
            nik_pasien=nik_pasien,
            patient_ihs_id=patient_ihs,
            patient_name=patient_name,
            practitioner_ihs_id=practitioner_ihs,
            practitioner_name=None,
            location_id=location_id,
            location_name=location_name,
            encounter_id=encounter_id,
            fhir_response=enc_res
        )
        
        return {
            "status": "success",
            "message": "Full flow completed successfully",
            "data": {
                "patient_ihs": patient_ihs,
                "location_id": location_id,
                "encounter_id": encounter_id
            }
        }
        
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Full flow error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Flow failed: {str(e)}")


@router.get("/registrations", summary="Lihat Semua Data Registrasi")
async def list_registrations(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """
    Mengambil semua data registrasi yang tersimpan di SQLite.
    """
    from app.database import get_all_registrations
    registrations = get_all_registrations(db, skip, limit)
    return {
        "status": "success",
        "data": [r.to_dict() for r in registrations]
    }


@router.get("/registrations/{encounter_id}", summary="Lihat Registrasi by Encounter ID")
async def get_registration(encounter_id: str, db: Session = Depends(get_db)):
    """
    Mengambil data registrasi berdasarkan Encounter ID.
    """
    from app.database import get_registration_by_encounter
    registration = get_registration_by_encounter(db, encounter_id)
    if not registration:
        raise HTTPException(status_code=404, detail="Registrasi tidak ditemukan")
    return {
        "status": "success",
        "data": registration.to_dict()
    }