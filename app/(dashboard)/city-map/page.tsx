import { CameraMap } from "@/components/dashboard/camera-map"

export default function CityMapPage() {
    return (
        <>
            <div>
                <h1 className="text-xl font-semibold text-foreground">City Map</h1>
                <p className="text-sm text-muted-foreground">
                    Camera locations and live status across Maseru.
                </p>
            </div>
            <CameraMap />
        </>
    )
}