"use client"

import {
  useEffect,
  useMemo,
  useState,
  type ChangeEvent,
  type FormEvent,
  type ReactNode,
} from "react"
import {
  Activity,
  Camera as CameraIcon,
  Cpu,
  MapPin,
  Network,
  Pencil,
  Plus,
  Power,
  Radio,
  RefreshCw,
  Search,
  Wifi,
  X,
} from "lucide-react"

import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent } from "@/components/ui/card"
import { apiFetch } from "@/lib/api"
import { cn } from "@/lib/utils"

type DeviceType =
  | "nanostation"
  | "jetson"
  | "network_switch"
  | "server"
  | "solar_controller"
  | "battery_monitor"
  | "sensor"
  | "other"

type DeviceRole =
  | "field_radio"
  | "hq_radio"
  | "edge_ai"
  | "hq_ai"
  | "network"
  | "power"
  | "sensor"
  | "other"

type DeviceStatus =
  | "planned"
  | "configured"
  | "online"
  | "degraded"
  | "offline"
  | "maintenance"
  | "retired"

type StreamStatus =
  | "unconfigured"
  | "unknown"
  | "online"
  | "degraded"
  | "offline"
  | "disabled"

type StreamProtocol = "rtsp" | "v380"

type LocationSummary = {
  id: number
  name: string
  code: string
  latitude: number
  longitude: number
  zone_id: number | null
}

type DeviceSummary = {
  id: number
  device_identifier: string
  name: string
  device_type: DeviceType
  role: DeviceRole
  status: DeviceStatus
  gis_location_id: number | null
}

type InfrastructureDevice = {
  id: number
  device_identifier: string
  name: string
  description: string | null
  device_type: DeviceType
  role: DeviceRole
  gis_location_id: number | null
  location: LocationSummary | null
  parent_device_id: number | null
  parent_device: DeviceSummary | null
  ip_address: string | null
  mac_address: string | null
  hostname: string | null
  manufacturer: string | null
  model: string | null
  serial_number: string | null
  configuration: Record<string, unknown>
  health_metrics: Record<string, unknown>
  status: DeviceStatus
  is_active: boolean
  installed_at: string | null
  last_seen_at: string | null
  created_at: string
  updated_at: string
}

type Camera = {
  id: number
  camera_identifier: string
  name: string
  description: string | null
  gis_location_id: number | null
  location: LocationSummary | null
  assigned_jetson_id: number | null
  assigned_jetson: DeviceSummary | null
  field_nanostation_id: number | null
  field_nanostation: DeviceSummary | null
  ip_address: string | null
  mac_address: string | null
  manufacturer: string | null
  model: string | null
  serial_number: string | null
  http_port: number | null
  rtsp_port: number | null
  rtsp_path: string | null
  onvif_port: number | null
  v380_port: number | null
  v380_device_id: number | null
  stream_protocol: StreamProtocol
  credential_reference: string | null
  credential_configured: boolean
  credential_source: string | null
  ai_enabled: boolean
  ai_profile: Record<string, unknown>
  status: DeviceStatus
  stream_status: StreamStatus
  is_active: boolean
  installed_at: string | null
  last_seen_at: string | null
  last_stream_check_at: string | null
  created_at: string
  updated_at: string
}

type CameraListResponse = {
  items: Camera[]
  total: number
  page: number
  page_size: number
  pages: number
  can_manage: boolean
}

type DeviceListResponse = {
  items: InfrastructureDevice[]
  total: number
  page: number
  page_size: number
  pages: number
  can_manage: boolean
}

type CameraSummaryResponse = {
  total_cameras: number
  active_cameras: number
  online_cameras: number
  degraded_cameras: number
  offline_cameras: number
  ai_enabled_cameras: number
  mapped_cameras: number
  stream_online_cameras: number
  can_manage: boolean
}

type DeviceSummaryResponse = {
  total_devices: number
  active_devices: number
  online_devices: number
  degraded_devices: number
  offline_devices: number
  type_counts: Record<string, number>
  status_counts: Record<string, number>
  can_manage: boolean
}

type DeviceOption = {
  id: number
  device_identifier: string
  name: string
  device_type: string
  role: string
  status: string
  gis_location_id: number | null
}

type CameraConnectionTestResponse = {
  success: boolean
  outcome: string
  login_result: number | null
  message: string
}

type CameraOptionsResponse = {
  locations: LocationSummary[]
  jetsons: DeviceOption[]
  nanostations: DeviceOption[]
  can_manage: boolean
}

type CameraGatewayWorkerHealth = {
  camera_identifier: string
  status: "online" | "degraded" | "offline"
  phase: string
  seconds_since_last_frame: number | null
  failure_code: string | null
  failure_message: string | null
  failure_at: string | null
  consecutive_failures: number
  retry_seconds: number | null
}

type CameraGatewayHealth = {
  available: boolean
  status: "online" | "degraded" | "offline"
  started_at: string | null
  uptime_seconds: number | null
  registry_connected: boolean
  registered_cameras: number
  last_registry_sync_at: string | null
  poll_seconds: number | null
  workers_total: number
  workers_alive: number
  workers_online: number
  workers_degraded: number
  workers_offline: number
  failure_code: string | null
  failure_message: string | null
  failure_at: string | null
  workers: CameraGatewayWorkerHealth[]
  observed_at: string | null
  generated_at: string
}

type Tab = "overview" | "cameras" | "devices"

const DEVICE_TYPES: DeviceType[] = [
  "nanostation",
  "jetson",
  "network_switch",
  "server",
  "solar_controller",
  "battery_monitor",
  "sensor",
  "other",
]

const DEVICE_ROLES: DeviceRole[] = [
  "field_radio",
  "hq_radio",
  "edge_ai",
  "hq_ai",
  "network",
  "power",
  "sensor",
  "other",
]

const DEVICE_STATUSES: DeviceStatus[] = [
  "planned",
  "configured",
  "online",
  "degraded",
  "offline",
  "maintenance",
  "retired",
]

const STREAM_STATUSES: StreamStatus[] = [
  "unconfigured",
  "unknown",
  "online",
  "degraded",
  "offline",
  "disabled",
]

const inputClass =
  "h-9 w-full rounded-md border border-input bg-background px-3 text-sm outline-none ring-offset-background focus:ring-2 focus:ring-ring"

