"use client"

import { useMemo, useRef, useState } from "react"
import {
    ChevronDown,
    ChevronLeft,
    ChevronRight,
    ChevronUp,
    Grid2x2,
    Grid3x3,
    Home,
    Maximize2,
    Minus,
    Plus,
    Scan,
    ScanLine,
    ShieldCheck,
    Square,
    UsersRound,
    VideoOff,
    Wifi,
} from "lucide-react"
import { Card, CardContent } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Switch } from "@/components/ui/switch"
import { cameras, type Camera, type CameraStatus } from "@/lib/mock-data"
import { cn } from "@/lib/utils"

const statusStyles: Record<CameraStatus, string> = {
    online: "bg-chart-2/15 text-chart-2 border-chart-2/30",
    degraded: "bg-chart-3/15 text-chart-3 border-chart-3/30",
    offline: "bg-destructive/15 text-destructive border-destructive/30",
}

const statusDot: Record<CameraStatus, string> = {
    online: "bg-chart-2",
    degraded: "bg-chart-3",
    offline: "bg-destructive",
}

type ViewMode = "single" | "2x2" | "4x4"

type AiKey = "plates" | "pedestrians" | "wrongWay" | "plateMask"

const aiToggleConfig: { key: AiKey; label: string; icon: typeof Scan; hint: string }[] = [
    { key: "plates", label: "License Plate Reading", icon: ScanLine, hint: "OCR of vehicle plates" },
    { key: "pedestrians", label: "Pedestrian Detection", icon: UsersRound, hint: "Bounding boxes on people" },
    { key: "wrongWay", label: "Wrong-Way Drivers", icon: Scan, hint: "Flag reverse-direction vehicles" },
    { key: "plateMask", label: "License Plate Mask", icon: ShieldCheck, hint: "Blur plates for privacy" },
]

