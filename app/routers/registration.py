"""
Router untuk alur pendaftaran pasien SATUSEHAT.
Mengimplementasikan 4 langkah berurutan:
  1. Autentikasi (token)
  2. Lookup IHS Number pasien & dokter by NIK
  3. POST Location
  4. POST Encounter
"""

import logging
from fastapi import APIRouter, HTTPException
from app.config import settings
from app.services.auth import get_access_token
from app.services.satusehat_client import fhir_get, fhir_post
from app.services.fhir_builder import build_location_payload, build_encounter_payload

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/registration", tags=["Pendaftaran Pasien"])

# Data dummy sandbox SATUSEHAT
NIK_PASIEN  = "9271060312000001"
NIK_DOKTER  = "1000000000000002"   # NIK dokter (lookup by NIK)
IHS_DOKTER  = "10006926841"        # IHS Number dokter dummy sandbox


# ---------------------------------------------------------------------------
# STEP 1 – Token
# ---------------------------------------------------------------------------

@router.get("/token", summary="Step 1: Dapatkan Access Token")
async def step1_get_token():
    """
    Mendapatkan OAuth2 access token dari server SATUSEHAT (Sandbox).
    Token di-cache otomatis dan di-refresh saat kedaluwarsa.
    """
    try:
        token = await get_access_token()
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))

    return {
        "step": 1,
        "status": "success",
        "message": "Access token berhasil didapatkan",
        "access_token_preview": f"{token[:20]}...",
    }


# ---------------------------------------------------------------------------
# STEP 2 – Master Data: IHS Number Pasien & Dokter
# ---------------------------------------------------------------------------

@router.get("/patient-ihs", summary="Step 2a: Cari IHS Number Pasien by NIK")
async def step2a_get_patient_ihs(nik: str = NIK_PASIEN):
    """
    Mencari IHS Number pasien berdasarkan NIK.
    Default NIK dummy sandbox: 9271060312000001
    """
    result = await fhir_get(
        "/Patient",
        params={"identifier": f"https://fhir.kemkes.go.id/id/nik|{nik}"},
    )

    entries = result.get("entry", [])
    if not entries:
        raise HTTPException(
            status_code=404,
            detail=f"Pasien dengan NIK {nik} tidak ditemukan di SATUSEHAT.",
        )

    patient = entries[0]["resource"]
    ihs_id = patient["id"]

    return {
        "step": "2a",
        "status": "success",
        "nik": nik,
        "patient_ihs_id": ihs_id,
        "patient_name": patient.get("name", [{}])[0].get("text", "-"),
    }


@router.get("/practitioner-ihs", summary="Step 2b: Cari IHS Number Dokter by NIK")
async def step2b_get_practitioner_ihs(nik: str = NIK_DOKTER):
    """
    Mencari IHS Number practitioner berdasarkan NIK.
    Gunakan endpoint /practitioner-by-ihs jika hanya punya IHS Number.
    """
    result = await fhir_get(
        "/Practitioner",
        params={"identifier": f"https://fhir.kemkes.go.id/id/nik|{nik}"},
    )

    entries = result.get("entry", [])
    if not entries:
        raise HTTPException(
            status_code=404,
            detail=f"Practitioner dengan NIK {nik} tidak ditemukan di SATUSEHAT.",
        )

    practitioner = entries[0]["resource"]
    ihs_id = practitioner["id"]

    return {
        "step": "2b",
        "status": "success",
        "nik": nik,
        "practitioner_ihs_id": ihs_id,
        "practitioner_name": practitioner.get("name", [{}])[0].get("text", "-"),
    }


@router.get("/practitioner-by-ihs", summary="Step 2b (alt): Cari Dokter langsung by IHS Number")
async def step2b_get_practitioner_by_ihs(ihs_id: str = IHS_DOKTER):
    """
    Mencari data practitioner langsung menggunakan IHS Number (bukan NIK).
    Digunakan saat NIK dokter tidak diketahui, hanya IHS Number-nya.
    Default IHS dummy sandbox: 10006926841
    """
    result = await fhir_get(f"/Practitioner/{ihs_id}")

    if result.get("resourceType") != "Practitioner":
        raise HTTPException(
            status_code=404,
            detail=f"Practitioner dengan IHS ID {ihs_id} tidak ditemukan.",
        )

    name_list = result.get("name", [{}])
    name_text = name_list[0].get("text", "-") if name_list else "-"

    return {
        "step": "2b",
        "status": "success",
        "practitioner_ihs_id": result["id"],
        "practitioner_name": name_text,
    }


# ---------------------------------------------------------------------------
# STEP 3 – POST Location
# ---------------------------------------------------------------------------

@router.post("/location", summary="Step 3: Buat Resource Location")
async def step3_create_location(location_name: str = "Ruang Poli Umum"):
    """
    Membuat resource Location (ruangan) yang terhubung dengan Organization fasyankes.
    Mengembalikan Location ID untuk digunakan di langkah berikutnya.
    """
    payload = build_location_payload(
        org_id=settings.satusehat_org_id,
        location_name=location_name,
    )

    result = await fhir_post("/Location", payload)
    location_id = result.get("id")

    if not location_id:
        raise HTTPException(
            status_code=500,
            detail="Server SATUSEHAT tidak mengembalikan Location ID.",
        )

    return {
        "step": 3,
        "status": "success",
        "message": f"Location '{location_name}' berhasil dibuat",
        "location_id": location_id,
        "fhir_response": result,
    }


