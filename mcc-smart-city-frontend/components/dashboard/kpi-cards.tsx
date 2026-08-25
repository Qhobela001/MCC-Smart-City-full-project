import Link from "next/link"
import { ArrowDownRight, ArrowUpRight, Minus } from "lucide-react"
import { Card } from "@/components/ui/card"
import { kpis } from "@/lib/mock-data"
import { cn } from "@/lib/utils"

export function KpiCards() {
  return (
      <div className="grid grid-cols-2 gap-4 xl:grid-cols-4">
        {kpis.map((kpi) => {
          const TrendIcon =
              kpi.trend === "up" ? ArrowUpRight : kpi.trend === "down" ? ArrowDownRight : Minus
          return (
              <Link
                  key={kpi.label}
                  href={kpi.href}
                  className="rounded-xl transition-colors hover:border-primary/40 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
              >
                <Card className="h-full gap-2 p-4 transition-colors hover:bg-accent/40">
                  <p className="text-sm text-muted-foreground">{kpi.label}</p>
                  <div className="flex items-end justify-between gap-2">
                <span className="font-mono text-2xl font-semibold tracking-tight text-foreground md:text-3xl">
                  {kpi.value}
                </span>
                    <span
                        className={cn(
                            "flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-medium",
                            kpi.tone === "critical" && "bg-destructive/15 text-destructive",
                            kpi.tone === "good" && "bg-chart-2/15 text-chart-2",
                            kpi.tone === "default" && "bg-muted text-muted-foreground",
                        )}
                    >
                  <TrendIcon className="size-3" />
                      {kpi.delta}
                </span>
                  </div>
                </Card>
              </Link>
          )
        })}
      </div>
  )
}