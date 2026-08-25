from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.modules.departments.schemas import DepartmentRead
from app.modules.roles.schemas import RoleRead
from app.modules.users.models import UserStatus


class UserCreate(BaseModel):
    full_name: str = Field(min_length=2, max_length=150)
    employee_number: str | None = Field(default=None, max_length=50)
    email: str = Field(min_length=3, max_length=255)
    phone_number: str | None = Field(default=None, max_length=30)
    department_id: int | None = None
    role_id: int | None = None
    temporary_password: str = Field(min_length=8)
    status: UserStatus = UserStatus.active
    is_superuser: bool = False


class UserUpdate(BaseModel):
    full_name: str | None = Field(default=None, min_length=2, max_length=150)
    employee_number: str | None = Field(default=None, max_length=50)
    email: str | None = Field(default=None, min_length=3, max_length=255)
    phone_number: str | None = Field(default=None, max_length=30)
    department_id: int | None = None
    role_id: int | None = None
    status: UserStatus | None = None
    is_active: bool | None = None


class PasswordChange(BaseModel):
    current_password: str
    new_password: str = Field(min_length=8)


class PasswordResetByAdmin(BaseModel):
    new_temporary_password: str = Field(min_length=8)


class UserRead(BaseModel):
    id: int
    full_name: str
    employee_number: str | None
    email: str
    phone_number: str | None
    department_id: int | None
    role_id: int | None
    status: UserStatus
    is_active: bool
    is_superuser: bool
    must_change_password: bool
    department: DepartmentRead | None = None
    role: RoleRead | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
