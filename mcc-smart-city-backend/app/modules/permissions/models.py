from sqlalchemy import Boolean, Column, DateTime, Integer, String
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.base import Base
from app.modules.roles.models import role_permissions
class Permission(Base):
 __tablename__='permissions'
 id=Column(Integer,primary_key=True,index=True); name=Column(String(150),unique=True,nullable=False,index=True); code=Column(String(150),unique=True,nullable=False,index=True)
 description=Column(String(255)); is_active=Column(Boolean,default=True,nullable=False); is_system=Column(Boolean,default=False,nullable=False)
 created_at=Column(DateTime(timezone=True),server_default=func.now(),nullable=False)
 roles=relationship('Role',secondary=role_permissions,back_populates='permissions')
