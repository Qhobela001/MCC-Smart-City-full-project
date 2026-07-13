"use client"

import { useEffect, useState } from "react"
import { Moon, Sun } from "lucide-react"

export function ThemeToggle() {
    const [isDark, setIsDark] = useState(true)

    // Sync state with whatever class is already on <html> (set by the no-flash script)
    useEffect(() => {
        setIsDark(document.documentElement.classList.contains("dark"))
    }, [])

    function toggle() {
        const next = !isDark
        setIsDark(next)
        document.documentElement.classList.toggle("dark", next)
        try {
            localStorage.setItem("theme", next ? "dark" : "light")
        } catch {
            // ignore storage errors (e.g. private mode)
        }
    }

    return (
        <button
            onClick={toggle}
            aria-label={isDark ? "Switch to light mode" : "Switch to dark mode"}
            title={isDark ? "Switch to light mode" : "Switch to dark mode"}
            className="flex size-9 items-center justify-center rounded-md border border-border bg-card text-muted-foreground transition-colors hover:text-foreground"
        >
            {isDark ? <Sun className="size-4" /> : <Moon className="size-4" />}
        </button>
    )
}