export default function LiveFeedsPage() {
    const [viewMode, setViewMode] = useState<ViewMode>("single")
    const [selectedId, setSelectedId] = useState<string>(cameras[0].id)
    const [ai, setAi] = useState<Record<AiKey, boolean>>({
        plates: false,
        pedestrians: true,
        wrongWay: false,
        plateMask: false,
    })
    const [ptzLog, setPtzLog] = useState<string>("Centered · 1.0x")

    const active = cameras.find((c) => c.id === selectedId) ?? cameras[0]

    const gridCameras = useMemo(() => {
        if (viewMode === "single") return [active]
        if (viewMode === "2x2") return cameras.slice(0, 4)
        return cameras // 4x4 — we have 6 cameras, show them all
    }, [viewMode, active])

    function toggleAi(key: AiKey) {
        setAi((prev) => ({ ...prev, [key]: !prev[key] }))
    }

    return (
        <>
            <div className="flex flex-wrap items-end justify-between gap-3">
                <div>
                    <h1 className="text-xl font-semibold text-foreground">Live Feeds</h1>
                    <p className="text-sm text-muted-foreground">
                        Real-time CCTV monitoring · {cameras.length} sources
                    </p>
                </div>

                {/* view mode switch */}
                <div className="flex items-center gap-1 rounded-md border border-border bg-card p-1">
                    <ViewButton active={viewMode === "single"} onClick={() => setViewMode("single")} icon={Square} label="Single" />
                    <ViewButton active={viewMode === "2x2"} onClick={() => setViewMode("2x2")} icon={Grid2x2} label="2x2" />
                    <ViewButton active={viewMode === "4x4"} onClick={() => setViewMode("4x4")} icon={Grid3x3} label="Grid" />
                </div>
            </div>

            <div className="grid grid-cols-1 gap-4 lg:grid-cols-[1fr_20rem]">
                {/* main viewport area */}
                <div className="flex flex-col gap-4">
                    <div
                        className={cn(
                            "grid gap-3",
                            viewMode === "single" && "grid-cols-1",
                            viewMode === "2x2" && "grid-cols-1 sm:grid-cols-2",
                            viewMode === "4x4" && "grid-cols-2 lg:grid-cols-3",
                        )}
                    >
                        {gridCameras.map((cam) => (
                            <CameraFeed
                                key={cam.id}
                                camera={cam}
                                ai={ai}
                                large={viewMode === "single"}
                                selected={cam.id === selectedId}
                                onSelect={() => setSelectedId(cam.id)}
                            />
                        ))}
                    </div>

                    {/* camera strip for quick selection */}
                    <div className="flex gap-2 overflow-x-auto pb-1">
                        {cameras.map((cam) => (
                            <button
                                key={cam.id}
                                onClick={() => setSelectedId(cam.id)}
                                className={cn(
                                    "flex shrink-0 items-center gap-2 rounded-md border px-3 py-1.5 text-xs transition-colors",
                                    cam.id === selectedId
                                        ? "border-primary bg-primary/10 text-foreground"
                                        : "border-border bg-card text-muted-foreground hover:text-foreground",
                                )}
                            >
                                <span className={cn("size-2 rounded-full", statusDot[cam.status])} />
                                {cam.id}
                            </button>
                        ))}
                    </div>
                </div>

                {/* control sidebar */}
                <div className="flex flex-col gap-4">
                    {/* active camera info */}
                    <Card>
                        <CardContent className="space-y-1 p-4">
                            <div className="flex items-center justify-between">
                                <span className="font-mono text-xs text-muted-foreground">{active.id}</span>
                                <Badge variant="outline" className={cn("capitalize", statusStyles[active.status])}>
                                    {active.status}
                                </Badge>
                            </div>
                            <div className="text-base font-semibold text-foreground">{active.name}</div>
                            <div className="text-sm text-muted-foreground">{active.zone}</div>
                            <div className="flex items-center gap-1 pt-1 font-mono text-xs text-muted-foreground">
                                <Wifi className="size-3.5" />
                                Signal {active.signal}%
                            </div>
                        </CardContent>
                    </Card>

                    {/* AI analytics toggles */}
                    <Card>
                        <CardContent className="space-y-3 p-4">
                            <div className="text-sm font-semibold text-foreground">AI Analytics</div>
                            {aiToggleConfig.map((t) => (
                                <label
                                    key={t.key}
                                    htmlFor={t.key}
                                    className="flex cursor-pointer items-center justify-between gap-3"
                                >
                  <span className="flex items-start gap-2">
                    <t.icon className="mt-0.5 size-4 text-muted-foreground" />
                    <span>
                      <span className="block text-sm text-foreground">{t.label}</span>
                      <span className="block text-xs text-muted-foreground">{t.hint}</span>
                    </span>
                  </span>
                                    <Switch id={t.key} checked={ai[t.key]} onCheckedChange={() => toggleAi(t.key)} />
                                </label>
                            ))}
                        </CardContent>
                    </Card>

                    {/* PTZ controls */}
                    <Card>
                        <CardContent className="space-y-3 p-4">
                            <div className="flex items-center justify-between">
                                <span className="text-sm font-semibold text-foreground">PTZ Control</span>
                                <span className="font-mono text-[11px] text-muted-foreground">{ptzLog}</span>
                            </div>

                            {/* directional pad */}
                            <div className="mx-auto grid w-32 grid-cols-3 grid-rows-3 gap-1">
                                <span />
                                <PtzButton icon={ChevronUp} onClick={() => setPtzLog("Tilt up")} label="Tilt up" />
                                <span />
                                <PtzButton icon={ChevronLeft} onClick={() => setPtzLog("Pan left")} label="Pan left" />
                                <PtzButton icon={Home} onClick={() => setPtzLog("Centered · 1.0x")} label="Home" />
                                <PtzButton icon={ChevronRight} onClick={() => setPtzLog("Pan right")} label="Pan right" />
                                <span />
                                <PtzButton icon={ChevronDown} onClick={() => setPtzLog("Tilt down")} label="Tilt down" />
                                <span />
                            </div>

                            {/* zoom */}
                            <div className="flex items-center gap-2">
                                <Button size="sm" variant="outline" className="flex-1" onClick={() => setPtzLog("Zoom out")}>
                                    <Minus className="size-3.5" />
                                    Zoom
                                </Button>
                                <Button size="sm" variant="outline" className="flex-1" onClick={() => setPtzLog("Zoom in")}>
                                    <Plus className="size-3.5" />
                                    Zoom
                                </Button>
                            </div>

                            {/* presets */}
                            <div>
                                <div className="mb-1.5 text-xs text-muted-foreground">Presets</div>
                                <div className="flex flex-wrap gap-1.5">
                                    {["Entrance", "Junction", "Wide", "Gate"].map((preset) => (
                                        <button
                                            key={preset}
                                            onClick={() => setPtzLog(`Preset · ${preset}`)}
                                            className="rounded border border-border bg-card px-2 py-1 text-xs text-muted-foreground transition-colors hover:border-primary/40 hover:text-foreground"
                                        >
                                            {preset}
                                        </button>
                                    ))}
                                </div>
                            </div>
                        </CardContent>
                    </Card>
                </div>
            </div>
        </>
    )
}

function ViewButton({
                        active,
                        onClick,
                        icon: Icon,
                        label,
                    }: {
    active: boolean
    onClick: () => void
    icon: typeof Square
    label: string
}) {
    return (
        <button
            onClick={onClick}
            className={cn(
                "flex items-center gap-1.5 rounded px-2.5 py-1.5 text-xs font-medium transition-colors",
                active ? "bg-primary text-primary-foreground" : "text-muted-foreground hover:text-foreground",
            )}
            aria-pressed={active}
        >
            <Icon className="size-4" />
            <span className="hidden sm:inline">{label}</span>
        </button>
    )
}

