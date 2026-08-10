"use client"

import Link from "next/link"
import { useCallback, useEffect, useRef, useState } from "react"
import {
  Bell,
  Check,
  CheckCheck,
  CircleAlert,
  Clock3,
  ExternalLink,
  LoaderCircle,
  X,
} from "lucide-react"

import { apiFetch } from "@/lib/api"
import type {
  Alert,
  AlertListResponse,
  UnreadCountResponse,
} from "@/lib/types"

const POLL_INTERVAL_MS = 5000

export function NotificationBell() {
  const [open, setOpen] = useState(false)
  const [alerts, setAlerts] = useState<Alert[]>([])
  const [unreadCount, setUnreadCount] = useState(0)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState("")
  const wrapperRef = useRef<HTMLDivElement>(null)

  const loadCount = useCallback(async () => {
    try {
      const data = await apiFetch<UnreadCountResponse>(
        "/alerts/unread-count",
      )
      setUnreadCount(data.unread_count)
    } catch {
      // The session/auth provider handles authentication failures.
    }
  }, [])

  const loadAlerts = useCallback(async () => {
    setLoading(true)
    setError("")

    try {
      const data = await apiFetch<AlertListResponse>(
        "/alerts?limit=8&offset=0",
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
    void loadCount()

    const timer = window.setInterval(
      () => void loadCount(),
      POLL_INTERVAL_MS,
    )

    return () => window.clearInterval(timer)
  }, [loadCount])

  useEffect(() => {
    if (open) {
      void loadAlerts()
    }
  }, [open, loadAlerts])

  useEffect(() => {
    function onPointerDown(event: MouseEvent) {
      if (
        wrapperRef.current &&
        !wrapperRef.current.contains(event.target as Node)
      ) {
        setOpen(false)
      }
    }

    document.addEventListener("mousedown", onPointerDown)
    return () => {
      document.removeEventListener("mousedown", onPointerDown)
    }
  }, [])

  async function markRead(alert: Alert) {
    if (alert.is_read) {
      return
    }

    try {
      const updated = await apiFetch<Alert>(
        `/alerts/${alert.id}/read`,
        { method: "PATCH" },
      )

      setAlerts((current) =>
        current.map((item) =>
          item.id === updated.id ? updated : item,
        ),
      )
      setUnreadCount((current) => Math.max(0, current - 1))
    } catch {
      // Keep the dropdown usable if marking read fails.
    }
  }

  async function acknowledge(alert: Alert) {
    try {
      const wasUnread = !alert.is_read

      const updated = await apiFetch<Alert>(
        `/alerts/${alert.id}/acknowledge`,
        { method: "PATCH" },
      )

      setAlerts((current) =>
        current.map((item) =>
          item.id === updated.id ? updated : item,
        ),
      )

      if (wasUnread) {
        setUnreadCount((current) => Math.max(0, current - 1))
      }
    } catch (requestError) {
      setError(
        requestError instanceof Error
          ? requestError.message
          : "Unable to acknowledge alert.",
      )
    }
  }

  async function archive(alert: Alert) {
    try {
      const wasUnread = !alert.is_read

      await apiFetch<Alert>(
        `/alerts/${alert.id}/archive`,
        { method: "PATCH" },
      )

      setAlerts((current) =>
        current.filter((item) => item.id !== alert.id),
      )

      if (wasUnread) {
        setUnreadCount((current) => Math.max(0, current - 1))
      }
    } catch (requestError) {
      setError(
        requestError instanceof Error
          ? requestError.message
          : "Unable to archive alert.",
      )
    }
  }

  async function markAllRead() {
    try {
      await apiFetch<{ success: boolean }>("/alerts/read-all", {
        method: "PATCH",
      })

      setAlerts((current) =>
        current.map((alert) => ({
          ...alert,
          is_read: true,
          read_at: alert.read_at ?? new Date().toISOString(),
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
    <div ref={wrapperRef} className="relative">
      <button
        type="button"
        onClick={() => setOpen((current) => !current)}
        aria-label="Notifications"
        aria-expanded={open}
        className="relative flex size-9 items-center justify-center rounded-md border bg-card text-muted-foreground transition hover:text-foreground"
      >
        <Bell className="size-4" />

        {unreadCount > 0 && (
          <span className="absolute -right-1.5 -top-1.5 flex min-w-5 items-center justify-center rounded-full bg-destructive px-1.5 py-0.5 text-[10px] font-semibold leading-none text-destructive-foreground">
            {unreadCount > 99 ? "99+" : unreadCount}
          </span>
        )}
      </button>

      {open && (
        <div className="absolute right-0 z-50 mt-2 w-[min(420px,calc(100vw-2rem))] overflow-hidden rounded-xl border bg-popover text-popover-foreground shadow-2xl">
          <div className="flex items-center justify-between border-b px-4 py-3">
            <div>
              <h3 className="text-sm font-semibold">Notifications</h3>
              <p className="text-xs text-muted-foreground">
                {unreadCount === 0
                  ? "You are all caught up."
                  : `${unreadCount} unread alert${unreadCount === 1 ? "" : "s"}`}
              </p>
            </div>

            {unreadCount > 0 && (
              <button
                type="button"
                onClick={() => void markAllRead()}
                className="flex items-center gap-1.5 text-xs font-medium text-primary hover:underline"
              >
                <CheckCheck className="size-3.5" />
                Mark all read
              </button>
            )}
          </div>

          {error && (
            <div className="border-b bg-destructive/10 px-4 py-2 text-xs text-destructive">
              {error}
            </div>
          )}

          <div className="max-h-[460px] overflow-y-auto">
            {loading && (
              <div className="flex items-center justify-center gap-2 p-8 text-sm text-muted-foreground">
                <LoaderCircle className="size-4 animate-spin" />
                Loading notifications...
              </div>
            )}

            {!loading && alerts.length === 0 && (
              <div className="p-8 text-center">
                <Bell className="mx-auto size-7 text-muted-foreground/60" />
                <p className="mt-3 text-sm font-medium">
                  No notifications
                </p>
                <p className="mt-1 text-xs text-muted-foreground">
                  Operational alerts will appear here.
                </p>
              </div>
            )}

            {!loading &&
              alerts.map((alert) => (
                <AlertRow
                  key={alert.id}
                  alert={alert}
                  onRead={() => void markRead(alert)}
                  onAcknowledge={() => void acknowledge(alert)}
                  onArchive={() => void archive(alert)}
                  onNavigate={() => {
                    void markRead(alert)
                    setOpen(false)
                  }}
                />
              ))}
          </div>

          <div className="border-t p-2">
            <Link
              href="/notifications"
              onClick={() => setOpen(false)}
              className="flex h-9 items-center justify-center rounded-md text-sm font-medium transition hover:bg-muted"
            >
              View all notifications
            </Link>
          </div>
        </div>
      )}
    </div>
  )
}

function AlertRow({
  alert,
  onRead,
  onAcknowledge,
  onArchive,
  onNavigate,
}: {
  alert: Alert
  onRead: () => void
  onAcknowledge: () => void
  onArchive: () => void
  onNavigate: () => void
}) {
  return (
    <div
      className={`border-b p-4 last:border-b-0 ${
        alert.is_read ? "bg-background" : "bg-primary/[0.045]"
      }`}
    >
      <div className="flex gap-3">
        <div
          className={`mt-0.5 flex size-9 shrink-0 items-center justify-center rounded-lg ${severityClasses(
            alert.severity,
          )}`}
        >
          <CircleAlert className="size-4" />
        </div>

        <div className="min-w-0 flex-1">
          <div className="flex items-start gap-2">
            <div className="min-w-0 flex-1">
              <p className="truncate text-sm font-medium">
                {alert.title}
              </p>
              <p className="mt-1 line-clamp-2 text-xs leading-5 text-muted-foreground">
                {alert.message}
              </p>
            </div>

            {!alert.is_read && (
              <span className="mt-1 size-2 shrink-0 rounded-full bg-primary" />
            )}
          </div>

          <div className="mt-2 flex items-center gap-2 text-[11px] text-muted-foreground">
            <Clock3 className="size-3" />
            {relativeTime(alert.created_at)}
            <span>•</span>
            <span className="capitalize">{alert.severity}</span>
          </div>

          <div className="mt-3 flex flex-wrap items-center gap-2">
            {alert.action_url && (
              <Link
                href={alert.action_url}
                onClick={onNavigate}
                className="inline-flex h-7 items-center gap-1 rounded-md bg-primary px-2.5 text-xs font-medium text-primary-foreground"
              >
                Open incident
                <ExternalLink className="size-3" />
              </Link>
            )}

            {!alert.is_acknowledged && (
              <button
                type="button"
                onClick={onAcknowledge}
                className="inline-flex h-7 items-center gap-1 rounded-md border px-2.5 text-xs font-medium hover:bg-muted"
              >
                <Check className="size-3" />
                Acknowledge
              </button>
            )}

            {!alert.is_read && (
              <button
                type="button"
                onClick={onRead}
                className="h-7 px-1 text-xs text-muted-foreground hover:text-foreground"
              >
                Mark read
              </button>
            )}

            <button
              type="button"
              onClick={onArchive}
              aria-label="Archive notification"
              className="ml-auto flex size-7 items-center justify-center rounded-md text-muted-foreground hover:bg-muted hover:text-foreground"
            >
              <X className="size-3.5" />
            </button>
          </div>
        </div>
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

export function relativeTime(value: string) {
  const then = new Date(value).getTime()
  const now = Date.now()
  const seconds = Math.max(0, Math.floor((now - then) / 1000))

  if (seconds < 60) {
    return "just now"
  }

  const minutes = Math.floor(seconds / 60)
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

  return new Date(value).toLocaleDateString("en-GB", {
    day: "2-digit",
    month: "short",
    year: "numeric",
  })
}
