from sqlalchemy import select
from sqlalchemy.orm import Session
from app.modules.departments.models import Department
def list_all(db): return list(db.scalars(select(Department).order_by(Department.name)).all())
def get(db,id): return db.get(Department,id)
def create(db,obj): db.add(obj); db.commit(); db.refresh(obj); return obj
def delete(db,obj): db.delete(obj); db.commit()
