from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    PROJECT_NAME: str = "Finanzas Autónomo API"
    DATABASE_URL: str = "postgresql+psycopg2://postgres:postgres@localhost:5432/finanzas"
    SECRET_KEY: str = "cambia-esto-en-produccion"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24

    # Orígenes del frontend permitidos por CORS, separados por comas.
    CORS_ORIGINS: str = "http://localhost:5173"

    # Ruta al ejecutable de Tesseract si no está en el PATH (por ejemplo en Windows).
    TESSERACT_CMD: str = ""

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]

    class Config:
        env_file = ".env"


settings = Settings()

if settings.SECRET_KEY == "cambia-esto-en-produccion":
    import warnings

    warnings.warn(
        "SECRET_KEY sigue en su valor por defecto. Cámbialo antes de desplegar en producción.",
        stacklevel=1,
    )
