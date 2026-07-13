import { AlertsFeed } from "@/components/dashboard/alerts-feed"
import { AnalyticsCharts } from "@/components/dashboard/analytics-charts"
import { CameraMap } from "@/components/dashboard/camera-map"
import { DeviceHealth } from "@/components/dashboard/device-health"
import { KpiCards } from "@/components/dashboard/kpi-cards"
import { LiveFeeds } from "@/components/dashboard/live-feeds"

export default function OverviewPage() {
  return (
      <>
        <KpiCards />
        <div className="grid grid-cols-1 gap-4 md:gap-6 xl:grid-cols-3">
          <div className="flex flex-col gap-4 md:gap-6 xl:col-span-2">
            <LiveFeeds />
            <CameraMap />
          </div>
          <AlertsFeed />
        </div>
        <AnalyticsCharts />
        <DeviceHealth />
      </>
  )
}