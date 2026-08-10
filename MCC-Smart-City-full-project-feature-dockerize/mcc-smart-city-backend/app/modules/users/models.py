import enum
from sqlalchemy import Boolean, Column, DateTime, Enum, ForeignKey, Integer, String
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.base import Base
class UserStatus(str,enum.Enum): active='active'; suspended='suspended'; deactivated='deactivated'
class User(Base):
 __tablename__='users'
 id=Column(Integer,primary_key=True,index=True); full_name=Column(String(150),nullable=False); employee_number=Column(String(50),unique=True,index=True)
 email=Column(String(255),unique=True,nullable=False,index=True); phone_number=Column(String(30),unique=True,index=True); hashed_password=Column(String(255),nullable=False)
 department_id=Column(Integer,ForeignKey('departments.id'),nullable=True,index=True); role_id=Column(Integer,ForeignKey('roles.id'),nullable=True,index=True)
 status=Column(Enum(UserStatus,name='user_status'),default=UserStatus.active,nullable=False); is_active=Column(Boolean,default=True,nullable=False)
 is_superuser=Column(Boolean,default=False,nullable=False); must_change_password=Column(Boolean,default=True,nullable=False)
 created_at=Column(DateTime(timezone=True),server_default=func.now(),nullable=False); updated_at=Column(DateTime(timezone=True),server_default=func.now(),onupdate=func.now(),nullable=False)
 department=relationship('Department',back_populates='users',lazy='joined'); role=relationship('Role',back_populates='users',lazy='joined')
