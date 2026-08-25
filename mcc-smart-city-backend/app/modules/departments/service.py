from fastapi import HTTPException
from sqlalchemy import select
from app.modules.departments.models import Department
from app.modules.users.models import User
def ensure_unique(db,name,code,exclude=None):
 q=select(Department).where((Department.name==name)|(Department.code==code))
 for x in db.scalars(q):
  if x.id!=exclude: raise HTTPException(409,'Department name or code already exists')
def remove(db,obj):
 if db.scalar(select(User).where(User.department_id==obj.id)): raise HTTPException(409,'Department has assigned users; deactivate it instead')
 db.delete(obj); db.commit()
