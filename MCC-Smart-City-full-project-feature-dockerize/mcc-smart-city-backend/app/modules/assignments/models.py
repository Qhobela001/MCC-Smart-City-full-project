import enum

from sqlalchemy import Column, DateTime, Enum, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db.base import Base


class AssignmentStatus(str, enum.Enum):
    pending = "pending"
    accepted = "accepted"
    in_progress = "in_progress"
    submitted = "submitted"
    completed = "completed"
    rejected = "rejected"
    cancelled = "cancelled"


class Assignment(Base):
    __tablename__ = "assignments"

    id = Column(Integer, primary_key=True, index=True)
    assignment_number = Column(String(40), unique=True, nullable=False, index=True)

    incident_id = Column(Integer, ForeignKey("incidents.id", ondelete="CASCADE"), nullable=False, index=True)
    department_id = Column(Integer, ForeignKey("departments.id"), nullable=False, index=True)
    assigned_user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    assigned_by_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    title = Column(String(200), nullable=False)
    instructions = Column(Text, nullable=True)
    priority = Column(String(20), nullable=False, default="medium")
    status = Column(Enum(AssignmentStatus, name="assignment_status"), nullable=False, default=AssignmentStatus.pending, index=True)

    due_at = Column(DateTime(timezone=True), nullable=True)
    accepted_at = Column(DateTime(timezone=True), nullable=True)
    started_at = Column(DateTime(timezone=True), nullable=True)
    submitted_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    cancelled_at = Column(DateTime(timezone=True), nullable=True)

    completion_notes = Column(Text, nullable=True)
    verification_notes = Column(Text, nullable=True)
    rejection_reason = Column(Text, nullable=True)
    cancellation_reason = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    incident = relationship("Incident", lazy="joined")
    department = relationship("Department", lazy="joined")
    assigned_user = relationship("User", foreign_keys=[assigned_user_id], lazy="joined")
    assigned_by = relationship("User", foreign_keys=[assigned_by_id], lazy="joined")

    activities = relationship("AssignmentActivity", back_populates="assignment", cascade="all, delete-orphan", order_by="AssignmentActivity.created_at")
    evidence_links = relationship("AssignmentEvidenceLink", back_populates="assignment", cascade="all, delete-orphan")


class AssignmentActivity(Base):
    __tablename__ = "assignment_activities"

    id = Column(Integer, primary_key=True, index=True)
    assignment_id = Column(Integer, ForeignKey("assignments.id", ondelete="CASCADE"), nullable=False, index=True)
    actor_user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    action = Column(String(80), nullable=False, index=True)
    previous_status = Column(Enum(AssignmentStatus, name="assignment_activity_previous_status"), nullable=True)
    new_status = Column(Enum(AssignmentStatus, name="assignment_activity_new_status"), nullable=True)
    notes = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    assignment = relationship("Assignment", back_populates="activities")
    actor = relationship("User", lazy="joined")


class AssignmentEvidenceLink(Base):
    __tablename__ = "assignment_evidence_links"
    __table_args__ = (UniqueConstraint("assignment_id", "evidence_id", name="uq_assignment_evidence"),)

    id = Column(Integer, primary_key=True, index=True)
    assignment_id = Column(Integer, ForeignKey("assignments.id", ondelete="CASCADE"), nullable=False, index=True)
    evidence_id = Column(Integer, ForeignKey("evidence.id", ondelete="CASCADE"), nullable=False, index=True)
    added_by_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    assignment = relationship("Assignment", back_populates="evidence_links")
    evidence = relationship("Evidence", lazy="joined")
    added_by = relationship("User", lazy="joined")
