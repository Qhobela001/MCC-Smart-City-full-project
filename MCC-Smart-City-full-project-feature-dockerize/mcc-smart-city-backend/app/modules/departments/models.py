from sqlalchemy import Boolean, Column, DateTime, Integer, String
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.base import Base
class Department(Base):
 __tablename__='departments'
 id=Column(Integer,primary_key=True,index=True); name=Column(String(150),unique=True,nullable=False,index=True); code=Column(String(30),unique=True,nullable=False,index=True)
 description=Column(String(255)); is_active=Column(Boolean,default=True,nullable=False)
 created_at=Column(DateTime(timezone=True),server_default=func.now(),nullable=False); updated_at=Column(DateTime(timezone=True),server_default=func.now(),onupdate=func.now(),nullable=False)
 users=relationship('User',back_populates='department')
