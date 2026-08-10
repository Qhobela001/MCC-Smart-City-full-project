from sqlalchemy import Boolean, Column, DateTime, Integer, String
from sqlalchemy.sql import func
from app.db.base import Base
class NavigationItem(Base):
 __tablename__='navigation_items'
 id=Column(Integer,primary_key=True,index=True); label=Column(String(100),nullable=False); href=Column(String(200),nullable=False); icon=Column(String(100),default='LayoutDashboard',nullable=False)
 section=Column(String(100),default='Workspace',nullable=False); sort_order=Column(Integer,default=0,nullable=False); permission_code=Column(String(150),nullable=True,index=True)
 is_active=Column(Boolean,default=True,nullable=False); is_system=Column(Boolean,default=False,nullable=False); created_at=Column(DateTime(timezone=True),server_default=func.now(),nullable=False)
