from sqlalchemy import select
from app.core.deps import user_has_permission
from app.modules.navigation.models import NavigationItem
def for_user(db,user):
 items=list(db.scalars(select(NavigationItem).where(NavigationItem.is_active.is_(True)).order_by(NavigationItem.section,NavigationItem.sort_order)).all())
 return [i for i in items if i.permission_code is None or user_has_permission(user,i.permission_code)]
