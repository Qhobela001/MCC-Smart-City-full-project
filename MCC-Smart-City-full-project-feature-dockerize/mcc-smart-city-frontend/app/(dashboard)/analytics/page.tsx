import { AnalyticsCharts } from "@/components/dashboard/analytics-charts"

export default function AnalyticsPage() {
    return (
        <div className="space-y-6">

            <div>
                <h1 className="text-xl font-semibold text-foreground">
                    AI Monitoring Analytics
                </h1>

                <p className="mt-1 text-sm text-muted-foreground">
                    City intelligence generated from MCC computer-vision detections
                    across monitored locations.
                </p>
            </div>

            <AnalyticsCharts />

        </div>
    )
}