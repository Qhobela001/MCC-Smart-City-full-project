# Validation report

Static validation performed on the generated integration package:

- Python files compile successfully with `py_compile`.
- TypeScript/TSX files parse successfully with the TypeScript compiler parser.
- The API router imports and registers `live_streams_router`.
- No camera RTSP credentials are returned in the Live Monitoring response schemas.
- The viewer uses a short-lived stream-scoped HMAC token rather than exposing the user's MCC application JWT to MediaMTX.
- MediaMTX Control API port 9997 is not published by the compose override.
- Actual RTSP/WebRTC video cannot be acceptance-tested until a physical camera has an IP address, RTSP path and compatible stream codec configured.
