from pydantic import BaseModel, field_validator, model_validator

from app.modules.users.schemas import UserRead


class LoginRequest(BaseModel):
    identifier: str
    password: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserRead


class ForgotPasswordRequest(BaseModel):
    email: str

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        email = value.strip().lower()

        if not email or len(email) > 255 or "@" not in email:
            raise ValueError("Enter a valid email address")

        return email


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str
    confirm_password: str

    @field_validator("token")
    @classmethod
    def validate_token(cls, value: str) -> str:
        token = value.strip()

        if not token:
            raise ValueError("Reset token is required")

        return token

    @field_validator("new_password", "confirm_password")
    @classmethod
    def validate_password(cls, value: str) -> str:
        if len(value) < 12:
            raise ValueError(
                "Password must contain at least 12 characters"
            )

        if len(value) > 128:
            raise ValueError(
                "Password must contain no more than 128 characters"
            )

        return value

    @model_validator(mode="after")
    def passwords_must_match(self):
        if self.new_password != self.confirm_password:
            raise ValueError("Passwords do not match")

        return self


class AuthMessageResponse(BaseModel):
    message: str
