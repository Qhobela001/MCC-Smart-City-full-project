from __future__ import annotations

import base64
import hashlib
import os

from cryptography.fernet import Fernet, InvalidToken
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.cameras.models import Camera, CameraCredential


VAULT_PREFIX = "vault:camera:"
ENV_PREFIX = "env:"


class CredentialVaultError(RuntimeError):
    pass


class CredentialVaultConfigurationError(CredentialVaultError):
    pass


class CredentialVaultDecryptionError(CredentialVaultError):
    pass


class CredentialReferenceError(CredentialVaultError):
    pass


def vault_reference(camera_id: int) -> str:
    return f"{VAULT_PREFIX}{camera_id}"


def credential_source(reference: str | None) -> str:
    normalized = (reference or "").strip()
    if not normalized:
        return "none"
    if normalized.lower().startswith(VAULT_PREFIX):
        return "vault"
    if normalized.lower().startswith(ENV_PREFIX):
        return "environment"
    # Historical MCC rows sometimes stored the environment variable name
    # without the "env:" prefix. Keep this as legacy environment fallback.
    return "environment"


def _fernet() -> Fernet:
    master_secret = os.getenv("CAMERA_CREDENTIAL_MASTER_KEY", "").strip()
    if not master_secret:
        raise CredentialVaultConfigurationError(
            "CAMERA_CREDENTIAL_MASTER_KEY is not configured on the backend."
        )

    # The deployment key can be any high-entropy secret. Derive the exact
    # 32-byte Fernet key format deterministically without storing a second key.
    digest = hashlib.sha256(master_secret.encode("utf-8")).digest()
    return Fernet(base64.urlsafe_b64encode(digest))


def _credential_row(
    db: Session,
    camera_id: int,
) -> CameraCredential | None:
    return db.scalar(
        select(CameraCredential).where(
            CameraCredential.camera_id == camera_id
        )
    )


def _environment_credentials(
    camera: Camera,
) -> tuple[str, str]:
    reference = (camera.credential_reference or "").strip()
    if not reference:
        raise CredentialReferenceError(
            "Camera credential reference is not configured."
        )
    if reference.lower().startswith(VAULT_PREFIX):
        raise CredentialReferenceError(
            "Camera already uses the encrypted credential vault."
        )

    if reference.lower().startswith(ENV_PREFIX):
        reference = reference[len(ENV_PREFIX):].strip()

    if not reference:
        raise CredentialReferenceError(
            "Camera credential reference is invalid."
        )

    secret_value = os.getenv(reference)
    if not secret_value:
        raise CredentialReferenceError(
            "Camera credentials are not available in the legacy server environment."
        )
    if ":" not in secret_value:
        raise CredentialReferenceError(
            "Legacy camera credentials are invalid on the server."
        )

    username, password = secret_value.split(":", 1)
    username = username.strip()
    if not username or not password:
        raise CredentialReferenceError(
            "Legacy camera credentials are invalid on the server."
        )
    return username, password


def upsert_credentials(
    db: Session,
    camera: Camera,
    *,
    username: str,
    password: str,
    actor_id: int | None,
) -> CameraCredential:
    username = username.strip()
    if not username:
        raise CredentialReferenceError(
            "Camera credential username cannot be empty."
        )
    if not password:
        raise CredentialReferenceError(
            "Camera credential password cannot be empty."
        )

    encrypted_password = _fernet().encrypt(
        password.encode("utf-8")
    ).decode("ascii")

    row = _credential_row(db, camera.id)
    if row is None:
        row = CameraCredential(
            camera_id=camera.id,
            username=username,
            encrypted_password=encrypted_password,
            encryption_scheme="fernet-sha256-v1",
            created_by_id=actor_id,
            updated_by_id=actor_id,
        )
        db.add(row)
    else:
        row.username = username
        row.encrypted_password = encrypted_password
        row.encryption_scheme = "fernet-sha256-v1"
        row.updated_by_id = actor_id
        db.add(row)

    camera.credential_reference = vault_reference(camera.id)
    db.add(camera)
    db.flush()
    return row


def resolve_credentials(
    db: Session,
    camera: Camera,
) -> tuple[str, str] | None:
    source = credential_source(camera.credential_reference)

    if source == "none":
        return None

    if source == "environment":
        return _environment_credentials(camera)

    row = _credential_row(db, camera.id)
    if row is None:
        raise CredentialReferenceError(
            "Encrypted camera credential record is missing."
        )
    if row.encryption_scheme != "fernet-sha256-v1":
        raise CredentialReferenceError(
            "Camera credential encryption scheme is unsupported."
        )

    try:
        password = _fernet().decrypt(
            row.encrypted_password.encode("ascii")
        ).decode("utf-8")
    except (InvalidToken, ValueError, UnicodeDecodeError) as exc:
        raise CredentialVaultDecryptionError(
            "Encrypted camera credentials could not be decrypted."
        ) from exc

    return row.username, password


def migrate_environment_credentials(
    db: Session,
    camera: Camera,
    *,
    actor_id: int | None,
) -> bool:
    source = credential_source(camera.credential_reference)
    if source == "vault":
        return False
    if source != "environment":
        raise CredentialReferenceError(
            "Camera does not have a legacy environment credential to migrate."
        )

    username, password = _environment_credentials(camera)
    upsert_credentials(
        db,
        camera,
        username=username,
        password=password,
        actor_id=actor_id,
    )
    return True
