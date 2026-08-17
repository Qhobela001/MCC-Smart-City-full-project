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
  stream_protocol: string
  credential_reference: string | null
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

type CameraOptionsResponse = {
  locations: LocationSummary[]
  jetsons: DeviceOption[]
  nanostations: DeviceOption[]
  can_manage: boolean
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
      ])

      setCameraSummary(nextCameraSummary)
      setDeviceSummary(nextDeviceSummary)
      setCameras(nextCameras.items)
      setDevices(nextDevices.items)
      setOptions(nextOptions)
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
}: {
  items: Camera[]
  selected: Camera | null
  onSelect: (id: number) => void
  canManage: boolean
  onEdit: (camera: Camera) => void
  onRetire: (camera: Camera) => void
}) {
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
                  label="RTSP"
                  value={
                    selected.rtsp_path
                      ? `${selected.stream_protocol} :${
                          selected.rtsp_port ?? "—"
                        }${selected.rtsp_path}`
                      : "Not configured"
                  }
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
    rtsp_port: camera?.rtsp_port ? String(camera.rtsp_port) : "554",
    rtsp_path: camera?.rtsp_path ?? "",
    onvif_port: camera?.onvif_port ? String(camera.onvif_port) : "",
    ai_enabled: camera?.ai_enabled ?? true,
    status: camera?.status ?? ("configured" as DeviceStatus),
    stream_status:
      camera?.stream_status ?? ("unconfigured" as StreamStatus),
  })
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function submit(event: FormEvent) {
    event.preventDefault()
    setSaving(true)
    setError(null)

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
      rtsp_port: numberOrNull(form.rtsp_port),
      rtsp_path: nullable(form.rtsp_path),
      onvif_port: numberOrNull(form.onvif_port),
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
              onChange={(e: ChangeEvent<HTMLInputElement>) =>
                setForm({ ...form, ip_address: e.target.value })
              }
              className={inputClass}
              placeholder="10.20.1.21"
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

        <div className="rounded-md border border-border bg-muted/20 p-3 text-xs text-muted-foreground">
          Do not paste camera usernames or passwords into the RTSP path.
          Credentials will be handled separately during secure hardware
          integration.
        </div>

        <div className="flex justify-end gap-2">
          <Button type="button" variant="outline" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" disabled={saving}>
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

function formatDate(value: string | null) {
  if (!value) return "Never"
  const date = new Date(value)
  return Number.isNaN(date.getTime())
    ? "Unknown"
    : date.toLocaleString()
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
