from sqlalchemy import select
from app.modules.roles.models import Role
def list_all(db): return list(db.scalars(select(Role).order_by(Role.name)).unique().all())
def get(db,id): return db.get(Role,id)
def create(db,obj): db.add(obj); db.commit(); db.refresh(obj); return obj
