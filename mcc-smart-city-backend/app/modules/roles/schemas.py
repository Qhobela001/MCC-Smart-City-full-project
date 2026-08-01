from datetime import datetime
from pydantic import BaseModel, ConfigDict

from app.modules.permissions.schemas import PermissionRead
class RoleCreate(BaseModel): name:str; description:str|None=None; is_active:bool=True; permission_ids:list[int]=[]
class RoleUpdate(BaseModel): name:str|None=None; description:str|None=None; is_active:bool|None=None; permission_ids:list[int]|None=None
class RoleRead(BaseModel):
 id:int; name:str; description:str|None; is_system:bool; is_active:bool; permissions:list[PermissionRead]=[]; created_at:datetime; updated_at:datetime
 model_config=ConfigDict(from_attributes=True)
