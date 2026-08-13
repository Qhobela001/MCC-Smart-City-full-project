"use client"

import {
  FormEvent,
  ReactNode,
  useCallback,
  useEffect,
  useMemo,
  useState,
} from "react"
import {
  AlertTriangle,
  BrainCircuit,
  CircleDot,
  Crosshair,
  Layers3,
  LoaderCircle,
  Map,
  MapPin,
  Plus,
  RefreshCw,
  Search,
  ShieldCheck,
  Trash2,
  X,
} from "lucide-react"

import { useAuth } from "@/components/auth/auth-provider"
import { apiFetch } from "@/lib/api"


type ZoneType =
  | "monitoring"
  | "vending"
  | "no_vending"
  | "waste_management"
  | "no_dumping"
  | "road_monitoring"
  | "public_space"
  | "municipal_boundary"
  | "ward"
  | "custom"

type LocationType =
  | "camera_site"
  | "intersection"
  | "road_segment"
  | "market"
  | "waste_site"
  | "public_space"
  | "municipal_facility"
  | "other"

type IncidentType =
  | "noise_pollution"
  | "illegal_dumping"
  | "skip_overflow"
  | "unauthorized_vending"
  | "street_cleaner_non_compliance"
  | "public_urination"
  | "vehicle_smoke_emission"
  | "road_damage"
  | "pothole"
  | "other"

type IncidentPriority =
  | "low"
  | "medium"
  | "high"
  | "critical"

type IncidentStatus =
  | "new"
  | "under_review"
  | "confirmed"
  | "assigned"
  | "in_progress"
  | "resolved"
  | "dismissed"

type DetectionType = IncidentType

type GeoPoint = {
  latitude: number
  longitude: number
}

type GISZone = {
  id: number
  name: string
  code: string
  zone_type: ZoneType
  description: string | null
  center_latitude: number | null
  center_longitude: number | null
  boundary: GeoPoint[]
  display_color: string
  is_active: boolean
  created_by_id: number
  location_count: number
  created_at: string
  updated_at: string
}

type GISZoneSummary = {
  id: number
  name: string
  code: string
  zone_type: ZoneType
  display_color: string
  is_active: boolean
}

type GISLocation = {
  id: number
  name: string
  code: string
  location_type: LocationType
  address: string | null
  description: string | null
  latitude: number
  longitude: number
  zone_id: number | null
  zone: GISZoneSummary | null
  is_active: boolean
  created_by_id: number
  created_at: string
  updated_at: string
}

type GISSummary = {
  total_zones: number
  active_zones: number
  zones_with_boundaries: number
  total_locations: number
  active_locations: number
  locations_assigned_to_zone: number
  linked_incidents: number
  linked_ai_detections: number
  can_manage: boolean
  generated_at: string
}

type GISMapIncident = {
  id: number
  incident_number: string
  incident_type: IncidentType
  priority: IncidentPriority
  status: IncidentStatus
  title: string
  gis_location_id: number
  zone_id: number | null
  location_name: string
  latitude: number
  longitude: number
  reported_at: string
  is_ai_generated: boolean
}

type GISMapDetection = {
  id: number
  detection_type: DetectionType
  class_name: string
  confidence: number
  gis_location_id: number
  zone_id: number | null
  incident_id: number
  camera_identifier: string | null
  location_name: string
  latitude: number
  longitude: number
  detected_at: string
}

type GISMapData = {
  incidents: GISMapIncident[]
  ai_detections: GISMapDetection[]
  generated_at: string
}

type GISZoneListResponse = {
  items: GISZone[]
  total: number
}

type GISLocationListResponse = {
  items: GISLocation[]
  total: number
}

const ZONE_TYPES: Array<{ value: ZoneType; label: string }> = [
  { value: "monitoring", label: "Monitoring zone" },
  { value: "vending", label: "Approved vending zone" },
  { value: "no_vending", label: "No-vending zone" },
  { value: "waste_management", label: "Waste management zone" },
  { value: "no_dumping", label: "No-dumping zone" },
  { value: "road_monitoring", label: "Road monitoring zone" },
  { value: "public_space", label: "Public space zone" },
  { value: "municipal_boundary", label: "Municipal boundary" },
  { value: "ward", label: "Ward" },
  { value: "custom", label: "Custom" },
]

const LOCATION_TYPES: Array<{ value: LocationType; label: string }> = [
  { value: "camera_site", label: "Camera site" },
  { value: "intersection", label: "Intersection" },
  { value: "road_segment", label: "Road segment" },
  { value: "market", label: "Market" },
  { value: "waste_site", label: "Waste site" },
  { value: "public_space", label: "Public space" },
  { value: "municipal_facility", label: "Municipal facility" },
  { value: "other", label: "Other" },
]

const emptyZoneForm = {
  name: "",
  code: "",
  zone_type: "monitoring" as ZoneType,
  description: "",
  center_latitude: "",
  center_longitude: "",
  boundary: "",
}

const emptyLocationForm = {
  name: "",
  code: "",
  location_type: "camera_site" as LocationType,
  address: "",
  description: "",
  latitude: "",
  longitude: "",
  zone_id: "",
}


