from fastapi import APIRouter,Depends
from sqlalchemy.orm import Session
from app.core.deps import get_current_user,get_db
from app.modules.authentication.schemas import LoginRequest,LoginResponse
from app.modules.authentication.service import authenticate
from app.modules.users.schemas import UserRead
router=APIRouter(prefix='/auth',tags=['Authentication'])
@router.post('/login',response_model=LoginResponse)
def login(payload:LoginRequest,db:Session=Depends(get_db)):
 token,user=authenticate(db,payload.identifier,payload.password); return LoginResponse(access_token=token,user=user)
@router.get('/me',response_model=UserRead)
def me(user=Depends(get_current_user)): return user
