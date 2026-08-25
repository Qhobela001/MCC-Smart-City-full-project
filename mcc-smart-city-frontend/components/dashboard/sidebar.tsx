"use client"

import Link from "next/link"
import { usePathname } from "next/navigation"
import { useEffect, useMemo, useState } from "react"
import * as Icons from "lucide-react"
import {
  ChevronRight,
  LogOut,
  ShieldCheck,
  X,
} from "lucide-react"

import { useAuth } from "@/components/auth/auth-provider"
import { apiFetch } from "@/lib/api"
import type { NavigationItem } from "@/lib/types"
import { cn } from "@/lib/utils"

const fallback: NavigationItem[] = [
  {
    id: 1,
    label: "Dashboard",
    href: "/",
    icon: "LayoutDashboard",
    section: "Overview",
    sort_order: 1,
    is_active: true,
    is_system: true,
    created_at: "",
  },
  {
    id: 2,
    label: "Users",
    href: "/administration/users",
    icon: "Users",
    section: "Administration",
    sort_order: 1,
    is_active: true,
    is_system: true,
    created_at: "",
  },
  {
    id: 3,
    label: "Departments",
    href: "/administration/departments",
    icon: "Building2",
    section: "Administration",
    sort_order: 2,
    is_active: true,
    is_system: true,
    created_at: "",
  },
  {
    id: 4,
    label: "Roles & Permissions",
    href: "/administration/roles",
    icon: "ShieldCheck",
    section: "Administration",
    sort_order: 3,
    is_active: true,
    is_system: true,
    created_at: "",
  },
  {
    id: 5,
    label: "Navigation",
    href: "/administration/navigation",
    icon: "PanelLeft",
    section: "Administration",
    sort_order: 4,
    is_active: true,
    is_system: true,
    created_at: "",
  },
  {
    id: 6,
    label: "AI Test Lab",
    href: "/ai-test-lab",
    icon: "BrainCircuit",
    section: "Operations",
    sort_order: 6,
    is_active: true,
    is_system: true,
    created_at: "",
  },
]

const sectionPriority: Record<string, number> = {
  Overview: 1,
  Operations: 2,
  Administration: 3,
  Analytics: 4,
}

function iconFor(name: string) {
  return (
    (
      Icons as unknown as Record<string, Icons.LucideIcon>
    )[name] || Icons.Circle
  )
}

function routeFor(href: string) {
  if (href === "/dashboard") {
    return "/"
  }

  if (href === "/monitoring/live") {
    return "/live-feeds"
  }

  if (href === "/reports") {
    return "/analytics"
  }

  return href
}

function routeIsActive(pathname: string, href: string) {
  return (
    pathname === href ||
    (href !== "/" && pathname.startsWith(`${href}/`))
  )
}

type SidebarProps = {
  mobileOpen: boolean
  onMobileClose: () => void
}

