"""
Automatic physical-to-digital camera context integration.

The existing AI detection API already accepts ``camera_identifier`` and GIS
fields. This listener enriches a NEW detection from the authoritative Camera
Registry immediately before SQLAlchemy inserts it.

Important snapshot rule:
- Camera/GIS context is resolved only on INSERT.
- Historical detections are never re-geocoded when they are later reviewed or
  otherwise updated. This preserves the event-time location snapshot.

Transition behavior:
- If a camera identifier is registered and active, its GIS location wins.
- If the identifier is not registered yet, the existing detection workflow is
  left unchanged so current tests remain backward-compatible.
"""

from sqlalchemy import event, select

from app.modules.ai_detections.models import AIDetection
from app.modules.cameras.models import Camera
from app.modules.cameras.service import normalize_identifier
from app.modules.gis.models import GISLocation


def resolve_camera_context(connection, camera_identifier: str | None):
    if not camera_identifier:
        return None

    normalized = normalize_identifier(
        camera_identifier,
        http_error=False,
    )
    if not normalized:
        return None

    statement = (
        select(
            Camera.id.label("camera_id"),
            Camera.camera_identifier,
            Camera.gis_location_id,
            GISLocation.name.label("location_name"),
            GISLocation.latitude,
            GISLocation.longitude,
        )
        .outerjoin(
            GISLocation,
            GISLocation.id == Camera.gis_location_id,
        )
        .where(
            Camera.camera_identifier == normalized,
            Camera.is_active.is_(True),
            Camera.status != "retired",
        )
    )

    return connection.execute(statement).mappings().first()


@event.listens_for(AIDetection, "before_insert")
def apply_registered_camera_context(
    mapper,
    connection,
    target: AIDetection,
) -> None:
    context = resolve_camera_context(
        connection,
        target.camera_identifier,
    )
    if context is None:
        return

    target.camera_identifier = context["camera_identifier"]

    if context["gis_location_id"] is None:
        return

    target.gis_location_id = context["gis_location_id"]
    target.location_name = context["location_name"]
    target.latitude = context["latitude"]
    target.longitude = context["longitude"]
