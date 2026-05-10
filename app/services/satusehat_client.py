"""
HTTP client helper untuk semua request ke SATUSEHAT FHIR API.
Menangani Authorization header dan error umum secara terpusat.
"""

import httpx
from fastapi import HTTPException
from app.config import settings
from app.services.auth import get_access_token


async def _get_headers() -> dict:
    token = await get_access_token()
    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }


async def fhir_get(path: str, params: dict | None = None) -> dict:
    """
    GET ke FHIR endpoint.

    Args:
        path: path relatif, contoh '/Patient'
        params: query string parameters

    Returns:
        Parsed JSON response

    Raises:
        HTTPException dengan detail dari server SATUSEHAT
    """
    headers = await _get_headers()
    url = f"{settings.satusehat_base_url}{path}"

    async with httpx.AsyncClient() as client:
        response = await client.get(url, headers=headers, params=params, timeout=30.0)

    return _handle_response(response)


async def fhir_post(path: str, payload: dict) -> dict:
    """
    POST ke FHIR endpoint.

    Args:
        path: path relatif, contoh '/Location'
        payload: FHIR resource body (dict)

    Returns:
        Parsed JSON response (resource yang dibuat)

    Raises:
        HTTPException dengan detail dari server SATUSEHAT
    """
    headers = await _get_headers()
    url = f"{settings.satusehat_base_url}{path}"

    async with httpx.AsyncClient() as client:
        response = await client.post(
            url, headers=headers, json=payload, timeout=30.0
        )

    return _handle_response(response)


def _handle_response(response: httpx.Response) -> dict:
    """Centralized error handling untuk semua response FHIR."""

    if response.status_code == 401:
        raise HTTPException(
            status_code=401,
            detail="Token kedaluwarsa atau tidak valid. Coba ulangi request.",
        )

    if response.status_code == 404:
        raise HTTPException(
            status_code=404,
            detail=f"Resource tidak ditemukan di SATUSEHAT: {response.text}",
        )

    if response.status_code == 422:
        raise HTTPException(
            status_code=422,
            detail=f"Payload tidak valid (Unprocessable Entity): {response.text}",
        )

    if not response.is_success:
        raise HTTPException(
            status_code=response.status_code,
            detail=f"Error dari server SATUSEHAT: {response.text}",
        )

    return response.json()
