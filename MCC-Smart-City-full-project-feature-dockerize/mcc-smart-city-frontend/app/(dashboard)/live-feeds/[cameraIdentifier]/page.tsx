"use client"

import Link from "next/link"
import { useParams } from "next/navigation"
import { useCallback, useEffect, useRef, useState } from "react"
import type { ReactNode } from "react"
import {
  ArrowLeft,
  ArrowDown,
  ArrowUp,
  Bot,
  Cctv,
  Expand,
  Loader2,
  MapPin,
  RefreshCw,
  MoveLeft,
  MoveRight,
  Router,
  Volume2,
  VolumeX,
  WifiOff,
} from "lucide-react"

import { apiFetch } from "@/lib/api"
import { WebRTCPlayer } from "@/components/live-monitoring/webrtc-player"
import type {
  LiveCamera,
  LiveStreamSession,
} from "@/components/live-monitoring/types"

export default function CameraLiveViewerPage() {
  const params = useParams<{ cameraIdentifier: string }>()
  const cameraIdentifier = decodeURIComponent(params.cameraIdentifier)
  const playerContainerRef = useRef<HTMLDivElement | null>(null)

  const [camera, setCamera] = useState<LiveCamera | null>(null)
  const [session, setSession] = useState<LiveStreamSession | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [muted, setMuted] = useState(true)
  const [sessionKey, setSessionKey] = useState(0)
  const [ptzBusy, setPtzBusy] = useState<string | null>(null)
  const [ptzHead, setPtzHead] = useState<"main" | "right" | "left">("main")
  const [ptzMessage, setPtzMessage] = useState<string | null>(null)
  const [ptzError, setPtzError] = useState<string | null>(null)

  const connect = useCallback(async () => {
    setLoading(true)
    setError(null)
    setSession(null)

    try {
      const cameraData = await apiFetch<LiveCamera>(
        `/live-streams/cameras/${encodeURIComponent(cameraIdentifier)}`,
      )
      setCamera(cameraData)

      if (!cameraData.stream_configured) {
        setError(
          "This camera does not yet have an IP address and RTSP path configured in Camera & Device Management.",
        )
        return
      }

      const sessionData = await apiFetch<LiveStreamSession>(
        `/live-streams/cameras/${encodeURIComponent(cameraIdentifier)}/session`,
        { method: "POST" },
      )
      setCamera(sessionData.camera)
      setSession(sessionData)
    } catch (reason) {
      setError(
        reason instanceof Error
          ? reason.message
          : "Unable to start the live camera viewer.",
      )
    } finally {
      setLoading(false)
    }
  }, [cameraIdentifier, sessionKey])

  useEffect(() => {
    void connect()
  }, [connect])

  async function enterFullscreen() {
    try {
      await playerContainerRef.current?.requestFullscreen()
    } catch {
      // Browser can reject fullscreen when it is not initiated by the user.
    }
  }

  async function sendPtz(direction: "up" | "down" | "left" | "right") {
    if (ptzBusy) return
    setPtzBusy(direction)
    setPtzMessage(null)
    setPtzError(null)
    try {
      const result = await apiFetch<{ message: string }>(
        `/live-streams/cameras/${encodeURIComponent(cameraIdentifier)}/ptz`,
        {
          method: "POST",
          body: JSON.stringify({ direction, head: ptzHead }),
        },
      )
      setPtzMessage(result.message)
    } catch (reason) {
      setPtzError(
        reason instanceof Error
          ? reason.message
          : "Unable to move this camera.",
      )
    } finally {
      setPtzBusy(null)
    }
  }

  return (
    <div className="flex min-h-0 flex-col gap-4">
      <section className="flex flex-col gap-3 rounded-xl border border-border bg-card p-4 shadow-sm md:flex-row md:items-center">
        <div className="flex min-w-0 flex-1 items-center gap-3">
          <Link
            href="/live-feeds"
            className="rounded-md border border-border p-2 text-muted-foreground transition hover:bg-accent hover:text-foreground"
            title="Back to camera wall"
          >
            <ArrowLeft className="size-4" />
          </Link>
          <div className="min-w-0">
            <div className="flex items-center gap-2">
              <Cctv className="size-5 text-primary" />
              <h2 className="truncate text-lg font-semibold">
                {camera?.name || cameraIdentifier}
              </h2>
            </div>
            <p className="truncate text-xs text-muted-foreground">
              {camera?.camera_identifier || cameraIdentifier} · Dedicated live viewer
            </p>
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <button
            type="button"
            onClick={() => setMuted((value) => !value)}
            className="inline-flex items-center gap-2 rounded-md border border-border px-3 py-2 text-sm transition hover:bg-accent"
          >
            {muted ? <VolumeX className="size-4" /> : <Volume2 className="size-4" />}
            {muted ? "Muted" : "Audio on"}
          </button>
          <button
            type="button"
            onClick={() => void enterFullscreen()}
            className="inline-flex items-center gap-2 rounded-md border border-border px-3 py-2 text-sm transition hover:bg-accent"
          >
            <Expand className="size-4" />
            Full screen
          </button>
          <button
            type="button"
            onClick={() => setSessionKey((value) => value + 1)}
            className="inline-flex items-center gap-2 rounded-md border border-border px-3 py-2 text-sm transition hover:bg-accent"
          >
            <RefreshCw className="size-4" />
            Reconnect
          </button>
        </div>
      </section>

      <div
        ref={playerContainerRef}
        className="relative aspect-video w-full overflow-hidden rounded-xl border border-border bg-black shadow-lg"
      >
        {session ? (
          <WebRTCPlayer
            endpoint={session.whep_url}
            token={session.token}
            muted={muted}
            controls
          />
        ) : (
          <div className="absolute inset-0 flex flex-col items-center justify-center gap-4 bg-gradient-to-b from-slate-950 to-black px-6 text-center text-white">
            {loading ? (
              <>
                <Loader2 className="size-9 animate-spin text-primary" />
                <p className="text-sm">Preparing live camera session…</p>
              </>
            ) : (
              <>
                <WifiOff className="size-10 text-amber-400" />
                <p className="font-medium">Live video unavailable</p>
                <p className="max-w-xl text-sm text-white/60">
                  {error || "No live stream is available for this camera."}
                </p>
              </>
            )}
          </div>
        )}
      </div>

      <section className="rounded-xl border border-border bg-card p-4 shadow-sm">
        <div className="mb-4 grid grid-cols-3 gap-2" aria-label="PTZ camera head">
          {([
            ["left", "Left"],
            ["main", "Main"],
            ["right", "Right"],
          ] as const).map(([head, label]) => (
            <button
              key={head}
              type="button"
              onClick={() => setPtzHead(head)}
              aria-pressed={ptzHead === head}
              className={`rounded-lg border-2 px-3 py-2 text-sm font-medium transition ${
                ptzHead === head
                  ? "border-red-500 bg-red-500/10 text-red-600"
                  : "border-border hover:bg-accent"
              }`}
            >
              {label}
            </button>
          ))}
        </div>
        <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
          <div>
            <h3 className="text-sm font-semibold">Pan and tilt control</h3>
            <p className="mt-1 text-xs text-muted-foreground">
              Each press sends one short movement nudge through the active V380
              stream. Camera streaming remains connected.
            </p>
          </div>

          <div
            className="grid grid-cols-3 gap-2"
            aria-label="Camera movement controls"
          >
            <span />
            <PtzButton
              label="Tilt up"
              disabled={!session || ptzBusy !== null}
              active={ptzBusy === "up"}
              onClick={() => void sendPtz("up")}
            >
              <ArrowUp className="size-5" />
            </PtzButton>
            <span />
            <PtzButton
              label="Pan left"
              disabled={!session || ptzBusy !== null}
              active={ptzBusy === "left"}
              onClick={() => void sendPtz("left")}
            >
              <MoveLeft className="size-5" />
            </PtzButton>
            <div className="flex size-10 items-center justify-center rounded-md border border-dashed border-border text-[10px] text-muted-foreground">
              PTZ
            </div>
            <PtzButton
              label="Pan right"
              disabled={!session || ptzBusy !== null}
              active={ptzBusy === "right"}
              onClick={() => void sendPtz("right")}
            >
              <MoveRight className="size-5" />
            </PtzButton>
            <span />
            <PtzButton
              label="Tilt down"
              disabled={!session || ptzBusy !== null}
              active={ptzBusy === "down"}
              onClick={() => void sendPtz("down")}
            >
              <ArrowDown className="size-5" />
            </PtzButton>
            <span />
          </div>
        </div>
        {ptzMessage && (
          <p className="mt-3 text-xs text-emerald-600">{ptzMessage}</p>
        )}
        {ptzError && <p className="mt-3 text-xs text-destructive">{ptzError}</p>}
      </section>

      {camera && (
        <section className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
          <div className="rounded-xl border border-border bg-card p-4">
            <p className="flex items-center gap-2 text-xs font-medium uppercase tracking-wide text-muted-foreground">
              <MapPin className="size-3.5" /> Location
            </p>
            <p className="mt-2 text-sm font-semibold">
              {camera.location_name || "No GIS location"}
            </p>
            {camera.latitude != null && camera.longitude != null && (
              <p className="mt-1 text-xs text-muted-foreground">
                {camera.latitude}, {camera.longitude}
              </p>
            )}
          </div>

          <div className="rounded-xl border border-border bg-card p-4">
            <p className="flex items-center gap-2 text-xs font-medium uppercase tracking-wide text-muted-foreground">
              <Bot className="size-3.5" /> AI processing
            </p>
            <p className="mt-2 text-sm font-semibold">
              {camera.ai_enabled ? "Enabled" : "Disabled"}
            </p>
            <p className="mt-1 text-xs text-muted-foreground">
              {camera.assigned_jetson_identifier || "No Jetson assigned"}
            </p>
          </div>

          <div className="rounded-xl border border-border bg-card p-4">
            <p className="flex items-center gap-2 text-xs font-medium uppercase tracking-wide text-muted-foreground">
              <Router className="size-3.5" /> Field backhaul
            </p>
            <p className="mt-2 text-sm font-semibold">
              {camera.field_nanostation_identifier || "No field radio"}
            </p>
            <p className="mt-1 text-xs text-muted-foreground">
              NanoStation transport
            </p>
          </div>

          <div className="rounded-xl border border-border bg-card p-4">
            <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
              Stream health
            </p>
            <p className="mt-2 text-sm font-semibold capitalize">
              {camera.stream_status}
            </p>
            <p className="mt-1 text-xs text-muted-foreground">
              Gateway path: {camera.gateway_path}
            </p>
          </div>
        </section>
      )}
    </div>
  )
}

function PtzButton({
  label,
  disabled,
  active,
  onClick,
  children,
}: {
  label: string
  disabled: boolean
  active: boolean
  onClick: () => void
  children: ReactNode
}) {
  return (
    <button
      type="button"
      title={label}
      aria-label={label}
      disabled={disabled}
      onClick={onClick}
      className="flex size-10 items-center justify-center rounded-md border border-border transition hover:bg-accent disabled:cursor-not-allowed disabled:opacity-40"
    >
      {active ? <Loader2 className="size-4 animate-spin" /> : children}
    </button>
  )
}
