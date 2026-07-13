import { AlertsFeed } from "@/components/dashboard/alerts-feed"

export default function IncidentsPage() {
    return (
        <>
            <div>
                <h1 className="text-xl font-semibold text-foreground">Incidents</h1>
                <p className="text-sm text-muted-foreground">
                    AI-detected events awaiting operator review and dispatch.
                </p>
            </div>
            <AlertsFeed />
        </>
    )
}