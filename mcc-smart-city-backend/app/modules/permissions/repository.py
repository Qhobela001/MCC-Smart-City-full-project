from sqlalchemy import select
from app.modules.permissions.models import Permission
def list_all(db): return list(db.scalars(select(Permission).order_by(Permission.code)).all())
def get(db,id): return db.get(Permission,id)
def create(db,obj): db.add(obj); db.commit(); db.refresh(obj); return obj
