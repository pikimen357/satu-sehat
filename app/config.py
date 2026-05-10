from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    satusehat_client_id: str
    satusehat_client_secret: str
    satusehat_org_id: str = "10000004"
    satusehat_auth_url: str = (
        "https://api-satusehat-stg.dto.kemkes.go.id/oauth2/v1/accesstoken"
    )
    satusehat_base_url: str = (
        "https://api-satusehat-stg.dto.kemkes.go.id/fhir-r4/v1"
    )


settings = Settings()
