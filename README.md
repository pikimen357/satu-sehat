# SATUSEHAT Patient Registration API

Backend FastAPI untuk simulasi alur pendaftaran pasien ke platform **SATUSEHAT** Kemenkes RI (environment Sandbox).

---

## Struktur Proyek

```
satusehat-fastapi/
├── app/
│   ├── main.py                      # Entry point FastAPI
│   ├── config.py                    # Konfigurasi dari .env
│   ├── routers/
│   │   └── registration.py          # Semua endpoint alur pendaftaran
│   └── services/
│       ├── auth.py                  # OAuth2 token management (dengan cache)
│       ├── satusehat_client.py      # HTTP client ke FHIR API SATUSEHAT
│       └── fhir_builder.py          # Builder payload FHIR R4
├── .env.example                     # Template konfigurasi (SALIN & ISI)
├── requirements.txt
├── SATUSEHAT_Registration.postman_collection.json
└── README.md
```

---

## Cara Instalasi & Menjalankan

### 1. Clone / download project, lalu masuk ke folder

```bash
cd satusehat-fastapi
```

### 2. Buat virtual environment & install dependencies

```bash
python -m venv venv
source venv/bin/activate        # Linux/macOS
venv\Scripts\activate           # Windows

pip install -r requirements.txt
```

### 3. Konfigurasi `.env`

Salin file `.env.example` menjadi `.env`:

```bash
cp .env .env
```

Lalu isi nilai yang diperlukan:

```env
SATUSEHAT_CLIENT_ID=your_client_id_here
SATUSEHAT_CLIENT_SECRET=your_client_secret_here
SATUSEHAT_ORG_ID=10000004
```

> **Catatan:** `CLIENT_ID` dan `CLIENT_SECRET` didapatkan dari portal SATUSEHAT Platform setelah registrasi sistem RME.

### 4. Jalankan server

```bash
uvicorn app.main:app --reload
```

Server berjalan di `http://localhost:8000`

---

## Dokumentasi API (Swagger UI)

Buka browser dan akses:

```
http://localhost:8000/docs
```

---

## Alur Pendaftaran Pasien

Jalankan endpoint secara berurutan:

| Langkah | Method | Endpoint | Keterangan |
|---------|--------|----------|------------|
| 1 | GET | `/registration/token` | Dapatkan OAuth2 Access Token |
| 2a | GET | `/registration/patient-ihs` | Cari IHS Number Pasien by NIK |
| 2b | GET | `/registration/practitioner-ihs` | Cari IHS Number Dokter by NIK |
| 3 | POST | `/registration/location` | Buat resource Location (Ruang Poli) |
| 4 | POST | `/registration/encounter` | Daftarkan Kunjungan (Encounter) |
| * | POST | `/registration/run-full-flow` | Jalankan semua langkah sekaligus |

### NIK Dummy (Sandbox)

| Peran | NIK |
|-------|-----|
| Pasien | `1000000000000001` |
| Dokter | `1000000000000002` |

---

## Postman Collection

Import file `SATUSEHAT_Registration.postman_collection.json` ke Postman.

Fitur:
- Urutan request step 1 → 4 sudah tersedia
- Script otomatis menyimpan `patient_ihs_id`, `practitioner_ihs_id`, dan `location_id` ke Collection Variables
- Request terakhir menggunakan variable tersebut otomatis

---

## Environment Variables

| Variabel | Wajib | Default | Keterangan |
|----------|-------|---------|------------|
| `SATUSEHAT_CLIENT_ID` | ✅ | - | Client ID dari portal SATUSEHAT |
| `SATUSEHAT_CLIENT_SECRET` | ✅ | - | Client Secret dari portal SATUSEHAT |
| `SATUSEHAT_ORG_ID` | ❌ | `10000004` | Organization ID Fasyankes |
| `SATUSEHAT_AUTH_URL` | ❌ | Sandbox URL | URL endpoint OAuth2 token |
| `SATUSEHAT_BASE_URL` | ❌ | Sandbox URL | Base URL FHIR R4 API |

---

## Error Handling

| HTTP Status | Keterangan |
|-------------|------------|
| `401` | Token kedaluwarsa / client_id atau client_secret salah |
| `404` | NIK tidak ditemukan di SATUSEHAT |
| `422` | Payload FHIR tidak valid |
| `500` | Server SATUSEHAT bermasalah atau ID tidak dikembalikan |
