from fastapi import HTTPException
from sqlalchemy import select
from app.modules.permissions.models import Permission
def permissions_by_ids(db,ids):
 values=list(db.scalars(select(Permission).where(Permission.id.in_(ids))).all()) if ids else []
 if len(values)!=len(set(ids)): raise HTTPException(400,'One or more permission IDs are invalid')
 return values
