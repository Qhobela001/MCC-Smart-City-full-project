import os
from types import SimpleNamespace

from dotenv import load_dotenv

load_dotenv()

settings = SimpleNamespace(
    APP_NAME=os.getenv("APP_NAME", "MCC Smart City API"),
    APP_ENV=os.getenv("APP_ENV", "development"),
    DEBUG=os.getenv("DEBUG", "true").lower() == "true",

    DATABASE_URL=os.getenv(
        "DATABASE_URL",
        "postgresql+psycopg://mcc_backend_user:mcc_backend_password@localhost:5432/mcc_smart_city",
    ),

    API_V1_STR=os.getenv("API_V1_STR", "/api/v1"),
    PROJECT_NAME=os.getenv("PROJECT_NAME", "MCC Smart City API"),

    FRONTEND_URL=os.getenv("FRONTEND_URL", "http://localhost:3000"),

    SECRET_KEY=os.getenv(
        "SECRET_KEY",
        "change-this-secret-in-production",
    ),
    JWT_ALGORITHM=os.getenv("JWT_ALGORITHM", "HS256"),
    ACCESS_TOKEN_EXPIRE_MINUTES=int(
        os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60")
    ),

    ALLOWED_ORIGINS=[
        origin.strip()
        for origin in os.getenv(
            "ALLOWED_ORIGINS",
            "http://localhost:3000,http://127.0.0.1:3000",
        ).split(",")
        if origin.strip()
    ],

    SUPERADMIN_EMAIL=os.getenv(
        "SUPERADMIN_EMAIL",
        "admin@mcc.org.ls",
    ),
    SUPERADMIN_PASSWORD=os.getenv(
        "SUPERADMIN_PASSWORD",
        "ChangeMe123!",
    ),
    SUPERADMIN_NAME=os.getenv(
        "SUPERADMIN_NAME",
        "MCC Super Administrator",
    ),
)