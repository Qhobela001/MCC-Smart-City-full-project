"use client"

import Link from "next/link"
import {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react"
import {
  Activity,
  AlertTriangle,
  ArrowRight,
  Bell,
  BrainCircuit,
  Camera,
  CheckCircle2,
  CircleDot,
  Clock3,
  FileImage,
  LayoutDashboard,
  LoaderCircle,
  MapPin,
  RadioTower,
  RefreshCw,
  ShieldCheck,
  Users,
} from "lucide-react"

import { apiFetch } from "@/lib/api"
import type {
  Alert,
  Incident,
  IncidentStatus,
} from "@/lib/types"


type DashboardStats = {
  openIncidents: number
  criticalIncidents: number
  resolvedIncidents: number
  unreadAlerts: number
}


type DashboardSummaryResponse = {
  stats: {
    open_incidents: number
    critical_incidents: number
    resolved_incidents: number
    unread_alerts: number
  }
  status_counts: Record<IncidentStatus, number>
  recent_incidents: Incident[]
  recent_alerts: Alert[]
  generated_at: string
}


type DashboardLoadMode =
  | "initial"
  | "manual"
  | "poll"


const INITIAL_STATUS_COUNTS: Record<IncidentStatus, number> = {
  new: 0,
  under_review: 0,
  confirmed: 0,
  assigned: 0,
  in_progress: 0,
  resolved: 0,
  dismissed: 0,
}


const DASHBOARD_POLL_INTERVAL_MS = 10_000


export default function DashboardPage() {
  const [recentIncidents, setRecentIncidents] = useState<Incident[]>([])
  const [recentAlerts, setRecentAlerts] = useState<Alert[]>([])

  const [stats, setStats] = useState<DashboardStats>({
    openIncidents: 0,
    criticalIncidents: 0,
    resolvedIncidents: 0,
    unreadAlerts: 0,
  })

  const [statusCounts, setStatusCounts] = useState<
    Record<IncidentStatus, number>
  >(INITIAL_STATUS_COUNTS)

  const [loading, setLoading] = useState(true)
  const [refreshing, setRefreshing] = useState(false)
  const [error, setError] = useState("")
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null)

  const requestInFlight = useRef(false)


  const loadDashboard = useCallback(
    async (
      mode: DashboardLoadMode = "initial",
    ) => {
      if (requestInFlight.current) {
        return
      }

      requestInFlight.current = true

      if (mode === "initial") {
        setLoading(true)
      }

      if (mode === "manual") {
        setRefreshing(true)
      }

      try {
        const response =
          await apiFetch<DashboardSummaryResponse>(
            "/dashboard/summary",
          )

        setRecentIncidents(
          response.recent_incidents,
        )

        setRecentAlerts(
          response.recent_alerts,
        )

        setStats({
          openIncidents:
            response.stats.open_incidents,
          criticalIncidents:
            response.stats.critical_incidents,
          resolvedIncidents:
            response.stats.resolved_incidents,
          unreadAlerts:
            response.stats.unread_alerts,
        })

        setStatusCounts(
          response.status_counts,
        )

        const generatedAt = new Date(
          response.generated_at,
        )

        setLastUpdated(
          Number.isNaN(generatedAt.getTime())
            ? new Date()
            : generatedAt,
        )

        setError("")
      } catch (requestError) {
        setError(
          requestError instanceof Error
            ? requestError.message
            : "Unable to load the command centre dashboard.",
        )
      } finally {
        requestInFlight.current = false

        if (mode === "initial") {
          setLoading(false)
        }

        if (mode === "manual") {
          setRefreshing(false)
        }
      }
    },
    [],
  )


  useEffect(() => {
    void loadDashboard("initial")

    const pollDashboard = () => {
      if (
        document.visibilityState === "visible"
      ) {
        void loadDashboard("poll")
      }
    }

    const intervalId = window.setInterval(
      pollDashboard,
      DASHBOARD_POLL_INTERVAL_MS,
    )

    const handleVisibilityChange = () => {
      if (
        document.visibilityState === "visible"
      ) {
        void loadDashboard("poll")
      }
    }

    document.addEventListener(
      "visibilitychange",
      handleVisibilityChange,
    )

    return () => {
      window.clearInterval(intervalId)

      document.removeEventListener(
        "visibilitychange",
        handleVisibilityChange,
      )
    }
  }, [loadDashboard])


  const incidentStatusBreakdown = useMemo(
    () => [
      {
        status: "new" as IncidentStatus,
        label: "New",
        value: statusCounts.new,
      },
      {
        status: "under_review" as IncidentStatus,
        label: "Under review",
        value: statusCounts.under_review,
      },
      {
        status: "assigned" as IncidentStatus,
        label: "Assigned",
        value: statusCounts.assigned,
      },
      {
        status: "in_progress" as IncidentStatus,
        label: "In progress",
        value: statusCounts.in_progress,
      },
      {
        status: "resolved" as IncidentStatus,
        label: "Resolved",
        value: statusCounts.resolved,
      },
    ],
    [statusCounts],
  )

  if (loading) {
    return (
        <div className="flex min-h-[60vh] items-center justify-center">
          <div className="flex items-center gap-3 text-sm text-muted-foreground">
            <LoaderCircle className="size-5 animate-spin text-primary" />
            Loading MCC Command Centre...
          </div>
        </div>
    )
  }

  return (
      <>
        <section className="overflow-hidden rounded-2xl border bg-card">
          <div className="relative p-5 md:p-7">
            <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_top_right,hsl(var(--primary)/0.13),transparent_38%)]" />

            <div className="relative flex flex-col gap-5 lg:flex-row lg:items-center lg:justify-between">
              <div className="max-w-3xl">
                <div className="mb-3 inline-flex items-center gap-2 rounded-full border bg-background/70 px-3 py-1 text-xs font-medium text-muted-foreground">
                  <CircleDot className="size-3.5 text-emerald-500" />
                  MCC operational platform online
                </div>

                <h2 className="text-2xl font-semibold tracking-tight md:text-3xl">
                  Smart City Command Centre
                </h2>

                <p className="mt-2 max-w-2xl text-sm leading-6 text-muted-foreground">
                  Central operational view for municipal incidents,
                  enforcement evidence, officer assignments, and system
                  notifications across Maseru City Council.
                </p>

                <div className="mt-4 flex flex-wrap items-center gap-x-5 gap-y-2 text-xs text-muted-foreground">
                <span className="inline-flex items-center gap-1.5">
                  <ShieldCheck className="size-3.5 text-emerald-500" />
                  Authentication & RBAC active
                </span>

                  <span className="inline-flex items-center gap-1.5">
                  <Bell className="size-3.5 text-primary" />
                  Alert workflow active
                </span>

                  <span className="inline-flex items-center gap-1.5">
                  <Clock3 className="size-3.5" />
                    {lastUpdated
                        ? `Updated ${formatTime(lastUpdated)}`
                        : "Awaiting refresh"}
                </span>
                </div>
              </div>

              <div className="flex flex-wrap gap-2">
                <button
                    type="button"
                    onClick={() => void loadDashboard("manual")}
                    disabled={refreshing}
                    className="inline-flex h-10 items-center gap-2 rounded-md border bg-background px-4 text-sm font-medium transition hover:bg-muted disabled:opacity-50"
                >
                  <RefreshCw
                      className={`size-4 ${
                          refreshing ? "animate-spin" : ""
                      }`}
                  />
                  Refresh
                </button>

                <Link
                    href="/incidents"
                    className="inline-flex h-10 items-center gap-2 rounded-md bg-primary px-4 text-sm font-medium text-primary-foreground transition hover:opacity-90"
                >
                  <AlertTriangle className="size-4" />
                  Open incidents
                </Link>
              </div>
            </div>
          </div>
        </section>

        {error && (
            <div className="rounded-lg border border-destructive/30 bg-destructive/10 p-4 text-sm text-destructive">
              {error}
            </div>
        )}

        <section className="grid grid-cols-2 gap-3 lg:grid-cols-4">
          <KpiCard
              label="Open incidents"
              value={stats.openIncidents}
              detail="Requires operational follow-up"
              icon={<AlertTriangle className="size-5" />}
              href="/incidents"
              tone="warning"
          />

          <KpiCard
              label="Critical incidents"
              value={stats.criticalIncidents}
              detail="All critical-priority records"
              icon={<Activity className="size-5" />}
              href="/incidents?priority=critical"
              tone="critical"
          />

          <KpiCard
              label="Unread alerts"
              value={stats.unreadAlerts}
              detail="Notifications awaiting review"
              icon={<Bell className="size-5" />}
              href="/notifications"
              tone="primary"
          />

          <KpiCard
              label="Resolved incidents"
              value={stats.resolvedIncidents}
              detail="Completed incident records"
              icon={<CheckCircle2 className="size-5" />}
              href="/incidents?status=resolved"
              tone="good"
          />
        </section>

        <section className="grid gap-4 xl:grid-cols-[1.65fr_1fr]">
          <div className="overflow-hidden rounded-xl border bg-card">
            <SectionHeader
                title="Recent incidents"
                description="Latest incident records visible to your account."
                href="/incidents"
                actionLabel="View all incidents"
            />

            <div className="divide-y">
              {recentIncidents.length === 0 ? (
                  <EmptyState
                      icon={<AlertTriangle className="size-6" />}
                      title="No incidents available"
                      description="New incident records will appear here as they are reported."
                  />
              ) : (
                  recentIncidents.slice(0, 6).map((incident) => (
                      <Link
                          key={incident.id}
                          href="/incidents"
                          className="flex flex-col gap-3 p-4 transition hover:bg-muted/35 sm:flex-row sm:items-center"
                      >
                        <div
                            className={`flex size-10 shrink-0 items-center justify-center rounded-lg ${priorityIconClass(
                                incident.priority,
                            )}`}
                        >
                          <AlertTriangle className="size-4" />
                        </div>

                        <div className="min-w-0 flex-1">
                          <div className="flex flex-wrap items-center gap-2">
                            <p className="truncate text-sm font-medium">
                              {incident.title}
                            </p>

                            <StatusPill status={incident.status} />

                            <PriorityPill priority={incident.priority} />
                          </div>

                          <div className="mt-1 flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-muted-foreground">
                      <span className="font-mono">
                        {incident.incident_number}
                      </span>

                            {incident.location_name && (
                                <span className="inline-flex items-center gap-1">
                          <MapPin className="size-3" />
                                  {incident.location_name}
                        </span>
                            )}

                            <span>
                        {formatRelativeTime(incident.created_at)}
                      </span>
                          </div>
                        </div>

                        <div className="flex items-center gap-3 text-xs text-muted-foreground">
                          {incident.evidence_count > 0 && (
                              <span className="inline-flex items-center gap-1">
                        <FileImage className="size-3.5" />
                                {incident.evidence_count}
                      </span>
                          )}

                          <ArrowRight className="size-4" />
                        </div>
                      </Link>
                  ))
              )}
            </div>
          </div>

          <div className="overflow-hidden rounded-xl border bg-card">
            <SectionHeader
                title="Recent notifications"
                description="Operational alerts addressed to you."
                href="/notifications"
                actionLabel="Notification centre"
            />

            <div className="divide-y">
              {recentAlerts.length === 0 ? (
                  <EmptyState
                      icon={<Bell className="size-6" />}
                      title="No notifications"
                      description="Assignments, evidence activity, and status changes will appear here."
                  />
              ) : (
                  recentAlerts.slice(0, 6).map((alert) => (
                      <Link
                          key={alert.id}
                          href={alert.action_url || "/notifications"}
                          className={`block p-4 transition hover:bg-muted/35 ${
                              alert.is_read ? "" : "bg-primary/[0.035]"
                          }`}
                      >
                        <div className="flex gap-3">
                    <span
                        className={`mt-1 size-2 shrink-0 rounded-full ${alertSeverityDot(
                            alert.severity,
                            alert.is_read,
                        )}`}
                    />

                          <div className="min-w-0 flex-1">
                            <div className="flex items-start gap-2">
                              <p className="line-clamp-1 flex-1 text-sm font-medium">
                                {alert.title}
                              </p>

                              {!alert.is_read && (
                                  <span className="rounded-full bg-primary/10 px-2 py-0.5 text-[10px] font-semibold uppercase text-primary">
                            New
                          </span>
                              )}
                            </div>

                            <p className="mt-1 line-clamp-2 text-xs leading-5 text-muted-foreground">
                              {alert.message}
                            </p>

                            <div className="mt-2 flex items-center justify-between text-[11px] text-muted-foreground">
                        <span className="capitalize">
                          {alert.severity}
                        </span>

                              <span>
                          {formatRelativeTime(alert.created_at)}
                        </span>
                            </div>
                          </div>
                        </div>
                      </Link>
                  ))
              )}
            </div>
          </div>
        </section>

        <section className="grid gap-4 xl:grid-cols-3">
          <div className="rounded-xl border bg-card p-5 xl:col-span-2">
            <div className="flex items-start justify-between gap-4">
              <div>
                <h3 className="text-base font-semibold">
                  Recent incident status
                </h3>
                <p className="mt-1 text-xs text-muted-foreground">
                  Distribution within the latest incident records.
                </p>
              </div>

              <LayoutDashboard className="size-5 text-muted-foreground" />
            </div>

            <div className="mt-6 space-y-4">
              {incidentStatusBreakdown.map((item) => {
                const max = Math.max(
                    1,
                    ...incidentStatusBreakdown.map(
                        (entry) => entry.value,
                    ),
                )
                const width = Math.max(
                    item.value > 0 ? 7 : 0,
                    (item.value / max) * 100,
                )

                return (
                    <div key={item.status}>
                      <div className="mb-1.5 flex items-center justify-between text-xs">
                    <span className="font-medium">
                      {item.label}
                    </span>
                        <span className="font-mono text-muted-foreground">
                      {item.value}
                    </span>
                      </div>

                      <div className="h-2 overflow-hidden rounded-full bg-muted">
                        <div
                            className={`h-full rounded-full ${statusBarClass(
                                item.status,
                            )}`}
                            style={{ width: `${width}%` }}
                        />
                      </div>
                    </div>
                )
              })}
            </div>
          </div>

          <div className="rounded-xl border bg-card p-5">
            <div className="flex items-start justify-between">
              <div>
                <h3 className="text-base font-semibold">
                  Quick actions
                </h3>
                <p className="mt-1 text-xs text-muted-foreground">
                  Common operational destinations.
                </p>
              </div>

              <Activity className="size-5 text-muted-foreground" />
            </div>

            <div className="mt-5 grid gap-2">
              <QuickAction
                  href="/incidents"
                  icon={<AlertTriangle className="size-4" />}
                  title="Incident management"
                  description="Review, assign and resolve incidents"
              />

              <QuickAction
                  href="/notifications"
                  icon={<Bell className="size-4" />}
                  title="Notification centre"
                  description="Review and acknowledge alerts"
              />

              <QuickAction
                  href="/administration/users"
                  icon={<Users className="size-4" />}
                  title="User management"
                  description="Manage authorised MCC users"
              />

              <QuickAction
                  href="/city-map"
                  icon={<MapPin className="size-4" />}
                  title="City map"
                  description="GIS integration workspace"
              />
            </div>
          </div>
        </section>

        <section className="rounded-xl border bg-card p-5">
          <div className="flex flex-col gap-2 sm:flex-row sm:items-end sm:justify-between">
            <div>
              <h3 className="text-base font-semibold">
                Platform readiness
              </h3>
              <p className="mt-1 text-xs text-muted-foreground">
                Current implementation state of the MCC Smart City
                operational platform.
              </p>
            </div>

            <span className="text-xs text-muted-foreground">
            Software-first deployment phase
          </span>
          </div>

          <div className="mt-5 grid gap-3 md:grid-cols-2 xl:grid-cols-3">
            <ReadinessCard
                icon={<ShieldCheck className="size-5" />}
                title="Identity & access"
                description="Authentication, roles, permissions and dynamic navigation."
                status="Operational"
                state="ready"
            />

            <ReadinessCard
                icon={<AlertTriangle className="size-5" />}
                title="Incidents & evidence"
                description="Workflow, assignments, timelines and protected evidence."
                status="Operational"
                state="ready"
            />

            <ReadinessCard
                icon={<Bell className="size-5" />}
                title="Alerts & notifications"
                description="Personal alert inbox and incident-driven notifications."
                status="Operational"
                state="ready"
            />

            <ReadinessCard
                icon={<MapPin className="size-5" />}
                title="GIS & zones"
                description="Locations, enforcement zones and city map data."
                status="Next phase"
                state="planned"
            />

            <ReadinessCard
                icon={<Camera className="size-5" />}
                title="Camera monitoring"
                description="Live feeds and field-camera connectivity."
                status="Awaiting camera"
                state="pending"
            />

            <ReadinessCard
                icon={<BrainCircuit className="size-5" />}
                title="Edge AI processing"
                description="YOLO inference and automated incident generation."
                status="Awaiting Jetson"
                state="pending"
            />
          </div>
        </section>

        <section className="grid gap-4 md:grid-cols-2">
          <div className="rounded-xl border border-dashed bg-muted/15 p-5">
            <div className="flex items-start gap-4">
              <div className="rounded-lg bg-muted p-3 text-muted-foreground">
                <RadioTower className="size-5" />
              </div>

              <div>
                <h3 className="text-sm font-semibold">
                  Live infrastructure monitoring
                </h3>
                <p className="mt-1 text-xs leading-5 text-muted-foreground">
                  Camera, NanoStation and Jetson health metrics will
                  populate this panel after field hardware integration.
                  No simulated device status is shown here.
                </p>
              </div>
            </div>
          </div>

          <div className="rounded-xl border border-dashed bg-muted/15 p-5">
            <div className="flex items-start gap-4">
              <div className="rounded-lg bg-muted p-3 text-muted-foreground">
                <BrainCircuit className="size-5" />
              </div>

              <div>
                <h3 className="text-sm font-semibold">
                  AI detection pipeline
                </h3>
                <p className="mt-1 text-xs leading-5 text-muted-foreground">
                  Trained YOLO models will later feed detections into the
                  existing Incident → Evidence → Alert workflow without
                  replacing the operational modules already completed.
                </p>
              </div>
            </div>
          </div>
        </section>
      </>
  )
}