export default function DevicesPage() {
  const [tab, setTab] = useState<Tab>("overview")
  const [cameraSummary, setCameraSummary] =
    useState<CameraSummaryResponse | null>(null)
  const [deviceSummary, setDeviceSummary] =
    useState<DeviceSummaryResponse | null>(null)
  const [cameras, setCameras] = useState<Camera[]>([])
  const [devices, setDevices] = useState<InfrastructureDevice[]>([])
  const [options, setOptions] = useState<CameraOptionsResponse | null>(null)
  const [gatewayHealth, setGatewayHealth] =
    useState<CameraGatewayHealth | null>(null)
  const [selectedCameraId, setSelectedCameraId] = useState<number | null>(null)
  const [selectedDeviceId, setSelectedDeviceId] = useState<number | null>(null)
  const [search, setSearch] = useState("")
  const [loading, setLoading] = useState(true)
  const [refreshing, setRefreshing] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [cameraModal, setCameraModal] = useState<Camera | "new" | null>(null)
  const [deviceModal, setDeviceModal] =
    useState<InfrastructureDevice | "new" | null>(null)

  const canManage = Boolean(
    cameraSummary?.can_manage ||
      deviceSummary?.can_manage ||
      options?.can_manage,
  )

  async function loadData(mode: "initial" | "refresh" = "initial") {
    mode === "initial" ? setLoading(true) : setRefreshing(true)

    try {
      const [
        nextCameraSummary,
        nextDeviceSummary,
        nextCameras,
        nextDevices,
        nextOptions,
        nextGatewayHealth,
      ] = await Promise.all([
        apiFetch<CameraSummaryResponse>("/cameras/summary"),
        apiFetch<DeviceSummaryResponse>("/devices/summary"),
        apiFetch<CameraListResponse>(
          "/cameras?page=1&page_size=200&active_only=false",
        ),
        apiFetch<DeviceListResponse>(
          "/devices?page=1&page_size=200&active_only=false",
        ),
        apiFetch<CameraOptionsResponse>("/cameras/options"),
        apiFetch<CameraGatewayHealth>("/live-streams/camera-gateway/health"),
      ])

      setCameraSummary(nextCameraSummary)
      setDeviceSummary(nextDeviceSummary)
      setCameras(nextCameras.items)
      setDevices(nextDevices.items)
      setOptions(nextOptions)
      setGatewayHealth(nextGatewayHealth)
      setError(null)

      setSelectedCameraId((current) => {
        if (
          current &&
          nextCameras.items.some((camera) => camera.id === current)
        ) {
          return current
        }
        return nextCameras.items[0]?.id ?? null
      })

      setSelectedDeviceId((current) => {
        if (
          current &&
          nextDevices.items.some((device) => device.id === current)
        ) {
          return current
        }
        return nextDevices.items[0]?.id ?? null
      })
    } catch (err) {
      setError(messageFromError(err))
    } finally {
      setLoading(false)
      setRefreshing(false)
    }
  }

  useEffect(() => {
    void loadData()
  }, [])

  useEffect(() => {
    const interval = window.setInterval(() => {
      void apiFetch<CameraGatewayHealth>(
        "/live-streams/camera-gateway/health",
      )
        .then(setGatewayHealth)
        .catch(() => setGatewayHealth(null))
    }, 10_000)

    return () => window.clearInterval(interval)
  }, [])

  const filteredCameras = useMemo(() => {
    const term = search.trim().toLowerCase()
    if (!term) return cameras

    return cameras.filter((camera) =>
      [
        camera.camera_identifier,
        camera.name,
        camera.location?.name,
        camera.ip_address,
        camera.manufacturer,
        camera.model,
        camera.stream_protocol,
        camera.v380_device_id,
      ]
        .filter(Boolean)
        .some((value) => String(value).toLowerCase().includes(term)),
    )
  }, [cameras, search])

  const filteredDevices = useMemo(() => {
    const term = search.trim().toLowerCase()
    if (!term) return devices

    return devices.filter((device) =>
      [
        device.device_identifier,
        device.name,
        device.device_type,
        device.role,
        device.location?.name,
        device.ip_address,
        device.hostname,
      ]
        .filter(Boolean)
        .some((value) => String(value).toLowerCase().includes(term)),
    )
  }, [devices, search])

  const selectedCamera =
    cameras.find((camera) => camera.id === selectedCameraId) ?? null
  const selectedDevice =
    devices.find((device) => device.id === selectedDeviceId) ?? null

  async function retireCamera(camera: Camera) {
    if (!window.confirm(`Retire ${camera.camera_identifier}?`)) return

    try {
      await apiFetch<Camera>(`/cameras/${camera.id}`, { method: "DELETE" })
      await loadData("refresh")
    } catch (err) {
      setError(messageFromError(err))
    }
  }

  async function retireDevice(device: InfrastructureDevice) {
    if (!window.confirm(`Retire ${device.device_identifier}?`)) return

    try {
      await apiFetch<InfrastructureDevice>(`/devices/${device.id}`, {
        method: "DELETE",
      })
      await loadData("refresh")
    } catch (err) {
      setError(messageFromError(err))
    }
  }

  if (loading) {
    return (
      <div className="flex min-h-[50vh] items-center justify-center text-sm text-muted-foreground">
        Loading physical infrastructure registry…
      </div>
    )
  }

  return (
    <div className="space-y-5">
      <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
        <div>
          <h1 className="text-xl font-semibold text-foreground">
            Camera & Device Management
          </h1>
          <p className="text-sm text-muted-foreground">
            Physical-to-digital registry for MCC cameras, NanoStations, Jetson
            nodes and supporting infrastructure.
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={() => void loadData("refresh")}
            disabled={refreshing}
          >
            <RefreshCw
              className={cn("size-4", refreshing && "animate-spin")}
            />
            Refresh
          </Button>

          {canManage && (
            <>
              <Button
                size="sm"
                variant="outline"
                onClick={() => setDeviceModal("new")}
              >
                <Plus className="size-4" />
                Register device
              </Button>
              <Button size="sm" onClick={() => setCameraModal("new")}>
                <Plus className="size-4" />
                Register camera
              </Button>
            </>
          )}
        </div>
      </div>

      {error && <FormError>{error}</FormError>}

      <GatewayHealthPanel health={gatewayHealth} />

      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        <MetricCard
          icon={<CameraIcon className="size-4" />}
          label="Registered cameras"
          value={cameraSummary?.total_cameras ?? 0}
          hint={`${cameraSummary?.mapped_cameras ?? 0} mapped to GIS`}
        />
        <MetricCard
          icon={<Wifi className="size-4" />}
          label="Camera streams online"
          value={cameraSummary?.stream_online_cameras ?? 0}
          hint={`${cameraSummary?.ai_enabled_cameras ?? 0} AI enabled`}
        />
        <MetricCard
          icon={<Network className="size-4" />}
          label="Infrastructure devices"
          value={deviceSummary?.total_devices ?? 0}
          hint={`${deviceSummary?.active_devices ?? 0} active`}
        />
        <MetricCard
          icon={<Activity className="size-4" />}
          label="Devices online"
          value={deviceSummary?.online_devices ?? 0}
          hint={`${deviceSummary?.degraded_devices ?? 0} degraded`}
        />
      </div>

      <div className="flex flex-col gap-3 rounded-md border border-border bg-card p-3 lg:flex-row lg:items-center lg:justify-between">
        <div className="flex flex-wrap gap-2">
          <TabButton active={tab === "overview"} onClick={() => setTab("overview")}>
            Overview
          </TabButton>
          <TabButton active={tab === "cameras"} onClick={() => setTab("cameras")}>
            Cameras
          </TabButton>
          <TabButton active={tab === "devices"} onClick={() => setTab("devices")}>
            Devices
          </TabButton>
        </div>

        {(tab === "cameras" || tab === "devices") && (
          <div className="relative w-full lg:w-80">
            <Search className="absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
            <input
              value={search}
              onChange={(event: ChangeEvent<HTMLInputElement>) => setSearch(event.target.value)}
              placeholder={`Search ${tab}…`}
              className="h-9 w-full rounded-md border border-input bg-background pl-9 pr-3 text-sm outline-none ring-offset-background focus:ring-2 focus:ring-ring"
            />
          </div>
        )}
      </div>

      {tab === "overview" && (
        <Overview
          cameraSummary={cameraSummary}
          deviceSummary={deviceSummary}
          cameras={cameras}
          devices={devices}
        />
      )}

      {tab === "cameras" && (
        <CameraRegistry
          items={filteredCameras}
          selected={selectedCamera}
          onSelect={setSelectedCameraId}
          canManage={canManage}
          onEdit={setCameraModal}
          onRetire={(camera) => void retireCamera(camera)}
          workerHealth={gatewayHealth?.workers ?? []}
        />
      )}

      {tab === "devices" && (
        <DeviceRegistry
          items={filteredDevices}
          selected={selectedDevice}
          onSelect={setSelectedDeviceId}
          canManage={canManage}
          onEdit={setDeviceModal}
          onRetire={(device) => void retireDevice(device)}
        />
      )}

      {cameraModal && options && (
        <CameraModal
          key={
            cameraModal === "new"
              ? "new-camera"
              : `camera-${cameraModal.id}`
          }
          camera={cameraModal === "new" ? null : cameraModal}
          options={options}
          onClose={() => setCameraModal(null)}
          onSaved={async () => {
            setCameraModal(null)
            await loadData("refresh")
          }}
        />
      )}

      {deviceModal && options && (
        <DeviceModal
          key={
            deviceModal === "new"
              ? "new-device"
              : `device-${deviceModal.id}`
          }
          device={deviceModal === "new" ? null : deviceModal}
          options={options}
          devices={devices}
          onClose={() => setDeviceModal(null)}
          onSaved={async () => {
            setDeviceModal(null)
            await loadData("refresh")
          }}
        />
      )}
    </div>
  )
}