export function Sidebar({
  mobileOpen,
  onMobileClose,
}: SidebarProps) {
  const pathname = usePathname()
  const { user, logout } = useAuth()

  const [items, setItems] = useState<NavigationItem[]>([])
  const [expandedSections, setExpandedSections] = useState<
    Record<string, boolean>
  >({})

  useEffect(() => {
    apiFetch<NavigationItem[]>("/navigation/me")
      .then(setItems)
      .catch(() => setItems(fallback))
  }, [])

  const groups = useMemo(() => {
    const map = new Map<string, NavigationItem[]>()

    const activeItems = items
      .filter((item) => item.is_active)
      .sort((a, b) => a.sort_order - b.sort_order)

    for (const item of activeItems) {
      const section = item.section || "Workspace"
      map.set(section, [...(map.get(section) || []), item])
    }

    return [...map.entries()].sort(
      ([sectionA], [sectionB]) => {
        const priorityA = sectionPriority[sectionA] ?? 999
        const priorityB = sectionPriority[sectionB] ?? 999

        if (priorityA !== priorityB) {
          return priorityA - priorityB
        }

        return sectionA.localeCompare(sectionB)
      },
    )
  }, [items])

  useEffect(() => {
    if (groups.length === 0) {
      return
    }

    setExpandedSections((current) => {
      const next = { ...current }

      for (const [section] of groups) {
        if (next[section] === undefined) {
          next[section] = true
        }
      }

      return next
    })
  }, [groups])

  useEffect(() => {
    for (const [section, links] of groups) {
      const containsActiveRoute = links.some((item) => {
        const href = routeFor(item.href)
        return routeIsActive(pathname, href)
      })

      if (containsActiveRoute) {
        setExpandedSections((current) => ({
          ...current,
          [section]: true,
        }))
        break
      }
    }
  }, [pathname, groups])

  function toggleSection(section: string) {
    setExpandedSections((current) => ({
      ...current,
      [section]: !(current[section] ?? true),
    }))
  }

  const initials = (user?.full_name || "MCC")
    .split(/\s+/)
    .map((part) => part[0])
    .slice(0, 2)
    .join("")
    .toUpperCase()

  return (
    <>
      {mobileOpen && (
        <button
          type="button"
          aria-label="Close navigation menu"
          onClick={onMobileClose}
          className="fixed inset-0 z-40 bg-black/55 backdrop-blur-[1px] lg:hidden"
        />
      )}

      <aside
        id="mcc-sidebar"
        className={cn(
          "fixed inset-y-0 left-0 z-50 flex w-64 shrink-0 flex-col border-r border-sidebar-border bg-sidebar shadow-2xl transition-transform duration-200 ease-out lg:static lg:z-auto lg:translate-x-0 lg:shadow-none",
          mobileOpen ? "translate-x-0" : "-translate-x-full",
        )}
      >
        <div className="flex h-16 items-center gap-3 border-b border-sidebar-border px-5">
          <div className="flex size-9 items-center justify-center rounded-lg bg-primary/15 text-primary">
            <ShieldCheck className="size-5" />
          </div>

          <div className="min-w-0 flex-1 leading-tight">
            <p className="text-sm font-semibold text-sidebar-foreground">
              MCC Command
            </p>
            <p className="text-xs text-muted-foreground">
              Maseru City Council
            </p>
          </div>

          <button
            type="button"
            onClick={onMobileClose}
            aria-label="Close navigation menu"
            className="rounded-md p-2 text-muted-foreground transition hover:bg-sidebar-accent hover:text-sidebar-foreground lg:hidden"
          >
            <X className="size-4" />
          </button>
        </div>

        <nav className="flex flex-1 flex-col overflow-y-auto px-3 py-4">
          {groups.map(([section, links]) => {
            const expanded = expandedSections[section] ?? true

            const sectionHasActiveRoute = links.some((item) => {
              const href = routeFor(item.href)
              return routeIsActive(pathname, href)
            })

            return (
              <div key={section} className="mb-2">
                <button
                  type="button"
                  onClick={() => toggleSection(section)}
                  aria-expanded={expanded}
                  className={cn(
                    "group flex w-full items-center gap-2 rounded-lg px-2 py-2 text-left transition",
                    "hover:bg-sidebar-accent",
                    sectionHasActiveRoute &&
                      "text-sidebar-foreground",
                  )}
                >
                  <ChevronRight
                    className={cn(
                      "size-3.5 shrink-0 text-muted-foreground transition-transform duration-200",
                      expanded && "rotate-90",
                    )}
                  />

                  <span
                    className={cn(
                      "flex-1 text-[11px] font-semibold uppercase tracking-[.16em]",
                      sectionHasActiveRoute
                        ? "text-sidebar-foreground"
                        : "text-muted-foreground",
                    )}
                  >
                    {section}
                  </span>

                  <span className="text-[10px] tabular-nums text-muted-foreground/70">
                    {links.length}
                  </span>
                </button>

                <div
                  className={cn(
                    "grid transition-all duration-200 ease-in-out",
                    expanded
                      ? "grid-rows-[1fr] opacity-100"
                      : "grid-rows-[0fr] opacity-0",
                  )}
                >
                  <div className="overflow-hidden">
                    <div className="space-y-1 pb-2 pt-1">
                      {links.map((item) => {
                        const Icon = iconFor(item.icon)
                        const href = routeFor(item.href)
                        const active = routeIsActive(
                          pathname,
                          href,
                        )

                        return (
                          <Link
                            key={item.id}
                            href={href}
                            onClick={onMobileClose}
                            className={cn(
                              "group flex items-center gap-3 rounded-lg py-2.5 pl-7 pr-3 text-sm transition",
                              active
                                ? "bg-primary/12 font-medium text-primary"
                                : "text-muted-foreground hover:bg-sidebar-accent hover:text-sidebar-foreground",
                            )}
                          >
                            <Icon className="size-4 shrink-0" />
                            <span className="flex-1 truncate">
                              {item.label}
                            </span>
                            <ChevronRight
                              className={cn(
                                "size-3.5 shrink-0 opacity-0 transition",
                                "group-hover:opacity-70",
                                active && "opacity-70",
                              )}
                            />
                          </Link>
                        )
                      })}
                    </div>
                  </div>
                </div>
              </div>
            )
          })}
        </nav>

        <div className="border-t border-sidebar-border p-3">
          <div className="rounded-xl bg-sidebar-accent/55 p-3">
            <div className="flex items-center gap-3">
              <div className="flex size-9 shrink-0 items-center justify-center rounded-full bg-primary/15 text-xs font-bold text-primary">
                {initials}
              </div>

              <div className="min-w-0 flex-1">
                <p className="truncate text-sm font-medium">
                  {user?.full_name}
                </p>
                <p className="truncate text-xs text-muted-foreground">
                  {user?.is_superuser
                    ? "Super Administrator"
                    : user?.role?.name || "MCC Employee"}
                </p>
              </div>

              <button
                type="button"
                onClick={logout}
                title="Sign out"
                className="rounded-md p-2 text-muted-foreground transition hover:bg-background hover:text-foreground"
              >
                <LogOut className="size-4" />
              </button>
            </div>
          </div>
        </div>
      </aside>
    </>
  )
}