function KpiCard({
                   label,
                   value,
                   detail,
                   icon,
                   href,
                   tone,
                 }: {
  label: string
  value: number
  detail: string
  icon: React.ReactNode
  href: string
  tone: "critical" | "warning" | "primary" | "good"
}) {
  const toneClasses = {
    critical: "bg-destructive/10 text-destructive",
    warning: "bg-amber-500/10 text-amber-500",
    primary: "bg-primary/10 text-primary",
    good: "bg-emerald-500/10 text-emerald-500",
  }

  return (
      <Link
          href={href}
          className="group rounded-xl border bg-card p-4 transition hover:border-primary/30 hover:bg-muted/20"
      >
        <div className="flex items-start justify-between gap-3">
          <div>
            <p className="text-xs font-medium text-muted-foreground">
              {label}
            </p>

            <p className="mt-2 font-mono text-2xl font-semibold tracking-tight md:text-3xl">
              {value}
            </p>
          </div>

          <div
              className={`rounded-lg p-2.5 ${toneClasses[tone]}`}
          >
            {icon}
          </div>
        </div>

        <div className="mt-3 flex items-center justify-between gap-2">
          <p className="line-clamp-1 text-[11px] text-muted-foreground">
            {detail}
          </p>

          <ArrowRight className="size-3.5 shrink-0 text-muted-foreground transition-transform group-hover:translate-x-0.5 group-hover:text-primary" />
        </div>
      </Link>
  )
}


