"use client"

import { useMemo, useState } from "react"
import { Filter, Maximize2, VideoOff, Wifi, Camera, Download, FileText, MapPin } from "lucide-react"
import { Card, CardContent } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { ScrollArea } from "@/components/ui/scroll-area"
import { cameras, type CameraStatus } from "@/lib/mock-data"
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

const filters = ["All", "online", "degraded", "offline"] as const
type StatusFilter = (typeof filters)[number]

export default function LiveFeedsPage() {
    const [filter, setFilter] = useState<StatusFilter>("All")
    const [selectedId, setSelectedId] = useState<string>(cameras[0].id)

    const list = useMemo(
        () => cameras.filter((c) => filter === "All" || c.status === filter),
        [filter],
    )

    const active = cameras.find((c) => c.id === selectedId) ?? list[0]

    return (
        <>
            <div>
                <h1 className="text-xl font-semibold text-foreground">Live Feeds</h1>
                <p className="text-sm text-muted-foreground">
                    Real-time camera feeds from the field layer · {cameras.length} sources
                </p>
            </div>

            {/* filter bar */}
            <div className="flex flex-wrap items-center gap-2">
                <Filter className="size-4 text-muted-foreground" />
                {filters.map((f) => (
                    <Button
                        key={f}
                        size="sm"
                        variant={filter === f ? "default" : "outline"}
                        onClick={() => setFilter(f)}
                        className="capitalize"
                    >
                        {f}
                    </Button>
                ))}
            </div>

            {/* master-detail layout */}
            <div className="grid grid-cols-1 gap-4 lg:grid-cols-[1fr_1.4fr]">
                {/* list */}
                <Card>
                    <CardContent className="p-0">
                        <ScrollArea className="h-[calc(100vh-16rem)]">
                            <ul className="divide-y divide-border">
                                {list.map((cam) => (
                                    <li key={cam.id}>
                                        <button
                                            onClick={() => setSelectedId(cam.id)}
                                            className={cn(
                                                "flex w-full items-start gap-3 px-4 py-3 text-left transition-colors hover:bg-accent/40",
                                                active?.id === cam.id && "bg-accent/60",
                                            )}
                                        >
                                            <span className={cn("mt-1.5 size-2.5 shrink-0 rounded-full", statusDot[cam.status])} />
                                            <div className="min-w-0 flex-1">
                                                <div className="flex items-center justify-between gap-2">
                                                    <span className="truncate text-sm font-medium text-foreground">{cam.name}</span>
                                                    <span className="shrink-0 font-mono text-[11px] text-muted-foreground">{cam.id}</span>
                                                </div>
                                                <div className="truncate text-xs text-muted-foreground">{cam.zone}</div>
                                                <div className="mt-1.5 flex items-center gap-2">
                                                    <Badge
                                                        variant="outline"
                                                        className={cn("text-[10px] capitalize", statusStyles[cam.status])}
                                                    >
                                                        {cam.status}
                                                    </Badge>
                                                    <span className="flex items-center gap-1 font-mono text-[10px] text-muted-foreground">
                            <Wifi className="size-3" />
                                                        {cam.signal}%
                          </span>
                                                </div>
                                            </div>
                                        </button>
                                    </li>
                                ))}
                            </ul>
                        </ScrollArea>
                    </CardContent>
                </Card>

                {/* detail */}
                <Card>
                    <CardContent className="space-y-4 p-4">
                        {active && (
                            <>
                                <div className="flex items-start justify-between">
                                    <div>
                                        <div className="font-mono text-xs text-muted-foreground">{active.id}</div>
                                        <div className="text-xl font-semibold text-foreground">{active.name}</div>
                                        <div className="flex items-center gap-1 text-sm text-muted-foreground">
                                            <MapPin className="size-3.5" />
                                            {active.zone}
                                        </div>
                                    </div>
                                    <Badge variant="outline" className={cn("capitalize", statusStyles[active.status])}>
                                        {active.status}
                                    </Badge>
                                </div>

                                {/* feed viewport */}
                                <div className="relative aspect-video w-full overflow-hidden rounded-md border border-border bg-muted">
                                    {active.status === "offline" ? (
                                        <div className="flex h-full flex-col items-center justify-center gap-2 text-muted-foreground">
                                            <VideoOff className="size-7" />
                                            <span className="text-sm">Signal lost</span>
                                        </div>
                                    ) : (
                                        <>
                                            {/* eslint-disable-next-line @next/next/no-img-element */}
                                            <img
                                                src={active.feed || "/placeholder.svg"}
                                                alt={`Live feed from ${active.name}`}
                                                className={cn(
                                                    "h-full w-full object-cover",
                                                    active.status === "degraded" && "opacity-70 blur-[1px]",
                                                )}
                                            />
                                            <span className="absolute left-2 top-2 flex items-center gap-1.5 rounded bg-black/50 px-1.5 py-0.5 text-[10px] font-medium uppercase tracking-wide text-white backdrop-blur">
                        <span className="size-1.5 animate-pulse rounded-full bg-destructive" />
                        Live
                      </span>
                                            <button
                                                className="absolute right-2 top-2 rounded bg-black/50 p-1.5 text-white backdrop-blur transition-colors hover:bg-black/70"
                                                aria-label={`Expand ${active.name} feed`}
                                            >
                                                <Maximize2 className="size-3.5" />
                                            </button>
                                        </>
                                    )}
                                </div>

                                {/* metadata */}
                                <div className="grid grid-cols-3 gap-2">
                                    <Meta label="Signal" value={`${active.signal}%`} />
                                    <Meta label="Zone" value={active.zone} />
                                    <Meta label="Edge Node" value={active.id.replace("CAM", "EDGE")} />
                                </div>

                                {/* actions */}
                                <div className="flex flex-wrap gap-2">
                                    <Button size="sm">
                                        <Camera className="size-3.5" />
                                        Capture snapshot
                                    </Button>
                                    <Button size="sm" variant="outline">
                                        <FileText className="size-3.5" />
                                        Create incident
                                    </Button>
                                    <Button size="sm" variant="outline">
                                        <Download className="size-3.5" />
                                        Download clip
                                    </Button>
                                </div>
                            </>
                        )}
                    </CardContent>
                </Card>
            </div>
        </>
    )
}

function Meta({ label, value }: { label: string; value: string }) {
    return (
        <div className="rounded-md border border-border bg-muted/30 px-2 py-1.5">
            <div className="text-[10px] uppercase tracking-wide text-muted-foreground">{label}</div>
            <div className="font-mono text-sm text-foreground">{value}</div>
        </div>
    )
}