function GatewayHealthPanel({
  health,
}: {
  health: CameraGatewayHealth | null
}) {
  const available = Boolean(health?.available)
  const gatewayStatus = available ? health?.status ?? "degraded" : "offline"
  const workerFailures = (health?.workers ?? []).filter(
    (worker) => worker.failure_code && worker.failure_message,
  )

  return (
    <Card>
      <CardContent className="space-y-4 p-4">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div className="flex items-start gap-3">
            <div
              className={cn(
                "mt-0.5 rounded-md p-2",
                available
                  ? "bg-emerald-500/10 text-emerald-600"
                  : "bg-destructive/10 text-destructive",
              )}
            >
              <Network className="size-4" />
            </div>
            <div>
              <h2 className="font-semibold text-foreground">
                V380 camera gateway
              </h2>
              <p className="text-xs text-muted-foreground">
                Runtime health of the service that logs into field cameras and
                publishes their streams to MediaMTX.
              </p>
            </div>
          </div>
          <StatusBadge status={gatewayStatus} />
        </div>

        <div className="grid gap-2 sm:grid-cols-2 xl:grid-cols-6">
          <Info
            label="Gateway process"
            value={available ? "Reachable" : "Unreachable"}
          />
          <Info
            label="Registry connection"
            value={health?.registry_connected ? "Connected" : "Disconnected"}
          />
          <Info
            label="Workers alive"
            value={`${health?.workers_alive ?? 0}/${health?.workers_total ?? 0}`}
          />
          <Info
            label="Worker states"
            value={`${health?.workers_online ?? 0} online · ${
              health?.workers_degraded ?? 0
            } degraded · ${health?.workers_offline ?? 0} offline`}
          />
          <Info
            label="Gateway uptime"
            value={formatDuration(health?.uptime_seconds ?? null)}
          />
          <Info
            label="Last registry sync"
            value={formatDate(health?.last_registry_sync_at ?? null)}
          />
        </div>

        {health?.failure_message && (
          <FailureNotice
            title={failureTitle(health.failure_code)}
            message={health.failure_message}
            detail={
              health.failure_at
                ? `Detected ${formatDate(health.failure_at)}`
                : "Gateway health requires attention."
            }
          />
        )}

        {workerFailures.length > 0 && (
          <div className="space-y-2">
            <div className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
              Active camera failures
            </div>
            <div className="grid gap-2 lg:grid-cols-2">
              {workerFailures.map((worker) => (
                <FailureNotice
                  key={worker.camera_identifier}
                  title={`${worker.camera_identifier} · ${failureTitle(
                    worker.failure_code,
                  )}`}
                  message={worker.failure_message ?? "Camera worker failure."}
                  detail={`${worker.consecutive_failures} consecutive attempt${
                    worker.consecutive_failures === 1 ? "" : "s"
                  } · retry every ${worker.retry_seconds ?? "—"} seconds`}
                />
              ))}
            </div>
          </div>
        )}

        <div className="flex flex-wrap justify-between gap-2 text-xs text-muted-foreground">
          <span>
            {health?.registered_cameras ?? 0} registered camera configurations ·
            polling every {health?.poll_seconds ?? "—"} seconds
          </span>
          <span>
            Observed {formatDate(health?.observed_at ?? health?.generated_at ?? null)}
          </span>
        </div>
      </CardContent>
    </Card>
  )
}

function Overview({
  cameraSummary,
  deviceSummary,
  cameras,
  devices,
}: {
  cameraSummary: CameraSummaryResponse | null
  deviceSummary: DeviceSummaryResponse | null
  cameras: Camera[]
  devices: InfrastructureDevice[]
}) {
  const jetsons = devices.filter((device) => device.device_type === "jetson")
  const radios = devices.filter(
    (device) => device.device_type === "nanostation",
  )

  return (
    <div className="grid gap-4 xl:grid-cols-[1.2fr_1fr]">
      <Card>
        <CardContent className="space-y-4 p-4">
          <div>
            <h2 className="font-semibold text-foreground">
              Physical-to-digital chain
            </h2>
            <p className="text-xs text-muted-foreground">
              Registered infrastructure anchors real field equipment to GIS
              and the AI pipeline.
            </p>
          </div>

          <div className="grid gap-2 md:grid-cols-5">
            <ChainNode
              icon={<CameraIcon className="size-4" />}
              title="Camera"
              value={`${cameraSummary?.active_cameras ?? 0} active`}
            />
            <ChainNode
              icon={<Radio className="size-4" />}
              title="NanoStation"
              value={`${radios.length} registered`}
            />
            <ChainNode
              icon={<Cpu className="size-4" />}
              title="Jetson"
              value={`${jetsons.length} registered`}
            />
            <ChainNode
              icon={<Activity className="size-4" />}
              title="AI events"
              value="FastAPI pipeline"
            />
            <ChainNode
              icon={<MapPin className="size-4" />}
              title="GIS"
              value={`${cameraSummary?.mapped_cameras ?? 0} cameras mapped`}
            />
          </div>

          <div className="rounded-md border border-border bg-muted/20 p-3 text-sm text-muted-foreground">
            Registered camera identifiers are authoritative geographic context.
            A detection from a known camera is automatically enriched with the
            camera&apos;s GIS location before the existing Incident Engine runs.
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardContent className="space-y-3 p-4">
          <h2 className="font-semibold text-foreground">
            Deployment readiness
          </h2>
          <ReadinessRow
            label="Camera registry"
            ready={cameras.length > 0}
            detail={`${cameras.length} registered`}
          />
          <ReadinessRow
            label="GIS-linked cameras"
            ready={(cameraSummary?.mapped_cameras ?? 0) > 0}
            detail={`${cameraSummary?.mapped_cameras ?? 0} mapped`}
          />
          <ReadinessRow
            label="Field radios"
            ready={radios.some((device) => device.role === "field_radio")}
            detail={`${
              radios.filter((device) => device.role === "field_radio").length
            } field`}
          />
          <ReadinessRow
            label="Jetson nodes"
            ready={jetsons.length > 0}
            detail={`${jetsons.length} registered`}
          />
          <ReadinessRow
            label="Online infrastructure"
            ready={(deviceSummary?.online_devices ?? 0) > 0}
            detail={`${deviceSummary?.online_devices ?? 0} online`}
          />
        </CardContent>
      </Card>
    </div>
  )
}

