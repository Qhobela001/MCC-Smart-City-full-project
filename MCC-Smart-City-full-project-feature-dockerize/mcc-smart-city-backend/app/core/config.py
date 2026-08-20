import os
from types import SimpleNamespace

from dotenv import load_dotenv


load_dotenv()


def _env_bool(
    name: str,
    default: str,
) -> bool:
    return os.getenv(name, default).lower() == "true"


settings = SimpleNamespace(
    APP_NAME=os.getenv("APP_NAME", "MCC Smart City API"),
    APP_ENV=os.getenv("APP_ENV", "development"),
    DEBUG=_env_bool("DEBUG", "true"),

    DATABASE_URL=os.getenv(
        "DATABASE_URL",
        "postgresql+psycopg://mcc_backend_user:mcc_backend_password@localhost:5432/mcc_smart_city",
    ),

    API_V1_STR=os.getenv("API_V1_STR", "/api/v1"),
    PROJECT_NAME=os.getenv("PROJECT_NAME", "MCC Smart City API"),

    FRONTEND_URL=os.getenv(
        "FRONTEND_URL",
        "http://localhost:3000",
    ),

    SECRET_KEY=os.getenv(
        "SECRET_KEY",
        "change-this-secret-in-production",
    ),
    CAMERA_CREDENTIAL_MASTER_KEY=os.getenv(
        "CAMERA_CREDENTIAL_MASTER_KEY",
        "",
    ).strip(),
    JWT_ALGORITHM=os.getenv("JWT_ALGORITHM", "HS256"),
    ACCESS_TOKEN_EXPIRE_MINUTES=int(
        os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60")
    ),

    PASSWORD_RESET_TOKEN_EXPIRE_MINUTES=int(
        os.getenv(
            "PASSWORD_RESET_TOKEN_EXPIRE_MINUTES",
            "15",
        )
    ),
    PASSWORD_RESET_FRONTEND_URL=os.getenv(
        "PASSWORD_RESET_FRONTEND_URL",
        "http://localhost:3600",
    ),

    SMTP_HOST=os.getenv("SMTP_HOST", "").strip(),
    SMTP_PORT=int(os.getenv("SMTP_PORT", "587")),
    SMTP_USERNAME=os.getenv("SMTP_USERNAME", "").strip(),
    SMTP_PASSWORD=os.getenv("SMTP_PASSWORD", ""),
    SMTP_FROM_EMAIL=os.getenv(
        "SMTP_FROM_EMAIL",
        "no-reply@mcc.org.ls",
    ).strip(),
    SMTP_FROM_NAME=os.getenv(
        "SMTP_FROM_NAME",
        "MCC Command Center",
    ).strip(),
    SMTP_USE_TLS=_env_bool("SMTP_USE_TLS", "true"),
    SMTP_USE_SSL=_env_bool("SMTP_USE_SSL", "false"),
    SMTP_TIMEOUT_SECONDS=int(
        os.getenv("SMTP_TIMEOUT_SECONDS", "15")
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