export default function CityMapPage() {
  const { user } = useAuth()

  const [summary, setSummary] = useState<GISSummary | null>(null)
  const [zones, setZones] = useState<GISZone[]>([])
  const [locations, setLocations] = useState<GISLocation[]>([])
  const [mapData, setMapData] = useState<GISMapData>({
    incidents: [],
    ai_detections: [],
    generated_at: "",
  })

  const [search, setSearch] = useState("")
  const [tab, setTab] = useState<"map" | "locations" | "zones">("map")

  const [showLocations, setShowLocations] = useState(true)
  const [showIncidents, setShowIncidents] = useState(true)
  const [showDetections, setShowDetections] = useState(true)

  const [loading, setLoading] = useState(true)
  const [refreshing, setRefreshing] = useState(false)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState("")
  const [modalError, setModalError] = useState("")

  const [zoneOpen, setZoneOpen] = useState(false)
  const [locationOpen, setLocationOpen] = useState(false)
  const [zoneForm, setZoneForm] = useState({ ...emptyZoneForm })
  const [locationForm, setLocationForm] = useState({ ...emptyLocationForm })

  const canManage = Boolean(user?.is_superuser || summary?.can_manage)

  const loadGIS = useCallback(async (manual = false) => {
    if (manual) setRefreshing(true)
    else setLoading(true)

    setError("")

    try {
      const [
        summaryResponse,
        zoneResponse,
        locationResponse,
        mapResponse,
      ] = await Promise.all([
        apiFetch<GISSummary>("/gis/summary"),
        apiFetch<GISZoneListResponse>("/gis/zones?active_only=false"),
        apiFetch<GISLocationListResponse>(
          "/gis/locations?active_only=false",
        ),
        apiFetch<GISMapData>("/gis/map-data"),
      ])

      setSummary(summaryResponse)
      setZones(zoneResponse.items)
      setLocations(locationResponse.items)
      setMapData(mapResponse)
    } catch (requestError) {
      setError(
        requestError instanceof Error
          ? requestError.message
          : "Unable to load GIS data.",
      )
    } finally {
      setLoading(false)
      setRefreshing(false)
    }
  }, [])

  useEffect(() => {
    void loadGIS()
  }, [loadGIS])

  const filteredZones = useMemo(() => {
    const q = search.trim().toLowerCase()
    if (!q) return zones

    return zones.filter((zone) =>
      [zone.name, zone.code, zone.zone_type, zone.description || ""]
        .some((value) => value.toLowerCase().includes(q)),
    )
  }, [search, zones])

  const filteredLocations = useMemo(() => {
    const q = search.trim().toLowerCase()
    if (!q) return locations

    return locations.filter((location) =>
      [
        location.name,
        location.code,
        location.location_type,
        location.address || "",
        location.zone?.name || "",
      ].some((value) => value.toLowerCase().includes(q)),
    )
  }, [locations, search])

  const filteredIncidents = useMemo(() => {
    const q = search.trim().toLowerCase()
    if (!q) return mapData.incidents

    return mapData.incidents.filter((incident) =>
      [
        incident.incident_number,
        incident.title,
        incident.incident_type,
        incident.location_name,
        incident.status,
        incident.priority,
      ].some((value) => value.toLowerCase().includes(q)),
    )
  }, [mapData.incidents, search])

  const filteredDetections = useMemo(() => {
    const q = search.trim().toLowerCase()
    if (!q) return mapData.ai_detections

    return mapData.ai_detections.filter((detection) =>
      [
        detection.class_name,
        detection.detection_type,
        detection.location_name,
        detection.camera_identifier || "",
      ].some((value) => value.toLowerCase().includes(q)),
    )
  }, [mapData.ai_detections, search])

  async function createZone(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setBusy(true)
    setModalError("")

    try {
      const lat = zoneForm.center_latitude.trim()
      const lon = zoneForm.center_longitude.trim()

      if (Boolean(lat) !== Boolean(lon)) {
        throw new Error(
          "Zone center latitude and longitude must be supplied together.",
        )
      }

      await apiFetch<GISZone>("/gis/zones", {
        method: "POST",
        body: JSON.stringify({
          name: zoneForm.name.trim(),
          code: zoneForm.code.trim(),
          zone_type: zoneForm.zone_type,
          description: zoneForm.description.trim() || null,
          center_latitude: lat ? Number(lat) : null,
          center_longitude: lon ? Number(lon) : null,
          boundary: parseBoundary(zoneForm.boundary),
          display_color: "#2563EB",
          is_active: true,
        }),
      })

      setZoneOpen(false)
      setZoneForm({ ...emptyZoneForm })
      await loadGIS(true)
    } catch (requestError) {
      setModalError(
        requestError instanceof Error
          ? requestError.message
          : "Unable to create zone.",
      )
    } finally {
      setBusy(false)
    }
  }

  async function createLocation(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setBusy(true)
    setModalError("")

    try {
      await apiFetch<GISLocation>("/gis/locations", {
        method: "POST",
        body: JSON.stringify({
          name: locationForm.name.trim(),
          code: locationForm.code.trim(),
          location_type: locationForm.location_type,
          address: locationForm.address.trim() || null,
          description: locationForm.description.trim() || null,
          latitude: Number(locationForm.latitude),
          longitude: Number(locationForm.longitude),
          zone_id: locationForm.zone_id
            ? Number(locationForm.zone_id)
            : null,
          is_active: true,
        }),
      })

      setLocationOpen(false)
      setLocationForm({ ...emptyLocationForm })
      await loadGIS(true)
    } catch (requestError) {
      setModalError(
        requestError instanceof Error
          ? requestError.message
          : "Unable to create location.",
      )
    } finally {
      setBusy(false)
    }
  }

  async function removeLocation(location: GISLocation) {
    if (!window.confirm(`Delete "${location.name}"?`)) return

    setBusy(true)
    try {
      await apiFetch<void>(`/gis/locations/${location.id}`, {
        method: "DELETE",
      })
      await loadGIS(true)
    } catch (requestError) {
      setError(
        requestError instanceof Error
          ? requestError.message
          : "Unable to delete location.",
      )
    } finally {
      setBusy(false)
    }
  }

  async function removeZone(zone: GISZone) {
    if (!window.confirm(`Delete "${zone.name}"?`)) return

    setBusy(true)
    try {
      await apiFetch<void>(`/gis/zones/${zone.id}`, {
        method: "DELETE",
      })
      await loadGIS(true)
    } catch (requestError) {
      setError(
        requestError instanceof Error
          ? requestError.message
          : "Unable to delete zone.",
      )
    } finally {
      setBusy(false)
    }
  }

  if (loading) {
    return (
      <div className="flex min-h-[60vh] items-center justify-center">
        <div className="flex items-center gap-3 text-sm text-muted-foreground">
          <LoaderCircle className="size-5 animate-spin text-primary" />
          Loading MCC GIS workspace...
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-5">
      <section className="rounded-2xl border bg-card p-5 md:p-7">
        <div className="flex flex-col gap-5 lg:flex-row lg:items-end lg:justify-between">
          <div>
            <div className="mb-3 inline-flex items-center gap-2 rounded-full border bg-background px-3 py-1 text-xs text-muted-foreground">
              <CircleDot className="size-3.5 text-emerald-500" />
              Geographic intelligence layer active
            </div>

            <h1 className="text-2xl font-semibold tracking-tight md:text-3xl">
              City GIS & Zones
            </h1>

            <p className="mt-2 max-w-3xl text-sm leading-6 text-muted-foreground">
              MCC geographic locations now connect to operational incidents
              and AI detections while preserving event-time coordinate
              snapshots for audit and history.
            </p>
          </div>

          <div className="flex flex-wrap gap-2">
            <button
              type="button"
              onClick={() => void loadGIS(true)}
              disabled={refreshing || busy}
              className="inline-flex h-10 items-center gap-2 rounded-md border px-4 text-sm font-medium hover:bg-muted disabled:opacity-50"
            >
              <RefreshCw
                className={`size-4 ${refreshing ? "animate-spin" : ""}`}
              />
              Refresh
            </button>

            {canManage && (
              <>
                <button
                  type="button"
                  onClick={() => {
                    setModalError("")
                    setZoneForm({ ...emptyZoneForm })
                    setZoneOpen(true)
                  }}
                  className="inline-flex h-10 items-center gap-2 rounded-md border px-4 text-sm font-medium hover:bg-muted"
                >
                  <Layers3 className="size-4" />
                  New zone
                </button>

                <button
                  type="button"
                  onClick={() => {
                    setModalError("")
                    setLocationForm({ ...emptyLocationForm })
                    setLocationOpen(true)
                  }}
                  className="inline-flex h-10 items-center gap-2 rounded-md bg-primary px-4 text-sm font-medium text-primary-foreground"
                >
                  <Plus className="size-4" />
                  New location
                </button>
              </>
            )}
          </div>
        </div>
      </section>

      {error && (
        <div className="rounded-lg border border-destructive/30 bg-destructive/10 p-4 text-sm text-destructive">
          {error}
        </div>
      )}

      <section className="grid grid-cols-2 gap-3 xl:grid-cols-4">
        <Metric
          label="Active locations"
          value={summary?.active_locations ?? 0}
          detail={`${summary?.total_locations ?? 0} total GIS locations`}
          icon={<MapPin className="size-5" />}
        />

        <Metric
          label="Active zones"
          value={summary?.active_zones ?? 0}
          detail={`${summary?.zones_with_boundaries ?? 0} polygon zones`}
          icon={<Layers3 className="size-5" />}
        />

        <Metric
          label="Mapped incidents"
          value={summary?.linked_incidents ?? 0}
          detail="Incidents with structured GIS location"
          icon={<AlertTriangle className="size-5" />}
        />

        <Metric
          label="Mapped AI detections"
          value={summary?.linked_ai_detections ?? 0}
          detail="Non-test detections linked to GIS"
          icon={<BrainCircuit className="size-5" />}
        />
      </section>

      <section className="rounded-xl border bg-card">
        <div className="flex flex-col gap-3 border-b p-4 xl:flex-row xl:items-center xl:justify-between">
          <div className="flex flex-wrap gap-1 rounded-lg bg-muted/50 p-1">
            {(["map", "locations", "zones"] as const).map((value) => (
              <button
                key={value}
                type="button"
                onClick={() => setTab(value)}
                className={`rounded-md px-3 py-2 text-xs font-medium ${
                  tab === value
                    ? "bg-background text-foreground shadow-sm"
                    : "text-muted-foreground"
                }`}
              >
                {value === "map" ? "City Map" : humanize(value)}
              </button>
            ))}
          </div>

          <div className="flex h-10 w-full items-center gap-2 rounded-md border px-3 xl:w-80">
            <Search className="size-4 text-muted-foreground" />
            <input
              value={search}
              onChange={(event) => setSearch(event.target.value)}
              placeholder="Search GIS and map events..."
              className="w-full bg-transparent text-sm outline-none"
            />
          </div>
        </div>

        {tab === "map" && (
          <div className="space-y-4 p-4 md:p-5">
            <div className="flex flex-col gap-3 xl:flex-row xl:items-end xl:justify-between">
              <div>
                <h2 className="text-base font-semibold">
                  MCC operational map
                </h2>
                <p className="mt-1 max-w-2xl text-xs leading-5 text-muted-foreground">
                  Structured GIS sites, operational incidents and their
                  linked AI observations now share one geographic view.
                  The street basemap remains a later rendering upgrade.
                </p>
              </div>

              <div className="flex flex-wrap gap-2">
                <LayerToggle
                  checked={showLocations}
                  onChange={setShowLocations}
                  label="Locations"
                  markerClass="bg-primary"
                />
                <LayerToggle
                  checked={showIncidents}
                  onChange={setShowIncidents}
                  label="Incidents"
                  markerClass="bg-destructive"
                />
                <LayerToggle
                  checked={showDetections}
                  onChange={setShowDetections}
                  label="AI detections"
                  markerClass="bg-amber-500"
                />
              </div>
            </div>

            <CoveragePreview
              zones={filteredZones}
              locations={showLocations ? filteredLocations : []}
              incidents={showIncidents ? filteredIncidents : []}
              detections={showDetections ? filteredDetections : []}
            />

            <div className="grid gap-4 xl:grid-cols-2">
              <RecentIncidents incidents={filteredIncidents} />
              <RecentDetections detections={filteredDetections} />
            </div>
          </div>
        )}

        {tab === "locations" && (
          <div className="divide-y">
            {filteredLocations.length === 0 ? (
              <EmptyState text="No GIS locations match the current search." />
            ) : (
              filteredLocations.map((location) => (
                <div
                  key={location.id}
                  className="flex flex-col gap-3 p-4 lg:flex-row lg:items-center"
                >
                  <div className="rounded-lg bg-primary/10 p-3 text-primary">
                    <MapPin className="size-5" />
                  </div>

                  <div className="min-w-0 flex-1">
                    <div className="flex flex-wrap items-center gap-2">
                      <p className="font-medium">{location.name}</p>
                      <Badge active={location.is_active} />
                      <span className="text-xs text-muted-foreground">
                        {humanize(location.location_type)}
                      </span>
                    </div>

                    <p className="mt-1 text-xs text-muted-foreground">
                      {location.code} · {location.latitude.toFixed(6)},{" "}
                      {location.longitude.toFixed(6)} ·{" "}
                      {location.zone?.name || "No zone"}
                    </p>
                  </div>

                  {canManage && (
                    <button
                      type="button"
                      onClick={() => void removeLocation(location)}
                      disabled={busy}
                      className="inline-flex size-9 items-center justify-center rounded-md border text-destructive hover:bg-destructive/10 disabled:opacity-50"
                    >
                      <Trash2 className="size-4" />
                    </button>
                  )}
                </div>
              ))
            )}
          </div>
        )}

        {tab === "zones" && (
          <div className="divide-y">
            {filteredZones.length === 0 ? (
              <EmptyState text="No GIS zones match the current search." />
            ) : (
              filteredZones.map((zone) => (
                <div
                  key={zone.id}
                  className="flex flex-col gap-3 p-4 lg:flex-row lg:items-center"
                >
                  <div className="rounded-lg bg-primary/10 p-3 text-primary">
                    <Layers3 className="size-5" />
                  </div>

                  <div className="min-w-0 flex-1">
                    <div className="flex flex-wrap items-center gap-2">
                      <p className="font-medium">{zone.name}</p>
                      <Badge active={zone.is_active} />
                      <span className="text-xs text-muted-foreground">
                        {humanize(zone.zone_type)}
                      </span>
                    </div>

                    <p className="mt-1 text-xs text-muted-foreground">
                      {zone.code} · {zone.location_count} locations ·{" "}
                      {zone.boundary.length} boundary points
                    </p>
                  </div>

                  {canManage && (
                    <button
                      type="button"
                      onClick={() => void removeZone(zone)}
                      disabled={busy}
                      className="inline-flex size-9 items-center justify-center rounded-md border text-destructive hover:bg-destructive/10 disabled:opacity-50"
                    >
                      <Trash2 className="size-4" />
                    </button>
                  )}
                </div>
              ))
            )}
          </div>
        )}
      </section>

      <section className="grid gap-4 lg:grid-cols-2">
        <div className="rounded-xl border bg-card p-5">
          <div className="flex items-start gap-3">
            <div className="rounded-lg bg-primary/10 p-2.5 text-primary">
              <Crosshair className="size-5" />
            </div>
            <div>
              <h3 className="text-sm font-semibold">
                Canonical location + historical snapshot
              </h3>
              <p className="mt-1 text-xs leading-5 text-muted-foreground">
                Incidents and AI detections now store a GIS location ID while
                retaining the resolved location name and coordinates captured
                at event time. This keeps the current geographic relationship
                structured without losing historical context.
              </p>
            </div>
          </div>
        </div>

        <div className="rounded-xl border bg-card p-5">
          <div className="flex items-start gap-3">
            <div className="rounded-lg bg-primary/10 p-2.5 text-primary">
              <ShieldCheck className="size-5" />
            </div>
            <div>
              <h3 className="text-sm font-semibold">
                Incident visibility is preserved
              </h3>
              <p className="mt-1 text-xs leading-5 text-muted-foreground">
                The operational map only surfaces incidents visible to the
                signed-in MCC user and AI observations already attached to
                those visible incidents.
              </p>
            </div>
          </div>
        </div>
      </section>

      {zoneOpen && (
        <Modal title="Create GIS zone" onClose={() => !busy && setZoneOpen(false)}>
          <form onSubmit={createZone} className="space-y-4">
            <ModalError message={modalError} />

            <div className="grid gap-4 sm:grid-cols-2">
              <Field
                label="Zone name"
                value={zoneForm.name}
                onChange={(value) =>
                  setZoneForm((current) => ({ ...current, name: value }))
                }
                required
              />

              <Field
                label="Zone code"
                value={zoneForm.code}
                onChange={(value) =>
                  setZoneForm((current) => ({ ...current, code: value }))
                }
                required
              />

              <SelectField
                label="Zone type"
                value={zoneForm.zone_type}
                onChange={(value) =>
                  setZoneForm((current) => ({
                    ...current,
                    zone_type: value as ZoneType,
                  }))
                }
              >
                {ZONE_TYPES.map((item) => (
                  <option key={item.value} value={item.value}>
                    {item.label}
                  </option>
                ))}
              </SelectField>

              <Field
                label="Description"
                value={zoneForm.description}
                onChange={(value) =>
                  setZoneForm((current) => ({
                    ...current,
                    description: value,
                  }))
                }
              />

              <Field
                label="Center latitude"
                type="number"
                step="any"
                value={zoneForm.center_latitude}
                onChange={(value) =>
                  setZoneForm((current) => ({
                    ...current,
                    center_latitude: value,
                  }))
                }
              />

              <Field
                label="Center longitude"
                type="number"
                step="any"
                value={zoneForm.center_longitude}
                onChange={(value) =>
                  setZoneForm((current) => ({
                    ...current,
                    center_longitude: value,
                  }))
                }
              />

              <label className="grid gap-1.5 text-xs font-medium sm:col-span-2">
                Boundary points
                <textarea
                  value={zoneForm.boundary}
                  onChange={(event) =>
                    setZoneForm((current) => ({
                      ...current,
                      boundary: event.target.value,
                    }))
                  }
                  rows={5}
                  placeholder={"One latitude,longitude point per line"}
                  className="rounded-md border bg-background px-3 py-2 text-sm font-normal outline-none"
                />
              </label>
            </div>

            <Actions
              busy={busy}
              submitLabel="Create zone"
              onCancel={() => setZoneOpen(false)}
            />
          </form>
        </Modal>
      )}

      {locationOpen && (
        <Modal
          title="Create GIS location"
          onClose={() => !busy && setLocationOpen(false)}
        >
          <form onSubmit={createLocation} className="space-y-4">
            <ModalError message={modalError} />

            <div className="grid gap-4 sm:grid-cols-2">
              <Field
                label="Location name"
                value={locationForm.name}
                onChange={(value) =>
                  setLocationForm((current) => ({
                    ...current,
                    name: value,
                  }))
                }
                required
              />

              <Field
                label="Location code"
                value={locationForm.code}
                onChange={(value) =>
                  setLocationForm((current) => ({
                    ...current,
                    code: value,
                  }))
                }
                required
              />

              <SelectField
                label="Location type"
                value={locationForm.location_type}
                onChange={(value) =>
                  setLocationForm((current) => ({
                    ...current,
                    location_type: value as LocationType,
                  }))
                }
              >
                {LOCATION_TYPES.map((item) => (
                  <option key={item.value} value={item.value}>
                    {item.label}
                  </option>
                ))}
              </SelectField>

              <SelectField
                label="Zone"
                value={locationForm.zone_id}
                onChange={(value) =>
                  setLocationForm((current) => ({
                    ...current,
                    zone_id: value,
                  }))
                }
              >
                <option value="">No zone</option>
                {zones.filter((zone) => zone.is_active).map((zone) => (
                  <option key={zone.id} value={zone.id}>
                    {zone.name}
                  </option>
                ))}
              </SelectField>

              <Field
                label="Latitude"
                type="number"
                step="any"
                value={locationForm.latitude}
                onChange={(value) =>
                  setLocationForm((current) => ({
                    ...current,
                    latitude: value,
                  }))
                }
                required
              />

              <Field
                label="Longitude"
                type="number"
                step="any"
                value={locationForm.longitude}
                onChange={(value) =>
                  setLocationForm((current) => ({
                    ...current,
                    longitude: value,
                  }))
                }
                required
              />

              <Field
                label="Address / place"
                value={locationForm.address}
                onChange={(value) =>
                  setLocationForm((current) => ({
                    ...current,
                    address: value,
                  }))
                }
              />

              <Field
                label="Description"
                value={locationForm.description}
                onChange={(value) =>
                  setLocationForm((current) => ({
                    ...current,
                    description: value,
                  }))
                }
              />
            </div>

            <Actions
              busy={busy}
              submitLabel="Create location"
              onCancel={() => setLocationOpen(false)}
            />
          </form>
        </Modal>
      )}
    </div>
  )
}


function CoveragePreview({
  zones,
  locations,
  incidents,
  detections,
}: {
  zones: GISZone[]
  locations: GISLocation[]
  incidents: GISMapIncident[]
  detections: GISMapDetection[]
}) {
  const points: GeoPoint[] = [
    ...locations.map((item) => ({
      latitude: item.latitude,
      longitude: item.longitude,
    })),
    ...incidents.map((item) => ({
      latitude: item.latitude,
      longitude: item.longitude,
    })),
    ...detections.map((item) => ({
      latitude: item.latitude,
      longitude: item.longitude,
    })),
    ...zones.flatMap((item) => item.boundary),
  ]

  for (const zone of zones) {
    if (
      zone.center_latitude !== null
      && zone.center_longitude !== null
    ) {
      points.push({
        latitude: zone.center_latitude,
        longitude: zone.center_longitude,
      })
    }
  }

  const minLat = points.length
    ? Math.min(...points.map((item) => item.latitude)) - 0.01
    : -29.45

  const maxLat = points.length
    ? Math.max(...points.map((item) => item.latitude)) + 0.01
    : -29.15

  const minLon = points.length
    ? Math.min(...points.map((item) => item.longitude)) - 0.01
    : 27.35

  const maxLon = points.length
    ? Math.max(...points.map((item) => item.longitude)) + 0.01
    : 27.65

  function project(point: GeoPoint) {
    return {
      x: ((point.longitude - minLon) / (maxLon - minLon)) * 1000,
      y: ((maxLat - point.latitude) / (maxLat - minLat)) * 520,
    }
  }

  return (
    <div className="relative overflow-hidden rounded-xl border bg-muted/15">
      <svg
        viewBox="0 0 1000 520"
        className="h-[440px] w-full md:h-[560px]"
        role="img"
        aria-label="MCC GIS operational map preview"
      >
        <defs>
          <pattern
            id="gis-phase2-grid"
            width="50"
            height="50"
            patternUnits="userSpaceOnUse"
          >
            <path
              d="M 50 0 L 0 0 0 50"
              fill="none"
              stroke="currentColor"
              strokeOpacity="0.08"
              strokeWidth="1"
            />
          </pattern>
        </defs>

        <rect
          width="1000"
          height="520"
          fill="url(#gis-phase2-grid)"
          className="text-foreground"
        />

        {zones.map((zone) => {
          if (zone.boundary.length < 3) return null

          const polygon = zone.boundary
            .map((point) => {
              const p = project(point)
              return `${p.x},${p.y}`
            })
            .join(" ")

          return (
            <polygon
              key={`zone-${zone.id}`}
              points={polygon}
              fill={zone.display_color}
              fillOpacity={0.1}
              stroke={zone.display_color}
              strokeWidth="3"
              strokeOpacity={zone.is_active ? 0.85 : 0.3}
            >
              <title>
                {zone.name} · {humanize(zone.zone_type)}
              </title>
            </polygon>
          )
        })}

        {locations.map((location) => {
          const p = project(location)

          return (
            <g key={`location-${location.id}`}>
              <circle
                cx={p.x}
                cy={p.y}
                r="8"
                className="fill-primary stroke-background"
                strokeWidth="3"
                opacity={location.is_active ? 1 : 0.35}
              />
              <title>
                {location.name} · GIS location
              </title>
            </g>
          )
        })}

        {detections.map((detection) => {
          const p = project(detection)

          return (
            <g key={`detection-${detection.id}`}>
              <circle
                cx={p.x}
                cy={p.y}
                r="19"
                fill="none"
                className="stroke-amber-500"
                strokeWidth="4"
                strokeDasharray="5 4"
              />
              <title>
                {humanize(detection.detection_type)} ·{" "}
                {(detection.confidence * 100).toFixed(1)}% ·{" "}
                {detection.location_name}
              </title>
            </g>
          )
        })}

        {incidents.map((incident) => {
          const p = project(incident)

          const triangle = [
            `${p.x},${p.y - 16}`,
            `${p.x - 15},${p.y + 13}`,
            `${p.x + 15},${p.y + 13}`,
          ].join(" ")

          return (
            <g key={`incident-${incident.id}`}>
              <polygon
                points={triangle}
                className="fill-destructive stroke-background"
                strokeWidth="4"
              />
              <title>
                {incident.incident_number} ·{" "}
                {humanize(incident.incident_type)} ·{" "}
                {humanize(incident.priority)} ·{" "}
                {incident.location_name}
              </title>
            </g>
          )
        })}
      </svg>

      {points.length === 0 && (
        <div className="absolute inset-0 flex items-center justify-center">
          <div className="rounded-xl border bg-background/90 p-5 text-center shadow-sm">
            <MapPin className="mx-auto size-7 text-muted-foreground" />
            <p className="mt-2 text-sm font-medium">
              No geographic data in the current view
            </p>
            <p className="mt-1 text-xs text-muted-foreground">
              Create a GIS location or clear the search filter.
            </p>
          </div>
        </div>
      )}

      <div className="absolute bottom-3 left-3 rounded-lg border bg-background/90 px-3 py-2 text-[10px] text-muted-foreground shadow-sm">
        <p>
          Lat {minLat.toFixed(4)} → {maxLat.toFixed(4)}
        </p>
        <p>
          Lon {minLon.toFixed(4)} → {maxLon.toFixed(4)}
        </p>
      </div>
    </div>
  )
}


function RecentIncidents({
  incidents,
}: {
  incidents: GISMapIncident[]
}) {
  return (
    <div className="rounded-xl border">
      <div className="border-b p-4">
        <div className="flex items-center gap-2">
          <AlertTriangle className="size-4 text-destructive" />
          <h3 className="text-sm font-semibold">
            Recent mapped incidents
          </h3>
        </div>
      </div>

      <div className="divide-y">
        {incidents.length === 0 ? (
          <div className="p-5 text-xs text-muted-foreground">
            No GIS-linked incidents are visible yet.
          </div>
        ) : (
          incidents.slice(0, 5).map((incident) => (
            <div key={incident.id} className="p-4">
              <div className="flex flex-wrap items-center gap-2">
                <span className="font-mono text-xs font-semibold">
                  {incident.incident_number}
                </span>
                <span className="rounded-full bg-muted px-2 py-0.5 text-[10px] text-muted-foreground">
                  {humanize(incident.status)}
                </span>
                <span className="rounded-full bg-destructive/10 px-2 py-0.5 text-[10px] text-destructive">
                  {humanize(incident.priority)}
                </span>
              </div>

              <p className="mt-2 text-sm font-medium">
                {incident.title}
              </p>
              <p className="mt-1 text-xs text-muted-foreground">
                {incident.location_name} ·{" "}
                {formatDate(incident.reported_at)}
              </p>
            </div>
          ))
        )}
      </div>
    </div>
  )
}


function RecentDetections({
  detections,
}: {
  detections: GISMapDetection[]
}) {
  return (
    <div className="rounded-xl border">
      <div className="border-b p-4">
        <div className="flex items-center gap-2">
          <BrainCircuit className="size-4 text-amber-500" />
          <h3 className="text-sm font-semibold">
            Recent mapped AI observations
          </h3>
        </div>
      </div>

      <div className="divide-y">
        {detections.length === 0 ? (
          <div className="p-5 text-xs text-muted-foreground">
            No GIS-linked AI detections are attached to visible incidents yet.
          </div>
        ) : (
          detections.slice(0, 5).map((detection) => (
            <div key={detection.id} className="p-4">
              <div className="flex flex-wrap items-center gap-2">
                <span className="text-sm font-medium">
                  {humanize(detection.detection_type)}
                </span>
                <span className="rounded-full bg-amber-500/10 px-2 py-0.5 text-[10px] text-amber-600">
                  {(detection.confidence * 100).toFixed(1)}%
                </span>
              </div>

              <p className="mt-1 text-xs text-muted-foreground">
                {detection.location_name}
                {detection.camera_identifier
                  ? ` · ${detection.camera_identifier}`
                  : ""}
                {" · "}
                {formatDate(detection.detected_at)}
              </p>
            </div>
          ))
        )}
      </div>
    </div>
  )
}


function LayerToggle({
  checked,
  onChange,
  label,
  markerClass,
}: {
  checked: boolean
  onChange: (value: boolean) => void
  label: string
  markerClass: string
}) {
  return (
    <label className="inline-flex cursor-pointer items-center gap-2 rounded-md border bg-background px-3 py-2 text-xs font-medium">
      <input
        type="checkbox"
        checked={checked}
        onChange={(event) => onChange(event.target.checked)}
        className="size-3.5"
      />
      <span className={`size-2.5 rounded-full ${markerClass}`} />
      {label}
    </label>
  )
}


function Metric({
  label,
  value,
  detail,
  icon,
}: {
  label: string
  value: number
  detail: string
  icon: ReactNode
}) {
  return (
    <div className="rounded-xl border bg-card p-4">
      <div className="flex items-start justify-between">
        <div>
          <p className="text-xs text-muted-foreground">{label}</p>
          <p className="mt-2 font-mono text-2xl font-semibold">{value}</p>
        </div>

        <div className="rounded-lg bg-primary/10 p-2.5 text-primary">
          {icon}
        </div>
      </div>

      <p className="mt-3 text-[11px] text-muted-foreground">{detail}</p>
    </div>
  )
}


function Badge({ active }: { active: boolean }) {
  return (
    <span
      className={`rounded-full px-2 py-0.5 text-[10px] font-semibold ${
        active
          ? "bg-emerald-500/10 text-emerald-500"
          : "bg-muted text-muted-foreground"
      }`}
    >
      {active ? "Active" : "Inactive"}
    </span>
  )
}


function EmptyState({ text }: { text: string }) {
  return (
    <div className="flex min-h-48 items-center justify-center p-8 text-sm text-muted-foreground">
      {text}
    </div>
  )
}


function Modal({
  title,
  onClose,
  children,
}: {
  title: string
  onClose: () => void
  children: ReactNode
}) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/55 p-4">
      <div className="max-h-[90vh] w-full max-w-2xl overflow-y-auto rounded-xl border bg-background shadow-2xl">
        <div className="flex items-center justify-between border-b px-5 py-4">
          <h2 className="font-semibold">{title}</h2>

          <button type="button" onClick={onClose}>
            <X className="size-4" />
          </button>
        </div>

        <div className="p-5">{children}</div>
      </div>
    </div>
  )
}


