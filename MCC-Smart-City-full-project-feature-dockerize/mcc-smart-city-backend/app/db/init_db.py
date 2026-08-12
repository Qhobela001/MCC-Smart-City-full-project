from sqlalchemy import select

from app.core.config import settings
from app.core.security import get_password_hash
from app.db.base import Base
from app.db.session import SessionLocal, engine

from app.modules.ai_detections.models import AIDetection
from app.modules.alerts.models import Alert
from app.modules.assignments.models import (
    Assignment,
    AssignmentActivity,
    AssignmentEvidenceLink,
)
from app.modules.assignments.service import (
    backfill_existing_incident_assignments,
)
from app.modules.departments.models import Department
from app.modules.evidence.models import Evidence
from app.modules.incidents.models import (
    Incident,
    IncidentActivity,
)
from app.modules.navigation.models import NavigationItem
from app.modules.permissions.models import Permission
from app.modules.roles.models import Role
from app.modules.users.models import User


PERMISSIONS = [
    ("View Dashboard", "dashboard.view"),

    ("View Users", "users.view"),
    ("Create Users", "users.create"),
    ("Update Users", "users.update"),
    ("Reset User Passwords", "users.reset_password"),

    ("View Departments", "departments.view"),
    ("Create Departments", "departments.create"),
    ("Update Departments", "departments.update"),
    ("Delete Departments", "departments.delete"),

    ("View Roles", "roles.view"),
    ("Create Roles", "roles.create"),
    ("Update Roles", "roles.update"),
    ("View Permissions", "permissions.view"),

    ("View Navigation", "navigation.view"),
    ("Create Navigation", "navigation.create"),
    ("Update Navigation", "navigation.update"),

    ("View Cameras", "cameras.view"),
    ("Manage Cameras", "cameras.manage"),

    ("View Incidents", "incidents.view"),
    ("Create Incidents", "incidents.create"),
    ("Update Incidents", "incidents.update"),
    ("Assign Incidents", "incidents.assign"),
    ("Resolve Incidents", "incidents.resolve"),
    ("Dismiss Incidents", "incidents.dismiss"),

    ("View Evidence", "evidence.view"),
    ("Upload Evidence", "evidence.upload"),
    ("Delete Evidence", "evidence.delete"),

    ("View Alerts", "alerts.view"),

    (
        "View Department Assignments",
        "assignments.view_department",
    ),
    (
        "View All Assignments",
        "assignments.view_all",
    ),
    (
        "Create Assignments",
        "assignments.create",
    ),
    (
        "Manage Department Assignments",
        "assignments.manage_department",
    ),
    (
        "Manage All Assignments",
        "assignments.manage_all",
    ),
    (
        "Verify Assignment Completion",
        "assignments.verify",
    ),

    ("View AI Detections", "ai_detections.view"),
    ("Ingest AI Detections", "ai_detections.create"),
    ("Review AI Detections", "ai_detections.review"),

    ("View Reports", "reports.view"),
]


NAVIGATION_ITEMS = [
    (
        "Dashboard",
        "/dashboard",
        "LayoutDashboard",
        "Overview",
        1,
        "dashboard.view",
    ),
    (
        "Users",
        "/administration/users",
        "Users",
        "Administration",
        1,
        "users.view",
    ),
    (
        "Departments",
        "/administration/departments",
        "Building2",
        "Administration",
        2,
        "departments.view",
    ),
    (
        "Roles & Permissions",
        "/administration/roles",
        "ShieldCheck",
        "Administration",
        3,
        "roles.view",
    ),
    (
        "Navigation",
        "/administration/navigation",
        "PanelLeft",
        "Administration",
        4,
        "navigation.view",
    ),
    (
        "Live Monitoring",
        "/monitoring/live",
        "Cctv",
        "Operations",
        1,
        "cameras.view",
    ),
    (
        "Incidents",
        "/incidents",
        "TriangleAlert",
        "Operations",
        2,
        "incidents.view",
    ),
    (
        "Assignments",
        "/assignments",
        "ClipboardCheck",
        "Operations",
        3,
        "incidents.view",
    ),
    (
        "Reports",
        "/reports",
        "FileBarChart",
        "Analytics",
        1,
        "reports.view",
    ),
]


def init_db() -> None:
    # Importing all models above registers their tables
    # with Base.metadata before create_all executes.
    Base.metadata.create_all(bind=engine)

    with SessionLocal() as db:
        for name, code in PERMISSIONS:
            permission = db.scalar(
                select(Permission).where(
                    Permission.code == code
                )
            )

            if permission is None:
                db.add(
                    Permission(
                        name=name,
                        code=code,
                        description=name,
                        is_system=True,
                        is_active=True,
                    )
                )
            else:
                permission.name = name
                permission.description = name
                permission.is_system = True
                permission.is_active = True

        db.flush()

        role = db.scalar(
            select(Role).where(
                Role.name == "SuperAdmin"
            )
        )

        if role is None:
            role = Role(
                name="SuperAdmin",
                description=(
                    "System owner with unrestricted access"
                ),
                is_system=True,
                is_active=True,
            )
            db.add(role)
            db.flush()

        role.permissions = list(
            db.scalars(select(Permission)).all()
        )

        admin = db.scalar(
            select(User).where(
                User.email
                == settings.SUPERADMIN_EMAIL.lower()
            )
        )

        if admin is None:
            db.add(
                User(
                    full_name=settings.SUPERADMIN_NAME,
                    email=(
                        settings.SUPERADMIN_EMAIL.lower()
                    ),
                    hashed_password=get_password_hash(
                        settings.SUPERADMIN_PASSWORD
                    ),
                    role_id=role.id,
                    is_superuser=True,
                    is_active=True,
                    must_change_password=True,
                    status="active",
                )
            )

        for (
                label,
                href,
                icon,
                section,
                sort_order,
                permission_code,
        ) in NAVIGATION_ITEMS:
            item = db.scalar(
                select(NavigationItem).where(
                    NavigationItem.href == href
                )
            )

            if item is None:
                db.add(
                    NavigationItem(
                        label=label,
                        href=href,
                        icon=icon,
                        section=section,
                        sort_order=sort_order,
                        permission_code=permission_code,
                        is_system=True,
                        is_active=True,
                    )
                )

        backfill_existing_incident_assignments(db)

        db.commit()