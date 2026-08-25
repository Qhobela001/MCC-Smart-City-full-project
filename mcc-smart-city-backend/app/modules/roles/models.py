from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Table
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.base import Base
role_permissions=Table('role_permissions',Base.metadata,
 Column('role_id',Integer,ForeignKey('roles.id',ondelete='CASCADE'),primary_key=True),
 Column('permission_id',Integer,ForeignKey('permissions.id',ondelete='CASCADE'),primary_key=True))
class Role(Base):
 __tablename__='roles'
 id=Column(Integer,primary_key=True,index=True); name=Column(String(100),unique=True,nullable=False,index=True)
 description=Column(String(255)); is_system=Column(Boolean,default=False,nullable=False); is_active=Column(Boolean,default=True,nullable=False)
 created_at=Column(DateTime(timezone=True),server_default=func.now(),nullable=False); updated_at=Column(DateTime(timezone=True),server_default=func.now(),onupdate=func.now(),nullable=False)
 users=relationship('User',back_populates='role'); permissions=relationship('Permission',secondary=role_permissions,back_populates='roles',lazy='selectin')