function PtzButton({
                       icon: Icon,
                       onClick,
                       label,
                   }: {
    icon: typeof ChevronUp
    onClick: () => void
    label: string
}) {
    return (
        <button
            onClick={onClick}
            aria-label={label}
            className="flex items-center justify-center rounded-md border border-border bg-card py-2 text-muted-foreground transition-colors hover:border-primary/40 hover:text-foreground active:bg-accent"
        >
            <Icon className="size-4" />
        </button>
    )
}

function CameraFeed({
                        camera,
                        ai,
                        large,
                        selected,
                        onSelect,
                    }: {
    camera: Camera
    ai: Record<AiKey, boolean>
    large: boolean
    selected: boolean
    onSelect: () => void
}) {
    const ref = useRef<HTMLDivElement>(null)

    function goFullscreen(e: React.MouseEvent) {
        e.stopPropagation()
        const el = ref.current
        if (!el) return
        if (document.fullscreenElement) {
            document.exitFullscreen()
        } else {
            el.requestFullscreen?.()
        }
    }

    const offline = camera.status === "offline"

    return (
        <div
            ref={ref}
            onClick={onSelect}
            className={cn(
                "group relative cursor-pointer overflow-hidden rounded-lg border bg-muted",
                large ? "aspect-video" : "aspect-video",
                selected ? "border-primary ring-1 ring-primary" : "border-border",
            )}
        >
            {offline ? (
                <div className="flex h-full flex-col items-center justify-center gap-2 text-muted-foreground">
                    <VideoOff className="size-7" />
                    <span className="text-sm">Signal lost</span>
                </div>
            ) : (
                <>
                    {/* eslint-disable-next-line @next/next/no-img-element */}
                    <img
                        src={camera.feed || "/placeholder.svg"}
                        alt={`Live feed from ${camera.name}`}
                        className={cn(
                            "h-full w-full object-cover",
                            camera.status === "degraded" && "opacity-80",
                        )}
                    />

                    {/* AI overlays (illustrative) */}
                    {ai.pedestrians && (
                        <>
                            <DetectionBox className="left-[18%] top-[45%] h-[38%] w-[12%]" label="Pedestrian 0.94" tone="chart-2" />
                            <DetectionBox className="left-[62%] top-[52%] h-[30%] w-[10%]" label="Pedestrian 0.88" tone="chart-2" />
                        </>
                    )}
                    {ai.plates && (
                        <DetectionBox className="left-[40%] top-[68%] h-[8%] w-[16%]" label="A 1234 · LS" tone="chart-3" />
                    )}
                    {ai.plateMask && (
                        <div className="absolute left-[40%] top-[68%] h-[8%] w-[16%] rounded-sm bg-foreground/80 backdrop-blur-sm" />
                    )}
                    {ai.wrongWay && (
                        <DetectionBox className="left-[68%] top-[30%] h-[24%] w-[14%]" label="Wrong-way!" tone="destructive" />
                    )}

                    {/* live badge */}
                    <span className="absolute left-2 top-2 flex items-center gap-1.5 rounded bg-black/50 px-1.5 py-0.5 text-[10px] font-medium uppercase tracking-wide text-white backdrop-blur">
            <span className="size-1.5 animate-pulse rounded-full bg-destructive" />
            Live
          </span>
                </>
            )}

            {/* label bar */}
            <div className="absolute inset-x-0 bottom-0 flex items-center justify-between gap-2 bg-gradient-to-t from-black/70 to-transparent px-2 py-1.5">
        <span className="truncate text-xs font-medium text-white">
          {camera.id} · {camera.name}
        </span>
                <button
                    onClick={goFullscreen}
                    aria-label={`Fullscreen ${camera.name}`}
                    className="shrink-0 rounded bg-black/40 p-1 text-white opacity-0 transition-opacity hover:bg-black/70 group-hover:opacity-100"
                >
                    <Maximize2 className="size-3.5" />
                </button>
            </div>
        </div>
    )
}

function DetectionBox({
                          className,
                          label,
                          tone,
                      }: {
    className: string
    label: string
    tone: "chart-2" | "chart-3" | "destructive"
}) {
    const borderTone =
        tone === "chart-2" ? "border-chart-2" : tone === "chart-3" ? "border-chart-3" : "border-destructive"
    const bgTone =
        tone === "chart-2" ? "bg-chart-2" : tone === "chart-3" ? "bg-chart-3" : "bg-destructive"
    return (
        <div className={cn("absolute rounded-sm border-2", borderTone, className)}>
      <span className={cn("absolute -top-4 left-0 rounded-sm px-1 text-[9px] font-semibold text-white", bgTone)}>
        {label}
      </span>
        </div>
    )
}