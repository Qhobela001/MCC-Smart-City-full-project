"use client"

import { useState } from "react"
import { MapPin } from "lucide-react"
import { Card, CardHeader, CardTitle } from "@/components/ui/card"
import { cameras } from "@/lib/mock-data"
import { cn } from "@/lib/utils"

const pinColor: Record<string, string> = {
  online: "text-chart-2",
  degraded: "text-chart-3",
  offline: "text-destructive",
}

export function CameraMap() {
  const [active, setActive] = useState<string | null>(null)

  return (
    <Card className="gap-3">
      <CardHeader className="flex flex-row items-center justify-between">
        <CardTitle className="text-base">Camera Network — Maseru</CardTitle>
        <div className="flex items-center gap-3 text-[11px] text-muted-foreground">
          <span className="flex items-center gap-1">
            <span className="size-2 rounded-full bg-chart-2" /> Online
          </span>
          <span className="flex items-center gap-1">
            <span className="size-2 rounded-full bg-chart-3" /> Degraded
          </span>
          <span className="flex items-center gap-1">
            <span className="size-2 rounded-full bg-destructive" /> Offline
          </span>
        </div>
      </CardHeader>

      <div className="px-6 pb-6">
        <div
          className="relative aspect-[16/10] w-full overflow-hidden rounded-md border border-border"
          style={{
            backgroundColor: "oklch(0.22 0.01 250)",
            backgroundImage:
              "linear-gradient(oklch(1 0 0 / 6%) 1px, transparent 1px), linear-gradient(90deg, oklch(1 0 0 / 6%) 1px, transparent 1px)",
            backgroundSize: "40px 40px",
          }}
        >
          {/* stylized roads */}
          <svg className="absolute inset-0 h-full w-full" preserveAspectRatio="none">
            <path
              d="M 0 60% L 100% 45%"
              stroke="oklch(1 0 0 / 10%)"
              strokeWidth="6"
              fill="none"
            />
            <path d="M 35% 0 L 55% 100%" stroke="oklch(1 0 0 / 10%)" strokeWidth="6" fill="none" />
            <path d="M 10% 30% L 90% 75%" stroke="oklch(1 0 0 / 7%)" strokeWidth="4" fill="none" />
          </svg>

          {cameras.map((cam) => (
            <button
              key={cam.id}
              onMouseEnter={() => setActive(cam.id)}
              onMouseLeave={() => setActive(null)}
              onClick={() => setActive(active === cam.id ? null : cam.id)}
              className="absolute -translate-x-1/2 -translate-y-1/2"
              style={{ left: `${cam.x}%`, top: `${cam.y}%` }}
              aria-label={`${cam.name} — ${cam.status}`}
            >
              <span className="relative flex items-center justify-center">
                {cam.status !== "offline" && (
                  <span
                    className={cn(
                      "absolute inline-flex size-7 animate-ping rounded-full opacity-30",
                      cam.status === "online" ? "bg-chart-2" : "bg-chart-3",
                    )}
                  />
                )}
                <MapPin
                  className={cn("relative size-6 drop-shadow", pinColor[cam.status])}
                  fill="currentColor"
                />
              </span>

              {active === cam.id && (
                <div className="absolute left-1/2 top-full z-10 mt-1 w-40 -translate-x-1/2 rounded-md border border-border bg-popover p-2 text-left shadow-lg">
                  <p className="font-mono text-[10px] text-muted-foreground">{cam.id}</p>
                  <p className="text-xs font-medium text-popover-foreground">{cam.name}</p>
                  <p className="text-[11px] text-muted-foreground">{cam.zone}</p>
                  <p className="mt-1 text-[11px] capitalize text-muted-foreground">
                    Status: <span className={pinColor[cam.status]}>{cam.status}</span>
                  </p>
                </div>
              )}
            </button>
          ))}
        </div>
      </div>
    </Card>
  )
}
