"use client"

import {
  FormEvent,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react"

import {
  Activity,
  BrainCircuit,
  ChevronLeft,
  ChevronRight,
  FileVideo,
  ImageIcon,
  Layers3,
  Loader2,
  Play,
  ScanLine,
  Upload,
} from "lucide-react"

import { apiFetch } from "@/lib/api"


/* ==========================================================================
   TYPES
   ========================================================================== */

type MediaMode = "image" | "video"
type TestMode = "raw" | "pipeline"


type BBox = {
  x1: number
  y1: number
  x2: number
  y2: number
  width: number
  height: number
}


type Detection = {
  class_id: number
  class_name: string
  confidence: number
  bbox: BBox

  source?: string

  track_id?: string | null
  tracking_state?: string | null
  is_predicted?: boolean

  waste_state?: string | null
  associated_actor_track_id?: string | null
  associated_actor_kind?: string | null
  associated_waste_track_ids?: string[]

  parent_detection_index?: number | null
  seconds_since_detection?: number | null

  dumping_role?: string | null
  original_class_name?: string | null
}


type ModelInfo = {
  model_name: string
  number_of_classes: number
  classes: Record<string, string>
}


/* ==========================================================================
   RAW MODEL RESPONSES
   ========================================================================== */

type RawImageResponse = {
  mode: "raw_model"

  filename: string

  image_width: number
  image_height: number

  confidence_threshold: number
  image_size: number

  detections_count: number
  detections: Detection[]
}


type RawVideoClassSummary = {
  class_name: string

  detections: number

  frames_detected: number

  frame_presence_percent: number

  max_confidence: number

  mean_confidence: number
}


type VideoSample = {
  sampled_frame: number

  frame_index: number

  time_seconds: number

  image_width: number
  image_height: number

  detections: Detection[]
}


type RawVideoResponse = {
  mode: "raw_model"

  filename: string

  duration_seconds: number
  fps: number

  video_width: number
  video_height: number

  total_frames: number
  sampled_frames: number

  requested_frame_stride: number
  effective_frame_stride: number

  analysis_end_seconds: number
  analysis_coverage_percent: number

  confidence_threshold: number
  image_size: number

  total_detections: number

  class_summary: RawVideoClassSummary[]

  sampled_detections: VideoSample[]
}


/* ==========================================================================
   PIPELINE RESPONSES
   ========================================================================== */

type Association = {
  association_type: string

  left_index: number
  left_class: string
  left_track_id?: string | null

  right_index: number
  right_class: string
  right_track_id?: string | null

  relation: string

  confidence: number

  metadata: Record<string, unknown>
}


type RuleAssessment = {
  rule: string

  title: string

  status: string

  confidence: number

  reasons: string[]

  evidence_classes: string[]

  incident_type?: string | null

  related_track_ids: string[]

  details: Record<string, unknown>
}


type Occurrence = {
  occurrence_id: string

  occurrence_type: string

  title: string

  status: string

  confidence: number

  reasons: string[]

  evidence_classes: string[]

  track_ids: string[]

  incident_type?: string | null

  vehicle_track_id?: string | null

  person_track_ids: string[]

  waste_track_ids: string[]

  plate_track_id?: string | null

  plate_status?: string | null

  follow_up?: string | null

  details: Record<string, unknown>
}


type StreetCleanliness = {
  score: number
  state: string

  loose_waste_count: number
  contained_waste_count: number
  waste_around_skip_count: number
  waste_above_skip_count: number
  total_waste_count: number

  provisional: boolean

  reasons: string[]

  before_score?: number | null
  after_score?: number | null
  change?: number | null

  sampled_assessments?: number | null
}


type CleanerPerformance = {
  status: string
  title: string

  confidence: number

  before_score: number
  after_score: number
  change: number

  reasons: string[]

  related_track_ids: string[]
}


type PipelineImageResponse = {
  filename: string

  image_width: number
  image_height: number

  detections_count: number

  detections: Detection[]

  associations: Association[]

  rules: RuleAssessment[]

  occurrences: Occurrence[]

  street_cleanliness: StreetCleanliness
}


type PipelineVideoClassSummary = {
  class_name: string

  max_confidence: number

  detections: number
}


type VideoTrack = {
  track_id: string

  class_name: string

  first_sampled_frame: number
  last_sampled_frame: number

  hits: number

  predicted_frames?: number

  max_confidence: number

  first_seen_seconds?: number
  last_seen_seconds?: number
}


type AssociationSummary = {
  association_type: string
  hits: number
}


type PipelineVideoResponse = {
  filename: string

  duration_seconds: number
  fps: number

  video_width: number
  video_height: number

  total_frames: number
  sampled_frames: number

  frame_stride: number

  requested_frame_stride?: number | null
  effective_frame_stride?: number | null

  analysis_end_seconds?: number | null
  analysis_coverage_percent?: number | null

  sampled_detections: VideoSample[]

  predicted_boxes_count?: number

  class_summary: PipelineVideoClassSummary[]

  tracks: VideoTrack[]

  association_summary: AssociationSummary[]

  rules: RuleAssessment[]

  occurrences: Occurrence[]

  street_cleanliness?: StreetCleanliness | null

  cleaner_performance?: CleanerPerformance | null
}


/* ==========================================================================
   HELPERS
   ========================================================================== */

function percent(value: number) {
  return `${(value * 100).toFixed(1)}%`
}


function label(value: string) {
  return value.replace(/_/g, " ")
}


function clamp(value: number, min: number, max: number) {
  return Math.min(max, Math.max(min, value))
}


function statusClass(status: string) {
  const normalized = status.toLowerCase()

  if (
    normalized.includes("candidate") ||
    normalized.includes("warning") ||
    normalized.includes("poor") ||
    normalized.includes("review")
  ) {
    return "border-amber-500/30 bg-amber-500/10 text-amber-300"
  }

  if (
    normalized.includes("clean") ||
    normalized.includes("effective") ||
    normalized.includes("confirmed") ||
    normalized.includes("detected")
  ) {
    return "border-emerald-500/30 bg-emerald-500/10 text-emerald-300"
  }

  return "border-blue-500/30 bg-blue-500/10 text-blue-300"
}


/* ==========================================================================
   SMALL COMPONENTS
   ========================================================================== */

function Metric({
  title,
  value,
}: {
  title: string
  value: string
}) {
  return (
    <div className="rounded-lg border border-border bg-muted/30 p-3">
      <p className="text-[11px] uppercase tracking-wide text-muted-foreground">
        {title}
      </p>

      <p className="mt-1 text-lg font-semibold">
        {value}
      </p>
    </div>
  )
}


function DetectionOverlay({
  detections,
  width,
  height,
}: {
  detections: Detection[]
  width: number
  height: number
}) {
  if (width <= 0 || height <= 0) {
    return null
  }

  return (
    <div className="pointer-events-none absolute inset-0">
      {detections.map((item, index) => {
        const x1 = clamp(
          (item.bbox.x1 / width) * 100,
          0,
          100,
        )

        const y1 = clamp(
          (item.bbox.y1 / height) * 100,
          0,
          100,
        )

        const x2 = clamp(
          (item.bbox.x2 / width) * 100,
          0,
          100,
        )

        const y2 = clamp(
          (item.bbox.y2 / height) * 100,
          0,
          100,
        )

        const boxWidth = Math.max(
          0,
          x2 - x1,
        )

        const boxHeight = Math.max(
          0,
          y2 - y1,
        )

        const predicted = Boolean(
          item.is_predicted,
        )

        const displayName =
          item.class_name

        return (
          <div
            key={`${item.track_id ?? item.class_name}-${index}`}
            className={`absolute border-2 ${
              predicted
                ? "border-dashed border-amber-400"
                : "border-emerald-400"
            }`}
            style={{
              left: `${x1}%`,
              top: `${y1}%`,
              width: `${boxWidth}%`,
              height: `${boxHeight}%`,
            }}
          >
            <div
              className={`absolute -top-6 left-0 whitespace-nowrap rounded px-1.5 py-0.5 text-[10px] font-medium ${
                predicted
                  ? "bg-amber-400 text-black"
                  : "bg-emerald-400 text-black"
              }`}
            >
              {displayName}

              {" "}

              {percent(item.confidence)}

              {item.track_id
                ? ` · ${item.track_id}`
                : ""}

              {predicted
                ? " · TRACKED"
                : ""}
            </div>
          </div>
        )
      })}
    </div>
  )
}


function DetectionList({
  detections,
}: {
  detections: Detection[]
}) {
  if (detections.length === 0) {
    return (
      <p className="text-sm text-muted-foreground">
        No objects were detected at the current threshold.
      </p>
    )
  }

  return (
    <div className="space-y-2">
      {detections.map((item, index) => (
        <div
          key={`${item.track_id ?? item.class_name}-${index}`}
          className="flex items-center justify-between gap-4 rounded-lg border border-border bg-muted/25 px-3 py-2"
        >
          <div>
            <p className="text-sm font-medium">
              {label(item.class_name)}
            </p>

            <p className="mt-0.5 text-[11px] text-muted-foreground">
              class #{item.class_id}

              {item.track_id
                ? ` · ${item.track_id}`
                : ""}

              {item.source
                ? ` · ${label(item.source)}`
                : ""}
            </p>
          </div>

          <p className="font-mono text-sm">
            {percent(item.confidence)}
          </p>
        </div>
      ))}
    </div>
  )
}


function RuleCard({
  rule,
}: {
  rule: RuleAssessment
}) {
  return (
    <div className="rounded-lg border border-border bg-muted/20 p-4">
      <div className="flex flex-wrap items-center gap-2">
        <p className="font-medium">
          {rule.title}
        </p>

        <span
          className={`rounded-full border px-2 py-0.5 text-[10px] uppercase ${statusClass(rule.status)}`}
        >
          {rule.status}
        </span>

        <span className="text-xs text-muted-foreground">
          {percent(rule.confidence)}
        </span>
      </div>

      <div className="mt-2 space-y-1">
        {rule.reasons.map((reason) => (
          <p
            key={reason}
            className="text-xs text-muted-foreground"
          >
            • {reason}
          </p>
        ))}
      </div>
    </div>
  )
}


function OccurrenceCard({
  occurrence,
}: {
  occurrence: Occurrence
}) {
  return (
    <div className="rounded-lg border border-border bg-muted/20 p-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="font-medium">
            {occurrence.title}
          </p>

          <p className="mt-1 font-mono text-[10px] text-muted-foreground">
            {occurrence.occurrence_id}
          </p>
        </div>

        <span
          className={`rounded-full border px-2 py-0.5 text-[10px] uppercase ${statusClass(occurrence.status)}`}
        >
          {occurrence.status}
        </span>
      </div>

      <div className="mt-3 space-y-1">
        {occurrence.reasons.map((reason) => (
          <p
            key={reason}
            className="text-xs text-muted-foreground"
          >
            • {reason}
          </p>
        ))}
      </div>

      {occurrence.track_ids.length > 0 && (
        <p className="mt-3 text-[11px] text-muted-foreground">
          Tracks: {occurrence.track_ids.join(", ")}
        </p>
      )}
    </div>
  )
}


/* ==========================================================================
   MAIN PAGE
   ========================================================================== */

export default function AITestLabPage() {
  /* ------------------------------------------------------------------------
     Main state
     ------------------------------------------------------------------------ */

  const [mediaMode, setMediaMode] =
    useState<MediaMode>("image")

  const [testMode, setTestMode] =
    useState<TestMode>("raw")

  const [file, setFile] =
    useState<File | null>(null)

  const [preview, setPreview] =
    useState<string | null>(null)

  const [loading, setLoading] =
    useState(false)

  const [error, setError] =
    useState<string | null>(null)

  const [modelInfo, setModelInfo] =
    useState<ModelInfo | null>(null)


  /* ------------------------------------------------------------------------
     General model controls
     ------------------------------------------------------------------------ */

  const [confidence, setConfidence] =
    useState(0.25)

  const [imageSize, setImageSize] =
    useState(640)

  const [frameStride, setFrameStride] =
    useState(2)


  /* ------------------------------------------------------------------------
     Pipeline-only controls
     ------------------------------------------------------------------------ */

  const [
    enhanceVehicleDetails,
    setEnhanceVehicleDetails,
  ] = useState(true)

  const [
    carRecoveryConfidence,
    setCarRecoveryConfidence,
  ] = useState(0.15)

  const [
    smokeDetailConfidence,
    setSmokeDetailConfidence,
  ] = useState(0.12)

  const [
    plateDetailConfidence,
    setPlateDetailConfidence,
  ] = useState(0.18)

  const [
    smokeWindowSeconds,
    setSmokeWindowSeconds,
  ] = useState(3)

  const [
    smokeCandidateHits,
    setSmokeCandidateHits,
  ] = useState(2)

  const [
    smokeStrongHits,
    setSmokeStrongHits,
  ] = useState(3)


  /* ------------------------------------------------------------------------
     Results
     ------------------------------------------------------------------------ */

  const [
    rawImageResult,
    setRawImageResult,
  ] = useState<RawImageResponse | null>(
    null,
  )

  const [
    rawVideoResult,
    setRawVideoResult,
  ] = useState<RawVideoResponse | null>(
    null,
  )

  const [
    pipelineImageResult,
    setPipelineImageResult,
  ] = useState<PipelineImageResponse | null>(
    null,
  )

  const [
    pipelineVideoResult,
    setPipelineVideoResult,
  ] = useState<PipelineVideoResponse | null>(
    null,
  )


  /* ------------------------------------------------------------------------
     Video review state
     ------------------------------------------------------------------------ */

  const videoRef =
    useRef<HTMLVideoElement | null>(null)

  const [
    currentVideoTime,
    setCurrentVideoTime,
  ] = useState(0)

  const [
    playbackRate,
    setPlaybackRate,
  ] = useState(0.5)


  /* ------------------------------------------------------------------------
     Load actual model class list
     ------------------------------------------------------------------------ */

  useEffect(() => {
    let cancelled = false

    async function loadModel() {
      try {
        const result =
          await apiFetch<ModelInfo>(
            "/ai-detection/model",
          )

        if (!cancelled) {
          setModelInfo(result)
        }
      } catch {
        // Model metadata failure should not block testing.
      }
    }

    void loadModel()

    return () => {
      cancelled = true
    }
  }, [])


  /* ------------------------------------------------------------------------
     Derived model class list
     ------------------------------------------------------------------------ */

  const modelClasses =
    useMemo(() => {
      if (!modelInfo) {
        return []
      }

      return Object.entries(
        modelInfo.classes,
      )
        .map(([id, name]) => ({
          id: Number(id),
          name,
        }))
        .sort(
          (a, b) => a.id - b.id,
        )
    }, [modelInfo])


  /* ------------------------------------------------------------------------
     Raw image class summary
     ------------------------------------------------------------------------ */

  const rawImageClassSummary =
    useMemo(() => {
      if (!rawImageResult) {
        return []
      }

      const stats = new Map<
        string,
        {
          detections: number
          best: number
          total: number
        }
      >()

      for (const modelClass of modelClasses) {
        stats.set(
          modelClass.name,
          {
            detections: 0,
            best: 0,
            total: 0,
          },
        )
      }

      for (
        const detection
        of rawImageResult.detections
      ) {
        const current =
          stats.get(
            detection.class_name,
          ) ?? {
            detections: 0,
            best: 0,
            total: 0,
          }

        current.detections += 1

        current.total +=
          detection.confidence

        current.best = Math.max(
          current.best,
          detection.confidence,
        )

        stats.set(
          detection.class_name,
          current,
        )
      }

      return Array.from(
        stats.entries(),
      ).map(
        ([className, value]) => ({
          className,

          detections:
            value.detections,

          best:
            value.best,

          mean:
            value.detections > 0
              ? value.total /
                value.detections
              : 0,
        }),
      )
    }, [
      rawImageResult,
      modelClasses,
    ])


  /* ------------------------------------------------------------------------
     Active video source
     ------------------------------------------------------------------------ */

  const videoSamples =
    testMode === "raw"
      ? (
          rawVideoResult
            ?.sampled_detections
          ?? []
        )
      : (
          pipelineVideoResult
            ?.sampled_detections
          ?? []
        )


  const activeVideoFrame =
    useMemo(() => {
      if (
        videoSamples.length === 0
      ) {
        return null
      }

      let closest =
        videoSamples[0]

      let distance =
        Math.abs(
          closest.time_seconds -
            currentVideoTime,
        )

      for (
        const sample
        of videoSamples.slice(1)
      ) {
        const nextDistance =
          Math.abs(
            sample.time_seconds -
              currentVideoTime,
          )

        if (
          nextDistance < distance
        ) {
          closest = sample
          distance = nextDistance
        }
      }

      return closest
    }, [
      videoSamples,
      currentVideoTime,
    ])


  const activeVideoFrameIndex =
    useMemo(() => {
      if (!activeVideoFrame) {
        return -1
      }

      return videoSamples.findIndex(
        (sample) =>
          sample.frame_index ===
          activeVideoFrame.frame_index,
      )
    }, [
      activeVideoFrame,
      videoSamples,
    ])


  /* ------------------------------------------------------------------------
     Helpers
     ------------------------------------------------------------------------ */

  function clearResults() {
    setRawImageResult(null)
    setRawVideoResult(null)

    setPipelineImageResult(null)
    setPipelineVideoResult(null)

    setCurrentVideoTime(0)

    setError(null)
  }


  function chooseFile(
    nextFile: File | null,
  ) {
    clearResults()

    setFile(nextFile)

    if (preview) {
      URL.revokeObjectURL(preview)
    }

    if (nextFile) {
      setPreview(
        URL.createObjectURL(
          nextFile,
        ),
      )
    } else {
      setPreview(null)
    }
  }


  function changeMediaMode(
    nextMode: MediaMode,
  ) {
    if (nextMode === mediaMode) {
      return
    }

    if (preview) {
      URL.revokeObjectURL(preview)
    }

    setMediaMode(nextMode)

    setFile(null)
    setPreview(null)

    clearResults()
  }


  function changeTestMode(
    nextMode: TestMode,
  ) {
    if (nextMode === testMode) {
      return
    }

    setTestMode(nextMode)

    clearResults()
  }


  function seekSample(
    offset: number,
  ) {
    if (
      !videoRef.current ||
      videoSamples.length === 0
    ) {
      return
    }

    const current =
      activeVideoFrameIndex >= 0
        ? activeVideoFrameIndex
        : 0

    const next =
      clamp(
        current + offset,
        0,
        videoSamples.length - 1,
      )

    const sample =
      videoSamples[next]

    videoRef.current.pause()

    videoRef.current.currentTime =
      sample.time_seconds

    setCurrentVideoTime(
      sample.time_seconds,
    )
  }


  function setReviewSpeed(
    rate: number,
  ) {
    setPlaybackRate(rate)

    if (videoRef.current) {
      videoRef.current.playbackRate =
        rate
    }
  }


  /* ------------------------------------------------------------------------
     Submit
     ------------------------------------------------------------------------ */

  async function submit(
    event: FormEvent,
  ) {
    event.preventDefault()

    if (!file) {
      return
    }

    setLoading(true)
    setError(null)

    clearResults()

    const formData =
      new FormData()

    formData.append(
      "file",
      file,
    )

    try {
      if (mediaMode === "image") {
        if (testMode === "raw") {
          const result =
            await apiFetch<RawImageResponse>(
              `/ai-detection/detect?mode=raw&confidence=${confidence}&image_size=${imageSize}`,
              {
                method: "POST",
                body: formData,
              },
            )

          setRawImageResult(
            result,
          )
        } else {
          const result =
            await apiFetch<PipelineImageResponse>(
              `/ai-detection/detect?mode=pipeline&confidence=${confidence}&enhance_vehicle_details=${enhanceVehicleDetails}&car_recovery_confidence=${carRecoveryConfidence}&smoke_detail_confidence=${smokeDetailConfidence}&plate_detail_confidence=${plateDetailConfidence}`,
              {
                method: "POST",
                body: formData,
              },
            )

          setPipelineImageResult(
            result,
          )
        }

        return
      }


      if (testMode === "raw") {
        const result =
          await apiFetch<RawVideoResponse>(
            `/ai-detection/detect-video?mode=raw&confidence=${confidence}&image_size=${imageSize}&frame_stride=${frameStride}`,
            {
              method: "POST",
              body: formData,
            },
          )

        setRawVideoResult(
          result,
        )
      } else {
        const result =
          await apiFetch<PipelineVideoResponse>(
            `/ai-detection/detect-video?mode=pipeline&confidence=${confidence}&frame_stride=${frameStride}&enhance_vehicle_details=${enhanceVehicleDetails}&car_recovery_confidence=${carRecoveryConfidence}&smoke_detail_confidence=${smokeDetailConfidence}&plate_detail_confidence=${plateDetailConfidence}&smoke_window_seconds=${smokeWindowSeconds}&smoke_candidate_hits=${smokeCandidateHits}&smoke_strong_hits=${smokeStrongHits}`,
            {
              method: "POST",
              body: formData,
            },
          )

        setPipelineVideoResult(
          result,
        )
      }

      setCurrentVideoTime(0)

      setPlaybackRate(0.5)

      if (videoRef.current) {
        videoRef.current.pause()

        videoRef.current.currentTime =
          0

        videoRef.current.playbackRate =
          0.5
      }
    } catch (reason) {
      setError(
        reason instanceof Error
          ? reason.message
          : "AI model test failed.",
      )
    } finally {
      setLoading(false)
    }
  }


  /* ------------------------------------------------------------------------
     Unified current detections
     ------------------------------------------------------------------------ */

  const currentImageDetections =
    testMode === "raw"
      ? (
          rawImageResult
            ?.detections
          ?? []
        )
      : (
          pipelineImageResult
            ?.detections
          ?? []
        )


  const imageWidth =
    testMode === "raw"
      ? (
          rawImageResult
            ?.image_width
          ?? 0
        )
      : (
          pipelineImageResult
            ?.image_width
          ?? 0
        )


  const imageHeight =
    testMode === "raw"
      ? (
          rawImageResult
            ?.image_height
          ?? 0
        )
      : (
          pipelineImageResult
            ?.image_height
          ?? 0
        )


  const hasResult =
    Boolean(
      rawImageResult ||
      rawVideoResult ||
      pipelineImageResult ||
      pipelineVideoResult,
    )


  /* =========================================================================
     RENDER
     ========================================================================= */

  return (
    <div className="space-y-5 pb-10">
      {/* ================================================================
          PAGE HEADER
          ================================================================ */}

      <section className="rounded-xl border border-border bg-card p-5 shadow-sm">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <div className="flex items-center gap-2">
              <BrainCircuit className="size-5 text-primary" />

              <h1 className="text-xl font-semibold">
                AI Model Test Lab
              </h1>
            </div>

            <p className="mt-2 max-w-3xl text-sm text-muted-foreground">
              Evaluate the MCC YOLO model independently from the
              event-processing pipeline. Use Raw Model mode to determine
              whether retraining or additional data is required.
            </p>
          </div>

          {modelInfo && (
            <div className="rounded-lg border border-border bg-muted/20 px-4 py-3 text-right">
              <p className="text-xs text-muted-foreground">
                Loaded model
              </p>

              <p className="mt-1 font-medium">
                {modelInfo.model_name}
              </p>

              <p className="mt-1 text-xs text-muted-foreground">
                {modelInfo.number_of_classes} classes
              </p>
            </div>
          )}
        </div>
      </section>


      {/* ================================================================
          TEST TYPE
          ================================================================ */}

      <section className="rounded-xl border border-border bg-card p-5 shadow-sm">
        <div className="grid gap-5 lg:grid-cols-2">
          <div>
            <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
              Media
            </p>

            <div className="mt-2 flex gap-2">
              <button
                type="button"
                onClick={() =>
                  changeMediaMode(
                    "image",
                  )
                }
                className={`flex items-center gap-2 rounded-lg border px-4 py-2 text-sm ${
                  mediaMode === "image"
                    ? "border-primary bg-primary text-primary-foreground"
                    : "border-border bg-muted/20 hover:bg-muted/40"
                }`}
              >
                <ImageIcon className="size-4" />

                Image Test
              </button>

              <button
                type="button"
                onClick={() =>
                  changeMediaMode(
                    "video",
                  )
                }
                className={`flex items-center gap-2 rounded-lg border px-4 py-2 text-sm ${
                  mediaMode === "video"
                    ? "border-primary bg-primary text-primary-foreground"
                    : "border-border bg-muted/20 hover:bg-muted/40"
                }`}
              >
                <FileVideo className="size-4" />

                Video Test
              </button>
            </div>
          </div>


          <div>
            <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
              Evaluation Mode
            </p>

            <div className="mt-2 grid gap-2 sm:grid-cols-2">
              <button
                type="button"
                onClick={() =>
                  changeTestMode(
                    "raw",
                  )
                }
                className={`rounded-lg border p-3 text-left ${
                  testMode === "raw"
                    ? "border-emerald-500/50 bg-emerald-500/10"
                    : "border-border bg-muted/20 hover:bg-muted/40"
                }`}
              >
                <div className="flex items-center gap-2">
                  <ScanLine className="size-4" />

                  <span className="font-medium">
                    Raw Model
                  </span>
                </div>

                <p className="mt-1 text-xs text-muted-foreground">
                  Direct YOLO inference only. No tracking, recovery or rules.
                </p>
              </button>


              <button
                type="button"
                onClick={() =>
                  changeTestMode(
                    "pipeline",
                  )
                }
                className={`rounded-lg border p-3 text-left ${
                  testMode === "pipeline"
                    ? "border-blue-500/50 bg-blue-500/10"
                    : "border-border bg-muted/20 hover:bg-muted/40"
                }`}
              >
                <div className="flex items-center gap-2">
                  <Layers3 className="size-4" />

                  <span className="font-medium">
                    Full Pipeline
                  </span>
                </div>

                <p className="mt-1 text-xs text-muted-foreground">
                  YOLO plus recovery, tracking, associations and rules.
                </p>
              </button>
            </div>
          </div>
        </div>
      </section>


      {/* ================================================================
          MAIN TEST PANEL
          ================================================================ */}

      <section className="grid gap-5 xl:grid-cols-[minmax(0,1.6fr)_minmax(340px,0.9fr)]">
        <form
          onSubmit={submit}
          className="space-y-5 rounded-xl border border-border bg-card p-5 shadow-sm"
        >
          {/* ------------------------------------------------------------
              General settings
              ------------------------------------------------------------ */}

          <div className="grid gap-4 sm:grid-cols-3">
            <label className="space-y-1">
              <span className="text-sm font-medium">
                Confidence threshold
              </span>

              <input
                type="number"
                min="0.01"
                max="1"
                step="0.01"
                value={confidence}
                onChange={(event) =>
                  setConfidence(
                    Number(
                      event.target.value,
                    ),
                  )
                }
                className="w-full rounded-lg border border-border bg-background px-3 py-2 text-sm"
              />
            </label>


            {testMode === "raw" && (
              <label className="space-y-1">
                <span className="text-sm font-medium">
                  Inference size
                </span>

                <select
                  value={imageSize}
                  onChange={(event) =>
                    setImageSize(
                      Number(
                        event.target.value,
                      ),
                    )
                  }
                  className="w-full rounded-lg border border-border bg-background px-3 py-2 text-sm"
                >
                  <option value={640}>
                    640
                  </option>

                  <option value={960}>
                    960
                  </option>

                  <option value={1280}>
                    1280
                  </option>
                </select>
              </label>
            )}


            {mediaMode === "video" && (
              <label className="space-y-1">
                <span className="text-sm font-medium">
                  Frame stride
                </span>

                <input
                  type="number"
                  min="1"
                  max="30"
                  value={frameStride}
                  onChange={(event) =>
                    setFrameStride(
                      Math.max(
                        1,
                        Number(
                          event.target.value,
                        ),
                      ),
                    )
                  }
                  className="w-full rounded-lg border border-border bg-background px-3 py-2 text-sm"
                />

                <p className="text-[11px] text-muted-foreground">
                  1 analyses every frame.
                </p>
              </label>
            )}
          </div>


          {/* ------------------------------------------------------------
              Pipeline settings
              ------------------------------------------------------------ */}

          {testMode === "pipeline" && (
            <div className="rounded-lg border border-blue-500/20 bg-blue-500/5 p-4">
              <div className="flex items-center gap-2">
                <input
                  type="checkbox"
                  checked={
                    enhanceVehicleDetails
                  }
                  onChange={(event) =>
                    setEnhanceVehicleDetails(
                      event.target.checked,
                    )
                  }
                />

                <p className="text-sm font-medium">
                  Enhanced vehicle detail analysis
                </p>
              </div>

              <div className="mt-4 grid gap-3 sm:grid-cols-3">
                <ThresholdInput
                  label="Car recovery"
                  value={
                    carRecoveryConfidence
                  }
                  onChange={
                    setCarRecoveryConfidence
                  }
                />

                <ThresholdInput
                  label="Smoke recovery"
                  value={
                    smokeDetailConfidence
                  }
                  onChange={
                    setSmokeDetailConfidence
                  }
                />

                <ThresholdInput
                  label="Plate recovery"
                  value={
                    plateDetailConfidence
                  }
                  onChange={
                    setPlateDetailConfidence
                  }
                />
              </div>


              {mediaMode === "video" && (
                <div className="mt-4 border-t border-border pt-4">
                  <p className="text-sm font-medium">
                    Temporal smoke evidence
                  </p>

                  <div className="mt-3 grid gap-3 sm:grid-cols-3">
                    <NumberInput
                      label="Window seconds"
                      value={
                        smokeWindowSeconds
                      }
                      min={0.5}
                      step={0.5}
                      onChange={
                        setSmokeWindowSeconds
                      }
                    />

                    <NumberInput
                      label="Candidate hits"
                      value={
                        smokeCandidateHits
                      }
                      min={2}
                      step={1}
                      onChange={
                        setSmokeCandidateHits
                      }
                    />

                    <NumberInput
                      label="Strong hits"
                      value={
                        smokeStrongHits
                      }
                      min={3}
                      step={1}
                      onChange={
                        setSmokeStrongHits
                      }
                    />
                  </div>
                </div>
              )}
            </div>
          )}


          {/* ------------------------------------------------------------
              File selection
              ------------------------------------------------------------ */}

          <label className="flex min-h-40 cursor-pointer flex-col items-center justify-center rounded-xl border border-dashed border-border bg-muted/15 p-6 text-center hover:bg-muted/25">
            <Upload className="size-7 text-muted-foreground" />

            <p className="mt-3 font-medium">
              {file
                ? file.name
                : mediaMode === "image"
                  ? "Choose an image"
                  : "Choose a video"}
            </p>

            <p className="mt-1 text-xs text-muted-foreground">
              {mediaMode === "image"
                ? "JPG, JPEG, PNG, BMP or WEBP"
                : "MP4, AVI, MOV, MKV, WEBM or M4V"}
            </p>

            <input
              type="file"
              accept={
                mediaMode === "image"
                  ? "image/jpeg,image/png,image/bmp,image/webp"
                  : "video/mp4,video/x-msvideo,video/quicktime,video/x-matroska,video/webm"
              }
              className="hidden"
              onChange={(event) =>
                chooseFile(
                  event.target.files?.[0]
                  ?? null,
                )
              }
            />
          </label>


          <button
            type="submit"
            disabled={
              !file || loading
            }
            className="inline-flex items-center gap-2 rounded-lg bg-primary px-4 py-2.5 text-sm font-medium text-primary-foreground disabled:cursor-not-allowed disabled:opacity-50"
          >
            {loading ? (
              <>
                <Loader2 className="size-4 animate-spin" />

                Analysing...
              </>
            ) : (
              <>
                <Play className="size-4" />

                Run{" "}
                {testMode === "raw"
                  ? "Raw Model Test"
                  : "Pipeline Test"}
              </>
            )}
          </button>


          {error && (
            <div className="rounded-lg border border-red-500/30 bg-red-500/10 p-3 text-sm text-red-300">
              {error}
            </div>
          )}


          {/* ------------------------------------------------------------
              Image preview
              ------------------------------------------------------------ */}

          {mediaMode === "image" &&
            preview && (
              <div className="relative overflow-hidden rounded-xl border border-border bg-black">
                <img
                  src={preview}
                  alt="AI test"
                  className="block h-auto w-full"
                />

                {hasResult && (
                  <DetectionOverlay
                    detections={
                      currentImageDetections
                    }
                    width={imageWidth}
                    height={imageHeight}
                  />
                )}
              </div>
            )}


          {/* ------------------------------------------------------------
              Video preview
              ------------------------------------------------------------ */}

          {mediaMode === "video" &&
            preview && (
              <div>
                <div className="relative overflow-hidden rounded-xl border border-border bg-black">
                  <video
                    ref={videoRef}
                    src={preview}
                    controls
                    className="block w-full"
                    onTimeUpdate={(event) =>
                      setCurrentVideoTime(
                        event.currentTarget
                          .currentTime,
                      )
                    }
                    onLoadedMetadata={(event) => {
                      event.currentTarget
                        .playbackRate =
                        playbackRate
                    }}
                  />

                  {activeVideoFrame && (
                    <DetectionOverlay
                      detections={
                        activeVideoFrame
                          .detections
                      }
                      width={
                        activeVideoFrame
                          .image_width
                      }
                      height={
                        activeVideoFrame
                          .image_height
                      }
                    />
                  )}
                </div>


                {videoSamples.length > 0 && (
                  <div className="mt-3 flex flex-wrap items-center justify-between gap-3 rounded-lg border border-border bg-muted/20 p-3">
                    <div className="flex gap-2">
                      <button
                        type="button"
                        onClick={() =>
                          seekSample(-1)
                        }
                        className="inline-flex items-center gap-1 rounded-md border border-border px-3 py-1.5 text-xs"
                      >
                        <ChevronLeft className="size-3" />

                        Previous AI frame
                      </button>

                      <button
                        type="button"
                        onClick={() =>
                          seekSample(1)
                        }
                        className="inline-flex items-center gap-1 rounded-md border border-border px-3 py-1.5 text-xs"
                      >
                        Next AI frame

                        <ChevronRight className="size-3" />
                      </button>
                    </div>


                    <div className="flex items-center gap-2">
                      <span className="text-xs text-muted-foreground">
                        Review speed
                      </span>

                      {[0.25, 0.5, 1].map(
                        (rate) => (
                          <button
                            type="button"
                            key={rate}
                            onClick={() =>
                              setReviewSpeed(
                                rate,
                              )
                            }
                            className={`rounded-md border px-2 py-1 text-xs ${
                              playbackRate ===
                              rate
                                ? "border-primary bg-primary text-primary-foreground"
                                : "border-border"
                            }`}
                          >
                            {rate}x
                          </button>
                        ),
                      )}
                    </div>


                    {activeVideoFrame && (
                      <div className="text-xs text-muted-foreground">
                        Source frame{" "}
                        {
                          activeVideoFrame
                            .frame_index
                        }
                        {" · "}
                        {
                          activeVideoFrame
                            .time_seconds
                        }
                        s
                        {" · "}
                        {
                          activeVideoFrame
                            .detections
                            .length
                        }{" "}
                        detections
                      </div>
                    )}
                  </div>
                )}
              </div>
            )}
        </form>


        {/* ==============================================================
            RIGHT SUMMARY COLUMN
            ============================================================== */}

        <div className="space-y-5">
          <section className="rounded-xl border border-border bg-card p-5 shadow-sm">
            <div className="flex items-center gap-2">
              <Activity className="size-4 text-primary" />

              <h2 className="font-semibold">
                Test Status
              </h2>
            </div>

            <div className="mt-4 rounded-lg border border-border bg-muted/20 p-3">
              <p className="text-xs uppercase tracking-wide text-muted-foreground">
                Active evaluation
              </p>

              <p className="mt-1 font-medium">
                {testMode === "raw"
                  ? "Raw YOLO Model"
                  : "Full AI Pipeline"}
              </p>

              <p className="mt-2 text-xs text-muted-foreground">
                {testMode === "raw"
                  ? "Results below are produced directly by mcc_detector_v1.pt."
                  : "Results include enhanced inference, tracking and rule logic."}
              </p>
            </div>


            {rawImageResult && (
              <div className="mt-4 grid grid-cols-2 gap-3">
                <Metric
                  title="Detections"
                  value={String(
                    rawImageResult
                      .detections_count,
                  )}
                />

                <Metric
                  title="Classes seen"
                  value={String(
                    new Set(
                      rawImageResult
                        .detections
                        .map(
                          (item) =>
                            item.class_name,
                        ),
                    ).size,
                  )}
                />

                <Metric
                  title="Image size"
                  value={`${rawImageResult.image_width}×${rawImageResult.image_height}`}
                />

                <Metric
                  title="YOLO size"
                  value={String(
                    rawImageResult
                      .image_size,
                  )}
                />
              </div>
            )}


            {rawVideoResult && (
              <div className="mt-4 grid grid-cols-2 gap-3">
                <Metric
                  title="Duration"
                  value={`${rawVideoResult.duration_seconds}s`}
                />

                <Metric
                  title="Sampled frames"
                  value={String(
                    rawVideoResult
                      .sampled_frames,
                  )}
                />

                <Metric
                  title="Raw boxes"
                  value={String(
                    rawVideoResult
                      .total_detections,
                  )}
                />

                <Metric
                  title="Coverage"
                  value={`${rawVideoResult.analysis_coverage_percent.toFixed(1)}%`}
                />
              </div>
            )}


            {pipelineImageResult && (
              <div className="mt-4 grid grid-cols-2 gap-3">
                <Metric
                  title="Detections"
                  value={String(
                    pipelineImageResult
                      .detections_count,
                  )}
                />

                <Metric
                  title="Associations"
                  value={String(
                    pipelineImageResult
                      .associations
                      .length,
                  )}
                />

                <Metric
                  title="Rules"
                  value={String(
                    pipelineImageResult
                      .rules.length,
                  )}
                />

                <Metric
                  title="Occurrences"
                  value={String(
                    pipelineImageResult
                      .occurrences
                      .length,
                  )}
                />
              </div>
            )}


            {pipelineVideoResult && (
              <div className="mt-4 grid grid-cols-2 gap-3">
                <Metric
                  title="Duration"
                  value={`${pipelineVideoResult.duration_seconds}s`}
                />

                <Metric
                  title="Tracks"
                  value={String(
                    pipelineVideoResult
                      .tracks.length,
                  )}
                />

                <Metric
                  title="Sampled frames"
                  value={String(
                    pipelineVideoResult
                      .sampled_frames,
                  )}
                />

                <Metric
                  title="Occurrences"
                  value={String(
                    pipelineVideoResult
                      .occurrences
                      .length,
                  )}
                />
              </div>
            )}


            {!hasResult && (
              <p className="mt-4 text-sm text-muted-foreground">
                Choose media and run a test to see model results.
              </p>
            )}
          </section>


          {/* ------------------------------------------------------------
              Current video frame
              ------------------------------------------------------------ */}

          {activeVideoFrame && (
            <section className="rounded-xl border border-border bg-card p-5 shadow-sm">
              <h2 className="font-semibold">
                Current AI Frame
              </h2>

              <p className="mt-1 text-xs text-muted-foreground">
                Nearest analysed frame to the current playback position.
              </p>

              <div className="mt-4">
                <DetectionList
                  detections={
                    activeVideoFrame
                      .detections
                  }
                />
              </div>
            </section>
          )}
        </div>
      </section>


      {/* ================================================================
          RAW MODEL EVALUATION
          ================================================================ */}

      {testMode === "raw" &&
        rawImageResult && (
          <section className="rounded-xl border border-border bg-card p-5 shadow-sm">
            <div className="flex items-center gap-2">
              <ScanLine className="size-4 text-emerald-400" />

              <h2 className="font-semibold">
                Raw Model Class Results
              </h2>
            </div>

            <p className="mt-1 text-xs text-muted-foreground">
              These are direct YOLO results only. Zero means the model did
              not detect that class in this image at the selected threshold.
            </p>

            <div className="mt-4 overflow-x-auto">
              <table className="w-full min-w-[650px] text-left text-sm">
                <thead>
                  <tr className="border-b border-border text-xs uppercase tracking-wide text-muted-foreground">
                    <th className="px-3 py-2">
                      Class
                    </th>

                    <th className="px-3 py-2">
                      Detections
                    </th>

                    <th className="px-3 py-2">
                      Mean confidence
                    </th>

                    <th className="px-3 py-2">
                      Best confidence
                    </th>
                  </tr>
                </thead>

                <tbody>
                  {rawImageClassSummary.map(
                    (item) => (
                      <tr
                        key={item.className}
                        className="border-b border-border/60"
                      >
                        <td className="px-3 py-2 font-medium">
                          {item.className}
                        </td>

                        <td className="px-3 py-2">
                          {item.detections}
                        </td>

                        <td className="px-3 py-2">
                          {item.detections > 0
                            ? percent(
                                item.mean,
                              )
                            : "—"}
                        </td>

                        <td className="px-3 py-2">
                          {item.detections > 0
                            ? percent(
                                item.best,
                              )
                            : "—"}
                        </td>
                      </tr>
                    ),
                  )}
                </tbody>
              </table>
            </div>
          </section>
        )}


      {testMode === "raw" &&
        rawVideoResult && (
          <section className="rounded-xl border border-border bg-card p-5 shadow-sm">
            <div className="flex items-center gap-2">
              <ScanLine className="size-4 text-emerald-400" />

              <h2 className="font-semibold">
                Raw Video Model Evaluation
              </h2>
            </div>

            <p className="mt-1 max-w-4xl text-xs text-muted-foreground">
              This table measures what the YOLO model itself returned.
              Frame presence is the percentage of sampled frames containing
              at least one detection of that class. It is not ground-truth
              recall; we will compare it with what is visibly present in the
              test video.
            </p>


            <div className="mt-4 overflow-x-auto">
              <table className="w-full min-w-[850px] text-left text-sm">
                <thead>
                  <tr className="border-b border-border text-xs uppercase tracking-wide text-muted-foreground">
                    <th className="px-3 py-2">
                      Class
                    </th>

                    <th className="px-3 py-2">
                      Boxes
                    </th>

                    <th className="px-3 py-2">
                      Frames detected
                    </th>

                    <th className="px-3 py-2">
                      Frame presence
                    </th>

                    <th className="px-3 py-2">
                      Mean confidence
                    </th>

                    <th className="px-3 py-2">
                      Best confidence
                    </th>
                  </tr>
                </thead>

                <tbody>
                  {rawVideoResult
                    .class_summary
                    .map((item) => (
                      <tr
                        key={
                          item.class_name
                        }
                        className={`border-b border-border/60 ${
                          item.frames_detected ===
                          0
                            ? "text-muted-foreground"
                            : ""
                        }`}
                      >
                        <td className="px-3 py-2 font-medium">
                          {
                            item.class_name
                          }
                        </td>

                        <td className="px-3 py-2">
                          {
                            item.detections
                          }
                        </td>

                        <td className="px-3 py-2">
                          {
                            item.frames_detected
                          }
                          {" / "}
                          {
                            rawVideoResult
                              .sampled_frames
                          }
                        </td>

                        <td className="px-3 py-2">
                          {
                            item.frame_presence_percent
                          }
                          %
                        </td>

                        <td className="px-3 py-2">
                          {item.detections >
                          0
                            ? percent(
                                item.mean_confidence,
                              )
                            : "—"}
                        </td>

                        <td className="px-3 py-2">
                          {item.detections >
                          0
                            ? percent(
                                item.max_confidence,
                              )
                            : "—"}
                        </td>
                      </tr>
                    ))}
                </tbody>
              </table>
            </div>


            <div className="mt-4 rounded-lg border border-border bg-muted/20 p-3 text-xs text-muted-foreground">
              Requested stride:{" "}
              {
                rawVideoResult
                  .requested_frame_stride
              }
              {" · "}
              Effective stride:{" "}
              {
                rawVideoResult
                  .effective_frame_stride
              }
              {" · "}
              YOLO size:{" "}
              {
                rawVideoResult
                  .image_size
              }
              {" · "}
              Confidence:{" "}
              {percent(
                rawVideoResult
                  .confidence_threshold,
              )}
            </div>
          </section>
        )}


      {/* ================================================================
          PIPELINE RESULTS
          ================================================================ */}

      {testMode === "pipeline" &&
        (
          pipelineImageResult ||
          pipelineVideoResult
        ) && (
          <section className="grid gap-5 xl:grid-cols-2">
            <section className="rounded-xl border border-border bg-card p-5 shadow-sm">
              <h2 className="font-semibold">
                Occurrences
              </h2>

              <p className="mt-1 text-xs text-muted-foreground">
                Event-level interpretations created from detections,
                tracking and associations.
              </p>

              <div className="mt-4 space-y-3">
                {(
                  pipelineImageResult
                    ?.occurrences
                  ??
                  pipelineVideoResult
                    ?.occurrences
                  ??
                  []
                ).length === 0 ? (
                  <p className="text-sm text-muted-foreground">
                    No occurrence was produced.
                  </p>
                ) : (
                  (
                    pipelineImageResult
                      ?.occurrences
                    ??
                    pipelineVideoResult
                      ?.occurrences
                    ??
                    []
                  ).map(
                    (occurrence) => (
                      <OccurrenceCard
                        key={
                          occurrence
                            .occurrence_id
                        }
                        occurrence={
                          occurrence
                        }
                      />
                    ),
                  )
                )}
              </div>
            </section>


            <section className="rounded-xl border border-border bg-card p-5 shadow-sm">
              <h2 className="font-semibold">
                Rule Engine
              </h2>

              <p className="mt-1 text-xs text-muted-foreground">
                Rule results are separate from raw model performance.
              </p>

              <div className="mt-4 space-y-3">
                {(
                  pipelineImageResult
                    ?.rules
                  ??
                  pipelineVideoResult
                    ?.rules
                  ??
                  []
                ).length === 0 ? (
                  <p className="text-sm text-muted-foreground">
                    No rules were triggered.
                  </p>
                ) : (
                  (
                    pipelineImageResult
                      ?.rules
                    ??
                    pipelineVideoResult
                      ?.rules
                    ??
                    []
                  ).map(
                    (rule) => (
                      <RuleCard
                        key={rule.rule}
                        rule={rule}
                      />
                    ),
                  )
                )}
              </div>
            </section>
          </section>
        )}


      {/* ================================================================
          PIPELINE TRACKING
          ================================================================ */}

      {testMode === "pipeline" &&
        pipelineVideoResult &&
        pipelineVideoResult.tracks.length >
          0 && (
          <section className="rounded-xl border border-border bg-card p-5 shadow-sm">
            <h2 className="font-semibold">
              Tracked Objects
            </h2>

            <p className="mt-1 text-xs text-muted-foreground">
              Tracking belongs to the full pipeline and is intentionally
              excluded from Raw Model mode.
            </p>

            <div className="mt-4 overflow-x-auto">
              <table className="w-full min-w-[750px] text-left text-sm">
                <thead>
                  <tr className="border-b border-border text-xs uppercase tracking-wide text-muted-foreground">
                    <th className="px-3 py-2">
                      Track
                    </th>

                    <th className="px-3 py-2">
                      Class
                    </th>

                    <th className="px-3 py-2">
                      Direct hits
                    </th>

                    <th className="px-3 py-2">
                      Held frames
                    </th>

                    <th className="px-3 py-2">
                      Best confidence
                    </th>
                  </tr>
                </thead>

                <tbody>
                  {pipelineVideoResult.tracks.map(
                    (track) => (
                      <tr
                        key={track.track_id}
                        className="border-b border-border/60"
                      >
                        <td className="px-3 py-2 font-mono text-xs">
                          {track.track_id}
                        </td>

                        <td className="px-3 py-2">
                          {track.class_name}
                        </td>

                        <td className="px-3 py-2">
                          {track.hits}
                        </td>

                        <td className="px-3 py-2">
                          {
                            track.predicted_frames
                            ?? 0
                          }
                        </td>

                        <td className="px-3 py-2">
                          {percent(
                            track.max_confidence,
                          )}
                        </td>
                      </tr>
                    ),
                  )}
                </tbody>
              </table>
            </div>
          </section>
        )}
    </div>
  )
}


/* ==========================================================================
   INPUT COMPONENTS
   ========================================================================== */

function ThresholdInput({
  label: inputLabel,
  value,
  onChange,
}: {
  label: string
  value: number
  onChange: (value: number) => void
}) {
  return (
    <label className="space-y-1">
      <span className="text-xs text-muted-foreground">
        {inputLabel}
      </span>

      <input
        type="number"
        min="0.01"
        max="1"
        step="0.01"
        value={value}
        onChange={(event) =>
          onChange(
            Number(
              event.target.value,
            ),
          )
        }
        className="w-full rounded-lg border border-border bg-background px-3 py-2 text-sm"
      />
    </label>
  )
}


function NumberInput({
  label: inputLabel,
  value,
  min,
  step,
  onChange,
}: {
  label: string
  value: number
  min: number
  step: number
  onChange: (value: number) => void
}) {
  return (
    <label className="space-y-1">
      <span className="text-xs text-muted-foreground">
        {inputLabel}
      </span>

      <input
        type="number"
        min={min}
        step={step}
        value={value}
        onChange={(event) =>
          onChange(
            Number(
              event.target.value,
            ),
          )
        }
        className="w-full rounded-lg border border-border bg-background px-3 py-2 text-sm"
      />
    </label>
  )
}