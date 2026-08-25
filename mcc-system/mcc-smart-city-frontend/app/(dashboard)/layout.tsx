import type { ReactNode } from "react"
import { Sidebar } from "@/components/dashboard/sidebar"
import { TopBar } from "@/components/dashboard/top-bar"

export default function DashboardLayout({ children }: { children: ReactNode }) {
    return (
        <div className="flex h-screen overflow-hidden bg-background">
            <Sidebar />
            <div className="flex min-w-0 flex-1 flex-col">
                <TopBar />
                <main className="flex-1 overflow-y-auto p-4 md:p-6">
                    <div className="mx-auto flex max-w-7xl flex-col gap-4 md:gap-6">
                        {children}
                    </div>
                </main>
            </div>
        </div>
    )
}