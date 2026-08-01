from fastapi import HTTPException
from sqlalchemy.orm import Session
from app.core.security import create_access_token, verify_password
from app.modules.authentication.repository import find_by_identifier
from app.modules.users.models import UserStatus
def authenticate(db:Session,identifier:str,password:str):
 user=find_by_identifier(db,identifier)
 if not user or not verify_password(password,user.hashed_password): raise HTTPException(status_code=401,detail='Invalid login credentials')
 if not user.is_active or user.status!=UserStatus.active: raise HTTPException(status_code=403,detail='User account is not active')
 return create_access_token({'sub':str(user.id),'user_id':user.id}),user
