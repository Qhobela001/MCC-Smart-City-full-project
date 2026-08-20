"use client"

import Link from "next/link"
import { useEffect, useState } from "react"
import {
  Bot,
  ExternalLink,
  MapPin,
  Radio,
  Router,
  TriangleAlert,
  VideoOff,
} from "lucide-react"

import { apiFetch } from "@/lib/api"
import { WebRTCPlayer } from "@/components/live-monitoring/webrtc-player"
import type {
  LiveCamera,
  LiveStreamSession,
} from "@/components/live-monitoring/types"


type LiveCameraTileProps = {
  camera: LiveCamera
  gatewayAvailable: boolean
  compact?: boolean
}

function badgeClass(value: string) {
  if (value === "online") {
    return "bg-emerald-500/15 text-emerald-400"
  }
  if (value === "degraded") {
    return "bg-amber-500/15 text-amber-400"
  }
  if (value === "offline") {
    return "bg-red-500/15 text-red-400"
  }
  return "bg-muted text-muted-foreground"
}

export function LiveCameraTile({
  camera,
  gatewayAvailable,
  compact = false,
}: LiveCameraTileProps) {
  const [session, setSession] = useState<LiveStreamSession | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)
  const [sessionKey, setSessionKey] = useState(0)

  useEffect(() => {
    let cancelled = false

    if (!camera.stream_configured || !gatewayAvailable) {
      setSession(null)
      setLoading(false)
      return
    }

    setLoading(true)
    setError(null)

    apiFetch<LiveStreamSession>(
      `/live-streams/cameras/${encodeURIComponent(camera.camera_identifier)}/session`,
      { method: "POST" },
    )
      .then((data) => {
        if (!cancelled) setSession(data)
      })
      .catch((reason: unknown) => {
        if (!cancelled) {
          setError(
            reason instanceof Error
              ? reason.message
              : "Unable to start live stream.",
          )
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })

    return () => {
      cancelled = true
    }
  }, [camera.camera_identifier, camera.stream_configured, gatewayAvailable, sessionKey])

  const viewerHref = `/live-feeds/${encodeURIComponent(camera.camera_identifier)}`

  return (
    <article className="group flex min-h-0 flex-col overflow-hidden rounded-xl border border-border bg-card shadow-sm">
      <div className="relative aspect-video min-h-0 bg-black">
        {session ? (
          <WebRTCPlayer
            endpoint={session.whep_url}
            token={session.token}
            muted
            className="aspect-video"
          />
        ) : (
          <div className="absolute inset-0 flex flex-col items-center justify-center gap-3 bg-gradient-to-b from-slate-950 to-black px-5 text-center">
            {!gatewayAvailable ? (
              <>
                <TriangleAlert className="size-8 text-amber-400" />
                <p className="text-sm font-medium text-white">
                  Stream gateway offline
                </p>
                <p className="text-xs text-white/55">
                  Camera metadata remains available, but live viewing requires the MCC HQ stream gateway.
                </p>
              </>
            ) : !camera.stream_configured ? (
              <>
                <VideoOff className="size-8 text-white/45" />
                <p className="text-sm font-medium text-white">
                  Stream not configured
                </p>
                <p className="text-xs text-white/55">
                  Add the camera IP address and RTSP path in Camera &amp; Device Management.
                </p>
              </>
            ) : loading ? (
              <>
                <Radio className="size-8 animate-pulse text-primary" />
                <p className="text-sm text-white">Opening live stream…</p>
              </>
            ) : (
              <>
                <TriangleAlert className="size-8 text-amber-400" />
                <p className="text-sm font-medium text-white">
                  Live stream unavailable
                </p>
                <p className="text-xs text-white/55">
                  {error || "The stream could not be started."}
                </p>
                <button
                  type="button"
                  onClick={() => setSessionKey((value) => value + 1)}
                  className="rounded-md border border-white/15 bg-white/5 px-3 py-1.5 text-xs font-medium text-white transition hover:bg-white/10"
                >
                  Retry
                </button>
              </>
            )}
          </div>
        )}

        <div className="absolute right-3 top-3 flex items-center gap-2">
          <span
            className={`rounded-full px-2 py-1 text-[10px] font-semibold uppercase tracking-wide ${badgeClass(camera.stream_status)}`}
          >
            {camera.stream_status}
          </span>
        </div>
      </div>

      <div className={`flex min-h-0 flex-1 flex-col ${compact ? "p-3" : "p-4"}`}>
        <div className="flex items-start gap-3">
          <div className="min-w-0 flex-1">
            <p className="truncate text-sm font-semibold">{camera.name}</p>
            <p className="truncate text-xs text-muted-foreground">
              {camera.camera_identifier}
            </p>
          </div>

          <Link
            href={viewerHref}
            title="Open dedicated viewer"
            className="rounded-md border border-border p-2 text-muted-foreground transition hover:bg-accent hover:text-foreground"
          >
            <ExternalLink className="size-4" />
          </Link>
        </div>

        {!compact && (
          <div className="mt-3 grid gap-2 text-xs text-muted-foreground sm:grid-cols-2">
            <span className="flex min-w-0 items-center gap-2">
              <MapPin className="size-3.5 shrink-0" />
              <span className="truncate">
                {camera.location_name || "No GIS location"}
              </span>
            </span>
            <span className="flex min-w-0 items-center gap-2">
              <Bot className="size-3.5 shrink-0" />
              <span className="truncate">
                {camera.assigned_jetson_identifier || "No Jetson assigned"}
              </span>
            </span>
            <span className="flex min-w-0 items-center gap-2">
              <Router className="size-3.5 shrink-0" />
              <span className="truncate">
                {camera.field_nanostation_identifier || "No field radio"}
              </span>
            </span>
            <span className="flex items-center gap-2">
              <Radio className="size-3.5 shrink-0" />
              {camera.ai_enabled ? "AI enabled" : "AI disabled"}
            </span>
          </div>
        )}
      </div>
    </article>
  )
}
