"use client"

import {
  useCallback,
  useEffect,
  useMemo,
  useState,
} from "react"

import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  XAxis,
  YAxis,
} from "recharts"

import {
  CalendarDays,
  Filter,
  RefreshCw,
  RotateCcw,
} from "lucide-react"

import { apiFetch } from "@/lib/api"

import {
  Card,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"

import {
  ChartConfig,
  ChartContainer,
  ChartTooltip,
  ChartTooltipContent,
} from "@/components/ui/chart"


type AnalyticsOverview = {
  total_detections: number
  average_confidence: number
  unique_cameras: number
  unique_locations: number
  unreviewed: number
  confirmed: number
  rejected: number
  earliest_detection: string | null
  latest_detection: string | null
}


type DetectionTypeAnalytics = {
  detection_type: string
  count: number
  average_confidence: number
  percentage: number
}


type TrendPoint = {
  date: string
  count: number
  average_confidence: number
}


type LocationAnalytics = {
  location_name: string
  count: number
  average_confidence: number
}


type CameraAnalytics = {
  camera_identifier: string
  count: number
  average_confidence: number
  latest_detection: string | null
}


type HourAnalytics = {
  hour: number
  count: number
  average_confidence: number
}


type ModelPerformance = {
  model_name: string
  model_version: string | null
  detections: number
  average_confidence: number
  minimum_confidence: number
  maximum_confidence: number
  unreviewed: number
  confirmed: number
  rejected: number
}


type RecentDetection = {
  id: number
  detection_uuid: string
  detection_type: string
  class_name: string
  confidence: number
  detected_at: string
  source_type: string
  camera_identifier: string | null
  stream_identifier: string | null
  model_name: string
  model_version: string | null
  location_name: string | null
  latitude: number | null
  longitude: number | null
  snapshot_path: string | null
  clip_path: string | null
  object_count: number
  attributes: Record<string, unknown>
  incident_id: number | null
  review_status: string
  reviewed_by_id: number | null
  reviewed_at: string | null
  is_test: boolean
  created_at: string
  updated_at: string
}


type RecentResponse = {
  items: RecentDetection[]
}


type AnalyticsFilters = {
  dateFrom: string
  dateTo: string
  detectionType: string
  cameraIdentifier: string
  modelName: string
  minConfidence: string
  includeTest: boolean
}


const emptyFilters: AnalyticsFilters = {
  dateFrom: "",
  dateTo: "",
  detectionType: "",
  cameraIdentifier: "",
  modelName: "",
  minConfidence: "",
  includeTest: true,
}


const detectionTypes = [
  ["illegal_dumping", "Illegal Dumping"],
  ["pothole", "Pothole"],
  ["road_damage", "Road Damage"],
  ["public_urination", "Public Urination"],
  ["unauthorized_vending", "Unauthorized Vending"],
  [
    "street_cleaner_non_compliance",
    "Street Cleaner Non-Compliance",
  ],
  ["skip_overflow", "Skip Overflow"],
  [
    "vehicle_smoke_emission",
    "Vehicle Smoke Emission",
  ],
  ["noise_pollution", "Noise Pollution"],
  ["other", "Other"],
]


const trendConfig = {
  count: {
    label: "Detections",
    color: "var(--chart-1)",
  },
} satisfies ChartConfig


const typeConfig = {
  count: {
    label: "Detections",
    color: "var(--chart-2)",
  },
} satisfies ChartConfig


const hourConfig = {
  count: {
    label: "Detections",
    color: "var(--chart-3)",
  },
} satisfies ChartConfig


function detectionLabel(value: string) {
  const match = detectionTypes.find(
      ([key]) => key === value,
  )

  if (match) {
    return match[1]
  }

  return value
      .split("_")
      .map(
          (part) =>
              part.charAt(0).toUpperCase() +
              part.slice(1),
      )
      .join(" ")
}


function reviewLabel(value: string) {
  if (value === "confirmed") {
    return "Confirmed"
  }

  if (value === "rejected") {
    return "Rejected"
  }

  return "Unreviewed"
}


function formatConfidence(value: number) {
  return `${(value * 100).toFixed(1)}%`
}


function formatDate(value: string | null) {
  if (!value) {
    return "—"
  }

  return new Intl.DateTimeFormat("en-ZA", {
    day: "2-digit",
    month: "short",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(value))
}


function formatShortDate(value: string) {
  return new Intl.DateTimeFormat("en-ZA", {
    day: "2-digit",
    month: "short",
  }).format(
      new Date(`${value}T00:00:00`),
  )
}


function hourLabel(hour: number) {
  return `${String(hour).padStart(2, "0")}:00`
}


function dateInputValue(date: Date) {
  const year = date.getFullYear()

  const month = String(
      date.getMonth() + 1,
  ).padStart(2, "0")

  const day = String(
      date.getDate(),
  ).padStart(2, "0")

  return `${year}-${month}-${day}`
}


function buildQuery(
    filters: AnalyticsFilters,
) {
  const params = new URLSearchParams()

  params.set(
      "include_test",
      filters.includeTest
          ? "true"
          : "false",
  )

  if (filters.dateFrom) {
    const start = new Date(
        `${filters.dateFrom}T00:00:00`,
    )

    params.set(
        "date_from",
        start.toISOString(),
    )
  }

  if (filters.dateTo) {
    const end = new Date(
        `${filters.dateTo}T23:59:59`,
    )

    params.set(
        "date_to",
        end.toISOString(),
    )
  }

  if (filters.detectionType) {
    params.set(
        "detection_type",
        filters.detectionType,
    )
  }

  if (filters.cameraIdentifier) {
    params.set(
        "camera_identifier",
        filters.cameraIdentifier,
    )
  }

  if (filters.modelName) {
    params.set(
        "model_name",
        filters.modelName,
    )
  }

  if (filters.minConfidence) {
    params.set(
        "min_confidence",
        filters.minConfidence,
    )
  }

  return params.toString()
}


export function AnalyticsCharts() {
  const [overview, setOverview] =
      useState<AnalyticsOverview | null>(null)

  const [byType, setByType] =
      useState<DetectionTypeAnalytics[]>([])

  const [trend, setTrend] =
      useState<TrendPoint[]>([])

  const [locations, setLocations] =
      useState<LocationAnalytics[]>([])

  const [cameras, setCameras] =
      useState<CameraAnalytics[]>([])

  const [hourly, setHourly] =
      useState<HourAnalytics[]>([])

  const [models, setModels] =
      useState<ModelPerformance[]>([])

  const [recent, setRecent] =
      useState<RecentDetection[]>([])

  const [filters, setFilters] =
      useState<AnalyticsFilters>(
          emptyFilters,
      )

  const [appliedFilters, setAppliedFilters] =
      useState<AnalyticsFilters>(
          emptyFilters,
      )

  const [loading, setLoading] =
      useState(true)

  const [error, setError] =
      useState<string | null>(null)


  const loadAnalytics =
      useCallback(async () => {
        setLoading(true)
        setError(null)

        const query =
            buildQuery(appliedFilters)

        try {
          const [
            overviewResponse,
            typeResponse,
            trendResponse,
            locationResponse,
            cameraResponse,
            hourResponse,
            modelResponse,
            recentResponse,
          ] = await Promise.all([
            apiFetch<AnalyticsOverview>(
                `/analytics/overview?${query}`,
            ),

            apiFetch<
                DetectionTypeAnalytics[]
            >(
                `/analytics/by-type?${query}`,
            ),

            apiFetch<TrendPoint[]>(
                `/analytics/trend?${query}`,
            ),

            apiFetch<LocationAnalytics[]>(
                `/analytics/by-location?${query}`,
            ),

            apiFetch<CameraAnalytics[]>(
                `/analytics/by-camera?${query}`,
            ),

            apiFetch<HourAnalytics[]>(
                `/analytics/by-hour?${query}`,
            ),

            apiFetch<ModelPerformance[]>(
                `/analytics/model-performance?${query}`,
            ),

            apiFetch<RecentResponse>(
                `/analytics/recent?limit=15&${query}`,
            ),
          ])

          setOverview(
              overviewResponse,
          )

          setByType(typeResponse)
          setTrend(trendResponse)
          setLocations(locationResponse)
          setCameras(cameraResponse)
          setHourly(hourResponse)
          setModels(modelResponse)

          setRecent(
              recentResponse.items,
          )
        } catch (requestError) {
          setError(
              requestError instanceof Error
                  ? requestError.message
                  : "Unable to load analytics.",
          )
        } finally {
          setLoading(false)
        }
      }, [appliedFilters])


  useEffect(() => {
    void loadAnalytics()
  }, [loadAnalytics])


  const trendData = useMemo(
      () =>
          trend.map((item) => ({
            ...item,
            label: formatShortDate(
                item.date,
            ),
          })),
      [trend],
  )


  const typeData = useMemo(
      () =>
          byType.map((item) => ({
            ...item,
            label: detectionLabel(
                item.detection_type,
            ),
          })),
      [byType],
  )


  const hourlyData = useMemo(
      () =>
          hourly.map((item) => ({
            ...item,
            label: hourLabel(item.hour),
          })),
      [hourly],
  )


  const cameraOptions = useMemo(
      () =>
          [...cameras]
              .map(
                  (item) =>
                      item.camera_identifier,
              )
              .filter(Boolean)
              .sort(),
      [cameras],
  )


  const modelOptions = useMemo(
      () =>
          [
            ...new Set(
                models.map(
                    (item) =>
                        item.model_name,
                ),
            ),
          ].sort(),
      [models],
  )


  const activeFilterCount =
      useMemo(() => {
        let count = 0

        if (
            appliedFilters.dateFrom
        ) {
          count++
        }

        if (appliedFilters.dateTo) {
          count++
        }

        if (
            appliedFilters.detectionType
        ) {
          count++
        }

        if (
            appliedFilters.cameraIdentifier
        ) {
          count++
        }

        if (
            appliedFilters.modelName
        ) {
          count++
        }

        if (
            appliedFilters.minConfidence
        ) {
          count++
        }

        if (
            !appliedFilters.includeTest
        ) {
          count++
        }

        return count
      }, [appliedFilters])


  function applyFilters() {
    setAppliedFilters({
      ...filters,
    })
  }


  function resetFilters() {
    setFilters({
      ...emptyFilters,
    })

    setAppliedFilters({
      ...emptyFilters,
    })
  }


  function setPreset(
      days: number | null,
  ) {
    if (days === null) {
      setFilters((current) => ({
        ...current,
        dateFrom: "",
        dateTo: "",
      }))

      return
    }

    const today = new Date()

    const start = new Date(
        today,
    )

    start.setDate(
        today.getDate() -
        (days - 1),
    )

    setFilters((current) => ({
      ...current,
      dateFrom:
          dateInputValue(start),
      dateTo:
          dateInputValue(today),
    }))
  }


  return (
      <div className="space-y-4">

        {/* Filters */}
        <Card>
          <div className="p-5">

            <div className="flex flex-col gap-4 xl:flex-row xl:items-center xl:justify-between">

              <div>
                <div className="flex items-center gap-2">
                  <Filter className="size-4 text-primary" />

                  <h2 className="text-sm font-semibold">
                    Analytics Filters
                  </h2>

                  {activeFilterCount > 0 && (
                      <span className="rounded-full bg-primary/10 px-2 py-0.5 text-[10px] font-semibold text-primary">
                    {activeFilterCount} active
                  </span>
                  )}
                </div>

                <p className="mt-1 text-xs text-muted-foreground">
                  Filter AI-generated detection intelligence by date,
                  category, camera, model and confidence.
                </p>
              </div>


              <div className="flex flex-wrap items-center gap-2">

                <PresetButton
                    label="Today"
                    onClick={() =>
                        setPreset(1)
                    }
                />

                <PresetButton
                    label="7 Days"
                    onClick={() =>
                        setPreset(7)
                    }
                />

                <PresetButton
                    label="30 Days"
                    onClick={() =>
                        setPreset(30)
                    }
                />

                <PresetButton
                    label="All Time"
                    onClick={() =>
                        setPreset(null)
                    }
                />

              </div>

            </div>


            <div className="mt-5 grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-4">

              <FilterField
                  label="From"
              >
                <input
                    type="date"
                    value={
                      filters.dateFrom
                    }
                    onChange={(event) =>
                        setFilters(
                            (current) => ({
                              ...current,
                              dateFrom:
                              event.target
                                  .value,
                            }),
                        )
                    }
                    className="h-10 w-full rounded-md border bg-background px-3 text-sm outline-none transition focus:border-primary"
                />
              </FilterField>


              <FilterField
                  label="To"
              >
                <input
                    type="date"
                    value={
                      filters.dateTo
                    }
                    onChange={(event) =>
                        setFilters(
                            (current) => ({
                              ...current,
                              dateTo:
                              event.target
                                  .value,
                            }),
                        )
                    }
                    className="h-10 w-full rounded-md border bg-background px-3 text-sm outline-none transition focus:border-primary"
                />
              </FilterField>


              <FilterField
                  label="Detection Type"
              >
                <select
                    value={
                      filters.detectionType
                    }
                    onChange={(event) =>
                        setFilters(
                            (current) => ({
                              ...current,
                              detectionType:
                              event.target
                                  .value,
                            }),
                        )
                    }
                    className="h-10 w-full rounded-md border bg-background px-3 text-sm outline-none transition focus:border-primary"
                >
                  <option value="">
                    All detection types
                  </option>

                  {detectionTypes.map(
                      ([value, label]) => (
                          <option
                              key={value}
                              value={value}
                          >
                            {label}
                          </option>
                      ),
                  )}
                </select>
              </FilterField>


              <FilterField
                  label="Minimum Confidence"
              >
                <select
                    value={
                      filters.minConfidence
                    }
                    onChange={(event) =>
                        setFilters(
                            (current) => ({
                              ...current,
                              minConfidence:
                              event.target
                                  .value,
                            }),
                        )
                    }
                    className="h-10 w-full rounded-md border bg-background px-3 text-sm outline-none transition focus:border-primary"
                >
                  <option value="">
                    Any confidence
                  </option>

                  <option value="0.5">
                    50%+
                  </option>

                  <option value="0.6">
                    60%+
                  </option>

                  <option value="0.7">
                    70%+
                  </option>

                  <option value="0.8">
                    80%+
                  </option>

                  <option value="0.9">
                    90%+
                  </option>
                </select>
              </FilterField>


              <FilterField label="Camera">
                <select
                    value={
                      filters.cameraIdentifier
                    }
                    onChange={(event) =>
                        setFilters(
                            (current) => ({
                              ...current,
                              cameraIdentifier:
                              event.target
                                  .value,
                            }),
                        )
                    }
                    className="h-10 w-full rounded-md border bg-background px-3 text-sm outline-none transition focus:border-primary"
                >
                  <option value="">
                    All cameras
                  </option>

                  {cameraOptions.map(
                      (camera) => (
                          <option
                              key={camera}
                              value={camera}
                          >
                            {camera}
                          </option>
                      ),
                  )}
                </select>
              </FilterField>


              <FilterField label="AI Model">
                <select
                    value={
                      filters.modelName
                    }
                    onChange={(event) =>
                        setFilters(
                            (current) => ({
                              ...current,
                              modelName:
                              event.target
                                  .value,
                            }),
                        )
                    }
                    className="h-10 w-full rounded-md border bg-background px-3 text-sm outline-none transition focus:border-primary"
                >
                  <option value="">
                    All AI models
                  </option>

                  {modelOptions.map(
                      (model) => (
                          <option
                              key={model}
                              value={model}
                          >
                            {model}
                          </option>
                      ),
                  )}
                </select>
              </FilterField>


              <div className="flex items-end">
                <label className="flex h-10 w-full cursor-pointer items-center gap-3 rounded-md border bg-background px-3">

                  <input
                      type="checkbox"
                      checked={
                        filters.includeTest
                      }
                      onChange={(event) =>
                          setFilters(
                              (current) => ({
                                ...current,
                                includeTest:
                                event.target
                                    .checked,
                              }),
                          )
                      }
                      className="size-4"
                  />

                  <div>
                    <p className="text-xs font-medium">
                      Include test data
                    </p>

                    <p className="text-[10px] text-muted-foreground">
                      Development detections
                    </p>
                  </div>

                </label>
              </div>


              <div className="flex items-end gap-2">

                <button
                    type="button"
                    onClick={applyFilters}
                    className="inline-flex h-10 flex-1 items-center justify-center gap-2 rounded-md bg-primary px-4 text-sm font-medium text-primary-foreground transition hover:bg-primary/90"
                >
                  <Filter className="size-4" />
                  Apply
                </button>

                <button
                    type="button"
                    onClick={resetFilters}
                    title="Reset filters"
                    className="inline-flex size-10 items-center justify-center rounded-md border transition hover:bg-muted"
                >
                  <RotateCcw className="size-4" />
                </button>

              </div>

            </div>

          </div>
        </Card>


        {/* KPI cards */}
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-4">

          <MetricCard
              title="AI Detections"
              value={
                  overview?.total_detections.toLocaleString() ??
                  "0"
              }
              description="Events matching the current analysis"
          />

          <MetricCard
              title="Average Confidence"
              value={
                overview
                    ? formatConfidence(
                        overview.average_confidence,
                    )
                    : "0%"
              }
              description="Average AI detection confidence"
          />

          <MetricCard
              title="Active Cameras"
              value={
                  overview?.unique_cameras.toString() ??
                  "0"
              }
              description="Detection-producing cameras"
          />

          <MetricCard
              title="Detection Locations"
              value={
                  overview?.unique_locations.toString() ??
                  "0"
              }
              description="Locations represented in the data"
          />

        </div>


        {/* Review status */}
        <Card>
          <div className="grid grid-cols-1 divide-y md:grid-cols-3 md:divide-x md:divide-y-0">

            <ReviewMetric
                label="Unreviewed"
                value={
                    overview?.unreviewed ?? 0
                }
            />

            <ReviewMetric
                label="Confirmed"
                value={
                    overview?.confirmed ?? 0
                }
            />

            <ReviewMetric
                label="Rejected"
                value={
                    overview?.rejected ?? 0
                }
            />

          </div>
        </Card>


        {loading ? (
            <Card>
              <div className="flex h-[280px] items-center justify-center">
                <div className="flex items-center gap-2 text-sm text-muted-foreground">
                  <RefreshCw className="size-4 animate-spin" />
                  Loading analytics...
                </div>
              </div>
            </Card>
        ) : error ? (
            <Card>
              <div className="p-6">

                <p className="font-medium">
                  Analytics could not be loaded
                </p>

                <p className="mt-1 text-sm text-muted-foreground">
                  {error}
                </p>

                <button
                    type="button"
                    onClick={() =>
                        void loadAnalytics()
                    }
                    className="mt-4 rounded-md border px-4 py-2 text-sm font-medium transition hover:bg-muted"
                >
                  Try again
                </button>

              </div>
            </Card>
        ) : (
            <>

              {/* Trend */}
              <Card className="gap-3">

                <CardHeader className="flex-row items-start justify-between">

                  <div>
                    <CardTitle className="text-base">
                      Detection Trend
                    </CardTitle>

                    <p className="mt-1 text-xs text-muted-foreground">
                      AI-generated monitoring activity across the selected period
                    </p>
                  </div>

                  <button
                      type="button"
                      onClick={() =>
                          void loadAnalytics()
                      }
                      className="inline-flex h-9 items-center gap-2 rounded-md border px-3 text-xs font-medium transition hover:bg-muted"
                  >
                    <RefreshCw className="size-3.5" />
                    Refresh
                  </button>

                </CardHeader>

                <div className="px-6 pb-6">

                  {trendData.length === 0 ? (
                      <EmptyChart />
                  ) : (
                      <ChartContainer
                          config={trendConfig}
                          className="h-[280px] w-full"
                      >
                        <AreaChart
                            data={trendData}
                            margin={{
                              left: -16,
                              right: 8,
                              top: 8,
                            }}
                        >
                          <defs>
                            <linearGradient
                                id="fill-detections"
                                x1="0"
                                y1="0"
                                x2="0"
                                y2="1"
                            >
                              <stop
                                  offset="5%"
                                  stopColor="var(--color-count)"
                                  stopOpacity={0.4}
                              />

                              <stop
                                  offset="95%"
                                  stopColor="var(--color-count)"
                                  stopOpacity={0.05}
                              />
                            </linearGradient>
                          </defs>

                          <CartesianGrid
                              vertical={false}
                              stroke="var(--border)"
                          />

                          <XAxis
                              dataKey="label"
                              tickLine={false}
                              axisLine={false}
                              tickMargin={8}
                              fontSize={11}
                          />

                          <YAxis
                              allowDecimals={false}
                              tickLine={false}
                              axisLine={false}
                              fontSize={11}
                              width={32}
                          />

                          <ChartTooltip
                              content={
                                <ChartTooltipContent />
                              }
                          />

                          <Area
                              dataKey="count"
                              type="monotone"
                              stroke="var(--color-count)"
                              fill="url(#fill-detections)"
                              strokeWidth={2}
                          />

                        </AreaChart>
                      </ChartContainer>
                  )}

                </div>
              </Card>


              <div className="grid grid-cols-1 gap-4 xl:grid-cols-2">

                {/* By type */}
                <Card className="gap-3">

                  <CardHeader>
                    <CardTitle className="text-base">
                      Detections by Type
                    </CardTitle>

                    <p className="text-xs text-muted-foreground">
                      Distribution across AI monitoring categories
                    </p>
                  </CardHeader>

                  <div className="px-6 pb-6">

                    {typeData.length === 0 ? (
                        <EmptyChart />
                    ) : (
                        <ChartContainer
                            config={typeConfig}
                            className="h-[260px] w-full"
                        >
                          <BarChart
                              data={typeData}
                              margin={{
                                left: -12,
                                right: 8,
                                top: 8,
                                bottom: 20,
                              }}
                          >
                            <CartesianGrid
                                vertical={false}
                                stroke="var(--border)"
                            />

                            <XAxis
                                dataKey="label"
                                tickLine={false}
                                axisLine={false}
                                tickMargin={8}
                                fontSize={10}
                                angle={-15}
                                textAnchor="end"
                                height={55}
                            />

                            <YAxis
                                allowDecimals={false}
                                tickLine={false}
                                axisLine={false}
                                fontSize={11}
                                width={32}
                            />

                            <ChartTooltip
                                content={
                                  <ChartTooltipContent />
                                }
                            />

                            <Bar
                                dataKey="count"
                                fill="var(--color-count)"
                                radius={[4, 4, 0, 0]}
                            />

                          </BarChart>
                        </ChartContainer>
                    )}

                  </div>
                </Card>


                {/* By hour */}
                <Card className="gap-3">

                  <CardHeader>
                    <CardTitle className="text-base">
                      Detection Activity by Hour
                    </CardTitle>

                    <p className="text-xs text-muted-foreground">
                      Time-of-day pattern for the selected data
                    </p>
                  </CardHeader>

                  <div className="px-6 pb-6">

                    {hourlyData.length === 0 ? (
                        <EmptyChart />
                    ) : (
                        <ChartContainer
                            config={hourConfig}
                            className="h-[260px] w-full"
                        >
                          <BarChart
                              data={hourlyData}
                              margin={{
                                left: -12,
                                right: 8,
                                top: 8,
                              }}
                          >
                            <CartesianGrid
                                vertical={false}
                                stroke="var(--border)"
                            />

                            <XAxis
                                dataKey="label"
                                tickLine={false}
                                axisLine={false}
                                tickMargin={8}
                                fontSize={10}
                            />

                            <YAxis
                                allowDecimals={false}
                                tickLine={false}
                                axisLine={false}
                                fontSize={11}
                                width={32}
                            />

                            <ChartTooltip
                                content={
                                  <ChartTooltipContent />
                                }
                            />

                            <Bar
                                dataKey="count"
                                fill="var(--color-count)"
                                radius={[4, 4, 0, 0]}
                            />

                          </BarChart>
                        </ChartContainer>
                    )}

                  </div>
                </Card>

              </div>


              <div className="grid grid-cols-1 gap-4 xl:grid-cols-2">

                {/* Hotspots */}
                <Card className="gap-3">

                  <CardHeader>
                    <CardTitle className="text-base">
                      Detection Hotspots
                    </CardTitle>

                    <p className="text-xs text-muted-foreground">
                      Locations generating the highest detection volumes
                    </p>
                  </CardHeader>

                  <div className="px-6 pb-6">

                    {locations.length === 0 ? (
                        <EmptyList
                            message="No detection locations available."
                        />
                    ) : (
                        <div className="space-y-2">

                          {locations
                              .slice(0, 8)
                              .map(
                                  (
                                      location,
                                      index,
                                  ) => (
                                      <div
                                          key={
                                            location.location_name
                                          }
                                          className="flex items-center justify-between rounded-lg border p-3"
                                      >

                                        <div className="flex min-w-0 items-center gap-3">

                                          <div className="flex size-8 shrink-0 items-center justify-center rounded-md bg-muted text-xs font-semibold">
                                            {index + 1}
                                          </div>

                                          <div className="min-w-0">

                                            <p className="truncate text-sm font-medium">
                                              {
                                                location.location_name
                                              }
                                            </p>

                                            <p className="text-xs text-muted-foreground">
                                              Avg confidence{" "}
                                              {formatConfidence(
                                                  location.average_confidence,
                                              )}
                                            </p>

                                          </div>

                                        </div>

                                        <div className="ml-4 text-right">

                                          <p className="text-lg font-semibold">
                                            {
                                              location.count
                                            }
                                          </p>

                                          <p className="text-[11px] text-muted-foreground">
                                            detections
                                          </p>

                                        </div>

                                      </div>
                                  ),
                              )}

                        </div>
                    )}

                  </div>
                </Card>


                {/* Cameras */}
                <Card className="gap-3">

                  <CardHeader>
                    <CardTitle className="text-base">
                      Camera Detection Activity
                    </CardTitle>

                    <p className="text-xs text-muted-foreground">
                      Detection volume generated by monitoring sources
                    </p>
                  </CardHeader>

                  <div className="px-6 pb-6">

                    {cameras.length === 0 ? (
                        <EmptyList
                            message="No camera detection data available."
                        />
                    ) : (
                        <div className="space-y-2">

                          {cameras
                              .slice(0, 8)
                              .map(
                                  (camera) => (
                                      <div
                                          key={
                                            camera.camera_identifier
                                          }
                                          className="rounded-lg border p-3"
                                      >

                                        <div className="flex items-center justify-between gap-4">

                                          <div>
                                            <p className="text-sm font-medium">
                                              {
                                                camera.camera_identifier
                                              }
                                            </p>

                                            <p className="text-xs text-muted-foreground">
                                              Last detection{" "}
                                              {formatDate(
                                                  camera.latest_detection,
                                              )}
                                            </p>
                                          </div>

                                          <p className="text-lg font-semibold">
                                            {
                                              camera.count
                                            }
                                          </p>

                                        </div>

                                        <div className="mt-2 text-xs text-muted-foreground">
                                          Average confidence{" "}
                                          {formatConfidence(
                                              camera.average_confidence,
                                          )}
                                        </div>

                                      </div>
                                  ),
                              )}

                        </div>
                    )}

                  </div>
                </Card>

              </div>


              {/* Model performance */}
              <Card className="gap-3">

                <CardHeader>
                  <CardTitle className="text-base">
                    AI Model Performance
                  </CardTitle>

                  <p className="text-xs text-muted-foreground">
                    Detection volume and confidence statistics by model
                  </p>
                </CardHeader>

                <div className="overflow-x-auto px-6 pb-6">

                  {models.length === 0 ? (
                      <EmptyList
                          message="No model performance information available."
                      />
                  ) : (
                      <table className="w-full min-w-[760px] text-sm">

                        <thead>
                        <tr className="border-b text-left text-xs uppercase text-muted-foreground">

                          <th className="pb-3 font-medium">
                            Model
                          </th>

                          <th className="pb-3 font-medium">
                            Version
                          </th>

                          <th className="pb-3 text-right font-medium">
                            Detections
                          </th>

                          <th className="pb-3 text-right font-medium">
                            Avg Confidence
                          </th>

                          <th className="pb-3 text-right font-medium">
                            Minimum
                          </th>

                          <th className="pb-3 text-right font-medium">
                            Maximum
                          </th>

                          <th className="pb-3 text-right font-medium">
                            Confirmed
                          </th>

                        </tr>
                        </thead>

                        <tbody>

                        {models.map(
                            (model) => (
                                <tr
                                    key={`${model.model_name}-${model.model_version ?? "none"}`}
                                    className="border-b last:border-0"
                                >

                                  <td className="py-3 font-medium">
                                    {
                                      model.model_name
                                    }
                                  </td>

                                  <td className="py-3 text-muted-foreground">
                                    {
                                        model.model_version ??
                                        "—"
                                    }
                                  </td>

                                  <td className="py-3 text-right">
                                    {
                                      model.detections
                                    }
                                  </td>

                                  <td className="py-3 text-right">
                                    {formatConfidence(
                                        model.average_confidence,
                                    )}
                                  </td>

                                  <td className="py-3 text-right text-muted-foreground">
                                    {formatConfidence(
                                        model.minimum_confidence,
                                    )}
                                  </td>

                                  <td className="py-3 text-right text-muted-foreground">
                                    {formatConfidence(
                                        model.maximum_confidence,
                                    )}
                                  </td>

                                  <td className="py-3 text-right">
                                    {
                                      model.confirmed
                                    }
                                  </td>

                                </tr>
                            ),
                        )}

                        </tbody>

                      </table>
                  )}

                </div>
              </Card>


              {/* Recent */}
              <Card className="gap-3">

                <CardHeader>
                  <CardTitle className="text-base">
                    Recent AI Detections
                  </CardTitle>

                  <p className="text-xs text-muted-foreground">
                    Latest events matching the selected filters
                  </p>
                </CardHeader>

                <div className="overflow-x-auto px-6 pb-6">

                  {recent.length === 0 ? (
                      <EmptyList
                          message="No AI detections match the current filters."
                      />
                  ) : (
                      <table className="w-full min-w-[900px] text-sm">

                        <thead>
                        <tr className="border-b text-left text-xs uppercase text-muted-foreground">

                          <th className="pb-3 font-medium">
                            Detected
                          </th>

                          <th className="pb-3 font-medium">
                            Type
                          </th>

                          <th className="pb-3 font-medium">
                            Location
                          </th>

                          <th className="pb-3 font-medium">
                            Camera
                          </th>

                          <th className="pb-3 font-medium">
                            Model
                          </th>

                          <th className="pb-3 text-right font-medium">
                            Confidence
                          </th>

                          <th className="pb-3 font-medium">
                            Review
                          </th>

                        </tr>
                        </thead>

                        <tbody>

                        {recent.map(
                            (detection) => (
                                <tr
                                    key={
                                      detection.id
                                    }
                                    className="border-b last:border-0"
                                >

                                  <td className="whitespace-nowrap py-3 text-muted-foreground">
                                    {formatDate(
                                        detection.detected_at,
                                    )}
                                  </td>

                                  <td className="py-3 font-medium">
                                    {detectionLabel(
                                        detection.detection_type,
                                    )}
                                  </td>

                                  <td className="py-3">
                                    {
                                        detection.location_name ??
                                        "Unknown"
                                    }
                                  </td>

                                  <td className="py-3 text-muted-foreground">
                                    {
                                        detection.camera_identifier ??
                                        "—"
                                    }
                                  </td>

                                  <td className="py-3 text-muted-foreground">
                                    {
                                      detection.model_name
                                    }
                                  </td>

                                  <td className="py-3 text-right font-medium">
                                    {formatConfidence(
                                        detection.confidence,
                                    )}
                                  </td>

                                  <td className="py-3">
                                    <ReviewBadge
                                        status={
                                          detection.review_status
                                        }
                                    />
                                  </td>

                                </tr>
                            ),
                        )}

                        </tbody>

                      </table>
                  )}

                </div>
              </Card>


              {/* Period metadata */}
              <div className="flex flex-col gap-2 rounded-lg border bg-muted/20 px-4 py-3 text-xs text-muted-foreground sm:flex-row sm:items-center sm:justify-between">

            <span className="inline-flex items-center gap-2">
              <CalendarDays className="size-3.5" />

              First matching detection:{" "}
              {formatDate(
                  overview?.earliest_detection ??
                  null,
              )}
            </span>

                <span>
              Latest matching detection:{" "}
                  {formatDate(
                      overview?.latest_detection ??
                      null,
                  )}
            </span>

              </div>

            </>
        )}

      </div>
  )
}


function FilterField({
                       label,
                       children,
                     }: {
  label: string
  children: React.ReactNode
}) {
  return (
      <div>
        <label className="mb-1.5 block text-xs font-medium text-muted-foreground">
          {label}
        </label>

        {children}
      </div>
  )
}


function PresetButton({
                        label,
                        onClick,
                      }: {
  label: string
  onClick: () => void
}) {
  return (
      <button
          type="button"
          onClick={onClick}
          className="rounded-md border px-3 py-1.5 text-xs font-medium transition hover:bg-muted"
      >
        {label}
      </button>
  )
}


function MetricCard({
                      title,
                      value,
                      description,
                    }: {
  title: string
  value: string
  description: string
}) {
  return (
      <Card>
        <div className="p-5">

          <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
            {title}
          </p>

          <p className="mt-2 text-3xl font-semibold tracking-tight">
            {value}
          </p>

          <p className="mt-2 text-xs text-muted-foreground">
            {description}
          </p>

        </div>
      </Card>
  )
}


function ReviewMetric({
                        label,
                        value,
                      }: {
  label: string
  value: number
}) {
  return (
      <div className="p-4">

        <p className="text-xs text-muted-foreground">
          {label}
        </p>

        <p className="mt-1 text-xl font-semibold">
          {value}
        </p>

      </div>
  )
}


function ReviewBadge({
                       status,
                     }: {
  status: string
}) {
  const className =
      status === "confirmed"
          ? "border-green-500/30 bg-green-500/10 text-green-500"
          : status === "rejected"
              ? "border-red-500/30 bg-red-500/10 text-red-500"
              : "border-amber-500/30 bg-amber-500/10 text-amber-500"

  return (
      <span
          className={`inline-flex rounded-full border px-2 py-1 text-[11px] font-medium ${className}`}
      >
      {reviewLabel(status)}
    </span>
  )
}


function EmptyChart() {
  return (
      <div className="flex h-[220px] items-center justify-center rounded-lg border border-dashed">
        <p className="text-sm text-muted-foreground">
          No detection data available for this selection.
        </p>
      </div>
  )
}


function EmptyList({
                     message,
                   }: {
  message: string
}) {
  return (
      <div className="rounded-lg border border-dashed p-8 text-center">
        <p className="text-sm text-muted-foreground">
          {message}
        </p>
      </div>
  )
}