# MCC GIS & Zones — Phase 1

This bundle adds the first GIS data foundation to the MCC Smart City platform.

## Included

Backend:
- `gis_zones` table
- `gis_locations` table
- zone types and location types
- optional zone center coordinates
- optional zone polygon boundary stored as JSON coordinate points
- location-to-zone relationship
- authenticated GIS read APIs
- SuperAdmin-only GIS create/update/delete for Phase 1
- GIS summary endpoint

Frontend:
- full replacement for `/city-map`
- live summary cards
- Locations view
- Zones view
- create zone form
- create location form
- location-to-zone assignment
- delete test records
- coordinate/polygon coverage preview

No new frontend package is required.

## Why Phase 1 does not add PostGIS or Leaflet yet

The first goal is to verify the MCC geographic data structure and workflow before introducing geospatial database and map-library complexity.

The existing incident and AI-detection records already carry location text and coordinate snapshots. Phase 1 therefore adds canonical GIS records without modifying those existing tables.

After Phase 1 is verified, the next GIS integration can add:
- `gis_location_id` references to cameras, AI detections and incidents
- PostGIS geometry
- point-in-polygon geofencing
- OpenStreetMap/Leaflet or MapLibre basemap
- incident and AI-detection markers
- heatmaps and hotspot analytics

## Apply the files

Extract this ZIP into the project root:

```text
MCC-Smart-City-full-project-feature-dockerize
```

Allow the included paths to merge with the existing:

```text
mcc-smart-city-backend/
mcc-smart-city-frontend/
```

The bundle adds the GIS backend module and replaces only:
- `mcc-smart-city-backend/app/api/v1/router.py`
- `mcc-smart-city-frontend/app/(dashboard)/city-map/page.tsx`

## Build and verify backend

```powershell
docker compose build backend
docker compose up -d --force-recreate --no-deps backend
docker compose logs backend --tail=80
```

Check GIS routes:

```powershell
docker compose exec backend python -c "from app.main import app; print([p for p in app.openapi()['paths'] if '/gis/' in p])"
```

Expected paths include:

```text
/api/v1/gis/summary
/api/v1/gis/zones
/api/v1/gis/zones/{zone_id}
/api/v1/gis/locations
/api/v1/gis/locations/{location_id}
```

Check database tables:

```powershell
docker compose exec db psql -U postgres -d mcc_db -c "\dt gis_*"
```

Expected tables:

```text
gis_zones
gis_locations
```

## Build and verify frontend

```powershell
docker compose build frontend
docker compose up -d --force-recreate --no-deps frontend
docker compose logs frontend --tail=60
```

Open:

```text
http://localhost:3600/city-map
```

## Safe test

Create a temporary zone:

```text
Name: GIS Test Zone
Code: GIS-TEST-01
Type: Monitoring zone
Center latitude: -29.3158
Center longitude: 27.4869
```

Optional boundary:

```text
-29.312,27.482
-29.312,27.492
-29.321,27.492
-29.321,27.482
```

Then create a temporary location:

```text
Name: GIS Test Site
Code: LOC-TEST-01
Type: Camera site
Latitude: -29.3158
Longitude: 27.4869
Zone: GIS Test Zone
```

The coverage preview should show the polygon and location marker.

To clean up, delete the location first, then the zone.

## Phase 1 access policy

All authenticated MCC users can view GIS records.

Create/update/delete is restricted to the Super Administrator for now. This avoids inventing a municipal GIS-management role before MCC defines who should own geographic configuration.

After MCC confirms the access policy, dedicated permissions such as `gis.view` and `gis.manage` can be added to the existing RBAC system.
