from sqlalchemy import select

from app.core.config import settings
from app.core.security import get_password_hash
from app.db.base import Base
from app.db.camera_stream_schema import ensure_camera_stream_schema
from app.db.gis_link_schema import ensure_gis_event_links
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
from app.modules.gis.models import (
    GISLocation,
    GISZone,
)
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
    (
        "Reset User Passwords",
        "users.reset_password",
    ),

    ("View Departments", "departments.view"),
    (
        "Create Departments",
        "departments.create",
    ),
    (
        "Update Departments",
        "departments.update",
    ),
    (
        "Delete Departments",
        "departments.delete",
    ),

    ("View Roles", "roles.view"),
    ("Create Roles", "roles.create"),
    ("Update Roles", "roles.update"),
    (
        "View Permissions",
        "permissions.view",
    ),

    (
        "View Navigation",
        "navigation.view",
    ),
    (
        "Create Navigation",
        "navigation.create",
    ),
    (
        "Update Navigation",
        "navigation.update",
    ),

    ("View Cameras", "cameras.view"),
    ("Manage Cameras", "cameras.manage"),

    ("View Incidents", "incidents.view"),
    (
        "Create Incidents",
        "incidents.create",
    ),
    (
        "Update Incidents",
        "incidents.update",
    ),
    (
        "Assign Incidents",
        "incidents.assign",
    ),
    (
        "Resolve Incidents",
        "incidents.resolve",
    ),
    (
        "Dismiss Incidents",
        "incidents.dismiss",
    ),

    ("View Evidence", "evidence.view"),
    (
        "Upload Evidence",
        "evidence.upload",
    ),
    (
        "Delete Evidence",
        "evidence.delete",
    ),

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

    (
        "View AI Detections",
        "ai_detections.view",
    ),
    (
        "Ingest AI Detections",
        "ai_detections.create",
    ),
    (
        "Review AI Detections",
        "ai_detections.review",
    ),

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
        "/live-feeds",
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
        "City Map",
        "/city-map",
        "MapPin",
        "Operations",
        4,
        "incidents.view",
    ),
    (
        "Camera & Devices",
        "/devices",
        "Network",
        "Operations",
        5,
        "cameras.view",
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
    # Model imports above register all tables.
    Base.metadata.create_all(bind=engine)

    # create_all does not alter already-existing tables.
    # Upgrade the existing Docker volume safely and idempotently.
    ensure_camera_stream_schema(engine)
    ensure_gis_event_links(engine)

    with SessionLocal() as db:
        for name, code in PERMISSIONS:
            permission = db.scalar(
                select(Permission).where(
                    Permission.code == code
                )
            )

            if permission is None:
                permission = Permission(
                    name=name,
                    code=code,
                    description=name,
                    is_system=True,
                    is_active=True,
                )
                db.add(permission)
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
            db.scalars(
                select(Permission)
            ).all()
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
                    full_name=(
                        settings.SUPERADMIN_NAME
                    ),
                    email=(
                        settings.SUPERADMIN_EMAIL.lower()
                    ),
                    hashed_password=(
                        get_password_hash(
                            settings.SUPERADMIN_PASSWORD
                        )
                    ),
                    role_id=role.id,
                    is_superuser=True,
                    is_active=True,
                    must_change_password=True,
                    status="active",
                )
            )

        # Normalize Live Monitoring navigation. Older development seeds used
        # /monitoring/live while the real Next.js route is /live-feeds. During
        # development both rows may already exist, so keep the oldest row as
        # the canonical item and deactivate every duplicate without deleting
        # rows that may already be referenced by role/navigation relationships.
        live_monitoring_rows = list(
            db.scalars(
                select(NavigationItem)
                .where(
                    (NavigationItem.label == "Live Monitoring")
                    | NavigationItem.href.in_(
                        ["/monitoring/live", "/live-feeds"]
                    )
                )
                .order_by(NavigationItem.id.asc())
            ).all()
        )

        if live_monitoring_rows:
            canonical_live_monitoring = live_monitoring_rows[0]
            canonical_live_monitoring.label = "Live Monitoring"
            canonical_live_monitoring.href = "/live-feeds"
            canonical_live_monitoring.icon = "Cctv"
            canonical_live_monitoring.section = "Operations"
            canonical_live_monitoring.sort_order = 1
            canonical_live_monitoring.permission_code = "cameras.view"
            canonical_live_monitoring.is_system = True
            canonical_live_monitoring.is_active = True

            for duplicate in live_monitoring_rows[1:]:
                duplicate.is_active = False

        for (
            label,
            href,
            icon,
            section,
            sort_order,
            permission_code,
        ) in NAVIGATION_ITEMS:
            item = db.scalar(
                select(NavigationItem)
                .where(NavigationItem.href == href)
                .order_by(
                    NavigationItem.is_active.desc(),
                    NavigationItem.id.asc(),
                )
            )

            if item is None:
                item = NavigationItem(
                    label=label,
                    href=href,
                    icon=icon,
                    section=section,
                    sort_order=sort_order,
                    permission_code=(
                        permission_code
                    ),
                    is_system=True,
                    is_active=True,
                )
                db.add(item)
            else:
                item.label = label
                item.icon = icon
                item.section = section
                item.sort_order = sort_order
                item.permission_code = (
                    permission_code
                )
                item.is_system = True
                item.is_active = True

        backfill_existing_incident_assignments(
            db
        )

        db.commit()
