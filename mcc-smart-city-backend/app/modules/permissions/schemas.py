from datetime import datetime
from pydantic import BaseModel, ConfigDict

class PermissionCreate(BaseModel): name:str; code:str; description:str|None=None; is_active:bool=True
class PermissionUpdate(BaseModel): name:str|None=None; description:str|None=None; is_active:bool|None=None
class PermissionRead(PermissionCreate):
 id:int; is_system:bool=False; created_at:datetime
 model_config=ConfigDict(from_attributes=True)
