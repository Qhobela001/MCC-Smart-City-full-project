"use client"

import { Area, AreaChart, Bar, BarChart, CartesianGrid, Line, LineChart, XAxis, YAxis } from "recharts"
import { Card, CardHeader, CardTitle } from "@/components/ui/card"
import {
  ChartConfig,
  ChartContainer,
  ChartLegend,
  ChartLegendContent,
  ChartTooltip,
  ChartTooltipContent,
} from "@/components/ui/chart"
import { incidentTrend, responseLatency, teamPerformance } from "@/lib/mock-data"

const trendConfig = {
  dumping: { label: "Illegal Dumping", color: "var(--chart-1)" },
  road: { label: "Road Damage", color: "var(--chart-2)" },
  smoke: { label: "Vehicle Smoke", color: "var(--chart-3)" },
  noise: { label: "Noise", color: "var(--chart-4)" },
} satisfies ChartConfig

const latencyConfig = {
  latency: { label: "Alert Latency (s)", color: "var(--chart-2)" },
} satisfies ChartConfig

const teamConfig = {
  resolved: { label: "Resolved", color: "var(--chart-1)" },
} satisfies ChartConfig

export function AnalyticsCharts() {
  return (
    <div className="grid grid-cols-1 gap-4 xl:grid-cols-2">
      <Card className="gap-3 xl:col-span-2">
        <CardHeader>
          <CardTitle className="text-base">Incident Volume by Category</CardTitle>
          <p className="text-xs text-muted-foreground">Last 12 hours · AI-detected events</p>
        </CardHeader>
        <div className="px-6 pb-6">
          <ChartContainer config={trendConfig} className="h-[260px] w-full">
            <AreaChart data={incidentTrend} margin={{ left: -16, right: 8, top: 8 }}>
              <defs>
                {Object.entries(trendConfig).map(([key, cfg]) => (
                  <linearGradient key={key} id={`fill-${key}`} x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor={cfg.color} stopOpacity={0.4} />
                    <stop offset="95%" stopColor={cfg.color} stopOpacity={0.05} />
                  </linearGradient>
                ))}
              </defs>
              <CartesianGrid vertical={false} stroke="var(--border)" />
              <XAxis dataKey="hour" tickLine={false} axisLine={false} tickMargin={8} fontSize={11} />
              <YAxis tickLine={false} axisLine={false} fontSize={11} width={32} />
              <ChartTooltip content={<ChartTooltipContent />} />
              <ChartLegend content={<ChartLegendContent />} />
              {Object.keys(trendConfig).map((key) => (
                <Area
                  key={key}
                  dataKey={key}
                  type="monotone"
                  stackId="1"
                  stroke={`var(--color-${key})`}
                  fill={`url(#fill-${key})`}
                  strokeWidth={2}
                />
              ))}
            </AreaChart>
          </ChartContainer>
        </div>
      </Card>

      <Card className="gap-3">
        <CardHeader>
          <CardTitle className="text-base">AI Alert Latency</CardTitle>
          <p className="text-xs text-muted-foreground">Daily average · SLA target &lt; 5s</p>
        </CardHeader>
        <div className="px-6 pb-6">
          <ChartContainer config={latencyConfig} className="h-[220px] w-full">
            <LineChart data={responseLatency} margin={{ left: -16, right: 8, top: 8 }}>
              <CartesianGrid vertical={false} stroke="var(--border)" />
              <XAxis dataKey="day" tickLine={false} axisLine={false} tickMargin={8} fontSize={11} />
              <YAxis tickLine={false} axisLine={false} fontSize={11} width={32} domain={[0, 6]} />
              <ChartTooltip content={<ChartTooltipContent />} />
              <Line
                dataKey="latency"
                type="monotone"
                stroke="var(--color-latency)"
                strokeWidth={2}
                dot={{ r: 3, fill: "var(--color-latency)" }}
              />
            </LineChart>
          </ChartContainer>
        </div>
      </Card>

      <Card className="gap-3">
        <CardHeader>
          <CardTitle className="text-base">Weekly Team Performance</CardTitle>
          <p className="text-xs text-muted-foreground">Incidents resolved by field team</p>
        </CardHeader>
        <div className="px-6 pb-6">
          <ChartContainer config={teamConfig} className="h-[220px] w-full">
            <BarChart data={teamPerformance} margin={{ left: -16, right: 8, top: 8 }}>
              <CartesianGrid vertical={false} stroke="var(--border)" />
              <XAxis dataKey="team" tickLine={false} axisLine={false} tickMargin={8} fontSize={11} />
              <YAxis tickLine={false} axisLine={false} fontSize={11} width={32} />
              <ChartTooltip content={<ChartTooltipContent />} />
              <Bar dataKey="resolved" fill="var(--color-resolved)" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ChartContainer>
        </div>
      </Card>
    </div>
  )
}
