"use client"

import { useCallback, useEffect, useMemo, useState } from "react"
import {
  Cctv,
  Grid2X2,
  Grid3X3,
  Loader2,
  MonitorUp,
  RefreshCw,
  Search,
  ShieldCheck,
  Square,
} from "lucide-react"

import { apiFetch } from "@/lib/api"
import { LiveCameraTile } from "@/components/live-monitoring/live-camera-tile"
import type {
  LiveCamera,
  LiveStreamListResponse,
} from "@/components/live-monitoring/types"


type LayoutCount = 1 | 4 | 9 | 16

const layoutOptions: Array<{
  count: LayoutCount
  label: string
  icon: typeof Square
}> = [
  { count: 1, label: "1", icon: Square },
  { count: 4, label: "4", icon: Grid2X2 },
  { count: 9, label: "9", icon: Grid3X3 },
  { count: 16, label: "16", icon: MonitorUp },
]

function gridClass(count: LayoutCount) {
  if (count === 1) return "grid-cols-1"
  if (count === 4) return "grid-cols-1 xl:grid-cols-2"
  if (count === 9) return "grid-cols-1 md:grid-cols-2 2xl:grid-cols-3"
  return "grid-cols-1 md:grid-cols-2 xl:grid-cols-3 2xl:grid-cols-4"
}

function fillSlots(
  existing: Array<string | null>,
  cameras: LiveCamera[],
  count: LayoutCount,
) {
  const validIdentifiers = new Set(
    cameras.map((camera) => camera.camera_identifier),
  )
  const next: Array<string | null> = existing
    .filter((identifier) => !identifier || validIdentifiers.has(identifier))
    .slice(0, count)

  const used = new Set(next.filter(Boolean) as string[])

  for (const camera of cameras) {
    if (next.length >= count) break
    if (used.has(camera.camera_identifier)) continue
    next.push(camera.camera_identifier)
    used.add(camera.camera_identifier)
  }

  while (next.length < count) next.push(null)
  return next
}