function ModalError({ message }: { message: string }) {
  if (!message) return null

  return (
    <div className="rounded-md border border-destructive/30 bg-destructive/10 p-3 text-xs text-destructive">
      {message}
    </div>
  )
}


function Actions({
  busy,
  submitLabel,
  onCancel,
}: {
  busy: boolean
  submitLabel: string
  onCancel: () => void
}) {
  return (
    <div className="flex justify-end gap-2 border-t pt-4">
      <button
        type="button"
        onClick={onCancel}
        disabled={busy}
        className="h-10 rounded-md border px-4 text-sm font-medium"
      >
        Cancel
      </button>

      <button
        type="submit"
        disabled={busy}
        className="inline-flex h-10 items-center gap-2 rounded-md bg-primary px-4 text-sm font-medium text-primary-foreground"
      >
        {busy && <LoaderCircle className="size-4 animate-spin" />}
        {submitLabel}
      </button>
    </div>
  )
}


function Field({
  label,
  value,
  onChange,
  type = "text",
  step,
  required = false,
}: {
  label: string
  value: string
  onChange: (value: string) => void
  type?: string
  step?: string
  required?: boolean
}) {
  return (
    <label className="grid gap-1.5 text-xs font-medium">
      {label}

      <input
        type={type}
        step={step}
        value={value}
        required={required}
        onChange={(event) => onChange(event.target.value)}
        className="h-10 rounded-md border bg-background px-3 text-sm font-normal outline-none"
      />
    </label>
  )
}


