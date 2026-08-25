from datetime import datetime
from pydantic import BaseModel, ConfigDict

class NavigationCreate(BaseModel): label:str; href:str; icon:str='LayoutDashboard'; section:str='Workspace'; sort_order:int=0; permission_code:str|None=None; is_active:bool=True
class NavigationUpdate(BaseModel): label:str|None=None; href:str|None=None; icon:str|None=None; section:str|None=None; sort_order:int|None=None; permission_code:str|None=None; is_active:bool|None=None
class NavigationRead(NavigationCreate):
 id:int; is_system:bool=False; created_at:datetime
 model_config=ConfigDict(from_attributes=True)
