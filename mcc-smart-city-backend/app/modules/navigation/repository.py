from sqlalchemy import select
from app.modules.navigation.models import NavigationItem
def list_all(db): return list(db.scalars(select(NavigationItem).order_by(NavigationItem.section,NavigationItem.sort_order)).all())
def get(db,id): return db.get(NavigationItem,id)
def create(db,obj): db.add(obj); db.commit(); db.refresh(obj); return obj
