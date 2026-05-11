"""
Builder functions untuk membuat FHIR R4 resource payload.
Semua payload mengikuti skema yang disyaratkan oleh SATUSEHAT.
"""

from datetime import datetime, timezone


def build_location_payload(org_id: str, location_name: str = "Ruang Poli Umum") -> dict:
    """
    Membuat payload FHIR R4 untuk resource Location.

    Args:
        org_id: Organization ID fasyankes
        location_name: Nama ruangan/lokasi

    Returns:
        dict FHIR Location resource
    """
    return {
        "resourceType": "Location",
        "status": "active",
        "name": location_name,
        "description": location_name,
        "mode": "instance",
        "type": [
            {
                "coding": [
                    {
                        "system": "http://terminology.hl7.org/CodeSystem/v3-RoleCode",
                        "code": "RNEU",
                        "display": "Neuroradiology unit",
                    }
                ]
            }
        ],
        "physicalType": {
            "coding": [
                {
                    "system": "http://terminology.hl7.org/CodeSystem/location-physical-type",
                    "code": "ro",
                    "display": "Room",
                }
            ]
        },
        "managingOrganization": {
            "reference": f"Organization/{org_id}"
        },
    }


def build_encounter_payload(
    org_id: str,
    location_id: str,
    patient_ihs_id: str,
    practitioner_ihs_id: str,
) -> dict:
    """
    Membuat payload FHIR R4 untuk resource Encounter (kunjungan pasien).

    Args:
        org_id: Organization ID fasyankes
        location_id: Location ID yang dibuat di langkah sebelumnya
        patient_ihs_id: IHS Number pasien (dari pencarian by NIK)
        practitioner_ihs_id: IHS Number dokter/tenaga kesehatan

    Returns:
        dict FHIR Encounter resource
    """
    import uuid
    now_utc = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S+00:00")

    return {
        "resourceType": "Encounter",
        "identifier": [
            {
                "system": f"http://sys-ids.kemkes.go.id/encounter/{org_id}",
                "value": str(uuid.uuid4()),
            }
        ],
        "status": "arrived",
        "statusHistory": [
            {
                "status": "arrived",
                "period": {
                    "start": now_utc,
                },
            }
        ],
        "class": {
            "system": "http://terminology.hl7.org/CodeSystem/v3-ActCode",
            "code": "AMB",
            "display": "ambulatory",
        },
        "subject": {
            "reference": f"Patient/{patient_ihs_id}",
            "display": "Pasien",
        },
        "participant": [
            {
                "type": [
                    {
                        "coding": [
                            {
                                "system": "http://terminology.hl7.org/CodeSystem/v3-ParticipationType",
                                "code": "ATND",
                                "display": "attender",
                            }
                        ]
                    }
                ],
                "individual": {
                    "reference": f"Practitioner/{practitioner_ihs_id}",
                    "display": "Dokter",
                },
            }
        ],
        "period": {
            "start": now_utc,
        },
        "location": [
            {
                "location": {
                    "reference": f"Location/{location_id}",
                    "display": "Ruang Poli Umum",
                }
            }
        ],
        "serviceProvider": {
            "reference": f"Organization/{org_id}"
        },
    }