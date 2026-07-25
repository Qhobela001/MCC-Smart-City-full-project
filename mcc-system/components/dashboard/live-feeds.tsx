import { Maximize2, VideoOff, Wifi } from "lucide-react"
import { Card, CardHeader, CardTitle } from "@/components/ui/card"
import { cameras } from "@/lib/mock-data"
import { cn } from "@/lib/utils"

const statusStyles: Record<string, string> = {
  online: "bg-chart-2/15 text-chart-2 border-chart-2/30",
  degraded: "bg-chart-3/15 text-chart-3 border-chart-3/30",
  offline: "bg-destructive/15 text-destructive border-destructive/30",
}

export function LiveFeeds() {
  return (
    <Card className="gap-4">
      <CardHeader className="flex flex-row items-center justify-between">
        <CardTitle className="text-base">Live Camera Feeds</CardTitle>
        <span className="text-xs text-muted-foreground">Field Layer · {cameras.length} sources</span>
      </CardHeader>
      <div className="grid grid-cols-1 gap-3 px-6 pb-6 sm:grid-cols-2">
        {cameras.slice(0, 4).map((cam) => (
          <figure
            key={cam.id}
            className="group relative aspect-video overflow-hidden rounded-md border border-border bg-muted"
          >
            {cam.status === "offline" ? (
              <div className="flex h-full flex-col items-center justify-center gap-2 text-muted-foreground">
                <VideoOff className="size-6" />
                <span className="text-xs">Signal lost</span>
              </div>
            ) : (
              // eslint-disable-next-line @next/next/no-img-element
              <img
                src={cam.feed || "/placeholder.svg"}
                alt={`Live feed from ${cam.name}`}
                className={cn(
                  "h-full w-full object-cover transition-transform duration-500 group-hover:scale-105",
                  cam.status === "degraded" && "opacity-70 blur-[1px]",
                )}
              />
            )}

            {/* top overlay */}
            <div className="absolute inset-x-0 top-0 flex items-center justify-between bg-gradient-to-b from-black/70 to-transparent p-2">
              <span
                className={cn(
                  "flex items-center gap-1.5 rounded border px-1.5 py-0.5 text-[10px] font-medium uppercase tracking-wide backdrop-blur",
                  statusStyles[cam.status],
                )}
              >
                <span className="size-1.5 rounded-full bg-current" />
                {cam.status}
              </span>
              <span className="rounded bg-black/40 px-1.5 py-0.5 font-mono text-[10px] text-white/90 backdrop-blur">
                {cam.id}
              </span>
            </div>

            {/* bottom overlay */}
            <figcaption className="absolute inset-x-0 bottom-0 flex items-end justify-between bg-gradient-to-t from-black/75 to-transparent p-2">
              <div className="leading-tight">
                <p className="text-xs font-medium text-white">{cam.name}</p>
                <p className="text-[10px] text-white/70">{cam.zone}</p>
              </div>
              <span className="flex items-center gap-1 text-[10px] text-white/80">
                <Wifi className="size-3" />
                {cam.signal}%
              </span>
            </figcaption>

            <button
              className="absolute right-2 top-1/2 hidden -translate-y-1/2 rounded bg-black/50 p-1.5 text-white opacity-0 backdrop-blur transition-opacity group-hover:opacity-100 sm:block"
              aria-label={`Expand ${cam.name} feed`}
            >
              <Maximize2 className="size-3.5" />
            </button>
          </figure>
        ))}
      </div>
    </Card>
  )
}
