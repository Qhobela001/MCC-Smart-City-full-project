from fastapi import APIRouter,Depends,HTTPException,Response
from sqlalchemy.orm import Session
from app.core.deps import get_db,require_permission
from app.modules.departments import repository,service
from app.modules.departments.models import Department
from app.modules.departments.schemas import *
router=APIRouter(prefix='/departments',tags=['Departments'])
@router.get('',response_model=list[DepartmentRead])
def all(db:Session=Depends(get_db),_=Depends(require_permission('departments.view'))): return repository.list_all(db)
@router.post('',response_model=DepartmentRead,status_code=201)
def create(p:DepartmentCreate,db:Session=Depends(get_db),_=Depends(require_permission('departments.create'))): service.ensure_unique(db,p.name,p.code); return repository.create(db,Department(**p.model_dump()))
@router.patch('/{id}',response_model=DepartmentRead)
def update(id:int,p:DepartmentUpdate,db:Session=Depends(get_db),_=Depends(require_permission('departments.update'))):
 o=repository.get(db,id)
 if not o: raise HTTPException(404,'Department not found')
 data=p.model_dump(exclude_unset=True); service.ensure_unique(db,data.get('name',o.name),data.get('code',o.code),id)
 for k,v in data.items(): setattr(o,k,v)
 db.commit();db.refresh(o);return o
@router.delete('/{id}',status_code=204)
def delete(id:int,db:Session=Depends(get_db),_=Depends(require_permission('departments.delete'))):
 o=repository.get(db,id)
 if not o: raise HTTPException(404,'Department not found')
 service.remove(db,o); return Response(status_code=204)