function CameraRegistry({
  items,
  selected,
  onSelect,
  canManage,
  onEdit,
  onRetire,
  workerHealth,
}: {
  items: Camera[]
  selected: Camera | null
  onSelect: (id: number) => void
  canManage: boolean
  onEdit: (camera: Camera) => void
  onRetire: (camera: Camera) => void
  workerHealth: CameraGatewayWorkerHealth[]
}) {
  const selectedWorker = selected
    ? workerHealth.find(
        (worker) => worker.camera_identifier === selected.camera_identifier,
      ) ?? null
    : null

  return (
    <div className="grid gap-4 xl:grid-cols-[1fr_1.1fr]">
      <Card>
        <CardContent className="p-0">
          {items.length === 0 ? (
            <EmptyState title="No cameras registered" />
          ) : (
            <div className="divide-y divide-border">
              {items.map((camera) => (
                <button
                  key={camera.id}
                  onClick={() => onSelect(camera.id)}
                  className={cn(
                    "flex w-full items-start gap-3 px-4 py-3 text-left transition-colors hover:bg-accent/40",
                    selected?.id === camera.id && "bg-accent/60",
                  )}
                >
                  <StatusDot status={camera.status} />
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center justify-between gap-2">
                      <span className="truncate text-sm font-medium">
                        {camera.name}
                      </span>
                      <span className="font-mono text-[11px] text-muted-foreground">
                        {camera.camera_identifier}
                      </span>
                    </div>
                    <div className="mt-1 flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
                      <span>{camera.location?.name ?? "No GIS location"}</span>
                      <span>•</span>
                      <span>{camera.stream_protocol.toUpperCase()}</span>
                      <span>•</span>
                      <span>{pretty(camera.stream_status)}</span>
                      {camera.ai_enabled && (
                        <>
                          <span>•</span>
                          <span>AI enabled</span>
                        </>
                      )}
                    </div>
                  </div>
                </button>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardContent className="space-y-4 p-4">
          {selected ? (
            <>
              <div className="flex items-start justify-between gap-3">
                <div>
                  <div className="font-mono text-xs text-muted-foreground">
                    {selected.camera_identifier}
                  </div>
                  <h2 className="text-lg font-semibold">{selected.name}</h2>
                  <div className="mt-1 flex items-center gap-1 text-sm text-muted-foreground">
                    <MapPin className="size-3.5" />
                    {selected.location?.name ?? "Not mapped"}
                  </div>
                </div>
                <StatusBadge status={selected.status} />
              </div>

              <div className="grid gap-2 sm:grid-cols-2">
                <Info label="Stream" value={pretty(selected.stream_status)} />
                <Info
                  label="AI"
                  value={selected.ai_enabled ? "Enabled" : "Disabled"}
                />
                <Info
                  label="IP address"
                  value={
                    selected.ip_address ?? "Restricted / not configured"
                  }
                />
                <Info
                  label="Stream configuration"
                  value={cameraStreamSummary(selected)}
                />
                <Info
                  label="Credentials"
                  value={cameraCredentialSummary(selected)}
                />
                <Info
                  label="Jetson"
                  value={
                    selected.assigned_jetson?.device_identifier ??
                    "Not assigned"
                  }
                />
                <Info
                  label="Field radio"
                  value={
                    selected.field_nanostation?.device_identifier ??
                    "Not assigned"
                  }
                />
                <Info
                  label="Hardware"
                  value={
                    [selected.manufacturer, selected.model]
                      .filter(Boolean)
                      .join(" ") || "Not specified"
                  }
                />
                <Info
                  label="Last seen"
                  value={formatDate(selected.last_seen_at)}
                />
              </div>

              {selectedWorker?.failure_message && (
                <FailureNotice
                  title={failureTitle(selectedWorker.failure_code)}
                  message={selectedWorker.failure_message}
                  detail={`${selectedWorker.consecutive_failures} consecutive attempt${
                    selectedWorker.consecutive_failures === 1 ? "" : "s"
                  } · automatic retry every ${
                    selectedWorker.retry_seconds ?? "—"
                  } seconds · detected ${formatDate(
                    selectedWorker.failure_at,
                  )}`}
                />
              )}

              <div className="rounded-md border border-border bg-muted/20 p-3">
                <div className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
                  Integration identity
                </div>
                <div className="mt-1 font-mono text-sm">
                  {selected.camera_identifier}
                </div>
                <div className="mt-1 text-xs text-muted-foreground">
                  The Jetson sends this identifier with detections. The backend
                  resolves the registered GIS location automatically.
                </div>
              </div>

              {canManage && selected.is_active && (
                <div className="flex flex-wrap gap-2">
                  <Button size="sm" onClick={() => onEdit(selected)}>
                    <Pencil className="size-3.5" />
                    Edit camera
                  </Button>
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => onRetire(selected)}
                  >
                    <Power className="size-3.5" />
                    Retire
                  </Button>
                </div>
              )}
            </>
          ) : (
            <EmptyState title="Select a camera" />
          )}
        </CardContent>
      </Card>
    </div>
  )
}

function DeviceRegistry({
  items,
  selected,
  onSelect,
  canManage,
  onEdit,
  onRetire,
}: {
  items: InfrastructureDevice[]
  selected: InfrastructureDevice | null
  onSelect: (id: number) => void
  canManage: boolean
  onEdit: (device: InfrastructureDevice) => void
  onRetire: (device: InfrastructureDevice) => void
}) {
  return (
    <div className="grid gap-4 xl:grid-cols-[1fr_1.1fr]">
      <Card>
        <CardContent className="p-0">
          {items.length === 0 ? (
            <EmptyState title="No infrastructure devices registered" />
          ) : (
            <div className="divide-y divide-border">
              {items.map((device) => (
                <button
                  key={device.id}
                  onClick={() => onSelect(device.id)}
                  className={cn(
                    "flex w-full items-start gap-3 px-4 py-3 text-left transition-colors hover:bg-accent/40",
                    selected?.id === device.id && "bg-accent/60",
                  )}
                >
                  <StatusDot status={device.status} />
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center justify-between gap-2">
                      <span className="truncate text-sm font-medium">
                        {device.name}
                      </span>
                      <span className="font-mono text-[11px] text-muted-foreground">
                        {device.device_identifier}
                      </span>
                    </div>
                    <div className="mt-1 flex flex-wrap gap-2 text-xs text-muted-foreground">
                      <span>{pretty(device.device_type)}</span>
                      <span>•</span>
                      <span>{pretty(device.role)}</span>
                      <span>•</span>
                      <span>
                        {device.location?.name ?? "No GIS location"}
                      </span>
                    </div>
                  </div>
                </button>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardContent className="space-y-4 p-4">
          {selected ? (
            <>
              <div className="flex items-start justify-between gap-3">
                <div>
                  <div className="font-mono text-xs text-muted-foreground">
                    {selected.device_identifier}
                  </div>
                  <h2 className="text-lg font-semibold">{selected.name}</h2>
                  <div className="mt-1 text-sm text-muted-foreground">
                    {pretty(selected.device_type)} · {pretty(selected.role)}
                  </div>
                </div>
                <StatusBadge status={selected.status} />
              </div>

              <div className="grid gap-2 sm:grid-cols-2">
                <Info
                  label="GIS location"
                  value={selected.location?.name ?? "Not mapped"}
                />
                <Info
                  label="IP address"
                  value={
                    selected.ip_address ?? "Restricted / not configured"
                  }
                />
                <Info
                  label="Hostname"
                  value={selected.hostname ?? "Not configured"}
                />
                <Info
                  label="Parent / linked device"
                  value={
                    selected.parent_device?.device_identifier ?? "None"
                  }
                />
                <Info
                  label="Hardware"
                  value={
                    [selected.manufacturer, selected.model]
                      .filter(Boolean)
                      .join(" ") || "Not specified"
                  }
                />
                <Info
                  label="Last seen"
                  value={formatDate(selected.last_seen_at)}
                />
              </div>

              {Object.keys(selected.health_metrics ?? {}).length > 0 && (
                <div className="rounded-md border border-border bg-muted/20 p-3">
                  <div className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
                    Latest health metrics
                  </div>
                  <pre className="mt-2 overflow-x-auto text-xs text-foreground">
                    {JSON.stringify(selected.health_metrics, null, 2)}
                  </pre>
                </div>
              )}

              {canManage && selected.is_active && (
                <div className="flex flex-wrap gap-2">
                  <Button size="sm" onClick={() => onEdit(selected)}>
                    <Pencil className="size-3.5" />
                    Edit device
                  </Button>
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => onRetire(selected)}
                  >
                    <Power className="size-3.5" />
                    Retire
                  </Button>
                </div>
              )}
            </>
          ) : (
            <EmptyState title="Select a device" />
          )}
        </CardContent>
      </Card>
    </div>
  )
}

function CameraModal({
  camera,
  options,
  onClose,
  onSaved,
}: {
  camera: Camera | null
  options: CameraOptionsResponse
  onClose: () => void
  onSaved: () => Promise<void>
}) {
  const [form, setForm] = useState({
    camera_identifier: camera?.camera_identifier ?? "",
    name: camera?.name ?? "",
    description: camera?.description ?? "",
    gis_location_id: camera?.gis_location_id
      ? String(camera.gis_location_id)
      : "",
    assigned_jetson_id: camera?.assigned_jetson_id
      ? String(camera.assigned_jetson_id)
      : "",
    field_nanostation_id: camera?.field_nanostation_id
      ? String(camera.field_nanostation_id)
      : "",
    ip_address: camera?.ip_address ?? "",
    mac_address: camera?.mac_address ?? "",
    manufacturer: camera?.manufacturer ?? "",
    model: camera?.model ?? "",
    serial_number: camera?.serial_number ?? "",
    stream_protocol:
      camera?.stream_protocol === "v380" ? "v380" : ("rtsp" as StreamProtocol),
    credential_username:
      camera?.stream_protocol === "v380" ? "admin" : "",
    credential_password: "",
    rtsp_port: camera?.rtsp_port ? String(camera.rtsp_port) : "554",
    rtsp_path: camera?.rtsp_path ?? "",
    onvif_port: camera?.onvif_port ? String(camera.onvif_port) : "",
    v380_port: camera?.v380_port ? String(camera.v380_port) : "8800",
    v380_device_id: camera?.v380_device_id
      ? String(camera.v380_device_id)
      : "",
    ai_enabled: camera?.ai_enabled ?? true,
    status: camera?.status ?? ("configured" as DeviceStatus),
    stream_status:
      camera?.stream_status ?? ("unconfigured" as StreamStatus),
  })
  const [saving, setSaving] = useState(false)
  const [migrating, setMigrating] = useState(false)
  const [testingConnection, setTestingConnection] = useState(false)
  const [connectionTest, setConnectionTest] =
    useState<CameraConnectionTestResponse | null>(null)
  const [error, setError] = useState<string | null>(null)

  function invalidateConnectionTest() {
    setConnectionTest(null)
  }

  async function testV380Connection() {
    setError(null)

    if (!form.ip_address.trim()) {
      setError("V380 cameras require an IP address.")
      return
    }
    if (!positiveInteger(form.v380_device_id)) {
      setError("V380 device ID must be a positive integer.")
      return
    }
    if (!validPort(form.v380_port)) {
      setError("V380 port must be between 1 and 65535.")
      return
    }
    if (!form.credential_username.trim() || !form.credential_password) {
      setError("Enter the V380 camera username and password before testing.")
      return
    }

    setTestingConnection(true)
    setConnectionTest(null)
    try {
      const result = await apiFetch<CameraConnectionTestResponse>(
        "/cameras/test-connection",
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            ip_address: form.ip_address.trim(),
            v380_port: Number(form.v380_port),
            v380_device_id: Number(form.v380_device_id),
            credential_username: form.credential_username.trim(),
            credential_password: form.credential_password,
          }),
        },
      )
      setConnectionTest(result)
    } catch (err) {
      setError(messageFromError(err))
    } finally {
      setTestingConnection(false)
    }
  }

  async function submit(event: FormEvent) {
    event.preventDefault()
    setSaving(true)
    setError(null)

    const isV380 = form.stream_protocol === "v380"

    if (isV380 && !form.ip_address.trim()) {
      setError("V380 cameras require an IP address.")
      setSaving(false)
      return
    }

    if (isV380 && !positiveInteger(form.v380_device_id)) {
      setError("V380 device ID must be a positive integer.")
      setSaving(false)
      return
    }

    if (isV380 && !validPort(form.v380_port)) {
      setError("V380 port must be between 1 and 65535.")
      setSaving(false)
      return
    }

    const needsNewCredentials =
      isV380 && (!camera || !camera.credential_configured)

    if (
      needsNewCredentials &&
      (!form.credential_username.trim() || !form.credential_password)
    ) {
      setError("V380 cameras require a camera username and password.")
      setSaving(false)
      return
    }

    if (
      form.credential_password &&
      !form.credential_username.trim()
    ) {
      setError("Camera username is required when changing the password.")
      setSaving(false)
      return
    }

    if (isV380 && !camera && !connectionTest?.success) {
      setError(
        "Test the V380 LAN connection successfully before registering this camera.",
      )
      setSaving(false)
      return
    }

    const payload = {
      camera_identifier: form.camera_identifier,
      name: form.name,
      description: nullable(form.description),
      gis_location_id: numberOrNull(form.gis_location_id),
      assigned_jetson_id: numberOrNull(form.assigned_jetson_id),
      field_nanostation_id: numberOrNull(form.field_nanostation_id),
      ip_address: nullable(form.ip_address),
      mac_address: nullable(form.mac_address),
      manufacturer: nullable(form.manufacturer),
      model: nullable(form.model),
      serial_number: nullable(form.serial_number),
      stream_protocol: form.stream_protocol,
      credential_username: form.credential_password
        ? form.credential_username.trim()
        : undefined,
      credential_password: form.credential_password || undefined,
      rtsp_port: isV380 ? null : numberOrNull(form.rtsp_port),
      rtsp_path: isV380 ? null : nullable(form.rtsp_path),
      onvif_port: isV380 ? null : numberOrNull(form.onvif_port),
      v380_port: isV380 ? numberOrNull(form.v380_port) : null,
      v380_device_id: isV380 ? numberOrNull(form.v380_device_id) : null,
      ai_enabled: form.ai_enabled,
      status: form.status,
      stream_status: form.stream_status,
    }

    try {
      await apiFetch<Camera>(
        camera ? `/cameras/${camera.id}` : "/cameras",
        {
          method: camera ? "PATCH" : "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload),
        },
      )
      await onSaved()
    } catch (err) {
      setError(messageFromError(err))
    } finally {
      setSaving(false)
    }
  }

  async function migrateLegacyCredential() {
    if (!camera) return

    setMigrating(true)
    setError(null)
    try {
      await apiFetch(
        `/cameras/${camera.id}/credentials/migrate`,
        { method: "POST" },
      )
      await onSaved()
    } catch (err) {
      setError(messageFromError(err))
    } finally {
      setMigrating(false)
    }
  }

  return (
    <ModalShell
      title={camera ? "Edit camera" : "Register camera"}
      onClose={onClose}
    >
      <form onSubmit={submit} className="space-y-4">
        {error && <FormError>{error}</FormError>}

        <div className="grid gap-3 md:grid-cols-2">
          <Field label="MCC camera identifier" required>
            <input
              required
              value={form.camera_identifier}
              onChange={(e: ChangeEvent<HTMLInputElement>) =>
                setForm({ ...form, camera_identifier: e.target.value })
              }
              className={inputClass}
              placeholder="MCC-CAM-001"
            />
          </Field>

          <Field label="Display name" required>
            <input
              required
              value={form.name}
              onChange={(e: ChangeEvent<HTMLInputElement>) =>
                setForm({ ...form, name: e.target.value })
              }
              className={inputClass}
              placeholder="Kingsway Camera 01"
            />
          </Field>

          <Field label="GIS location">
            <select
              value={form.gis_location_id}
              onChange={(e: ChangeEvent<HTMLSelectElement>) =>
                setForm({ ...form, gis_location_id: e.target.value })
              }
              className={inputClass}
            >
              <option value="">Not assigned</option>
              {options.locations.map((location) => (
                <option key={location.id} value={location.id}>
                  {location.name} ({location.code})
                </option>
              ))}
            </select>
          </Field>

          <Field label="IP address">
            <input
              value={form.ip_address}
              onChange={(e: ChangeEvent<HTMLInputElement>) => {
                invalidateConnectionTest()
                setForm({ ...form, ip_address: e.target.value })
              }}
              className={inputClass}
              placeholder="192.168.30.12"
            />
          </Field>

          <Field label="Stream protocol" required>
            <select
              value={form.stream_protocol}
              onChange={(e: ChangeEvent<HTMLSelectElement>) => {
                const protocol = e.target.value as StreamProtocol
                invalidateConnectionTest()
                setForm({
                  ...form,
                  stream_protocol: protocol,
                  rtsp_port:
                    protocol === "rtsp" && !form.rtsp_port
                      ? "554"
                      : form.rtsp_port,
                  v380_port:
                    protocol === "v380" && !form.v380_port
                      ? "8800"
                      : form.v380_port,
                })
              }}
              className={inputClass}
            >
              <option value="rtsp">RTSP / ONVIF</option>
              <option value="v380">V380 proprietary LAN</option>
            </select>
          </Field>

          <Field
            label="Camera username"
            required={
              form.stream_protocol === "v380" &&
              (!camera || !camera.credential_configured)
            }
          >
            <input
              autoComplete="off"
              value={form.credential_username}
              onChange={(e: ChangeEvent<HTMLInputElement>) => {
                invalidateConnectionTest()
                setForm({ ...form, credential_username: e.target.value })
              }}
              className={inputClass}
              placeholder={form.stream_protocol === "v380" ? "admin" : "camera user"}
            />
          </Field>

          <Field
            label={camera?.credential_configured ? "New camera password" : "Camera password"}
            required={
              form.stream_protocol === "v380" &&
              (!camera || !camera.credential_configured)
            }
          >
            <input
              type="password"
              autoComplete="new-password"
              value={form.credential_password}
              onChange={(e: ChangeEvent<HTMLInputElement>) => {
                invalidateConnectionTest()
                setForm({ ...form, credential_password: e.target.value })
              }}
              className={inputClass}
              placeholder={
                camera?.credential_configured
                  ? "Leave blank to keep current password"
                  : "Enter camera password"
              }
            />
          </Field>

          <Field label="Field NanoStation">
            <select
              value={form.field_nanostation_id}
              onChange={(e: ChangeEvent<HTMLSelectElement>) =>
                setForm({
                  ...form,
                  field_nanostation_id: e.target.value,
                })
              }
              className={inputClass}
            >
              <option value="">Not assigned</option>
              {options.nanostations
                .filter((device) => device.role === "field_radio")
                .map((device) => (
                  <option key={device.id} value={device.id}>
                    {device.device_identifier} — {device.name}
                  </option>
                ))}
            </select>
          </Field>

          <Field label="Assigned Jetson">
            <select
              value={form.assigned_jetson_id}
              onChange={(e: ChangeEvent<HTMLSelectElement>) =>
                setForm({
                  ...form,
                  assigned_jetson_id: e.target.value,
                })
              }
              className={inputClass}
            >
              <option value="">Not assigned</option>
              {options.jetsons.map((device) => (
                <option key={device.id} value={device.id}>
                  {device.device_identifier} — {device.name}
                </option>
              ))}
            </select>
          </Field>

          <Field label="Manufacturer">
            <input
              value={form.manufacturer}
              onChange={(e: ChangeEvent<HTMLInputElement>) =>
                setForm({ ...form, manufacturer: e.target.value })
              }
              className={inputClass}
            />
          </Field>

          <Field label="Model">
            <input
              value={form.model}
              onChange={(e: ChangeEvent<HTMLInputElement>) =>
                setForm({ ...form, model: e.target.value })
              }
              className={inputClass}
            />
          </Field>

          <Field label="Serial number">
            <input
              value={form.serial_number}
              onChange={(e: ChangeEvent<HTMLInputElement>) =>
                setForm({ ...form, serial_number: e.target.value })
              }
              className={inputClass}
            />
          </Field>

          <Field label="MAC address">
            <input
              value={form.mac_address}
              onChange={(e: ChangeEvent<HTMLInputElement>) =>
                setForm({ ...form, mac_address: e.target.value })
              }
              className={inputClass}
              placeholder="AA:BB:CC:DD:EE:FF"
            />
          </Field>

          {form.stream_protocol === "v380" ? (
            <>
              <Field label="V380 port" required>
                <input
                  required
                  type="number"
                  min={1}
                  max={65535}
                  value={form.v380_port}
                  onChange={(e: ChangeEvent<HTMLInputElement>) => {
                    invalidateConnectionTest()
                    setForm({ ...form, v380_port: e.target.value })
                  }}
                  className={inputClass}
                  placeholder="8800"
                />
              </Field>

              <Field label="V380 device ID" required>
                <input
                  required
                  type="number"
                  min={1}
                  step={1}
                  value={form.v380_device_id}
                  onChange={(e: ChangeEvent<HTMLInputElement>) => {
                    invalidateConnectionTest()
                    setForm({ ...form, v380_device_id: e.target.value })
                  }}
                  className={inputClass}
                  placeholder="106519033"
                />
              </Field>
            </>
          ) : (
            <>
              <Field label="RTSP port">
                <input
                  type="number"
                  min={1}
                  max={65535}
                  value={form.rtsp_port}
                  onChange={(e: ChangeEvent<HTMLInputElement>) =>
                    setForm({ ...form, rtsp_port: e.target.value })
                  }
                  className={inputClass}
                />
              </Field>

              <Field label="RTSP path">
                <input
                  value={form.rtsp_path}
                  onChange={(e: ChangeEvent<HTMLInputElement>) =>
                    setForm({ ...form, rtsp_path: e.target.value })
                  }
                  className={inputClass}
                  placeholder="/stream1"
                />
              </Field>

              <Field label="ONVIF port">
                <input
                  type="number"
                  min={1}
                  max={65535}
                  value={form.onvif_port}
                  onChange={(e: ChangeEvent<HTMLInputElement>) =>
                    setForm({ ...form, onvif_port: e.target.value })
                  }
                  className={inputClass}
                />
              </Field>
            </>
          )}

          <Field label="Camera status">
            <select
              value={form.status}
              onChange={(e: ChangeEvent<HTMLSelectElement>) =>
                setForm({
                  ...form,
                  status: e.target.value as DeviceStatus,
                })
              }
              className={inputClass}
            >
              {DEVICE_STATUSES.map((value) => (
                <option key={value} value={value}>
                  {pretty(value)}
                </option>
              ))}
            </select>
          </Field>

          <Field label="Stream status">
            <select
              value={form.stream_status}
              onChange={(e: ChangeEvent<HTMLSelectElement>) =>
                setForm({
                  ...form,
                  stream_status: e.target.value as StreamStatus,
                })
              }
              className={inputClass}
            >
              {STREAM_STATUSES.map((value) => (
                <option key={value} value={value}>
                  {pretty(value)}
                </option>
              ))}
            </select>
          </Field>
        </div>

        <Field label="Description">
          <textarea
            value={form.description}
            onChange={(e: ChangeEvent<HTMLTextAreaElement>) =>
              setForm({ ...form, description: e.target.value })
            }
            className={cn(inputClass, "min-h-20 py-2")}
          />
        </Field>

        <label className="flex items-center gap-2 text-sm">
          <input
            type="checkbox"
            checked={form.ai_enabled}
            onChange={(e: ChangeEvent<HTMLInputElement>) =>
              setForm({ ...form, ai_enabled: e.target.checked })
            }
          />
          Enable AI processing for this camera
        </label>

        {form.stream_protocol === "v380" && !camera && (
          <div className="space-y-2 rounded-md border border-border bg-muted/20 p-3">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <div>
                <div className="text-sm font-medium text-foreground">
                  V380 LAN connection test
                </div>
                <div className="mt-1 text-xs text-muted-foreground">
                  Verify the camera IP, device ID, username and password before
                  registration. The test does not save the password.
                </div>
              </div>
              <Button
                type="button"
                size="sm"
                variant="outline"
                disabled={testingConnection || saving}
                onClick={() => void testV380Connection()}
              >
                {testingConnection ? "Testing…" : "Test connection"}
              </Button>
            </div>

            {connectionTest && (
              <div
                className={cn(
                  "rounded-md border px-3 py-2 text-xs",
                  connectionTest.success
                    ? "border-emerald-500/30 bg-emerald-500/10 text-emerald-700"
                    : "border-destructive/30 bg-destructive/10 text-destructive",
                )}
              >
                <div className="font-medium">
                  {connectionTest.success
                    ? "Camera authenticated successfully"
                    : "Camera connection test failed"}
                </div>
                <div className="mt-1">{connectionTest.message}</div>
                {connectionTest.login_result !== null && (
                  <div className="mt-1 font-mono">
                    V380 login result: {connectionTest.login_result}
                  </div>
                )}
              </div>
            )}
          </div>
        )}

        <div className="space-y-3 rounded-md border border-border bg-muted/20 p-3 text-xs text-muted-foreground">
          <div>
            Camera passwords are sent only when you register or rotate
            credentials. The backend encrypts them before database storage and
            never returns a stored password to this page.
            {camera?.credential_configured && (
              <span className="ml-1">
                Leave the password field blank to keep the current credential.
              </span>
            )}
          </div>

          {camera?.credential_source === "environment" && (
            <div className="flex flex-wrap items-center justify-between gap-2 rounded-md border border-amber-500/30 bg-amber-500/5 p-2">
              <span>
                This camera still uses the legacy per-camera environment
                credential. Migrate it to the encrypted vault before removing
                the old Docker environment variable.
              </span>
              <Button
                type="button"
                size="sm"
                variant="outline"
                disabled={migrating || saving}
                onClick={() => void migrateLegacyCredential()}
              >
                {migrating ? "Migrating…" : "Migrate to encrypted vault"}
              </Button>
            </div>
          )}
        </div>

        <div className="flex justify-end gap-2">
          <Button type="button" variant="outline" onClick={onClose}>
            Cancel
          </Button>
          <Button
            type="submit"
            disabled={
              saving ||
              testingConnection ||
              (form.stream_protocol === "v380" &&
                !camera &&
                !connectionTest?.success)
            }
          >
            {saving
              ? "Saving…"
              : camera
                ? "Save changes"
                : "Register camera"}
          </Button>
        </div>
      </form>
    </ModalShell>
  )
}

function DeviceModal({
  device,
  options,
  devices,
  onClose,
  onSaved,
}: {
  device: InfrastructureDevice | null
  options: CameraOptionsResponse
  devices: InfrastructureDevice[]
  onClose: () => void
  onSaved: () => Promise<void>
}) {
  const [form, setForm] = useState({
    device_identifier: device?.device_identifier ?? "",
    name: device?.name ?? "",
    description: device?.description ?? "",
    device_type: device?.device_type ?? ("nanostation" as DeviceType),
    role: device?.role ?? ("field_radio" as DeviceRole),
    gis_location_id: device?.gis_location_id
      ? String(device.gis_location_id)
      : "",
    parent_device_id: device?.parent_device_id
      ? String(device.parent_device_id)
      : "",
    ip_address: device?.ip_address ?? "",
    mac_address: device?.mac_address ?? "",
    hostname: device?.hostname ?? "",
    manufacturer: device?.manufacturer ?? "",
    model: device?.model ?? "",
    serial_number: device?.serial_number ?? "",
    status: device?.status ?? ("configured" as DeviceStatus),
  })
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function submit(event: FormEvent) {
    event.preventDefault()
    setSaving(true)
    setError(null)

    const payload = {
      device_identifier: form.device_identifier,
      name: form.name,
      description: nullable(form.description),
      device_type: form.device_type,
      role: form.role,
      gis_location_id: numberOrNull(form.gis_location_id),
      parent_device_id: numberOrNull(form.parent_device_id),
      ip_address: nullable(form.ip_address),
      mac_address: nullable(form.mac_address),
      hostname: nullable(form.hostname),
      manufacturer: nullable(form.manufacturer),
      model: nullable(form.model),
      serial_number: nullable(form.serial_number),
      status: form.status,
    }

    try {
      await apiFetch<InfrastructureDevice>(
        device ? `/devices/${device.id}` : "/devices",
        {
          method: device ? "PATCH" : "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload),
        },
      )
      await onSaved()
    } catch (err) {
      setError(messageFromError(err))
    } finally {
      setSaving(false)
    }
  }

  return (
    <ModalShell
      title={
        device
          ? "Edit infrastructure device"
          : "Register infrastructure device"
      }
      onClose={onClose}
    >
      <form onSubmit={submit} className="space-y-4">
        {error && <FormError>{error}</FormError>}

        <div className="grid gap-3 md:grid-cols-2">
          <Field label="MCC device identifier" required>
            <input
              required
              value={form.device_identifier}
              onChange={(e: ChangeEvent<HTMLInputElement>) =>
                setForm({
                  ...form,
                  device_identifier: e.target.value,
                })
              }
              className={inputClass}
              placeholder="MCC-NS-FIELD-001"
            />
          </Field>

          <Field label="Display name" required>
            <input
              required
              value={form.name}
              onChange={(e: ChangeEvent<HTMLInputElement>) =>
                setForm({ ...form, name: e.target.value })
              }
              className={inputClass}
              placeholder="Field NanoStation 01"
            />
          </Field>

          <Field label="Device type">
            <select
              value={form.device_type}
              onChange={(e: ChangeEvent<HTMLSelectElement>) =>
                setForm({
                  ...form,
                  device_type: e.target.value as DeviceType,
                })
              }
              className={inputClass}
            >
              {DEVICE_TYPES.map((value) => (
                <option key={value} value={value}>
                  {pretty(value)}
                </option>
              ))}
            </select>
          </Field>

          <Field label="Role">
            <select
              value={form.role}
              onChange={(e: ChangeEvent<HTMLSelectElement>) =>
                setForm({
                  ...form,
                  role: e.target.value as DeviceRole,
                })
              }
              className={inputClass}
            >
              {DEVICE_ROLES.map((value) => (
                <option key={value} value={value}>
                  {pretty(value)}
                </option>
              ))}
            </select>
          </Field>

          <Field label="GIS location">
            <select
              value={form.gis_location_id}
              onChange={(e: ChangeEvent<HTMLSelectElement>) =>
                setForm({ ...form, gis_location_id: e.target.value })
              }
              className={inputClass}
            >
              <option value="">Not assigned</option>
              {options.locations.map((location) => (
                <option key={location.id} value={location.id}>
                  {location.name} ({location.code})
                </option>
              ))}
            </select>
          </Field>

          <Field label="Parent / linked device">
            <select
              value={form.parent_device_id}
              onChange={(e: ChangeEvent<HTMLSelectElement>) =>
                setForm({
                  ...form,
                  parent_device_id: e.target.value,
                })
              }
              className={inputClass}
            >
              <option value="">None</option>
              {devices
                .filter(
                  (candidate) =>
                    candidate.id !== device?.id && candidate.is_active,
                )
                .map((candidate) => (
                  <option key={candidate.id} value={candidate.id}>
                    {candidate.device_identifier} — {candidate.name}
                  </option>
                ))}
            </select>
          </Field>

          <Field label="IP address">
            <input
              value={form.ip_address}
              onChange={(e: ChangeEvent<HTMLInputElement>) =>
                setForm({ ...form, ip_address: e.target.value })
              }
              className={inputClass}
              placeholder="10.20.1.2"
            />
          </Field>

          <Field label="Hostname">
            <input
              value={form.hostname}
              onChange={(e: ChangeEvent<HTMLInputElement>) =>
                setForm({ ...form, hostname: e.target.value })
              }
              className={inputClass}
              placeholder="mcc-jetson-01"
            />
          </Field>

          <Field label="MAC address">
            <input
              value={form.mac_address}
              onChange={(e: ChangeEvent<HTMLInputElement>) =>
                setForm({ ...form, mac_address: e.target.value })
              }
              className={inputClass}
            />
          </Field>

          <Field label="Manufacturer">
            <input
              value={form.manufacturer}
              onChange={(e: ChangeEvent<HTMLInputElement>) =>
                setForm({ ...form, manufacturer: e.target.value })
              }
              className={inputClass}
            />
          </Field>

          <Field label="Model">
            <input
              value={form.model}
              onChange={(e: ChangeEvent<HTMLInputElement>) =>
                setForm({ ...form, model: e.target.value })
              }
              className={inputClass}
            />
          </Field>

          <Field label="Serial number">
            <input
              value={form.serial_number}
              onChange={(e: ChangeEvent<HTMLInputElement>) =>
                setForm({ ...form, serial_number: e.target.value })
              }
              className={inputClass}
            />
          </Field>

          <Field label="Status">
            <select
              value={form.status}
              onChange={(e: ChangeEvent<HTMLSelectElement>) =>
                setForm({
                  ...form,
                  status: e.target.value as DeviceStatus,
                })
              }
              className={inputClass}
            >
              {DEVICE_STATUSES.map((value) => (
                <option key={value} value={value}>
                  {pretty(value)}
                </option>
              ))}
            </select>
          </Field>
        </div>

        <Field label="Description">
          <textarea
            value={form.description}
            onChange={(e: ChangeEvent<HTMLTextAreaElement>) =>
              setForm({ ...form, description: e.target.value })
            }
            className={cn(inputClass, "min-h-20 py-2")}
          />
        </Field>

        <div className="flex justify-end gap-2">
          <Button type="button" variant="outline" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" disabled={saving}>
            {saving
              ? "Saving…"
              : device
                ? "Save changes"
                : "Register device"}
          </Button>
        </div>
      </form>
    </ModalShell>
  )
}

function ModalShell({
  title,
  onClose,
  children,
}: {
  title: string
  onClose: () => void
  children: ReactNode
}) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4">
      <div className="max-h-[92vh] w-full max-w-4xl overflow-y-auto rounded-lg border border-border bg-background shadow-2xl">
        <div className="sticky top-0 z-10 flex items-center justify-between border-b border-border bg-background px-5 py-4">
          <h2 className="font-semibold">{title}</h2>
          <button
            onClick={onClose}
            className="rounded-md p-1 text-muted-foreground hover:bg-accent hover:text-foreground"
            aria-label="Close"
          >
            <X className="size-4" />
          </button>
        </div>
        <div className="p-5">{children}</div>
      </div>
    </div>
  )
}

function MetricCard({
  icon,
  label,
  value,
  hint,
}: {
  icon: ReactNode
  label: string
  value: number
  hint: string
}) {
  return (
    <Card>
      <CardContent className="p-4">
        <div className="flex items-center gap-2 text-xs text-muted-foreground">
          {icon}
          {label}
        </div>
        <div className="mt-2 text-2xl font-semibold">{value}</div>
        <div className="mt-1 text-xs text-muted-foreground">{hint}</div>
      </CardContent>
    </Card>
  )
}

function ChainNode({
  icon,
  title,
  value,
}: {
  icon: ReactNode
  title: string
  value: string
}) {
  return (
    <div className="rounded-md border border-border bg-muted/20 p-3">
      <div className="flex items-center gap-2 text-xs font-medium">
        {icon}
        {title}
      </div>
      <div className="mt-2 text-xs text-muted-foreground">{value}</div>
    </div>
  )
}

function ReadinessRow({
  label,
  ready,
  detail,
}: {
  label: string
  ready: boolean
  detail: string
}) {
  return (
    <div className="flex items-center justify-between gap-3 rounded-md border border-border px-3 py-2">
      <div className="flex items-center gap-2 text-sm">
        <span
          className={cn(
            "size-2 rounded-full",
            ready ? "bg-emerald-500" : "bg-muted-foreground/40",
          )}
        />
        {label}
      </div>
      <span className="text-xs text-muted-foreground">{detail}</span>
    </div>
  )
}

function TabButton({
  active,
  onClick,
  children,
}: {
  active: boolean
  onClick: () => void
  children: ReactNode
}) {
  return (
    <Button
      size="sm"
      variant={active ? "default" : "outline"}
      onClick={onClick}
    >
      {children}
    </Button>
  )
}

function StatusDot({ status }: { status: string }) {
  return (
    <span
      className={cn(
        "mt-1.5 size-2.5 shrink-0 rounded-full",
        status === "online" && "bg-emerald-500",
        status === "degraded" && "bg-amber-500",
        status === "offline" && "bg-destructive",
        status === "maintenance" && "bg-blue-500",
        status === "configured" && "bg-violet-500",
        status === "planned" && "bg-muted-foreground",
        status === "retired" && "bg-muted-foreground/40",
      )}
    />
  )
}

function StatusBadge({ status }: { status: string }) {
  return (
    <Badge
      variant="outline"
      className={cn(
        "capitalize",
        status === "online" &&
          "border-emerald-500/30 bg-emerald-500/10 text-emerald-600",
        status === "degraded" &&
          "border-amber-500/30 bg-amber-500/10 text-amber-600",
        status === "offline" &&
          "border-destructive/30 bg-destructive/10 text-destructive",
      )}
    >
      {pretty(status)}
    </Badge>
  )
}

function Info({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-md border border-border bg-muted/20 px-3 py-2">
      <div className="text-[10px] uppercase tracking-wide text-muted-foreground">
        {label}
      </div>
      <div className="mt-1 break-words text-sm text-foreground">{value}</div>
    </div>
  )
}

function Field({
  label,
  required = false,
  children,
}: {
  label: string
  required?: boolean
  children: ReactNode
}) {
  return (
    <label className="space-y-1.5 text-sm">
      <span className="text-xs font-medium text-muted-foreground">
        {label}
        {required && <span className="text-destructive"> *</span>}
      </span>
      {children}
    </label>
  )
}

function FormError({ children }: { children: ReactNode }) {
  return (
    <div className="rounded-md border border-destructive/30 bg-destructive/10 px-3 py-2 text-sm text-destructive">
      {children}
    </div>
  )
}

function EmptyState({ title }: { title: string }) {
  return (
    <div className="flex min-h-40 items-center justify-center px-4 text-sm text-muted-foreground">
      {title}
    </div>
  )
}

function pretty(value: string) {
  return value
    .replaceAll("_", " ")
    .replace(/\b\w/g, (letter) => letter.toUpperCase())
}

function cameraCredentialSummary(camera: Camera) {
  if (!camera.credential_configured) return "Not configured"
  if (camera.credential_source === "vault") return "Encrypted vault"
  if (camera.credential_source === "environment") {
    return "Legacy server environment"
  }
  return "Server-side credential configured"
}

function cameraStreamSummary(camera: Camera) {
  if (camera.stream_protocol === "v380") {
    if (!camera.v380_device_id) return "V380 · Not configured"
    return `V380 · device ${camera.v380_device_id} · :${
      camera.v380_port ?? 8800
    }`
  }

  if (!camera.rtsp_path) {
    return `RTSP · :${camera.rtsp_port ?? 554} · Path not configured`
  }

  return `RTSP · :${camera.rtsp_port ?? 554}${camera.rtsp_path}`
}

function validPort(value: string) {
  if (!value) return false
  const parsed = Number(value)
  return Number.isInteger(parsed) && parsed >= 1 && parsed <= 65535
}

function positiveInteger(value: string) {
  if (!value) return false
  const parsed = Number(value)
  return Number.isInteger(parsed) && parsed > 0
}

function formatDate(value: string | null) {
  if (!value) return "Never"
  const date = new Date(value)
  return Number.isNaN(date.getTime())
    ? "Unknown"
    : date.toLocaleString()
}

function FailureNotice({
  title,
  message,
  detail,
}: {
  title: string
  message: string
  detail: string
}) {
  return (
    <div className="rounded-md border border-destructive/30 bg-destructive/10 p-3">
      <div className="flex items-center gap-2 text-sm font-medium text-destructive">
        <Activity className="size-4" />
        {title}
      </div>
      <div className="mt-1 text-sm text-foreground">{message}</div>
      <div className="mt-1 text-xs text-muted-foreground">{detail}</div>
    </div>
  )
}

function formatDuration(value: number | null) {
  if (value === null || !Number.isFinite(value) || value < 0) return "Unavailable"

  const totalSeconds = Math.floor(value)
  const days = Math.floor(totalSeconds / 86_400)
  const hours = Math.floor((totalSeconds % 86_400) / 3_600)
  const minutes = Math.floor((totalSeconds % 3_600) / 60)

  if (days > 0) return `${days}d ${hours}h`
  if (hours > 0) return `${hours}h ${minutes}m`
  return `${minutes}m`
}

function failureTitle(code: string | null) {
  const titles: Record<string, string> = {
    authentication_rejected: "Authentication rejected",
    connection_timeout: "Connection timeout",
    video_decode_failed: "Video decoding failure",
    publisher_failed: "Stream publishing failure",
    stream_ended: "Live session ended",
    camera_unreachable: "Camera unreachable",
    worker_failed: "Camera worker failure",
    registry_unavailable: "Camera registry unavailable",
    worker_count_mismatch: "Worker count mismatch",
    worker_stopped: "Camera worker stopped",
    gateway_unreachable: "Camera gateway unreachable",
  }

  return code ? titles[code] ?? pretty(code) : "Operational failure"
}

function nullable(value: string) {
  const trimmed = value.trim()
  return trimmed ? trimmed : null
}

function numberOrNull(value: string) {
  if (!value) return null
  const parsed = Number(value)
  return Number.isFinite(parsed) ? parsed : null
}

function messageFromError(error: unknown) {
  return error instanceof Error ? error.message : "Request failed."
}
