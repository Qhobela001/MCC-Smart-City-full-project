# MCC Live Monitoring — integration package

This package turns `/live-feeds` into an API-backed control-room camera wall and adds a dedicated camera viewer.

## Architecture implemented

Camera RTSP reaches MCC HQ through the NanoStation wireless bridge. MediaMTX becomes the HQ stream gateway and pulls each configured camera once. Jetson/YOLO and authorized live viewers can consume the gateway stream independently. FastAPI controls camera metadata, stream registration and short-lived viewer authorization; FastAPI does not proxy video frames.

## Files

Backend:
- `app/modules/live_streams/__init__.py`
- `app/modules/live_streams/schemas.py`
- `app/modules/live_streams/service.py`
- `app/modules/live_streams/router.py`
- full replacement `app/api/v1/router.py`

Frontend:
- full replacement `app/(dashboard)/live-feeds/page.tsx`
- new `app/(dashboard)/live-feeds/[cameraIdentifier]/page.tsx`
- new `components/live-monitoring/types.ts`
- new `components/live-monitoring/webrtc-player.tsx`
- new `components/live-monitoring/live-camera-tile.tsx`
- full replacement `components/dashboard/top-bar.tsx` based on the mobile-sidebar-fixed version, with Live Monitoring title support.

Infrastructure:
- `mediamtx.yml`
- `docker-compose.live-monitoring.yml`

## Camera registry requirements

A camera can appear in Live Monitoring immediately, but live video starts only when it has:
- active camera record
- IP address
- RTSP path
- RTSP/RTSPS protocol
- stream not disabled

If the camera requires authentication, set `credential_reference` to an environment-variable name such as `MCC_CAM_001_RTSP_AUTH`, then set that variable in the backend environment to `username:password`. Raw passwords are never returned to the browser.

## Start command

Use the existing compose file plus the additive live-monitoring override:

```powershell
docker compose -f docker-compose.yml -f docker-compose.live-monitoring.yml up -d --build
```

For the current local browser at `http://localhost:3600`, the default public WebRTC URL is `http://localhost:8889`.

For another MCC control-room computer, set `MEDIAMTX_WEBRTC_PUBLIC_URL` to the HQ host IP/DNS address and add that same reachable host to `webrtcAdditionalHosts` and the frontend origin to `webrtcAllowOrigins` in `mediamtx.yml`.

## Stream synchronization

Opening a camera automatically registers/refreshes its MediaMTX path. For continuous Jetson processing after a MediaMTX restart, an authorized camera manager can call:

`POST /api/v1/live-streams/sync`

This registers all active, configured camera streams with the gateway. The gateway is configured with `sourceOnDemand: false`, so one upstream camera pull can remain available for Jetson and viewer consumers.

## Current MCC-CAM-001 behavior before hardware configuration

The registered camera will appear in the wall, but it should correctly show `Stream not configured` until its real IP address and RTSP path are entered in Camera & Device Management.
