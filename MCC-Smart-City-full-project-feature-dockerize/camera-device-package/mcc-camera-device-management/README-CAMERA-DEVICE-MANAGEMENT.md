# MCC Camera & Device Management — Physical-to-Digital Registry

This bundle replaces the empty backend `cameras` / `devices` modules and the
mock-backed `/devices` frontend page with the real infrastructure registry.

## Architecture

Registered camera identifier -> Camera Registry -> GIS Location -> AI Detection
-> Incident Engine -> Dashboard / City Map.

The backend also registers NanoStations, Jetson nodes, network and future power
telemetry devices.

## Important design decisions

- Camera and generic infrastructure device data are separate tables.
- No RTSP password is stored in `rtsp_path`.
- All authenticated users can read operational status.
- Network/credential-sensitive fields are hidden from non-SuperAdmin users.
- Only SuperAdmin can create/update/retire infrastructure in this first version.
- Heartbeat writes are SuperAdmin-only until machine/service authentication is
  added during hardware integration.
- Existing AI detection service/repository code is not replaced.
- A SQLAlchemy listener enriches detections from registered camera GIS context.
- Unknown/unregistered camera identifiers keep the existing behavior during the
  transition, so old tests are not broken.

## Files

Backend:
- `app/modules/cameras/__init__.py`
- `app/modules/cameras/models.py`
- `app/modules/cameras/schemas.py`
- `app/modules/cameras/repository.py`
- `app/modules/cameras/service.py`
- `app/modules/cameras/integration.py`
- `app/modules/cameras/router.py`
- `app/modules/devices/__init__.py`
- `app/modules/devices/models.py`
- `app/modules/devices/schemas.py`
- `app/modules/devices/repository.py`
- `app/modules/devices/service.py`
- `app/modules/devices/router.py`
- `app/api/v1/router.py`

Frontend:
- `app/(dashboard)/devices/page.tsx`

No `init_db.py` replacement is required. Importing the camera/device routers
registers both models before the application's existing `Base.metadata.create_all`
startup logic runs.

## Expected PostgreSQL tables after backend restart

- `cameras`
- `infrastructure_devices`

Existing GIS, AI detection and incident tables remain untouched.

## Validation sequence on the real project

```powershell
docker compose build backend frontend
docker compose up -d --force-recreate backend frontend
docker compose ps
```

Check OpenAPI route registration:

```powershell
docker compose exec backend python -c "from app.main import app; p=app.openapi()['paths']; print([x for x in p if '/cameras' in x or '/devices' in x])"
```

Check DB tables:

```powershell
docker compose exec db psql -U postgres -d mcc_db -c "\dt cameras"
docker compose exec db psql -U postgres -d mcc_db -c "\dt infrastructure_devices"
```

Then use the frontend `/devices` page to register:
1. `MCC-NS-FIELD-001` — NanoStation / field_radio
2. `MCC-JETSON-001` — Jetson / hq_ai
3. `MCC-CAM-001` — camera mapped to an existing GIS location and assigned to the two devices

Finally POST one AI detection with:
- `camera_identifier = MCC-CAM-001`
- no `gis_location_id`
- no `location_name`
- no latitude/longitude

The new listener should populate GIS context from the camera registry before the
existing Incident Engine processes the detection.

## Security note

Do not store camera passwords in `rtsp_path`. For today's hardware integration,
we will handle the camera credentials on the Jetson/runtime side first, then add
machine/service authentication and a proper secret-management strategy.

## Pre-delivery verification performed

The generated backend and frontend files were checked before packaging:

- Python compilation completed successfully for all generated backend files.
- Camera/device registry integration test passed using SQLAlchemy against a
  temporary database.
- Registered camera identifier -> GIS auto-resolution for AI detections passed.
- Batch-style ORM inserts also received registered camera GIS context.
- Historical detection GIS snapshot protection passed: later camera movement
  does not rewrite an existing detection when that detection is updated.
- Duplicate active use of one field NanoStation by two cameras is rejected.
- Camera/field-NanoStation GIS mismatch is rejected when both are mapped.
- Invalid RTSP paths containing embedded credentials are rejected.
- Non-SuperAdmin mutation is rejected.
- Sensitive network/credential fields are redacted for ordinary authenticated
  viewers.
- Active camera/device heartbeats update health state; retired cameras reject
  heartbeat resurrection.
- Referenced infrastructure cannot be retired while an active camera depends
  on it.
- Frontend page passed a strict TypeScript contract/syntax harness.
- Frontend/backend route contract checks passed and the page contains no
  `mock-data` import.

The final acceptance test must still be run inside the real MCC Docker project
because only the inspection snapshot, not the complete current repository, was
available to the generator. Use the commands below immediately after applying
these files; we should not proceed to hardware integration until they pass.

## Safe PowerShell application

Extract this ZIP into a temporary folder beside the project, for example
`camera-device-package`, then from the MCC project root run:

```powershell
Copy-Item -Recurse -Force ".\camera-device-package\mcc-smart-city-backend\app\modules\cameras\*" ".\mcc-smart-city-backend\app\modules\cameras\"
Copy-Item -Recurse -Force ".\camera-device-package\mcc-smart-city-backend\app\modules\devices\*" ".\mcc-smart-city-backend\app\modules\devices\"
Copy-Item -Force ".\camera-device-package\mcc-smart-city-backend\app\api\v1\router.py" ".\mcc-smart-city-backend\app\api\v1\router.py"
Copy-Item -Force ".\camera-device-package\mcc-smart-city-frontend\app\(dashboard)\devices\page.tsx" ".\mcc-smart-city-frontend\app\(dashboard)\devices\page.tsx"
```

Do not copy `camera-device-current-state.txt` into the application; it remains
only a local inspection artifact.

## Project-level acceptance gate

Run:

```powershell
docker compose build backend frontend
docker compose up -d --force-recreate backend frontend
docker compose ps
```

Then verify imports, route registration and table creation:

```powershell
docker compose exec backend python -c "from app.main import app; p=app.openapi()['paths']; print([x for x in p if '/cameras' in x or '/devices' in x])"
docker compose exec db psql -U postgres -d mcc_db -c "\dt cameras"
docker compose exec db psql -U postgres -d mcc_db -c "\dt infrastructure_devices"
```

Expected route families include `/api/v1/cameras` and `/api/v1/devices` and the
expected PostgreSQL tables are `cameras` and `infrastructure_devices`.
