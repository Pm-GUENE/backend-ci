import os


class Settings:
    DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./dentardv.db")
    JWT_SECRET = os.getenv("JWT_SECRET", "dev-only-secret-change-me-0123456789abcdef")
    JWT_EXPIRE_MINUTES = int(os.getenv("JWT_EXPIRE_MINUTES", "480"))
    ADMIN_IDENTIFIANT = os.getenv("ADMIN_IDENTIFIANT", "admin")
    ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "admin-dev")
    DEMO_PASSWORD = os.getenv("DEMO_PASSWORD", "Demo-dev-2026")
    CORS_ORIGINS = [o.strip() for o in os.getenv("CORS_ORIGINS", "*").split(",")]


settings = Settings()
