from pydantic import BaseModel
from app.modules.users.schemas import UserRead
class LoginRequest(BaseModel): identifier:str; password:str
class LoginResponse(BaseModel): access_token:str; token_type:str='bearer'; user:UserRead
