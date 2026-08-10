// Mock data for the MCC (Maseru City Council) Command Center prototype.
// All values are illustrative and intended for client demonstration only.

export type CameraStatus = "online" | "offline" | "degraded"

export const kpis = [
  { label: "Active Alerts", value: "6", delta: "+2", trend: "up", tone: "critical" as const, href: "/incidents" },
  { label: "Cameras Online", value: "4 / 6", delta: "-1", trend: "down", tone: "default" as const, href: "/devices" },
  { label: "Incidents Today", value: "73", delta: "+11%", trend: "up", tone: "default" as const, href: "/incidents" },
  { label: "Avg Alert Latency", value: "3.4s", delta: "Within SLA", trend: "flat", tone: "good" as const, href: "/devices" },
]

export interface Camera {
  id: string
  name: string
  zone: string
  status: CameraStatus
  feed: string
  // approximate map position as a percentage of the map container
  x: number
  y: number
  signal: number // wireless link quality %
}

export const cameras: Camera[] = [
  {
    id: "CAM-014",
    name: "Kingsway Intersection",
    zone: "CBD",
    status: "online",
    feed: "/feeds/feed-intersection.png",
    x: 42,
    y: 38,
    signal: 96,
  },
  {
    id: "CAM-021",
    name: "Pitso Ground Market",
    zone: "Sea Point",
    status: "online",
    feed: "/feeds/feed-market.png",
    x: 64,
    y: 55,
    signal: 88,
  },
  {
    id: "CAM-007",
    name: "Main North Road",
    zone: "Maseru West",
    status: "degraded",
    feed: "/feeds/feed-road.png",
    x: 28,
    y: 62,
    signal: 54,
  },
  {
    id: "CAM-033",
    name: "Lakeside Vacant Lot",
    zone: "Thetsane",
    status: "online",
    feed: "/feeds/feed-dumpsite.png",
    x: 74,
    y: 30,
    signal: 79,
  },
  {
    id: "CAM-009",
    name: "Cathedral Circle",
    zone: "CBD",
    status: "offline",
    feed: "/feeds/feed-intersection.png",
    x: 52,
    y: 22,
    signal: 0,
  },
  {
    id: "CAM-028",
    name: "Industrial Area Gate",
    zone: "Thetsane",
    status: "online",
    feed: "/feeds/feed-road.png",
    x: 18,
    y: 40,
    signal: 91,
  },
]

export type AlertSeverity = "critical" | "warning" | "info"
export type AlertStatus = "new" | "acknowledged" | "dispatched"

export interface Incident {
  id: string
  type: string
  camera: string
  location: string
  severity: AlertSeverity
  status: AlertStatus
  detectedAgo: string
  confidence: number
}

export const incidents: Incident[] = [
  {
    id: "INC-4821",
    type: "Illegal Dumping",
    camera: "CAM-033",
    location: "Lakeside Vacant Lot, Thetsane",
    severity: "critical",
    status: "new",
    detectedAgo: "12s ago",
    confidence: 94,
  },
  {
    id: "INC-4820",
    type: "Pothole / Road Damage",
    camera: "CAM-007",
    location: "Main North Road, Maseru West",
    severity: "warning",
    status: "new",
    detectedAgo: "1m ago",
    confidence: 87,
  },
  {
    id: "INC-4819",
    type: "Excessive Vehicle Smoke",
    camera: "CAM-014",
    location: "Kingsway Intersection, CBD",
    severity: "warning",
    status: "acknowledged",
    detectedAgo: "4m ago",
    confidence: 76,
  },
  {
    id: "INC-4817",
    type: "Public Urination",
    camera: "CAM-021",
    location: "Pitso Ground Market, Sea Point",
    severity: "info",
    status: "dispatched",
    detectedAgo: "9m ago",
    confidence: 81,
  },
  {
    id: "INC-4814",
    type: "Noise Disturbance",
    camera: "CAM-028",
    location: "Industrial Area Gate, Thetsane",
    severity: "info",
    status: "dispatched",
    detectedAgo: "17m ago",
    confidence: 69,
  },
  {
    id: "INC-4811",
    type: "Illegal Dumping",
    camera: "CAM-033",
    location: "Lakeside Vacant Lot, Thetsane",
    severity: "critical",
    status: "acknowledged",
    detectedAgo: "22m ago",
    confidence: 92,
  },
]

