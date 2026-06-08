import httpx
from app.config import settings
from fastapi import HTTPException

class SatuSehatService:
    def __init__(self):
        self.base_url = settings.satusehat_base_url
        self.client_id = settings.satusehat_client_id
        self.client_secret = settings.satusehat_client_secret

    async def get_token(self):
        """Mengambil access token menggunakan Client Credentials Grant"""
        url = settings.satusehat_auth_url 
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                url,
                params={"grant_type": "client_credentials"},
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                data={
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                },
                timeout=30.0,
            )
        
        if response.status_code == 401:
            raise HTTPException(
                status_code=401, 
                detail="Autentikasi gagal (401): client_id atau client_secret tidak valid."
            )
        
        if response.status_code != 200:
            raise HTTPException(status_code=response.status_code, detail=f"Auth failed: {response.text}")
        
        return response.json()

    async def get_patient_ihs(self, token, nik):
        """Mencari IHS Number pasien berdasarkan NIK"""
        url = f"{self.base_url}/Patient"
        params = {"identifier": f"https://fhir.kemkes.go.id/id/nik|{nik}"}
        headers = {"Authorization": f"Bearer {token}"}
        
        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=headers, params=params)
        
        if response.status_code != 200:
            raise HTTPException(status_code=404, detail="Patient not found or API error")
        
        data = response.json()
        if not data.get("entry"):
            raise HTTPException(status_code=404, detail="Patient record not found in Bundle")
            
        return data["entry"][0]["resource"]

    async def create_location(self, token, fhir_payload):
        """Membuat Resource Location di SATUSEHAT"""
        url = f"{self.base_url}/Location"
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/fhir+json"
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=fhir_payload, headers=headers)
        
        if response.status_code not in [200, 201]:
            raise HTTPException(status_code=response.status_code, detail=response.text)
            
        return response.json()

    async def get_practitioner_ihs(self, token, nik):
        """Mencari IHS Number dokter berdasarkan NIK"""
        url = f"{self.base_url}/Practitioner"
        params = {"identifier": f"https://fhir.kemkes.go.id/id/nik|{nik}"}
        headers = {"Authorization": f"Bearer {token}"}
        
        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=headers, params=params)
        
        if response.status_code != 200:
            raise HTTPException(status_code=404, detail="Practitioner not found or API error")
        
        data = response.json()
        if not data.get("entry"):
            raise HTTPException(status_code=404, detail="Practitioner record not found in Bundle")
            
        return data["entry"][0]["resource"]

    async def get_practitioner_by_ihs(self, token, ihs_id):
        """Mencari data dokter langsung berdasarkan IHS Number"""
        url = f"{self.base_url}/Practitioner/{ihs_id}"
        headers = {"Authorization": f"Bearer {token}"}
        
        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=headers)
        
        if response.status_code != 200:
            raise HTTPException(status_code=404, detail="Practitioner not found")
        
        return response.json()

    async def create_encounter(self, token, fhir_payload):
        """Membuat Resource Encounter untuk pendaftaran pasien"""
        url = f"{self.base_url}/Encounter"
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/fhir+json"
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=fhir_payload, headers=headers)
        
        if response.status_code not in [200, 201]:
            raise HTTPException(status_code=response.status_code, detail=response.text)
            
        return response.json()