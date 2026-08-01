from collections.abc import Callable, Generator
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session
from app.core.security import decode_access_token
from app.db.session import SessionLocal
from app.modules.users.models import User, UserStatus
security=HTTPBearer()
def get_db()->Generator[Session,None,None]:
 db=SessionLocal()
 try: yield db
 finally: db.close()
def get_current_user(credentials:HTTPAuthorizationCredentials=Depends(security),db:Session=Depends(get_db))->User:
 payload=decode_access_token(credentials.credentials)
 if not payload or not payload.get('sub'): raise HTTPException(status_code=401,detail='Invalid or expired token')
 user=db.get(User,int(payload['sub']))
 if not user: raise HTTPException(status_code=401,detail='User not found')
 if not user.is_active or user.status!=UserStatus.active: raise HTTPException(status_code=403,detail='User account is not active')
 return user
def require_superadmin(current_user:User=Depends(get_current_user))->User:
 if not current_user.is_superuser: raise HTTPException(status_code=403,detail='SuperAdmin access required')
 return current_user
def user_has_permission(user:User,code:str)->bool:
 return bool(user.is_superuser or (user.role and user.role.is_active and any(p.code==code and p.is_active for p in user.role.permissions)))
def require_permission(code:str)->Callable:
 def dependency(current_user:User=Depends(get_current_user))->User:
  if not user_has_permission(current_user,code): raise HTTPException(status_code=403,detail=f'Permission required: {code}')
  return current_user
 return dependency
