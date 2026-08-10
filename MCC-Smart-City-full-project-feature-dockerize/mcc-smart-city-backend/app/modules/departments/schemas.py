from datetime import datetime
from pydantic import BaseModel, ConfigDict

class DepartmentBase(BaseModel): name:str; code:str; description:str|None=None; is_active:bool=True
class DepartmentCreate(DepartmentBase): pass
class DepartmentUpdate(BaseModel): name:str|None=None; code:str|None=None; description:str|None=None; is_active:bool|None=None
class DepartmentRead(DepartmentBase):
 id:int; created_at:datetime; updated_at:datetime
 model_config=ConfigDict(from_attributes=True)
