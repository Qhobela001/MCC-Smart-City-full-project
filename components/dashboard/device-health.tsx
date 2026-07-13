import { Cpu, HardDrive, Radio } from "lucide-react"
import { Card, CardHeader, CardTitle } from "@/components/ui/card"
import { Progress } from "@/components/ui/progress"
import { edgeDevices } from "@/lib/mock-data"
import { cn } from "@/lib/utils"

const typeIcon: Record<string, typeof Cpu> = {
  "AI Inference": Cpu,
  "Wireless Link": Radio,
  "Footage Archive": HardDrive,
}

const statusStyles: Record<string, string> = {
  online: "bg-chart-2/15 text-chart-2",
  degraded: "bg-chart-3/15 text-chart-3",
  offline: "bg-destructive/15 text-destructive",
}

export function DeviceHealth() {
  return (
    <Card className="gap-3">
      <CardHeader>
        <CardTitle className="text-base">Edge & Infrastructure Health</CardTitle>
        <p className="text-xs text-muted-foreground">Field & central processing layers</p>
      </CardHeader>
      <div className="flex flex-col gap-3 px-6 pb-6">
        {edgeDevices.map((device) => {
          const Icon = typeIcon[device.type] ?? Cpu
          return (
            <div key={device.id} className="rounded-md border border-border bg-card/60 p-3">
              <div className="flex items-center gap-3">
                <div className="flex size-9 shrink-0 items-center justify-center rounded-md bg-secondary text-secondary-foreground">
                  <Icon className="size-4" />
                </div>
                <div className="min-w-0 flex-1">
                  <div className="flex items-center justify-between gap-2">
                    <p className="truncate text-sm font-medium text-foreground">{device.name}</p>
                    <span
                      className={cn(
                        "shrink-0 rounded px-1.5 py-0.5 text-[10px] font-medium capitalize",
                        statusStyles[device.status],
                      )}
                    >
                      {device.status}
                    </span>
                  </div>
                  <p className="font-mono text-[11px] text-muted-foreground">
                    {device.id} · {device.metric}
                  </p>
                </div>
              </div>
              <div className="mt-2.5 flex items-center gap-2">
                <Progress value={device.load} className="h-1.5" />
                <span className="w-9 text-right font-mono text-[11px] text-muted-foreground">
                  {device.load}%
                </span>
              </div>
            </div>
          )
        })}
      </div>
    </Card>
  )
}