function SectionHeader({
                         title,
                         description,
                         href,
                         actionLabel,
                       }: {
  title: string
  description: string
  href: string
  actionLabel: string
}) {
  return (
      <div className="flex items-start justify-between gap-4 border-b px-4 py-4">
        <div>
          <h3 className="text-base font-semibold">{title}</h3>
          <p className="mt-1 text-xs text-muted-foreground">
            {description}
          </p>
        </div>

        <Link
            href={href}
            className="hidden shrink-0 items-center gap-1 text-xs font-medium text-primary hover:underline sm:inline-flex"
        >
          {actionLabel}
          <ArrowRight className="size-3.5" />
        </Link>
      </div>
  )
}


function EmptyState({
                      icon,
                      title,
                      description,
                    }: {
  icon: React.ReactNode
  title: string
  description: string
}) {
  return (
      <div className="flex min-h-48 flex-col items-center justify-center p-8 text-center">
        <div className="rounded-xl bg-muted p-3 text-muted-foreground">
          {icon}
        </div>
        <p className="mt-3 text-sm font-medium">{title}</p>
        <p className="mt-1 max-w-xs text-xs leading-5 text-muted-foreground">
          {description}
        </p>
      </div>
  )
}


function QuickAction({
                       href,
                       icon,
                       title,
                       description,
                     }: {
  href: string
  icon: React.ReactNode
  title: string
  description: string
}) {
  return (
      <Link
          href={href}
          className="group flex items-center gap-3 rounded-lg border p-3 transition hover:border-primary/30 hover:bg-muted/25"
      >
        <div className="rounded-md bg-primary/10 p-2 text-primary">
          {icon}
        </div>

        <div className="min-w-0 flex-1">
          <p className="text-sm font-medium">{title}</p>
          <p className="truncate text-[11px] text-muted-foreground">
            {description}
          </p>
        </div>

        <ArrowRight className="size-4 text-muted-foreground transition-transform group-hover:translate-x-0.5 group-hover:text-primary" />
      </Link>
  )
}


