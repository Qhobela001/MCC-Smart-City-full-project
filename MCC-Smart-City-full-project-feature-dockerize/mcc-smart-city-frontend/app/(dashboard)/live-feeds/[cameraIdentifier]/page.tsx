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
  Camera,
  Cctv,
  Expand,
  Loader2,
  MapPin,
  RefreshCw,
  MoveLeft,
  MoveRight,
  Square,
  Router,
  Video,
  Volume2,
  VolumeX,
  WifiOff,
  ZoomIn,
  ZoomOut,
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
  const recorderRef = useRef<MediaRecorder | null>(null)
  const recordingCanvasRef = useRef<HTMLCanvasElement | null>(null)
  const recordingFrameRef = useRef<number | null>(null)
  const recordingChunksRef = useRef<Blob[]>([])
  const paneCanvasRefs = useRef<Record<"main" | "right" | "left", HTMLCanvasElement | null>>({
    main: null,
    right: null,
    left: null,
  })
  const paneFrameRef = useRef<number | null>(null)

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
  const [zoom, setZoom] = useState(1)
  const [recording, setRecording] = useState(false)
  const [captureMessage, setCaptureMessage] = useState<string | null>(null)
  const [captureError, setCaptureError] = useState<string | null>(null)

  const paneIndex = ptzHead === "right" ? 0 : ptzHead === "left" ? 1 : 2

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

  function getLiveVideo() {
    const video = playerContainerRef.current?.querySelector("video")
    if (!(video instanceof HTMLVideoElement) || video.readyState < 2) {
      throw new Error("The live video is not ready for capture.")
    }
    return video
  }

  function drawSelectedPane(
    canvas: HTMLCanvasElement,
    video: HTMLVideoElement,
  ) {
    const sourceHeight = Math.floor(video.videoHeight / 3)
    const sourceY = paneIndex * sourceHeight
    canvas.width = video.videoWidth
    canvas.height = sourceHeight
    const context = canvas.getContext("2d")
    if (!context) throw new Error("Canvas capture is unavailable.")
    context.drawImage(
      video,
      0,
      sourceY,
      video.videoWidth,
      sourceHeight,
      0,
      0,
      canvas.width,
      canvas.height,
    )
  }

  function downloadBlob(blob: Blob, suffix: string) {
    const url = URL.createObjectURL(blob)
    const link = document.createElement("a")
    const timestamp = new Date().toISOString().replace(/[:.]/g, "-")
    link.href = url
    link.download = `${cameraIdentifier}-${ptzHead}-${timestamp}.${suffix}`
    link.click()
    window.setTimeout(() => URL.revokeObjectURL(url), 1000)
  }

  async function captureSnapshot() {
    setCaptureError(null)
    setCaptureMessage(null)
    try {
      const video = getLiveVideo()
      const canvas = document.createElement("canvas")
      drawSelectedPane(canvas, video)
      const blob = await new Promise<Blob>((resolve, reject) => {
        canvas.toBlob(
          (value) => value ? resolve(value) : reject(new Error("Snapshot encoding failed.")),
          "image/png",
        )
      })
      downloadBlob(blob, "png")
      setCaptureMessage(`${ptzHead} head snapshot saved.`)
    } catch (reason) {
      setCaptureError(reason instanceof Error ? reason.message : "Snapshot failed.")
    }
  }

  function stopRecording() {
    recorderRef.current?.stop()
  }

  function startRecording() {
    setCaptureError(null)
    setCaptureMessage(null)
    try {
      if (!("MediaRecorder" in window)) {
        throw new Error("This browser does not support live recording.")
      }
      const video = getLiveVideo()
      const canvas = document.createElement("canvas")
      recordingCanvasRef.current = canvas
      drawSelectedPane(canvas, video)
      const canvasStream = canvas.captureStream(12)
      const sourceStream = video.srcObject
      if (sourceStream instanceof MediaStream) {
        sourceStream.getAudioTracks().forEach((track) => canvasStream.addTrack(track.clone()))
      }
      const preferredType = "video/webm;codecs=vp8,opus"
      const recorder = MediaRecorder.isTypeSupported(preferredType)
        ? new MediaRecorder(canvasStream, { mimeType: preferredType })
        : new MediaRecorder(canvasStream)
      recordingChunksRef.current = []
      recorder.ondataavailable = (event) => {
        if (event.data.size > 0) recordingChunksRef.current.push(event.data)
      }
      recorder.onstop = () => {
        if (recordingFrameRef.current !== null) {
          cancelAnimationFrame(recordingFrameRef.current)
          recordingFrameRef.current = null
        }
        canvasStream.getTracks().forEach((track) => track.stop())
        const blob = new Blob(recordingChunksRef.current, { type: "video/webm" })
        if (blob.size > 0) downloadBlob(blob, "webm")
        recorderRef.current = null
        recordingCanvasRef.current = null
        setRecording(false)
        setCaptureMessage(`${ptzHead} head recording saved.`)
      }
      const drawFrame = () => {
        drawSelectedPane(canvas, video)
        recordingFrameRef.current = requestAnimationFrame(drawFrame)
      }
      recorderRef.current = recorder
      recorder.start(1000)
      setRecording(true)
      drawFrame()
    } catch (reason) {
      setCaptureError(reason instanceof Error ? reason.message : "Recording failed.")
    }
  }

  useEffect(() => () => {
    if (recorderRef.current?.state === "recording") recorderRef.current.stop()
    if (recordingFrameRef.current !== null) cancelAnimationFrame(recordingFrameRef.current)
  }, [])

  useEffect(() => {
    if (!session) return
    const drawPanes = () => {
      const video = playerContainerRef.current?.querySelector("video")
      if (video instanceof HTMLVideoElement && video.readyState >= 2) {
        const paneHeight = Math.floor(video.videoHeight / 3)
        const headPanes = { right: 0, left: 1, main: 2 } as const
        ;(["main", "right", "left"] as const).forEach((head) => {
          const canvas = paneCanvasRefs.current[head]
          if (!canvas) return
          const paneY = headPanes[head] * paneHeight
          const headZoom = head === ptzHead ? zoom : 1
          const sourceWidth = video.videoWidth / headZoom
          const sourceHeight = paneHeight / headZoom
          const sourceX = (video.videoWidth - sourceWidth) / 2
          const sourceY = paneY + (paneHeight - sourceHeight) / 2
          canvas.width = video.videoWidth
          canvas.height = paneHeight
          canvas.getContext("2d")?.drawImage(
            video,
            sourceX,
            sourceY,
            sourceWidth,
            sourceHeight,
            0,
            0,
            canvas.width,
            canvas.height,
          )
        })
      }
      paneFrameRef.current = requestAnimationFrame(drawPanes)
    }
    drawPanes()
    return () => {
      if (paneFrameRef.current !== null) {
        cancelAnimationFrame(paneFrameRef.current)
        paneFrameRef.current = null
      }
    }
  }, [ptzHead, session, zoom])

  function renderLandscapePane(head: "main" | "right" | "left", label: string) {
    return (
      <button
        type="button"
        disabled={recording}
        onClick={() => { setPtzHead(head); setZoom(1) }}
        aria-label={`Select ${label} camera head`}
        aria-pressed={ptzHead === head}
        className={`relative aspect-video overflow-hidden rounded-lg border-2 bg-black text-left transition disabled:cursor-not-allowed ${
          ptzHead === head
            ? "border-red-500"
            : "border-transparent hover:border-white/60"
        }`}
      >
        <canvas
          ref={(element) => { paneCanvasRefs.current[head] = element }}
          className="pointer-events-none h-full w-full"
        />
        <span className={`absolute left-2 top-2 rounded px-2 py-1 text-[11px] font-semibold text-white ${
          ptzHead === head ? "bg-red-600" : "bg-black/60"
        }`}>
          {label}{ptzHead === head && zoom > 1 ? ` · ${zoom.toFixed(1)}×` : ""}
        </span>
      </button>
    )
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
        className="relative w-full overflow-hidden rounded-xl border border-border bg-black p-2 shadow-lg"
      >
        {session ? (
          <>
            <div className="pointer-events-none absolute size-px overflow-hidden opacity-0">
              <WebRTCPlayer
                endpoint={session.whep_url}
                token={session.token}
                muted={muted}
                controls={false}
              />
            </div>
            <div className="grid gap-2 lg:grid-cols-[2fr_1fr]" aria-label="Landscape camera head views">
              {renderLandscapePane("main", "Main")}
              <div className="grid gap-2">
                {renderLandscapePane("right", "Right")}
                {renderLandscapePane("left", "Left")}
              </div>
            </div>
          </>
        ) : (
          <div className="flex min-h-[360px] flex-col items-center justify-center gap-4 bg-gradient-to-b from-slate-950 to-black px-6 text-center text-white">
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

      <section className="flex flex-wrap items-center gap-2 rounded-xl border border-border bg-card p-4 shadow-sm">
        <button
          type="button"
          onClick={() => setZoom((value) => Math.max(1, value - 0.5))}
          disabled={!session || zoom <= 1}
          className="inline-flex items-center gap-2 rounded-md border border-border px-3 py-2 text-sm transition hover:bg-accent disabled:opacity-40"
        >
          <ZoomOut className="size-4" /> Zoom out
        </button>
        <span className="min-w-14 text-center text-sm font-semibold">{zoom.toFixed(1)}×</span>
        <button
          type="button"
          onClick={() => setZoom((value) => Math.min(10, value + 0.5))}
          disabled={!session || zoom >= 10}
          className="inline-flex items-center gap-2 rounded-md border border-border px-3 py-2 text-sm transition hover:bg-accent disabled:opacity-40"
        >
          <ZoomIn className="size-4" /> Zoom in
        </button>
        <button
          type="button"
          onClick={() => void captureSnapshot()}
          disabled={!session}
          className="inline-flex items-center gap-2 rounded-md border border-border px-3 py-2 text-sm transition hover:bg-accent disabled:opacity-40"
        >
          <Camera className="size-4" /> Snapshot {ptzHead}
        </button>
        <button
          type="button"
          onClick={recording ? stopRecording : startRecording}
          disabled={!session}
          className={`inline-flex items-center gap-2 rounded-md border px-3 py-2 text-sm transition disabled:opacity-40 ${
            recording
              ? "border-red-500 bg-red-500/10 text-red-600"
              : "border-border hover:bg-accent"
          }`}
        >
          {recording ? <Square className="size-4 fill-current" /> : <Video className="size-4" />}
          {recording ? "Stop recording" : `Record ${ptzHead}`}
        </button>
        {captureMessage && <p className="w-full text-xs text-emerald-600">{captureMessage}</p>}
        {captureError && <p className="w-full text-xs text-destructive">{captureError}</p>}
      </section>

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
              disabled={recording}
              onClick={() => setPtzHead(head)}
              aria-pressed={ptzHead === head}
              className={`rounded-lg border-2 px-3 py-2 text-sm font-medium transition disabled:cursor-not-allowed ${
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
