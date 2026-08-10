"use client"

import { usePathname } from "next/navigation"
import { Menu } from "lucide-react"

import { useAuth } from "@/components/auth/auth-provider"
import { NotificationBell } from "@/components/dashboard/notification-bell"
import { ThemeToggle } from "@/components/theme-toggle"


const titles: Record<string, string> = {
  "/": "Operations Overview",
  "/administration/users": "User Management",
  "/administration/departments": "Departments",
  "/administration/roles": "Roles & Permissions",
  "/administration/navigation": "Navigation Management",
  "/live-feeds": "Live Feeds",
  "/incidents": "Incidents",
  "/assignments": "Assignments",
  "/notifications": "Notifications",
  "/city-map": "City Map",
  "/analytics": "Analytics",
  "/devices": "Devices",
}


export function TopBar() {
  const pathname = usePathname()
  const { user } = useAuth()

  const title =
    titles[pathname] ||
    (pathname.startsWith("/incidents")
      ? "Incidents"
      : "MCC Command Center")

  return (
    <header className="flex h-16 shrink-0 items-center gap-4 border-b border-border bg-background/85 px-4 backdrop-blur md:px-6">
      <button className="rounded-md p-2 text-muted-foreground lg:hidden">
        <Menu className="size-5" />
      </button>

      <div>
        <h1 className="text-base font-semibold md:text-lg">
          {title}
        </h1>

        <p className="hidden text-xs text-muted-foreground sm:block">
          {user?.department?.name || "Maseru City Council"} ·
          Secure administration
        </p>
      </div>

      <div className="ml-auto flex items-center gap-2">
        <div className="hidden text-right md:block">
          <p className="text-xs font-medium">
            {user?.full_name}
          </p>

          <p className="text-[11px] text-muted-foreground">
            {user?.role?.name || "SuperAdmin"}
          </p>
        </div>

        <ThemeToggle />
        <NotificationBell />
      </div>
    </header>
  )
}
