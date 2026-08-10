from fastapi import APIRouter,Depends,HTTPException
from sqlalchemy.orm import Session
from app.core.deps import get_db,require_permission
from app.modules.roles import repository,service
from app.modules.roles.models import Role
from app.modules.roles.schemas import *
router=APIRouter(prefix='/roles',tags=['Roles'])
@router.get('',response_model=list[RoleRead])
def all(db:Session=Depends(get_db),_=Depends(require_permission('roles.view'))): return repository.list_all(db)
@router.post('',response_model=RoleRead,status_code=201)
def create(p:RoleCreate,db:Session=Depends(get_db),_=Depends(require_permission('roles.create'))):
 if any(x.name.lower()==p.name.lower() for x in repository.list_all(db)): raise HTTPException(409,'Role already exists')
 data=p.model_dump(exclude={'permission_ids'}); o=Role(**data,is_system=False); o.permissions=service.permissions_by_ids(db,p.permission_ids); return repository.create(db,o)
@router.patch('/{id}',response_model=RoleRead)
def update(id:int,p:RoleUpdate,db:Session=Depends(get_db),_=Depends(require_permission('roles.update'))):
 o=repository.get(db,id)
 if not o: raise HTTPException(404,'Role not found')
 data=p.model_dump(exclude_unset=True); ids=data.pop('permission_ids',None)
 for k,v in data.items(): setattr(o,k,v)
 if ids is not None: o.permissions=service.permissions_by_ids(db,ids)
 db.commit();db.refresh(o);return o