// 12-hour incident volume by category (for the analytics trend chart)
export const incidentTrend = [
  { hour: "06:00", dumping: 2, road: 1, smoke: 0, noise: 1 },
  { hour: "07:00", dumping: 3, road: 2, smoke: 1, noise: 0 },
  { hour: "08:00", dumping: 5, road: 4, smoke: 3, noise: 2 },
  { hour: "09:00", dumping: 4, road: 3, smoke: 2, noise: 1 },
  { hour: "10:00", dumping: 6, road: 2, smoke: 4, noise: 3 },
  { hour: "11:00", dumping: 8, road: 5, smoke: 3, noise: 2 },
  { hour: "12:00", dumping: 7, road: 4, smoke: 5, noise: 4 },
  { hour: "13:00", dumping: 9, road: 6, smoke: 4, noise: 3 },
  { hour: "14:00", dumping: 6, road: 3, smoke: 2, noise: 2 },
  { hour: "15:00", dumping: 5, road: 4, smoke: 3, noise: 1 },
  { hour: "16:00", dumping: 7, road: 5, smoke: 4, noise: 3 },
  { hour: "17:00", dumping: 4, road: 2, smoke: 2, noise: 2 },
]

// Average AI alert latency (seconds) — REQ-NFR-1 target is < 5s
export const responseLatency = [
  { day: "Mon", latency: 3.2 },
  { day: "Tue", latency: 2.8 },
  { day: "Wed", latency: 4.1 },
  { day: "Thu", latency: 3.6 },
  { day: "Fri", latency: 2.9 },
  { day: "Sat", latency: 4.4 },
  { day: "Sun", latency: 3.1 },
]

// Weekly sanitation team performance (incidents resolved)
export const teamPerformance = [
  { team: "Cleaning A", resolved: 42 },
  { team: "Cleaning B", resolved: 31 },
  { team: "Roads", resolved: 27 },
  { team: "Enforcement", resolved: 19 },
]

export interface EdgeDevice {
  id: string
  name: string
  type: string
  status: CameraStatus
  metric: string
  load: number
}

export const edgeDevices: EdgeDevice[] = [
  {
    id: "EDGE-01",
    name: "Jetson Orin Nano — CBD",
    type: "AI Inference",
    status: "online",
    metric: "Inference 28ms",
    load: 62,
  },
  {
    id: "EDGE-02",
    name: "Jetson Orin Nano — West",
    type: "AI Inference",
    status: "degraded",
    metric: "Inference 71ms",
    load: 88,
  },
  {
    id: "NET-01",
    name: "NanoStation 5GHz Uplink",
    type: "Wireless Link",
    status: "online",
    metric: "412 Mbps",
    load: 44,
  },
  {
    id: "STG-01",
    name: "HQ Storage Server",
    type: "Footage Archive",
    status: "online",
    metric: "18.4 / 32 TB",
    load: 58,
  },
]
// Current weather over Maseru (illustrative — swap for a live API later)
export const weather = {
  location: "Maseru, LS",
  condition: "Partly cloudy",
  temperatureC: 21,
  precipitationPct: 15, // chance of precipitation
  windKph: 12,
}

export type SystemHealth = "operational" | "degraded" | "critical"

// Derive overall system health from cameras and edge devices.
// - critical (red): anything offline
// - degraded (yellow): anything degraded but nothing offline
// - operational (green): everything online
export function getSystemHealth(): {
  level: SystemHealth
  online: number
  degraded: number
  offline: number
  total: number
} {
  const nodes = [
    ...cameras.map((c) => c.status),
    ...edgeDevices.map((d) => d.status),
  ]
  const offline = nodes.filter((s) => s === "offline").length
  const degraded = nodes.filter((s) => s === "degraded").length
  const online = nodes.filter((s) => s === "online").length
  const level: SystemHealth =
      offline > 0 ? "critical" : degraded > 0 ? "degraded" : "operational"
  return { level, online, degraded, offline, total: nodes.length }
}

