"use client"

import { usePathname } from "next/navigation"
import { Bell } from "lucide-react"
import { ThemeToggle } from "@/components/theme-toggle"
import { GlobalSearch } from "@/components/dashboard/global-search"
import {
    DateTimeWidget,
    SystemStatusWidget,
    WeatherWidget,
} from "@/components/dashboard/top-bar-widgets"

export function TopBar() {
    const pathname = usePathname()
    const isOverview = pathname === "/"

    return (
        <header className="flex h-16 shrink-0 items-center gap-4 border-b border-border bg-background/80 px-4 backdrop-blur md:px-6">
            {isOverview ? (
                <div>
                    <h1 className="text-base font-semibold text-foreground md:text-lg">Operations Overview</h1>
                    <p className="hidden text-xs text-muted-foreground sm:block">
                        Zone 3 — Headquarters · Central Processing Layer
                    </p>
                </div>
            ) : null}

            <div className="ml-auto flex items-center gap-2 md:gap-3">
                <GlobalSearch />

                <SystemStatusWidget />

                <WeatherWidget />

                <DateTimeWidget />

                <ThemeToggle />

                <button
                    className="relative flex size-9 items-center justify-center rounded-md border border-border bg-card text-muted-foreground transition-colors hover:text-foreground"
                    aria-label="Notifications"
                >
                    <Bell className="size-4" />
                    <span className="absolute -right-1 -top-1 flex size-4 items-center justify-center rounded-full bg-destructive text-[10px] font-semibold text-destructive-foreground">
            3
          </span>
                </button>
            </div>
        </header>
    )
}