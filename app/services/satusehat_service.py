import requests
from app.config import settings
from fastapi import HTTPException

class SatuSehatService:
    def __init__(self):
        self.base_url = settings.satusehat_base_url
        self.client_id = settings.satusehat_client_id
        self.client_secret = settings.satusehat_client_secret

    def get_token(self):
        """Mengambil access token menggunakan Client Credentials Grant"""
        url = settings.satusehat_auth_url 
        
        payload = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "grant_type": "client_credentials",
            "scope": "satu.sehat.app"
        }
        
        response = requests.post(url, data=payload)
        if response.status_code != 200:
            raise HTTPException(status_code=401, detail=f"Auth failed: {response.text}")
        
        return response.json()

    def get_patient_ihs(self, token, nik):
        """Mencari IHS Number pasien berdasarkan NIK"""
        url = f"{self.base_url}/Patient"
        params = {"identifier": f"https://satusehat.kemkes.go.id/id/nik.{nik}"}
        headers = {"Authorization": f"Bearer {token}"}
        
        response = requests.get(url, headers=headers, params=params)
        if response.status_code != 200:
            raise HTTPException(status_code=404, detail="Patient not found or API error")
        
        data = response.json()
        if not data.get("entry"):
            raise HTTPException(status_code=404, detail="Patient record not found in Bundle")
            
        return data["entry"][0]["resource"]

    def create_location(self, token, fhir_payload):
        """Membuat Resource Location di SATUSEHAT"""
        url = f"{self.base_url}/Location"
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/fhir+json"
        }
        
        response = requests.post(url, json=fhir_payload, headers=headers)
        if response.status_code not in [200, 201]:
            raise HTTPException(status_code=response.status_code, detail=response.text)
            
        return response.json()

    def create_encounter(self, token, fhir_payload):
        """Membuat Resource Encounter untuk pendaftaran pasien"""
        url = f"{self.base_url}/Encounter"
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/fhir+json"
        }
        
        response = requests.post(url, json=fhir_payload, headers=headers)
        if response.status_code not in [200, 201]:
            raise HTTPException(status_code=response.status_code, detail=response.text)
            
        return response.json()