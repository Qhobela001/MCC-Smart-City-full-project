from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.orm import Session

from app.core.deps import get_current_user, get_db
from app.modules.gis import service
from app.modules.gis.models import LocationType, ZoneType
from app.modules.gis.schemas import (
    GISLocationCreate,
    GISLocationListResponse,
    GISLocationRead,
    GISLocationUpdate,
    GISMapDataResponse,
    GISSummaryResponse,
    GISZoneCreate,
    GISZoneListResponse,
    GISZoneRead,
    GISZoneUpdate,
)
from app.modules.users.models import User


router = APIRouter(prefix="/gis", tags=["GIS & Zones"])


@router.get("/summary", response_model=GISSummaryResponse)
def get_gis_summary(
    db: Session = Depends(get_db),
    actor: User = Depends(get_current_user),
) -> GISSummaryResponse:
    return service.get_summary(db, actor)


@router.get("/map-data", response_model=GISMapDataResponse)
def get_map_data(
    db: Session = Depends(get_db),
    actor: User = Depends(get_current_user),
) -> GISMapDataResponse:
    return service.get_map_data(
        db,
        actor,
    )


@router.get("/zones", response_model=GISZoneListResponse)
def list_zones(
    active_only: bool = False,
    search: str | None = Query(default=None, max_length=100),
    zone_type: ZoneType | None = None,
    db: Session = Depends(get_db),
    actor: User = Depends(get_current_user),
) -> GISZoneListResponse:
    return service.list_zones(
        db,
        active_only=active_only,
        search=search,
        zone_type=zone_type,
    )


@router.post(
    "/zones",
    response_model=GISZoneRead,
    status_code=status.HTTP_201_CREATED,
)
def create_zone(
    payload: GISZoneCreate,
    db: Session = Depends(get_db),
    actor: User = Depends(get_current_user),
) -> GISZoneRead:
    return service.create_zone(db, payload, actor)


@router.get("/zones/{zone_id}", response_model=GISZoneRead)
def get_zone(
    zone_id: int,
    db: Session = Depends(get_db),
    actor: User = Depends(get_current_user),
) -> GISZoneRead:
    return service.zone_to_read(service.get_zone_or_404(db, zone_id))


@router.patch("/zones/{zone_id}", response_model=GISZoneRead)
def update_zone(
    zone_id: int,
    payload: GISZoneUpdate,
    db: Session = Depends(get_db),
    actor: User = Depends(get_current_user),
) -> GISZoneRead:
    return service.update_zone(db, zone_id, payload, actor)


@router.delete("/zones/{zone_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_zone(
    zone_id: int,
    db: Session = Depends(get_db),
    actor: User = Depends(get_current_user),
) -> Response:
    service.delete_zone(db, zone_id, actor)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/locations", response_model=GISLocationListResponse)
def list_locations(
    active_only: bool = False,
    search: str | None = Query(default=None, max_length=100),
    location_type: LocationType | None = None,
    zone_id: int | None = None,
    db: Session = Depends(get_db),
    actor: User = Depends(get_current_user),
) -> GISLocationListResponse:
    return service.list_locations(
        db,
        active_only=active_only,
        search=search,
        location_type=location_type,
        zone_id=zone_id,
    )


@router.post(
    "/locations",
    response_model=GISLocationRead,
    status_code=status.HTTP_201_CREATED,
)
def create_location(
    payload: GISLocationCreate,
    db: Session = Depends(get_db),
    actor: User = Depends(get_current_user),
) -> GISLocationRead:
    return service.create_location(db, payload, actor)


@router.get("/locations/{location_id}", response_model=GISLocationRead)
def get_location(
    location_id: int,
    db: Session = Depends(get_db),
    actor: User = Depends(get_current_user),
) -> GISLocationRead:
    return service.location_to_read(
        service.get_location_or_404(db, location_id)
    )


@router.patch("/locations/{location_id}", response_model=GISLocationRead)
def update_location(
    location_id: int,
    payload: GISLocationUpdate,
    db: Session = Depends(get_db),
    actor: User = Depends(get_current_user),
) -> GISLocationRead:
    return service.update_location(db, location_id, payload, actor)


@router.delete(
    "/locations/{location_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_location(
    location_id: int,
    db: Session = Depends(get_db),
    actor: User = Depends(get_current_user),
) -> Response:
    service.delete_location(db, location_id, actor)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
