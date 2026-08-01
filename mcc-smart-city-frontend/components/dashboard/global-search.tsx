"use client"

import { useMemo, useRef, useState } from "react"
import { useRouter } from "next/navigation"
import { Cctv, Search, TriangleAlert, Cpu, X } from "lucide-react"
import { cameras, incidents, edgeDevices } from "@/lib/mock-data"
import { cn } from "@/lib/utils"

type Result = {
    id: string
    title: string
    subtitle: string
    group: "Cameras" | "Incidents" | "Devices"
    href: string
}

// Build a flat, searchable index from the three data sets.
const searchIndex: Result[] = [
    ...cameras.map((c) => ({
        id: c.id,
        title: c.name,
        subtitle: `${c.id} · ${c.zone} · ${c.status}`,
        group: "Cameras" as const,
        href: "/live-feeds",
    })),
    ...incidents.map((i) => ({
        id: i.id,
        title: i.type,
        subtitle: `${i.id} · ${i.location} · ${i.severity}`,
        group: "Incidents" as const,
        href: "/incidents",
    })),
    ...edgeDevices.map((d) => ({
        id: d.id,
        title: d.name,
        subtitle: `${d.id} · ${d.type} · ${d.status}`,
        group: "Devices" as const,
        href: "/devices",
    })),
]

const groupIcon = {
    Cameras: Cctv,
    Incidents: TriangleAlert,
    Devices: Cpu,
}

export function GlobalSearch() {
    const router = useRouter()
    const [query, setQuery] = useState("")
    const [open, setOpen] = useState(false)
    const containerRef = useRef<HTMLDivElement>(null)

    const results = useMemo(() => {
        const q = query.trim().toLowerCase()
        if (!q) return []
        return searchIndex.filter(
            (item) =>
                item.title.toLowerCase().includes(q) ||
                item.subtitle.toLowerCase().includes(q) ||
                item.id.toLowerCase().includes(q),
        )
    }, [query])

    const grouped = useMemo(() => {
        const map: Record<string, Result[]> = {}
        for (const r of results) {
            map[r.group] = map[r.group] ?? []
            map[r.group].push(r)
        }
        return map
    }, [results])

    function go(href: string) {
        router.push(href)
        setQuery("")
        setOpen(false)
    }

    return (
        <div ref={containerRef} className="relative hidden lg:block">
            <div className="flex items-center gap-2 rounded-md border border-border bg-card px-3 py-1.5">
                <Search className="size-4 text-muted-foreground" />
                <input
                    value={query}
                    onChange={(e) => {
                        setQuery(e.target.value)
                        setOpen(true)
                    }}
                    onFocus={() => setOpen(true)}
                    onBlur={() => {
                        // delay so a click on a result registers before closing
                        window.setTimeout(() => setOpen(false), 150)
                    }}
                    onKeyDown={(e) => {
                        if (e.key === "Escape") {
                            setQuery("")
                            setOpen(false)
                        }
                        if (e.key === "Enter" && results[0]) {
                            go(results[0].href)
                        }
                    }}
                    placeholder="Search cameras, incidents, devices..."
                    className="w-56 bg-transparent text-sm text-foreground outline-none placeholder:text-muted-foreground"
                    aria-label="Search cameras, incidents and devices"
                />
                {query ? (
                    <button
                        onMouseDown={(e) => e.preventDefault()}
                        onClick={() => {
                            setQuery("")
                            setOpen(false)
                        }}
                        aria-label="Clear search"
                        className="text-muted-foreground transition-colors hover:text-foreground"
                    >
                        <X className="size-3.5" />
                    </button>
                ) : null}
            </div>

            {open && query.trim() ? (
                <div className="absolute left-0 right-0 top-full z-50 mt-2 max-h-96 overflow-y-auto rounded-md border border-border bg-popover p-1 shadow-lg">
                    {results.length === 0 ? (
                        <p className="px-3 py-4 text-center text-sm text-muted-foreground">
                            No matches for &ldquo;{query}&rdquo;
                        </p>
                    ) : (
                        Object.entries(grouped).map(([group, items]) => {
                            const Icon = groupIcon[group as keyof typeof groupIcon]
                            return (
                                <div key={group} className="mb-1 last:mb-0">
                                    <p className="px-2 py-1 text-[11px] font-medium uppercase tracking-wide text-muted-foreground">
                                        {group}
                                    </p>
                                    {items.map((item) => (
                                        <button
                                            key={item.id}
                                            onMouseDown={(e) => e.preventDefault()}
                                            onClick={() => go(item.href)}
                                            className={cn(
                                                "flex w-full items-start gap-2 rounded-md px-2 py-2 text-left transition-colors hover:bg-accent",
                                            )}
                                        >
                                            <Icon className="mt-0.5 size-4 shrink-0 text-muted-foreground" />
                                            <span className="min-w-0 flex-1">
                        <span className="block truncate text-sm text-foreground">{item.title}</span>
                        <span className="block truncate text-xs text-muted-foreground">
                          {item.subtitle}
                        </span>
                      </span>
                                        </button>
                                    ))}
                                </div>
                            )
                        })
                    )}
                </div>
            ) : null}
        </div>
    )
}