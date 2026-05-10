"""
Service untuk mengelola OAuth2 Access Token SATUSEHAT.
Token di-cache di memori dan di-refresh otomatis saat kedaluwarsa.
"""

import time
import httpx
from app.config import settings


class TokenCache:
    """Menyimpan token di memori agar tidak request ulang setiap saat."""

    def __init__(self):
        self._token: str | None = None
        self._expires_at: float = 0.0  # epoch seconds

    def is_valid(self) -> bool:
        # Anggap kedaluwarsa 60 detik lebih awal (buffer)
        return self._token is not None and time.time() < (self._expires_at - 60)

    def set(self, token: str, expires_in: int):
        self._token = token
        self._expires_at = time.time() + expires_in

    def get(self) -> str | None:
        return self._token if self.is_valid() else None


_cache = TokenCache()


async def get_access_token() -> str:
    """
    Mengembalikan access token yang valid.
    Jika cache kosong atau kedaluwarsa, otomatis minta token baru.

    Raises:
        HTTPException-like ValueError jika autentikasi gagal.
    """
    cached = _cache.get()
    if cached:
        return cached

    async with httpx.AsyncClient() as client:
        response = await client.post(
            settings.satusehat_auth_url,
            params={"grant_type": "client_credentials"},
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            data={
                "client_id": settings.satusehat_client_id,
                "client_secret": settings.satusehat_client_secret,
            },
            timeout=30.0,
        )

    if response.status_code == 401:
        raise ValueError(
            "Autentikasi gagal (401): client_id atau client_secret tidak valid. "
            "Periksa nilai di file .env Anda."
        )

    if not response.is_success:
        raise ValueError(
            f"Gagal mendapatkan token. Status: {response.status_code}, "
            f"Body: {response.text}"
        )

    data = response.json()
    token = data["access_token"]
    expires_in = int(data.get("expires_in", 3599))

    _cache.set(token, expires_in)
    return token
