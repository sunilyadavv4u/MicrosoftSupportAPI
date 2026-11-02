from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    app_name: str = "ADF Mock API Platform"
    database_path: str = "./data/mock_api.db"
    sources_manifest: str = "./data/sources.json"
    default_page_size: int = 100
    max_page_size: int = 1000
    api_key: str = "change-me-local-api-key"
    basic_username: str = "adf_user"
    basic_password: str = "ChangeThis_Basic_123!"
    static_bearer_token: str = "change-me-static-bearer-token"
    oauth_client_id: str = "adf-spn-client"
    oauth_client_secret: str = "ChangeThis_OAuth_Secret_123!"
    oauth_signing_secret: str = "replace-with-random-secret-minimum-32-characters"
    oauth_token_ttl_seconds: int = 3600
    entra_tenant_id: str | None = None
    entra_audience: str | None = None
    entra_issuer: str | None = None
    entra_required_scope: str = "Data.Read"
    entra_required_role: str = "Data.Read.All"
    max_delay_seconds: int = 60
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

settings = Settings()
