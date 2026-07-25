"use client"
import Link from "next/link"
import { usePathname } from "next/navigation"
import {
  Activity,
  AlertTriangle,
  BarChart3,
  Cctv,
  Cpu,
  LayoutDashboard,
  Map,
  Settings,
  ShieldCheck,
} from "lucide-react"
import { cn } from "@/lib/utils"

const navItems = [
  { label: "Overview", icon: LayoutDashboard, href: "/" },
  { label: "Live Feeds", icon: Cctv, href: "/live-feeds" },
  { label: "Incidents", icon: AlertTriangle, href: "/incidents", badge: 6 },
  { label: "City Map", icon: Map, href: "/city-map" },
  { label: "Analytics", icon: BarChart3, href: "/analytics" },
  { label: "Devices", icon: Cpu, href: "/devices" },
]

const secondaryItems = [
  { label: "System Health", icon: Activity },
  { label: "Settings", icon: Settings },
]

export function Sidebar() {
  const pathname = usePathname()
  return (
    <aside className="hidden w-60 shrink-0 flex-col border-r border-sidebar-border bg-sidebar lg:flex">
      <div className="flex h-16 items-center gap-2.5 border-b border-sidebar-border px-5">
        <div className="flex size-9 items-center justify-center rounded-md bg-primary/15 text-primary">
          <ShieldCheck className="size-5" />
        </div>
        <div className="leading-tight">
          <p className="text-sm font-semibold text-sidebar-foreground">MCC Command</p>
          <p className="text-xs text-muted-foreground">Maseru City Council</p>
        </div>
      </div>

      <nav className="flex flex-1 flex-col gap-1 px-3 py-4">
        <p className="px-2 pb-2 text-xs font-medium uppercase tracking-wider text-muted-foreground">
          Operations
        </p>
        {navItems.map((item) => {
          const active = pathname === item.href
          return (
              <Link
                  key={item.label}
                  href={item.href}
                  className={cn(
                      "flex items-center gap-3 rounded-md px-3 py-2 text-sm transition-colors",
                      active
                          ? "bg-sidebar-accent text-sidebar-accent-foreground"
                          : "text-muted-foreground hover:bg-sidebar-accent/60 hover:text-sidebar-foreground",
                  )}
              >
                <item.icon className="size-4" />
                <span className="flex-1 text-left">{item.label}</span>
                {item.badge ? (
                    <span className="flex size-5 items-center justify-center rounded-full bg-destructive text-[11px] font-semibold text-destructive-foreground">
                  {item.badge}
                </span>
                ) : null}
              </Link>
          )
        })}

        <p className="px-2 pb-2 pt-5 text-xs font-medium uppercase tracking-wider text-muted-foreground">
          System
        </p>
        {secondaryItems.map((item) => (
          <button
            key={item.label}
            className="flex items-center gap-3 rounded-md px-3 py-2 text-sm text-muted-foreground transition-colors hover:bg-sidebar-accent/60 hover:text-sidebar-foreground"
          >
            <item.icon className="size-4" />
            <span>{item.label}</span>
          </button>
        ))}
      </nav>

      <div className="border-t border-sidebar-border p-4">
        <div className="flex items-center gap-3">
          <div className="flex size-9 items-center justify-center rounded-full bg-secondary text-sm font-medium text-secondary-foreground">
            TM
          </div>
          <div className="min-w-0 leading-tight">
            <p className="truncate text-sm font-medium text-sidebar-foreground">T. Mokoena</p>
            <p className="truncate text-xs text-muted-foreground">Control Room Operator</p>
          </div>
        </div>
      </div>
    </aside>
  )
}
