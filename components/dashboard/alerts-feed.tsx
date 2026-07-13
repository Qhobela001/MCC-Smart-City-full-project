"use client"

import { useState } from "react"
import { Check, ChevronRight, Send, Trash2, Truck } from "lucide-react"
import { Card, CardHeader, CardTitle } from "@/components/ui/card"
import { ScrollArea } from "@/components/ui/scroll-area"
import { incidents as initialIncidents, type AlertStatus, type Incident } from "@/lib/mock-data"
import { cn } from "@/lib/utils"

const severityStyles: Record<string, string> = {
  critical: "border-l-destructive",
  warning: "border-l-chart-3",
  info: "border-l-primary",
}

const severityDot: Record<string, string> = {
  critical: "bg-destructive",
  warning: "bg-chart-3",
  info: "bg-primary",
}

const statusLabel: Record<AlertStatus, string> = {
  new: "New",
  acknowledged: "Acknowledged",
  dispatched: "Dispatched",
}

const statusStyles: Record<AlertStatus, string> = {
  new: "bg-destructive/15 text-destructive",
  acknowledged: "bg-chart-3/15 text-chart-3",
  dispatched: "bg-chart-2/15 text-chart-2",
}

export function AlertsFeed() {
  const [items, setItems] = useState<Incident[]>(initialIncidents)
  const [selected, setSelected] = useState<string | null>(null)

  const advance = (id: string) => {
    setItems((prev) =>
      prev.map((inc) =>
        inc.id === id
          ? {
              ...inc,
              status: inc.status === "new" ? "acknowledged" : "dispatched",
            }
          : inc,
      ),
    )
  }

  const dismiss = (id: string) => {
    setItems((prev) => prev.filter((inc) => inc.id !== id))
    if (selected === id) setSelected(null)
  }

  return (
    <Card className="flex h-full flex-col gap-3">
      <CardHeader className="flex flex-row items-center justify-between">
        <CardTitle className="text-base">Incident Alerts</CardTitle>
        <span className="rounded-full bg-destructive/15 px-2 py-0.5 text-xs font-medium text-destructive">
          {items.filter((i) => i.status === "new").length} new
        </span>
      </CardHeader>

      <ScrollArea className="h-[440px] px-3">
        <div className="flex flex-col gap-2 pb-3">
          {items.length === 0 ? (
            <p className="px-3 py-8 text-center text-sm text-muted-foreground">
              No active incidents. All clear.
            </p>
          ) : (
            items.map((inc) => {
              const isOpen = selected === inc.id
              return (
                <div
                  key={inc.id}
                  className={cn(
                    "rounded-md border border-l-2 border-border bg-card/60 transition-colors",
                    severityStyles[inc.severity],
                  )}
                >
                  <button
                    onClick={() => setSelected(isOpen ? null : inc.id)}
                    className="flex w-full items-start gap-3 p-3 text-left"
                  >
                    <span className={cn("mt-1.5 size-2 shrink-0 rounded-full", severityDot[inc.severity])} />
                    <div className="min-w-0 flex-1">
                      <div className="flex items-center justify-between gap-2">
                        <p className="truncate text-sm font-medium text-foreground">{inc.type}</p>
                        <span className="shrink-0 font-mono text-[11px] text-muted-foreground">
                          {inc.detectedAgo}
                        </span>
                      </div>
                      <p className="truncate text-xs text-muted-foreground">{inc.location}</p>
                      <div className="mt-1.5 flex items-center gap-2">
                        <span
                          className={cn(
                            "rounded px-1.5 py-0.5 text-[10px] font-medium",
                            statusStyles[inc.status],
                          )}
                        >
                          {statusLabel[inc.status]}
                        </span>
                        <span className="font-mono text-[10px] text-muted-foreground">
                          {inc.camera} · {inc.confidence}% conf.
                        </span>
                      </div>
                    </div>
                    <ChevronRight
                      className={cn(
                        "mt-1 size-4 shrink-0 text-muted-foreground transition-transform",
                        isOpen && "rotate-90",
                      )}
                    />
                  </button>

                  {isOpen && (
                    <div className="flex flex-wrap gap-2 border-t border-border px-3 py-2.5">
                      {inc.status === "new" && (
                        <button
                          onClick={() => advance(inc.id)}
                          className="flex items-center gap-1.5 rounded-md bg-secondary px-2.5 py-1.5 text-xs font-medium text-secondary-foreground transition-colors hover:bg-secondary/80"
                        >
                          <Check className="size-3.5" />
                          Acknowledge
                        </button>
                      )}
                      {inc.status !== "dispatched" && (
                        <button
                          onClick={() => advance(inc.status === "new" ? inc.id : inc.id)}
                          className="flex items-center gap-1.5 rounded-md bg-primary px-2.5 py-1.5 text-xs font-medium text-primary-foreground transition-colors hover:bg-primary/90"
                        >
                          <Truck className="size-3.5" />
                          Dispatch team
                        </button>
                      )}
                      <button className="flex items-center gap-1.5 rounded-md border border-border px-2.5 py-1.5 text-xs font-medium text-foreground transition-colors hover:bg-accent">
                        <Send className="size-3.5" />
                        Generate report
                      </button>
                      <button
                        onClick={() => dismiss(inc.id)}
                        className="flex items-center gap-1.5 rounded-md px-2.5 py-1.5 text-xs font-medium text-muted-foreground transition-colors hover:text-destructive"
                      >
                        <Trash2 className="size-3.5" />
                        Dismiss
                      </button>
                    </div>
                  )}
                </div>
              )
            })
          )}
        </div>
      </ScrollArea>
    </Card>
  )
}