export default function LiveFeedsPage() {
  const [data, setData] = useState<LiveStreamListResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [search, setSearch] = useState("")
  const [layoutCount, setLayoutCount] = useState<LayoutCount>(4)
  const [slots, setSlots] = useState<Array<string | null>>([])

  const load = useCallback(async (showSpinner = false) => {
    if (showSpinner) setLoading(true)

    try {
      const response = await apiFetch<LiveStreamListResponse>(
        "/live-streams",
      )
      setData(response)
      setError(null)
      setSlots((current) =>
        fillSlots(current, response.items, layoutCount),
      )
    } catch (reason) {
      setError(
        reason instanceof Error
          ? reason.message
          : "Unable to load live cameras.",
      )
    } finally {
      setLoading(false)
    }
  }, [layoutCount])

  useEffect(() => {
    void load(true)
    const interval = window.setInterval(() => void load(false), 15000)
    return () => window.clearInterval(interval)
  }, [load])

  useEffect(() => {
    if (!data) return
    setSlots((current) => fillSlots(current, data.items, layoutCount))
  }, [layoutCount, data])

  const cameras = data?.items ?? []

  const filteredCameras = useMemo(() => {
    const query = search.trim().toLowerCase()
    if (!query) return cameras

    return cameras.filter((camera) =>
      [
        camera.name,
        camera.camera_identifier,
        camera.location_name || "",
        camera.assigned_jetson_identifier || "",
      ].some((value) => value.toLowerCase().includes(query)),
    )
  }, [cameras, search])

  const cameraMap = useMemo(
    () => new Map(cameras.map((camera) => [camera.camera_identifier, camera])),
    [cameras],
  )

  const configuredCount = cameras.filter((camera) => camera.stream_configured).length
  const readyCount = cameras.filter((camera) => camera.gateway_ready).length

  function changeLayout(count: LayoutCount) {
    setLayoutCount(count)
    setSlots((current) => fillSlots(current, cameras, count))
  }

  function changeSlot(index: number, identifier: string) {
    setSlots((current) => {
      const next = [...current]
      next[index] = identifier || null
      return next
    })
  }

  return (
    <div className="flex min-h-0 flex-col gap-4">
      <section className="rounded-xl border border-border bg-card p-4 shadow-sm md:p-5">
        <div className="flex flex-col gap-4 xl:flex-row xl:items-center">
          <div className="min-w-0 flex-1">
            <div className="flex items-center gap-2">
              <Cctv className="size-5 text-primary" />
              <h2 className="text-lg font-semibold">Live Monitoring</h2>
            </div>
            <p className="mt-1 max-w-3xl text-sm text-muted-foreground">
              Authorized control-room view of registered MCC cameras. Live video is delivered by the HQ stream gateway while Jetson AI processing continues independently from the same source stream.
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-2">
            <span className="inline-flex items-center gap-2 rounded-full border border-border px-3 py-1.5 text-xs text-muted-foreground">
              <ShieldCheck className="size-3.5" />
              Authorized viewing
            </span>
            <span
              className={`inline-flex items-center gap-2 rounded-full px-3 py-1.5 text-xs font-medium ${
                data?.gateway_available
                  ? "bg-emerald-500/15 text-emerald-400"
                  : "bg-amber-500/15 text-amber-400"
              }`}
            >
              <span className="size-2 rounded-full bg-current" />
              {data?.gateway_available
                ? "Stream gateway online"
                : "Stream gateway offline"}
            </span>
            <button
              type="button"
              onClick={() => void load(true)}
              className="inline-flex items-center gap-2 rounded-md border border-border px-3 py-2 text-sm font-medium transition hover:bg-accent"
            >
              <RefreshCw className="size-4" />
              Refresh
            </button>
          </div>
        </div>

        <div className="mt-4 grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
          <div className="rounded-lg bg-muted/45 p-3">
            <p className="text-xs uppercase tracking-wide text-muted-foreground">Registered cameras</p>
            <p className="mt-1 text-xl font-semibold">{cameras.length}</p>
          </div>
          <div className="rounded-lg bg-muted/45 p-3">
            <p className="text-xs uppercase tracking-wide text-muted-foreground">Stream configured</p>
            <p className="mt-1 text-xl font-semibold">{configuredCount}</p>
          </div>
          <div className="rounded-lg bg-muted/45 p-3">
            <p className="text-xs uppercase tracking-wide text-muted-foreground">Live paths ready</p>
            <p className="mt-1 text-xl font-semibold">{readyCount}</p>
          </div>
          <div className="rounded-lg bg-muted/45 p-3">
            <p className="text-xs uppercase tracking-wide text-muted-foreground">Gateway ready</p>
            <p className="mt-1 text-xl font-semibold">
              {data?.gateway_available ? 1 : 0}
            </p>
          </div>
        </div>
      </section>

      <section className="flex flex-col gap-3 rounded-xl border border-border bg-card p-3 shadow-sm lg:flex-row lg:items-center">
        <div className="relative min-w-0 flex-1 lg:max-w-md">
          <Search className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
          <input
            value={search}
            onChange={(event) => setSearch(event.target.value)}
            placeholder="Search cameras, locations or Jetson…"
            className="h-10 w-full rounded-md border border-input bg-background pl-9 pr-3 text-sm outline-none ring-offset-background placeholder:text-muted-foreground focus:ring-2 focus:ring-ring"
          />
        </div>

        <div className="flex items-center gap-2 lg:ml-auto">
          <span className="mr-1 text-xs font-medium text-muted-foreground">
            Wall layout
          </span>
          {layoutOptions.map(({ count, label, icon: Icon }) => (
            <button
              key={count}
              type="button"
              onClick={() => changeLayout(count)}
              title={`${count}-camera layout`}
              className={`inline-flex h-9 min-w-9 items-center justify-center gap-1 rounded-md border px-2 text-xs font-semibold transition ${
                layoutCount === count
                  ? "border-primary bg-primary/10 text-primary"
                  : "border-border text-muted-foreground hover:bg-accent hover:text-foreground"
              }`}
            >
              <Icon className="size-3.5" />
              {label}
            </button>
          ))}
        </div>
      </section>

      {error && (
        <div className="rounded-lg border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-300">
          {error}
        </div>
      )}

      {loading && !data ? (
        <div className="flex min-h-80 items-center justify-center rounded-xl border border-border bg-card">
          <Loader2 className="size-7 animate-spin text-primary" />
        </div>
      ) : cameras.length === 0 ? (
        <div className="flex min-h-80 flex-col items-center justify-center rounded-xl border border-dashed border-border bg-card px-6 text-center">
          <Cctv className="size-10 text-muted-foreground" />
          <h3 className="mt-4 font-semibold">No cameras registered</h3>
          <p className="mt-1 max-w-md text-sm text-muted-foreground">
            Register field cameras in Camera &amp; Device Management before using the control-room wall.
          </p>
        </div>
      ) : (
        <div className={`grid min-h-0 gap-3 ${gridClass(layoutCount)}`}>
          {slots.map((identifier, index) => {
            const camera = identifier ? cameraMap.get(identifier) : undefined
            const availableChoices = filteredCameras.filter(
              (candidate) =>
                candidate.camera_identifier === identifier ||
                !slots.includes(candidate.camera_identifier),
            )

            return (
              <div key={`${index}-${identifier || "empty"}`} className="min-w-0">
                <div className="mb-2 flex items-center gap-2">
                  <span className="w-14 shrink-0 text-xs font-semibold text-muted-foreground">
                    View {index + 1}
                  </span>
                  <select
                    value={identifier || ""}
                    onChange={(event) => changeSlot(index, event.target.value)}
                    className="h-9 min-w-0 flex-1 rounded-md border border-input bg-background px-2 text-xs outline-none focus:ring-2 focus:ring-ring"
                  >
                    <option value="">Empty view</option>
                    {availableChoices.map((choice) => (
                      <option
                        key={choice.camera_identifier}
                        value={choice.camera_identifier}
                      >
                        {choice.camera_identifier} — {choice.name}
                      </option>
                    ))}
                  </select>
                </div>

                {camera ? (
                  <LiveCameraTile
                    camera={camera}
                    gatewayAvailable={Boolean(data?.gateway_available)}
                    compact={layoutCount >= 9}
                  />
                ) : (
                  <div className="flex aspect-video items-center justify-center rounded-xl border border-dashed border-border bg-card text-sm text-muted-foreground">
                    Select a camera for this view
                  </div>
                )}
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}
