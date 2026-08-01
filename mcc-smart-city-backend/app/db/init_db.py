from sqlalchemy import select
from app.core.config import settings
from app.core.security import get_password_hash
from app.db.base import Base
from app.db.session import SessionLocal,engine
from app.modules.departments.models import Department
from app.modules.navigation.models import NavigationItem
from app.modules.permissions.models import Permission
from app.modules.roles.models import Role
from app.modules.users.models import User
PERMISSIONS=[
('View Dashboard','dashboard.view'),('View Users','users.view'),('Create Users','users.create'),('Update Users','users.update'),('Reset User Passwords','users.reset_password'),
('View Departments','departments.view'),('Create Departments','departments.create'),('Update Departments','departments.update'),('Delete Departments','departments.delete'),
('View Roles','roles.view'),('Create Roles','roles.create'),('Update Roles','roles.update'),('View Permissions','permissions.view'),
('View Navigation','navigation.view'),('Create Navigation','navigation.create'),('Update Navigation','navigation.update'),
('View Cameras','cameras.view'),('Manage Cameras','cameras.manage'),('View Incidents','incidents.view'),('Assign Incidents','incidents.assign'),('Resolve Incidents','incidents.resolve'),('View Reports','reports.view')]
NAV=[('Dashboard','/dashboard','LayoutDashboard','Overview',1,'dashboard.view'),('Users','/administration/users','Users','Administration',1,'users.view'),('Departments','/administration/departments','Building2','Administration',2,'departments.view'),('Roles & Permissions','/administration/roles','ShieldCheck','Administration',3,'roles.view'),('Navigation','/administration/navigation','PanelLeft','Administration',4,'navigation.view'),('Live Monitoring','/monitoring/live','Cctv','Operations',1,'cameras.view'),('Incidents','/incidents','TriangleAlert','Operations',2,'incidents.view'),('Reports','/reports','FileBarChart','Analytics',1,'reports.view')]
def init_db():
 Base.metadata.create_all(bind=engine)
 with SessionLocal() as db:
  for name,code in PERMISSIONS:
   if not db.scalar(select(Permission).where(Permission.code==code)): db.add(Permission(name=name,code=code,description=name,is_system=True,is_active=True))
  db.flush()
  role=db.scalar(select(Role).where(Role.name=='SuperAdmin'))
  if not role: role=Role(name='SuperAdmin',description='System owner with unrestricted access',is_system=True,is_active=True);db.add(role);db.flush()
  role.permissions=list(db.scalars(select(Permission)).all())
  admin=db.scalar(select(User).where(User.email==settings.SUPERADMIN_EMAIL.lower()))
  if not admin: db.add(User(full_name=settings.SUPERADMIN_NAME,email=settings.SUPERADMIN_EMAIL.lower(),hashed_password=get_password_hash(settings.SUPERADMIN_PASSWORD),role_id=role.id,is_superuser=True,is_active=True,must_change_password=True,status='active'))
  for label,href,icon,section,order,permission in NAV:
   if not db.scalar(select(NavigationItem).where(NavigationItem.href==href)): db.add(NavigationItem(label=label,href=href,icon=icon,section=section,sort_order=order,permission_code=permission,is_system=True,is_active=True))
  db.commit()