function ReadinessCard({
                         icon,
                         title,
                         description,
                         status,
                         state,
                       }: {
  icon: React.ReactNode
  title: string
  description: string
  status: string
  state: "ready" | "planned" | "pending"
}) {
  const classes = {
    ready: {
      icon: "bg-emerald-500/10 text-emerald-500",
      badge: "bg-emerald-500/10 text-emerald-500",
    },
    planned: {
      icon: "bg-primary/10 text-primary",
      badge: "bg-primary/10 text-primary",
    },
    pending: {
      icon: "bg-muted text-muted-foreground",
      badge: "bg-muted text-muted-foreground",
    },
  }

  return (
      <div className="rounded-lg border bg-background/40 p-4">
        <div className="flex items-start gap-3">
          <div className={`rounded-lg p-2.5 ${classes[state].icon}`}>
            {icon}
          </div>

          <div className="min-w-0 flex-1">
            <div className="flex flex-wrap items-center gap-2">
              <p className="text-sm font-medium">{title}</p>

              <span
                  className={`rounded-full px-2 py-0.5 text-[10px] font-semibold ${classes[state].badge}`}
              >
              {status}
            </span>
            </div>

            <p className="mt-1 text-xs leading-5 text-muted-foreground">
              {description}
            </p>
          </div>
        </div>
      </div>
  )
}