function SelectField({
  label,
  value,
  onChange,
  children,
}: {
  label: string
  value: string
  onChange: (value: string) => void
  children: ReactNode
}) {
  return (
    <label className="grid gap-1.5 text-xs font-medium">
      {label}

      <select
        value={value}
        onChange={(event) => onChange(event.target.value)}
        className="h-10 rounded-md border bg-background px-3 text-sm font-normal"
      >
        {children}
      </select>
    </label>
  )
}


function parseBoundary(value: string): GeoPoint[] {
  const lines = value
    .split(/\r?\n/)
    .map((line) => line.trim())
    .filter(Boolean)

  if (lines.length === 0) return []

  if (lines.length < 3) {
    throw new Error("A boundary needs at least three points.")
  }

  return lines.map((line, index) => {
    const [latText, lonText] = line.split(",").map((part) => part.trim())
    const latitude = Number(latText)
    const longitude = Number(lonText)

    if (
      !latText
      || !lonText
      || Number.isNaN(latitude)
      || Number.isNaN(longitude)
      || latitude < -90
      || latitude > 90
      || longitude < -180
      || longitude > 180
    ) {
      throw new Error(
        `Boundary line ${index + 1} must be valid latitude,longitude.`,
      )
    }

    return { latitude, longitude }
  })
}


function humanize(value: string) {
  return value
    .replace(/_/g, " ")
    .replace(/\b\w/g, (character) => character.toUpperCase())
}


function formatDate(value: string) {
  const date = new Date(value)

  if (Number.isNaN(date.getTime())) {
    return value
  }

  return date.toLocaleString()
}
