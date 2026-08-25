from fastapi import APIRouter,Depends,HTTPException
from sqlalchemy.orm import Session
from app.core.deps import get_current_user,get_db,require_permission
from app.modules.navigation import repository,service
from app.modules.navigation.models import NavigationItem
from app.modules.navigation.schemas import *
router=APIRouter(prefix='/navigation',tags=['Navigation'])
@router.get('/me',response_model=list[NavigationRead])
def mine(db:Session=Depends(get_db),user=Depends(get_current_user)): return service.for_user(db,user)
@router.get('',response_model=list[NavigationRead])
def all(db:Session=Depends(get_db),_=Depends(require_permission('navigation.view'))): return repository.list_all(db)
@router.post('',response_model=NavigationRead,status_code=201)
def create(p:NavigationCreate,db:Session=Depends(get_db),_=Depends(require_permission('navigation.create'))): return repository.create(db,NavigationItem(**p.model_dump()))
@router.patch('/{id}',response_model=NavigationRead)
def update(id:int,p:NavigationUpdate,db:Session=Depends(get_db),_=Depends(require_permission('navigation.update'))):
 o=repository.get(db,id)
 if not o: raise HTTPException(404,'Navigation item not found')
 for k,v in p.model_dump(exclude_unset=True).items(): setattr(o,k,v)
 db.commit();db.refresh(o);return o
