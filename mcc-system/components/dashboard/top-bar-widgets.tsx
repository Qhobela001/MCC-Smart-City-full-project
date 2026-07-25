"use client"

import { useEffect, useState } from "react"
import { Cloud, CloudRain, Droplets, Wind, Clock } from "lucide-react"
import { weather, getSystemHealth } from "@/lib/mock-data"
import { cn } from "@/lib/utils"

/* ---------------- System Status Indicator ---------------- */

const statusConfig = {
    operational: { dot: "bg-chart-2", text: "text-chart-2", border: "border-chart-2/30", bg: "bg-chart-2/10", label: "Operational" },
    degraded: { dot: "bg-chart-3", text: "text-chart-3", border: "border-chart-3/30", bg: "bg-chart-3/10", label: "Degraded" },
    critical: { dot: "bg-destructive", text: "text-destructive", border: "border-destructive/30", bg: "bg-destructive/10", label: "Critical — Node Offline" },
}

export function SystemStatusWidget() {
    const health = getSystemHealth()
    const c = statusConfig[health.level]
    return (
        <div
            title={`Online ${health.online} · Degraded ${health.degraded} · Offline ${health.offline} of ${health.total} nodes`}
            className={cn("hidden items-center gap-2 rounded-md border px-2.5 py-1.5 md:flex", c.border, c.bg)}
        >
      <span className="relative flex size-2">
        <span className={cn("absolute inline-flex size-full animate-ping rounded-full opacity-75", c.dot)} />
        <span className={cn("relative inline-flex size-2 rounded-full", c.dot)} />
      </span>
            <span className={cn("text-xs font-medium", c.text)}>{c.label}</span>
        </div>
    )
}

/* ---------------- Active Weather Overlay ---------------- */

export function WeatherWidget() {
    const WeatherIcon = weather.precipitationPct >= 50 ? CloudRain : Cloud
    return (
        <div
            title={`${weather.location} · ${weather.condition}`}
            className="hidden items-center gap-3 rounded-md border border-border bg-card px-3 py-1.5 lg:flex"
        >
            <div className="flex items-center gap-1.5">
                <WeatherIcon className="size-4 text-muted-foreground" />
                <span className="text-sm font-medium text-foreground">{weather.temperatureC}&deg;C</span>
            </div>
            <div className="flex items-center gap-1 text-xs text-muted-foreground">
                <Droplets className="size-3.5" />
                <span className="tabular-nums">{weather.precipitationPct}%</span>
            </div>
            <div className="flex items-center gap-1 text-xs text-muted-foreground">
                <Wind className="size-3.5" />
                <span className="tabular-nums">{weather.windKph} km/h</span>
            </div>
        </div>
    )
}

/* ---------------- Time & Date (Local / UTC toggle) ---------------- */

export function DateTimeWidget() {
    const [now, setNow] = useState<Date | null>(null)
    const [useUtc, setUseUtc] = useState(false)

    useEffect(() => {
        setNow(new Date())
        const id = setInterval(() => setNow(new Date()), 1000)
        return () => clearInterval(id)
    }, [])

    if (!now) {
        // avoid hydration mismatch until mounted on the client
        return <div className="h-9 w-40 rounded-md border border-border bg-card" />
    }

    const time = now.toLocaleTimeString("en-GB", {
        hour: "2-digit",
        minute: "2-digit",
        second: "2-digit",
        timeZone: useUtc ? "UTC" : undefined,
    })
    const date = now.toLocaleDateString("en-GB", {
        day: "2-digit",
        month: "short",
        timeZone: useUtc ? "UTC" : undefined,
    })

    return (
        <button
            onClick={() => setUseUtc((v) => !v)}
            title="Click to toggle Local / UTC time"
            className="hidden items-center gap-2 rounded-md border border-border bg-card px-3 py-1.5 text-left transition-colors hover:bg-accent/50 md:flex"
        >
            <Clock className="size-4 text-muted-foreground" />
            <span className="font-mono text-sm tabular-nums text-foreground">{time}</span>
            <span className="hidden text-xs text-muted-foreground lg:inline">{date}</span>
            <span className="rounded bg-muted px-1.5 py-0.5 text-[10px] font-semibold uppercase text-muted-foreground">
        {useUtc ? "UTC" : "Local"}
      </span>
        </button>
    )
}