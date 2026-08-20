Fix: the previous 'Gateway ready' KPI incorrectly counted camera MediaMTX paths.
The gateway itself was already online. This replacement separates:
- Live paths ready: number of camera paths currently ready in MediaMTX
- Gateway ready: 1 when the MediaMTX Control API is reachable, otherwise 0
