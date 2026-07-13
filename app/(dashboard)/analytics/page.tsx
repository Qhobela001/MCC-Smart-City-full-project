import { AnalyticsCharts } from "@/components/dashboard/analytics-charts"

export default function AnalyticsPage() {
    return (
        <>
            <div>
                <h1 className="text-xl font-semibold text-foreground">Analytics</h1>
                <p className="text-sm text-muted-foreground">
                    Incident trends, alert latency, and field-team performance.
                </p>
            </div>
            <AnalyticsCharts />
        </>
    )
}