function StatusPill({
                      status,
                    }: {
  status: IncidentStatus
}) {
  return (
      <span
          className={`rounded-full px-2 py-0.5 text-[10px] font-semibold ${statusPillClass(
              status,
          )}`}
      >
      {humanize(status)}
    </span>
  )
}


function PriorityPill({
                        priority,
                      }: {
  priority: Incident["priority"]
}) {
  const classes = {
    low: "bg-blue-500/10 text-blue-500",
    medium: "bg-amber-500/10 text-amber-500",
    high: "bg-orange-500/10 text-orange-500",
    critical: "bg-destructive/10 text-destructive",
  }

  return (
      <span
          className={`rounded-full px-2 py-0.5 text-[10px] font-semibold ${classes[priority]}`}
      >
      {humanize(priority)}
    </span>
  )
}


function statusPillClass(status: IncidentStatus) {
  switch (status) {
    case "new":
      return "bg-destructive/10 text-destructive"
    case "under_review":
      return "bg-amber-500/10 text-amber-500"
    case "confirmed":
      return "bg-orange-500/10 text-orange-500"
    case "assigned":
      return "bg-blue-500/10 text-blue-500"
    case "in_progress":
      return "bg-primary/10 text-primary"
    case "resolved":
      return "bg-emerald-500/10 text-emerald-500"
    case "dismissed":
      return "bg-muted text-muted-foreground"
  }
}