# ---------------------------------------------------------------------------
# STEP 4 – POST Encounter
# ---------------------------------------------------------------------------

@router.post("/encounter", summary="Step 4: Daftarkan Kunjungan Pasien (Encounter)")
async def step4_create_encounter(
    patient_ihs_id: str,
    practitioner_ihs_id: str,
    location_id: str,
):
    """
    Mendaftarkan kunjungan pasien (Encounter) ke SATUSEHAT.

    - status: arrived (pasien baru tiba)
    - class: AMB (Ambulatory / Rawat Jalan)
    - timestamp: waktu saat request dijalankan (ISO 8601 UTC+0)

    Membutuhkan:
    - patient_ihs_id     : dari Step 2a
    - practitioner_ihs_id: dari Step 2b atau 2b-alt
    - location_id        : dari Step 3
    """
    payload = build_encounter_payload(
        org_id=settings.satusehat_org_id,
        location_id=location_id,
        patient_ihs_id=patient_ihs_id,
        practitioner_ihs_id=practitioner_ihs_id,
    )

    result = await fhir_post("/Encounter", payload)
    encounter_id = result.get("id")

    if not encounter_id:
        raise HTTPException(
            status_code=500,
            detail="Server SATUSEHAT tidak mengembalikan Encounter ID.",
        )

    return {
        "step": 4,
        "status": "success",
        "message": "Encounter berhasil dibuat. Pasien terdaftar!",
        "encounter_id": encounter_id,
        "fhir_response": result,
    }


# ---------------------------------------------------------------------------
# ALUR LENGKAP (all-in-one)
# ---------------------------------------------------------------------------

@router.post(
    "/run-full-flow",
    summary="[ALL-IN-ONE] Jalankan seluruh alur pendaftaran sekaligus",
)
async def run_full_registration_flow(
    nik_pasien: str = NIK_PASIEN,
    ihs_dokter: str = IHS_DOKTER,
    location_name: str = "Ruang Poli Umum",
):
    """
    Menjalankan keseluruhan alur pendaftaran pasien secara berurutan:
    1. Autentikasi → 2a. Lookup Patient by NIK → 2b. Lookup Practitioner by IHS
    → 3. Buat Location → 4. Buat Encounter
    """
    results = {}

    # Step 1 – Token
    logger.info("[Step 1] Mendapatkan access token...")
    try:
        token = await get_access_token()
        results["step1_token"] = {"status": "success", "preview": f"{token[:20]}..."}
    except ValueError as e:
        raise HTTPException(status_code=401, detail=f"[Step 1] {e}")

    # Step 2a – Patient by NIK
    logger.info("[Step 2a] Mencari IHS Number pasien NIK=%s", nik_pasien)
    patient_result = await fhir_get(
        "/Patient",
        params={"identifier": f"https://fhir.kemkes.go.id/id/nik|{nik_pasien}"},
    )
    entries = patient_result.get("entry", [])
    if not entries:
        raise HTTPException(
            status_code=404,
            detail=f"[Step 2a] Pasien dengan NIK {nik_pasien} tidak ditemukan.",
        )
    patient_ihs_id = entries[0]["resource"]["id"]
    results["step2a_patient"] = {"status": "success", "patient_ihs_id": patient_ihs_id}

    # Step 2b – Practitioner by IHS Number
    logger.info("[Step 2b] Mencari Practitioner IHS=%s", ihs_dokter)
    prac_result = await fhir_get(f"/Practitioner/{ihs_dokter}")
    if prac_result.get("resourceType") != "Practitioner":
        raise HTTPException(
            status_code=404,
            detail=f"[Step 2b] Practitioner IHS {ihs_dokter} tidak ditemukan.",
        )
    practitioner_ihs_id = prac_result["id"]
    results["step2b_practitioner"] = {
        "status": "success",
        "practitioner_ihs_id": practitioner_ihs_id,
    }

    # Step 3 – Location
    logger.info("[Step 3] Membuat Location: %s", location_name)
    location_payload = build_location_payload(
        org_id=settings.satusehat_org_id, location_name=location_name
    )
    location_result = await fhir_post("/Location", location_payload)
    location_id = location_result.get("id")
    if not location_id:
        raise HTTPException(status_code=500, detail="[Step 3] Location ID tidak diterima.")
    results["step3_location"] = {"status": "success", "location_id": location_id}

    # Step 4 – Encounter
    logger.info("[Step 4] Membuat Encounter...")
    encounter_payload = build_encounter_payload(
        org_id=settings.satusehat_org_id,
        location_id=location_id,
        patient_ihs_id=patient_ihs_id,
        practitioner_ihs_id=practitioner_ihs_id,
    )
    encounter_result = await fhir_post("/Encounter", encounter_payload)
    encounter_id = encounter_result.get("id")
    if not encounter_id:
        raise HTTPException(status_code=500, detail="[Step 4] Encounter ID tidak diterima.")
    results["step4_encounter"] = {
        "status": "success",
        "encounter_id": encounter_id,
        "fhir_response": encounter_result,
    }

    return {
        "status": "success",
        "message": "Seluruh alur pendaftaran berhasil dijalankan!",
        "summary": {
            "patient_ihs_id": patient_ihs_id,
            "practitioner_ihs_id": practitioner_ihs_id,
            "location_id": location_id,
            "encounter_id": encounter_id,
        },
        "detail": results,
    }