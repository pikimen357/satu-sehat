"""
SATUSEHAT Patient Registration API
===================================
FastAPI backend untuk simulasi alur pendaftaran pasien ke platform SATUSEHAT.

Alur:
  1. GET  /registration/token            - Dapatkan access token
  2a. GET  /registration/patient-ihs     - Cari IHS Number pasien by NIK
  2b. GET  /registration/practitioner-ihs - Cari IHS Number dokter by NIK
  3.  POST /registration/location        - Buat resource Location
  4.  POST /registration/encounter       - Daftarkan kunjungan (Encounter)
  *   POST /registration/run-full-flow   - Jalankan semua langkah sekaligus
"""

import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import registration

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

app = FastAPI(
    title="SATUSEHAT Patient Registration API",
    description=(
        "Simulasi alur pendaftaran pasien ke platform SATUSEHAT Kemenkes RI.\n\n"
        "Menggunakan environment **Sandbox/Development**.\n\n"
        "Ikuti urutan endpoint di bawah untuk menjalankan alur lengkap, "
        "atau gunakan `/registration/run-full-flow` untuk menjalankan semuanya sekaligus."
    ),
    version="1.0.0",
    contact={
        "name": "SATUSEHAT Docs",
        "url": "https://satusehat.kemkes.go.id/platform/docs/id/playbook/",
    },
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(registration.router)


@app.get("/", tags=["Root"])
async def root():
    return {
        "service": "SATUSEHAT Patient Registration API",
        "version": "1.0.0",
        "environment": "sandbox",
        "docs": "/docs",
        "endpoints": {
            "step1_token": "GET /registration/token",
            "step2a_patient": "GET /registration/patient-ihs",
            "step2b_practitioner": "GET /registration/practitioner-ihs",
            "step3_location": "POST /registration/location",
            "step4_encounter": "POST /registration/encounter",
            "full_flow": "POST /registration/run-full-flow",
        },
    }
