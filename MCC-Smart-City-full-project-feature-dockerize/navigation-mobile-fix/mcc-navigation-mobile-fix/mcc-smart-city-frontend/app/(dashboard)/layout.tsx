"use client"

import type { ReactNode } from "react"
import { useEffect, useState } from "react"
import { usePathname } from "next/navigation"

import { ProtectedRoute } from "@/components/auth/protected-route"
import { Sidebar } from "@/components/dashboard/sidebar"
import { TopBar } from "@/components/dashboard/top-bar"

export default function DashboardLayout({
  children,
}: {
  children: ReactNode
}) {
  const pathname = usePathname()
  const [mobileSidebarOpen, setMobileSidebarOpen] = useState(false)

  useEffect(() => {
    setMobileSidebarOpen(false)
  }, [pathname])

  return (
    <ProtectedRoute>
      <div className="flex h-screen overflow-hidden bg-background">
        <Sidebar
          mobileOpen={mobileSidebarOpen}
          onMobileClose={() => setMobileSidebarOpen(false)}
        />

        <div className="flex min-w-0 flex-1 flex-col">
          <TopBar
            mobileSidebarOpen={mobileSidebarOpen}
            onMenuClick={() =>
              setMobileSidebarOpen((current) => !current)
            }
          />

          <main className="flex-1 overflow-y-auto p-4 md:p-6">
            <div className="mx-auto flex max-w-7xl flex-col gap-4 md:gap-6">
              {children}
            </div>
          </main>
        </div>
      </div>
    </ProtectedRoute>
  )
}
