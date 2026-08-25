from fastapi import APIRouter,Depends,HTTPException
from sqlalchemy.orm import Session
from app.core.deps import get_db,require_permission,require_superadmin
from app.modules.permissions import repository
from app.modules.permissions.models import Permission
from app.modules.permissions.schemas import *
router=APIRouter(prefix='/permissions',tags=['Permissions'])
@router.get('',response_model=list[PermissionRead])
def all(db:Session=Depends(get_db),_=Depends(require_permission('permissions.view'))): return repository.list_all(db)
@router.post('',response_model=PermissionRead,status_code=201)
def create(p:PermissionCreate,db:Session=Depends(get_db),_=Depends(require_superadmin)):
 if any(x.code==p.code or x.name==p.name for x in repository.list_all(db)): raise HTTPException(409,'Permission already exists')
 return repository.create(db,Permission(**p.model_dump(),is_system=False))
@router.patch('/{id}',response_model=PermissionRead)
def update(id:int,p:PermissionUpdate,db:Session=Depends(get_db),_=Depends(require_superadmin)):
 o=repository.get(db,id)
 if not o: raise HTTPException(404,'Permission not found')
 for k,v in p.model_dump(exclude_unset=True).items(): setattr(o,k,v)
 db.commit();db.refresh(o);return o