function statusBarClass(status: IncidentStatus) {
  switch (status) {
    case "new":
      return "bg-destructive"
    case "under_review":
      return "bg-amber-500"
    case "confirmed":
      return "bg-orange-500"
    case "assigned":
      return "bg-blue-500"
    case "in_progress":
      return "bg-primary"
    case "resolved":
      return "bg-emerald-500"
    case "dismissed":
      return "bg-muted-foreground"
  }
}


function priorityIconClass(
    priority: Incident["priority"],
) {
  switch (priority) {
    case "critical":
      return "bg-destructive/10 text-destructive"
    case "high":
      return "bg-orange-500/10 text-orange-500"
    case "medium":
      return "bg-amber-500/10 text-amber-500"
    case "low":
      return "bg-blue-500/10 text-blue-500"
  }
}


function alertSeverityDot(
    severity: Alert["severity"],
    isRead: boolean,
) {
  if (isRead) {
    return "bg-muted-foreground/40"
  }

  switch (severity) {
    case "critical":
      return "bg-destructive"
    case "high":
      return "bg-orange-500"
    case "medium":
      return "bg-amber-500"
    case "low":
      return "bg-blue-500"
    case "info":
      return "bg-primary"
  }
}


function humanize(value: string) {
  return value
      .replace(/_/g, " ")
      .replace(/\b\w/g, (character) =>
          character.toUpperCase(),
      )
}


function formatTime(value: Date) {
  return new Intl.DateTimeFormat("en-LS", {
    hour: "2-digit",
    minute: "2-digit",
  }).format(value)
}


function formatRelativeTime(value: string) {
  const time = new Date(value).getTime()

  if (Number.isNaN(time)) {
    return "Unknown time"
  }

  const elapsedSeconds = Math.max(
      0,
      Math.floor((Date.now() - time) / 1000),
  )

  if (elapsedSeconds < 60) {
    return "just now"
  }

  const minutes = Math.floor(elapsedSeconds / 60)

  if (minutes < 60) {
    return `${minutes}m ago`
  }

  const hours = Math.floor(minutes / 60)

  if (hours < 24) {
    return `${hours}h ago`
  }

  const days = Math.floor(hours / 24)

  if (days < 7) {
    return `${days}d ago`
  }

  return new Intl.DateTimeFormat("en-LS", {
    day: "2-digit",
    month: "short",
    year: "numeric",
  }).format(new Date(value))
}
