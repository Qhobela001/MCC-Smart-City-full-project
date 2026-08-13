# MCC GIS & Zones — Phase 2
## Structured GIS links for AI detections, incidents and the City Map

This phase connects the GIS foundation already verified in Phase 1 to the working AI Detection → Incident Engine chain.

## Resulting flow

```text
GIS Zone
   ↓
GIS Location
   ↓
AI Detection (gis_location_id)
   ↓
Incident Engine
   ↓
Incident (same gis_location_id)
   ↓
GIS / City Map
```

The existing `location_name`, `latitude`, and `longitude` fields remain in both event tables as event-time snapshots.

## Important design choice

This bundle intentionally does **not** replace:

- `app/modules/ai_detections/service.py`
- `app/modules/incident_engine/service.py`
- `app/modules/incident_engine/repository.py`

Those files contain the already-tested detection-to-incident orchestration and deduplication logic.

Instead:
- AI Detection repository resolves a supplied `gis_location_id` into the canonical GIS name/coordinates before creating the ORM record.
- PostgreSQL maintains snapshot integrity.
- A small database trigger propagates `gis_location_id` to the incident when the existing incident engine links a detection to an incident.
- The trigger only fills an incident GIS link when the incident does not already have one; it does not silently overwrite a different incident location.

## Files in this bundle

```text
mcc-smart-city-backend/
└── app/
    ├── db/
    │   ├── gis_link_schema.py
    │   └── init_db.py
    └── modules/
        ├── ai_detections/
        │   ├── models.py
        │   ├── schemas.py
        │   └── repository.py
        ├── incidents/
        │   ├── models.py
        │   └── schemas.py
        └── gis/
            ├── schemas.py
            ├── repository.py
            ├── service.py
            └── router.py

mcc-smart-city-frontend/
└── app/
    └── (dashboard)/
        └── city-map/
            └── page.tsx
```

## Existing database upgrade

`Base.metadata.create_all()` cannot add columns to existing PostgreSQL tables.

For that reason `app/db/gis_link_schema.py` performs a small idempotent upgrade after `create_all()`:

- adds `ai_detections.gis_location_id`
- adds `incidents.gis_location_id`
- adds indexes
- adds `ON DELETE SET NULL` foreign keys
- conservatively backfills exact existing location matches
- snapshots GIS name/coordinates when a structured GIS link is assigned
- propagates the detection GIS link to an incident created/linked by the existing incident engine

It is safe to run again during later backend startups.

## Apply

Extract into the project root and allow replacement of the included files.

```powershell
Expand-Archive `
"$HOME\Downloads\mcc-gis-phase2-linking-full-files.zip" `
-DestinationPath "." `
-Force
```

## Backend build

```powershell
docker compose build backend
```

```powershell
docker compose up -d --force-recreate --no-deps backend
```

```powershell
docker compose logs backend --since=2m --tail=120
```

The backend must show a clean application startup.

## Verify database columns

```powershell
docker compose exec db psql -U postgres -d mcc_db -c "\d ai_detections"
```

You should see:

```text
gis_location_id | integer
```

Then:

```powershell
docker compose exec db psql -U postgres -d mcc_db -c "\d incidents"
```

You should also see:

```text
gis_location_id | integer
```

## Verify GIS map-data API registration

```powershell
docker compose exec backend python -c "from app.main import app; print([p for p in app.openapi()['paths'] if '/gis/' in p])"
```

You should now also see:

```text
/api/v1/gis/map-data
```

## Verify your GIS location ID

```powershell
docker compose exec db psql -U postgres -d mcc_db -c "SELECT id, name, code, latitude, longitude, zone_id, is_active FROM gis_locations ORDER BY id;"
```

Use one active location ID for the end-to-end test.

## End-to-end Swagger test

Open:

```text
http://localhost:8000/docs
```

Authorize as SuperAdmin.

POST:

```text
/api/v1/ai-detections
```

Use a new UUID every time. Example, assuming your GIS location ID is `1`:

```json
{
  "detection_uuid": "44444444-4444-4444-8444-444444444444",
  "detection_type": "illegal_dumping",
  "class_name": "illegal_dumping",
  "confidence": 0.94,
  "detected_at": "2026-08-13T14:15:00+02:00",
  "source_type": "camera",
  "camera_identifier": "GIS-CAM-TEST",
  "stream_identifier": "GIS-STREAM-TEST",
  "model_name": "mcc_illegal_dumping",
  "model_version": "1.0",
  "gis_location_id": 1,
  "snapshot_path": null,
  "clip_path": null,
  "object_count": 1,
  "attributes": {
    "simulation": true
  },
  "incident_id": null,
  "is_test": false
}
```

You do not need to send `location_name`, `latitude`, or `longitude` when `gis_location_id` is supplied. The backend resolves the snapshot from `gis_locations`.

## Verify detection → incident GIS propagation

Replace the UUID if you changed it:

```powershell
docker compose exec db psql -U postgres -d mcc_db -c "SELECT id, detection_uuid, gis_location_id, location_name, latitude, longitude, incident_id FROM ai_detections WHERE detection_uuid = '44444444-4444-4444-8444-444444444444';"
```

The expected result is:
- `gis_location_id` equals the GIS location used in the request
- name/latitude/longitude are filled automatically
- `incident_id` is populated by the existing incident engine

Then:

```powershell
docker compose exec db psql -U postgres -d mcc_db -c "SELECT i.id, i.incident_number, i.incident_type, i.gis_location_id, i.location_name, i.latitude, i.longitude FROM incidents i JOIN ai_detections d ON d.incident_id = i.id WHERE d.detection_uuid = '44444444-4444-4444-8444-444444444444';"
```

The incident should carry the same `gis_location_id`.

## Verify map API

In Swagger call:

```text
GET /api/v1/gis/map-data
```

The response should include the new incident under `incidents` and the new detection under `ai_detections`.

## Frontend build

```powershell
docker compose build frontend
```

```powershell
docker compose up -d --force-recreate --no-deps frontend
```

Open:

```text
http://localhost:3600/city-map
```

The map now has layers for:

- GIS Locations
- Incidents
- AI Detections
- Zone polygons

Visual markers:

```text
Blue dot      = GIS location
Red triangle  = Incident
Amber ring    = AI detection
Polygon       = GIS zone
```

The summary cards also show:
- active locations
- active zones
- mapped incidents
- mapped non-test AI detections

## What is deliberately next, not part of this phase

The camera/device module will later make the field flow even cleaner:

```text
camera_identifier
      ↓
registered camera
      ↓
gis_location_id
```

Then the Jetson will not need to decide a location itself; the backend will resolve the registered camera to its GIS site automatically.

PostGIS and an OpenStreetMap/MapLibre/Leaflet basemap remain later rendering/geofencing upgrades.
