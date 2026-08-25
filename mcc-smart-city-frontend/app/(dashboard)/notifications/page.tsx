"use client"

import Link from "next/link"
import { useCallback, useEffect, useMemo, useState } from "react"
import {
  Archive,
  Bell,
  Check,
  CheckCheck,
  CircleAlert,
  ExternalLink,
  LoaderCircle,
  RefreshCw,
} from "lucide-react"

import { apiFetch } from "@/lib/api"
import type {
  Alert,
  AlertListResponse,
} from "@/lib/types"


type Filter = "all" | "unread" | "acknowledged"


export default function NotificationsPage() {
  const [alerts, setAlerts] = useState<Alert[]>([])
  const [unreadCount, setUnreadCount] = useState(0)
  const [filter, setFilter] = useState<Filter>("all")
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState("")

  const load = useCallback(async () => {
    setLoading(true)
    setError("")

    try {
      const data = await apiFetch<AlertListResponse>(
        "/alerts?limit=100&offset=0",
      )
      setAlerts(data.items)
      setUnreadCount(data.unread_count)
    } catch (requestError) {
      setError(
        requestError instanceof Error
          ? requestError.message
          : "Unable to load notifications.",
      )
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    void load()
  }, [load])

  const filtered = useMemo(() => {
    if (filter === "unread") {
      return alerts.filter((alert) => !alert.is_read)
    }

    if (filter === "acknowledged") {
      return alerts.filter(
        (alert) => alert.is_acknowledged,
      )
    }

    return alerts
  }, [alerts, filter])

  async function updateAlert(
    alert: Alert,
    action: "read" | "acknowledge" | "archive",
  ) {
    try {
      const updated = await apiFetch<Alert>(
        `/alerts/${alert.id}/${action}`,
        { method: "PATCH" },
      )

      if (action === "archive") {
        setAlerts((current) =>
          current.filter((item) => item.id !== alert.id),
        )
      } else {
        setAlerts((current) =>
          current.map((item) =>
            item.id === updated.id ? updated : item,
          ),
        )
      }

      if (!alert.is_read) {
        setUnreadCount((current) =>
          Math.max(0, current - 1),
        )
      }
    } catch (requestError) {
      setError(
        requestError instanceof Error
          ? requestError.message
          : "Unable to update notification.",
      )
    }
  }

  async function markAllRead() {
    try {
      await apiFetch<{ success: boolean }>("/alerts/read-all", {
        method: "PATCH",
      })

      const readAt = new Date().toISOString()

      setAlerts((current) =>
        current.map((alert) => ({
          ...alert,
          is_read: true,
          read_at: alert.read_at ?? readAt,
        })),
      )
      setUnreadCount(0)
    } catch (requestError) {
      setError(
        requestError instanceof Error
          ? requestError.message
          : "Unable to mark notifications as read.",
      )
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <p className="text-sm font-medium text-primary">
            Operations
          </p>
          <h2 className="mt-1 text-2xl font-semibold">
            Notifications
          </h2>
          <p className="mt-1 text-sm text-muted-foreground">
            Incident assignments, status changes, evidence activity,
            and operational alerts addressed to your account.
          </p>
        </div>

        <div className="flex gap-2">
          <button
            type="button"
            onClick={() => void load()}
            disabled={loading}
            className="inline-flex h-10 items-center gap-2 rounded-md border px-4 text-sm font-medium hover:bg-muted disabled:opacity-50"
          >
            <RefreshCw
              className={`size-4 ${
                loading ? "animate-spin" : ""
              }`}
            />
            Refresh
          </button>

          {unreadCount > 0 && (
            <button
              type="button"
              onClick={() => void markAllRead()}
              className="inline-flex h-10 items-center gap-2 rounded-md bg-primary px-4 text-sm font-medium text-primary-foreground"
            >
              <CheckCheck className="size-4" />
              Mark all read
            </button>
          )}
        </div>
      </div>

      {error && (
        <div className="rounded-lg border border-destructive/30 bg-destructive/10 p-3 text-sm text-destructive">
          {error}
        </div>
      )}

      <div className="grid gap-4 sm:grid-cols-3">
        <SummaryCard
          label="All notifications"
          value={alerts.length}
          icon={<Bell className="size-5" />}
        />
        <SummaryCard
          label="Unread"
          value={unreadCount}
          icon={<CircleAlert className="size-5" />}
        />
        <SummaryCard
          label="Acknowledged"
          value={
            alerts.filter(
              (alert) => alert.is_acknowledged,
            ).length
          }
          icon={<Check className="size-5" />}
        />
      </div>

      <div className="flex flex-wrap gap-2">
        {(
          [
            ["all", "All"],
            ["unread", "Unread"],
            ["acknowledged", "Acknowledged"],
          ] as const
        ).map(([value, label]) => (
          <button
            key={value}
            type="button"
            onClick={() => setFilter(value)}
            className={`rounded-md px-3 py-2 text-sm font-medium transition ${
              filter === value
                ? "bg-primary text-primary-foreground"
                : "border bg-card hover:bg-muted"
            }`}
          >
            {label}
          </button>
        ))}
      </div>

      <div className="overflow-hidden rounded-xl border bg-card">
        {loading ? (
          <div className="flex min-h-48 items-center justify-center gap-2 text-sm text-muted-foreground">
            <LoaderCircle className="size-4 animate-spin" />
            Loading notifications...
          </div>
        ) : filtered.length === 0 ? (
          <div className="flex min-h-48 flex-col items-center justify-center p-8 text-center">
            <Bell className="size-8 text-muted-foreground/60" />
            <p className="mt-3 text-sm font-medium">
              No notifications found
            </p>
            <p className="mt-1 text-xs text-muted-foreground">
              New operational alerts will appear here.
            </p>
          </div>
        ) : (
          filtered.map((alert) => (
            <div
              key={alert.id}
              className={`border-b p-5 last:border-b-0 ${
                alert.is_read
                  ? ""
                  : "bg-primary/[0.035]"
              }`}
            >
              <div className="flex flex-col gap-4 md:flex-row md:items-start">
                <div
                  className={`flex size-10 shrink-0 items-center justify-center rounded-lg ${severityClasses(
                    alert.severity,
                  )}`}
                >
                  <CircleAlert className="size-5" />
                </div>

                <div className="min-w-0 flex-1">
                  <div className="flex flex-wrap items-center gap-2">
                    <h3 className="font-medium">
                      {alert.title}
                    </h3>

                    {!alert.is_read && (
                      <span className="rounded-full bg-primary/10 px-2 py-0.5 text-[10px] font-semibold uppercase text-primary">
                        New
                      </span>
                    )}

                    {alert.is_acknowledged && (
                      <span className="rounded-full bg-emerald-500/10 px-2 py-0.5 text-[10px] font-semibold uppercase text-emerald-500">
                        Acknowledged
                      </span>
                    )}

                    <span className="rounded-full border px-2 py-0.5 text-[10px] font-semibold uppercase text-muted-foreground">
                      {alert.severity}
                    </span>
                  </div>

                  <p className="mt-2 text-sm leading-6 text-muted-foreground">
                    {alert.message}
                  </p>

                  {alert.incident && (
                    <div className="mt-3 rounded-lg border bg-muted/20 p-3 text-xs">
                      <span className="font-medium">
                        {alert.incident.incident_number}
                      </span>
                      <span className="mx-2 text-muted-foreground">
                        •
                      </span>
                      <span className="text-muted-foreground">
                        {alert.incident.title}
                      </span>
                    </div>
                  )}

                  <p className="mt-3 text-xs text-muted-foreground">
                    {formatDate(alert.created_at)}
                  </p>
                </div>

                <div className="flex shrink-0 flex-wrap gap-2">
                  {alert.action_url && (
                    <Link
                      href={alert.action_url}
                      onClick={() => {
                        if (!alert.is_read) {
                          void updateAlert(alert, "read")
                        }
                      }}
                      className="inline-flex h-9 items-center gap-1.5 rounded-md bg-primary px-3 text-xs font-medium text-primary-foreground"
                    >
                      Open
                      <ExternalLink className="size-3.5" />
                    </Link>
                  )}

                  {!alert.is_acknowledged && (
                    <button
                      type="button"
                      onClick={() =>
                        void updateAlert(
                          alert,
                          "acknowledge",
                        )
                      }
                      className="inline-flex h-9 items-center gap-1.5 rounded-md border px-3 text-xs font-medium hover:bg-muted"
                    >
                      <Check className="size-3.5" />
                      Acknowledge
                    </button>
                  )}

                  <button
                    type="button"
                    onClick={() =>
                      void updateAlert(alert, "archive")
                    }
                    className="inline-flex h-9 items-center gap-1.5 rounded-md border px-3 text-xs font-medium text-muted-foreground hover:bg-muted hover:text-foreground"
                  >
                    <Archive className="size-3.5" />
                    Archive
                  </button>
                </div>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  )
}


function SummaryCard({
  label,
  value,
  icon,
}: {
  label: string
  value: number
  icon: React.ReactNode
}) {
  return (
    <div className="flex items-center gap-4 rounded-xl border bg-card p-4">
      <div className="rounded-lg bg-primary/10 p-3 text-primary">
        {icon}
      </div>
      <div>
        <p className="text-2xl font-semibold">{value}</p>
        <p className="text-xs text-muted-foreground">{label}</p>
      </div>
    </div>
  )
}


function severityClasses(severity: Alert["severity"]) {
  switch (severity) {
    case "critical":
      return "bg-destructive/10 text-destructive"
    case "high":
      return "bg-orange-500/10 text-orange-500"
    case "medium":
      return "bg-amber-500/10 text-amber-500"
    case "low":
      return "bg-blue-500/10 text-blue-500"
    default:
      return "bg-muted text-muted-foreground"
  }
}


function formatDate(value: string) {
  const date = new Date(value)

  if (Number.isNaN(date.getTime())) {
    return "Unknown time"
  }

  return new Intl.DateTimeFormat("en-LS", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(date)
}
