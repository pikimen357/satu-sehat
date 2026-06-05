import logging
from fastapi import APIRouter, HTTPException, Depends
from app.models import (
    TokenResponse, PatientIHSResponse, 
    LocationRequest, LocationResponse, 
    EncounterRequest, EncounterResponse, FullFlowResponse
)
from app.services.satusehat_service import SatuSehatService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/registration", tags=["Pendaftaran Pasien"])

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
        return service.get_token()
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {str(e)}")

# ---------------------------------------------------------------------------
# STEP 2 – Master Data
# ---------------------------------------------------------------------------

@router.get("/patient-ihs", summary="Step 2a: Cari IHS Number Pasien", response_model=PatientIHSResponse)
async def get_patient_ihs(token: str, nik: str = NIK_PASIEN_DUMMY):
    """
    Mencari IHS Number pasien berdasarkan NIK.
    """
    try:
        patient_data = service.get_patient_ihs(token, nik)
        # Transformasi FHIR Resource ke Simple Model
        return {
            "ihsNumber": patient_data["id"],
            "nik": nik,
            "fullName": patient_data.get("name", [{}])[0].get("text", "Unknown")
        }
    except HTTPException as e:
        raise e

@router.get("/practitioner-ihs", summary="Step 2b: Cari IHS Number Dokter", response_model=PatientIHSResponse)
async def get_practitioner_ihs(token: str, nik: str):
    """
    Mencari IHS Number dokter berdasarkan NIK.
    """
    try:
        # Menggunakan logic yang sama dengan patient lookup (karena sama-sama Resource FHIR)
        # Catatan: Di produksi, endpoint-nya mungkin berbeda /Practitioner vs /Patient
        prac_data = service.get_practitioner_ihs(token, nik)
        return {
            "ihsNumber": prac_data["id"],
            "nik": nik,
            "fullName": prac_data.get("name", [{}])[0].get("text", "Unknown")
        }
    except HTTPException as e:
        raise e

# ---------------------------------------------------------------------------
# STEP 3 – POST Location
# ---------------------------------------------------------------------------

@router.post("/location", summary="Step 3: Buat Resource Location", response_model=LocationResponse)
async def create_location(token: str, payload: LocationRequest):
    """
    Membuat resource Location berdasarkan request body.
    """
    fhir_payload = {
        "resourceType": "Location",
        "active": True,
        "name": payload.name,
        "description": payload.description,
        "category": [c.dict() for c in payload.category]
    }
    
    try:
        result = service.create_location(token, fhir_payload)
        return {
            "id": result["id"],
            "active": result.get("active", True),
            "name": result.get("name", payload.name)
        }
    except HTTPException as e:
        raise e

# ---------------------------------------------------------------------------
# STEP 4 – POST Encounter
# ---------------------------------------------------------------------------

@router.post("/encounter", summary="Step 4: Daftarkan Kunjungan (Encounter)", response_model=EncounterResponse)
async def create_encounter(token: str, payload: EncounterRequest):
    """
    Mendaftarkan kunjungan pasien ke SATUSEHAT.
    """
    # Sesuai rekomendasi FHIR SATUSEHAT
    fhir_payload = {
        "resourceType": "Encounter",
        "status": "planned",
        "class": {
            "system": "http://terminology.hl7.org/CodeSystem/v3-ActClass",
            "code": payload.encounter_class
        },
        "subject": { "reference": f"Patient/{payload.patient_ihs}" },
        "participant": [{
            "individual": { "reference": f"Practitioner/{payload.practitioner_ihs}" }
        }],
        "location": { "reference": f"Location/{payload.location_id}" },
        "description": payload.description
    }
    
    try:
        result = service.create_encounter(token, fhir_payload)
        return {
            "id": result["id"],
            "status": result.get("status", "planned"),
            "subject": {"reference": f"Patient/{payload.patient_ihs}"},
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
    location_name: str = "Ruang Poli Umum"
):
    """
    Menjalankan seluruh alur pendaftaran menggunakan service yang sudah ada.
    """
    try:
        # 1. Token
        token_data = service.get_token()
        token = token_data["access_token"]
        
        # 2a. Patient IHS
        patient_res = service.get_patient_ihs(token, nik_pasien)
        patient_ihs = patient_res["id"]
        
        # 2b. Practitioner IHS (Directly using IHS Number for flow)
        # Kita asumsikan ihs_dokter adalah IHS Number valid
        practitioner_ihs = ihs_dokter 
        
        # 3. Location
        loc_fhir = {
            "resourceType": "Location",
            "active": True,
            "name": location_name,
            "category": [{"system": "http://terminology.hl7.org/CodeSystem/v3-Role.code", "code": "LOC"}]
        }
        loc_res = service.create_location(token, loc_fhir)
        location_id = loc_res["id"]
        
        # 4. Encounter
        enc_fhir = {
            "resourceType": "Encounter",
            "status": "planned",
            "class": {"system": "http://terminology.hl7.org/CodeSystem/v3-ActClass", "code": "AMB"},
            "subject": {"reference": f"Patient/{patient_ihs}"},
            "participant": [{"individual": {"reference": f"Practitioner/{practitioner_ihs}"}}],
            "location": {"reference": f"Location/{location_id}"}
        }
        enc_res = service.create_encounter(token, enc_fhir)
        
        return {
            "status": "success",
            "message": "Full flow completed successfully",
            "data": {
                "patient_ihs": patient_ihs,
                "location_id": location_id,
                "encounter_id": enc_res["id"]
            }
        }
        
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Full flow error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Flow failed: {str(e)}")