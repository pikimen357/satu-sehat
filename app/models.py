from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any

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
  name: str
  description: Optional[str]
  address: Optional[str]
  category: List[Coding] = [
    Coding(system="http://terminology.hl7.org/CodeSystem/v3-Role.code", code="LOC", display="Location")
  ]

class LocationResponse(BaseModel):
  id: str
  active: bool
  name: str

class EncounterRequest(BaseModel):
  patient_ihs: str
  practitioner_ihs: str
  location_id: str
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