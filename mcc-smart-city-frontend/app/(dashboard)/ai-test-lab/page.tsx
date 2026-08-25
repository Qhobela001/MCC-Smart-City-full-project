"use client"

import { FormEvent, useMemo, useState } from "react"
import {
  BrainCircuit,
  CheckCircle2,
  FileVideo,
  ImageIcon,
  Loader2,
  ShieldAlert,
  Upload,
} from "lucide-react"

import { apiFetch } from "@/lib/api"


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
}

type RuleAssessment = {
  rule: string
  title: string
  status: string
  confidence: number
  reasons: string[]
  evidence_classes: string[]
  incident_type?: string | null
}

type ImageDetectionResponse = {
  filename: string
  image_width: number
  image_height: number
  detections_count: number
  detections: Detection[]
  rules: RuleAssessment[]
}

type VideoClassSummary = {
  class_name: string
  max_confidence: number
  detections: number
}

type VideoDetectionResponse = {
  filename: string
  duration_seconds: number
  total_frames: number
  sampled_frames: number
  frame_stride: number
  class_summary: VideoClassSummary[]
  rules: RuleAssessment[]
}

function confidencePercent(value: number) {
  return `${(value * 100).toFixed(1)}%`
}

function RuleCard({ rule }: { rule: RuleAssessment }) {
  const candidate = rule.status === "candidate"

  return (
    <div className="rounded-lg border border-border bg-muted/25 p-4">
      <div className="flex items-start gap-3">
        <div
          className={`mt-0.5 rounded-full p-1.5 ${
            candidate
              ? "bg-amber-500/15 text-amber-400"
              : "bg-blue-500/15 text-blue-400"
          }`}
        >
          {candidate ? (
            <ShieldAlert className="size-4" />
          ) : (
            <CheckCircle2 className="size-4" />
          )}
        </div>
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-2">
            <p className="font-medium">{rule.title}</p>
            <span className="rounded-full border border-border px-2 py-0.5 text-[11px] uppercase tracking-wide text-muted-foreground">
              {rule.status}
            </span>
            <span className="text-xs text-muted-foreground">
              {confidencePercent(rule.confidence)}
            </span>
          </div>
          {rule.incident_type && (
            <p className="mt-1 text-xs text-primary">
              Incident mapping: {rule.incident_type.replaceAll("_", " ")}
            </p>
          )}
          <ul className="mt-2 space-y-1 text-sm text-muted-foreground">
            {rule.reasons.map((reason) => (
              <li key={reason}>• {reason}</li>
            ))}
          </ul>
          <p className="mt-2 text-xs text-muted-foreground">
            Evidence: {rule.evidence_classes.join(", ") || "none"}
          </p>
        </div>
      </div>
    </div>
  )
}

export default function AITestLabPage() {
  const [mode, setMode] = useState<"image" | "video">("image")
  const [file, setFile] = useState<File | null>(null)
  const [preview, setPreview] = useState<string | null>(null)
  const [confidence, setConfidence] = useState(0.25)
  const [frameStride, setFrameStride] = useState(5)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [imageResult, setImageResult] = useState<ImageDetectionResponse | null>(null)
  const [videoResult, setVideoResult] = useState<VideoDetectionResponse | null>(null)

  const detectionsByClass = useMemo(() => {
    if (!imageResult) return []
    const map = new Map<string, Detection[]>()
    for (const detection of imageResult.detections) {
      map.set(detection.class_name, [
        ...(map.get(detection.class_name) || []),
        detection,
      ])
    }
    return [...map.entries()]
  }, [imageResult])

  function chooseFile(nextFile: File | null) {
    setFile(nextFile)
    setImageResult(null)
    setVideoResult(null)
    setError(null)

    if (preview) URL.revokeObjectURL(preview)
    setPreview(nextFile ? URL.createObjectURL(nextFile) : null)
  }

  async function submit(event: FormEvent) {
    event.preventDefault()
    if (!file) return

    setLoading(true)
    setError(null)
    setImageResult(null)
    setVideoResult(null)

    const body = new FormData()
    body.append("file", file)

    try {
      if (mode === "image") {
        const response = await apiFetch<ImageDetectionResponse>(
          `/ai-detection/detect?confidence=${confidence}`,
          { method: "POST", body },
        )
        setImageResult(response)
      } else {
        const response = await apiFetch<VideoDetectionResponse>(
          `/ai-detection/detect-video?confidence=${confidence}&frame_stride=${frameStride}`,
          { method: "POST", body },
        )
        setVideoResult(response)
      }
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "AI test failed.")
    } finally {
      setLoading(false)
    }
  }

  const rules = imageResult?.rules ?? videoResult?.rules ?? []

  return (
    <div className="space-y-5">
      <section className="rounded-xl border border-border bg-card p-5 shadow-sm">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
          <div>
            <div className="flex items-center gap-2">
              <BrainCircuit className="size-5 text-primary" />
              <h1 className="text-xl font-semibold">AI Test Lab</h1>
            </div>
            <p className="mt-2 max-w-3xl text-sm text-muted-foreground">
              Validate the MCC YOLO detector and provisional event rules before connecting the production camera pipeline or Jetson Orin Nano.
            </p>
          </div>
          <div className="rounded-lg border border-border bg-muted/35 px-3 py-2 text-xs text-muted-foreground">
            Test-lab results are observations only. They do not create enforcement incidents.
          </div>
        </div>

        <div className="mt-5 flex gap-2">
          <button
            type="button"
            onClick={() => {
              setMode("image")
              chooseFile(null)
            }}
            className={`inline-flex items-center gap-2 rounded-md border px-3 py-2 text-sm ${
              mode === "image" ? "border-primary bg-primary/10 text-primary" : "border-border"
            }`}
          >
            <ImageIcon className="size-4" /> Image test
          </button>
          <button
            type="button"
            onClick={() => {
              setMode("video")
              chooseFile(null)
            }}
            className={`inline-flex items-center gap-2 rounded-md border px-3 py-2 text-sm ${
              mode === "video" ? "border-primary bg-primary/10 text-primary" : "border-border"
            }`}
          >
            <FileVideo className="size-4" /> Video test
          </button>
        </div>
      </section>

      <section className="grid gap-5 xl:grid-cols-[minmax(0,1.5fr)_minmax(360px,1fr)]">
        <div className="rounded-xl border border-border bg-card p-5 shadow-sm">
          <form onSubmit={submit} className="space-y-4">
            <div className="grid gap-4 md:grid-cols-2">
              <label className="space-y-2 text-sm">
                <span className="font-medium">Confidence threshold</span>
                <input
                  type="number"
                  min={0.01}
                  max={1}
                  step={0.01}
                  value={confidence}
                  onChange={(event) => setConfidence(Number(event.target.value))}
                  className="h-10 w-full rounded-md border border-input bg-background px-3"
                />
              </label>

              {mode === "video" && (
                <label className="space-y-2 text-sm">
                  <span className="font-medium">Frame stride</span>
                  <input
                    type="number"
                    min={1}
                    max={30}
                    value={frameStride}
                    onChange={(event) => setFrameStride(Number(event.target.value))}
                    className="h-10 w-full rounded-md border border-input bg-background px-3"
                  />
                </label>
              )}
            </div>

            <label className="flex cursor-pointer flex-col items-center justify-center rounded-xl border border-dashed border-border bg-muted/20 px-6 py-10 text-center transition hover:bg-muted/35">
              <Upload className="size-8 text-primary" />
              <span className="mt-3 font-medium">
                {file ? file.name : `Choose ${mode === "image" ? "an image" : "a video"}`}
              </span>
              <span className="mt-1 text-xs text-muted-foreground">
                {mode === "image" ? "JPG, PNG, BMP or WEBP" : "MP4, AVI, MOV, MKV, WEBM or M4V"}
              </span>
              <input
                type="file"
                className="hidden"
                accept={mode === "image" ? "image/*" : "video/*"}
                onChange={(event) => chooseFile(event.target.files?.[0] || null)}
              />
            </label>

            {error && (
              <div className="rounded-lg border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-300">
                {error}
              </div>
            )}

            <button
              type="submit"
              disabled={!file || loading}
              className="inline-flex items-center gap-2 rounded-md bg-primary px-4 py-2.5 text-sm font-semibold text-primary-foreground disabled:opacity-50"
            >
              {loading ? <Loader2 className="size-4 animate-spin" /> : <BrainCircuit className="size-4" />}
              {loading ? "Running model..." : "Run AI test"}
            </button>
          </form>

          {preview && mode === "image" && (
            <div className="mt-5 overflow-hidden rounded-xl border border-border bg-black">
              <div className="relative inline-block w-full">
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img src={preview} alt="AI test" className="block h-auto w-full" />
                {imageResult?.detections.map((detection, index) => {
                  const left = (detection.bbox.x1 / imageResult.image_width) * 100
                  const top = (detection.bbox.y1 / imageResult.image_height) * 100
                  const width = (detection.bbox.width / imageResult.image_width) * 100
                  const height = (detection.bbox.height / imageResult.image_height) * 100
                  return (
                    <div
                      key={`${detection.class_name}-${index}`}
                      className="pointer-events-none absolute border-2 border-primary"
                      style={{ left: `${left}%`, top: `${top}%`, width: `${width}%`, height: `${height}%` }}
                    >
                      <span className="absolute -top-6 left-0 whitespace-nowrap rounded bg-primary px-1.5 py-0.5 text-[11px] font-semibold text-primary-foreground">
                        {detection.class_name} {confidencePercent(detection.confidence)}
                      </span>
                    </div>
                  )
                })}
              </div>
            </div>
          )}

          {preview && mode === "video" && (
            <video src={preview} controls className="mt-5 w-full rounded-xl border border-border bg-black" />
          )}
        </div>

        <div className="space-y-5">
          <section className="rounded-xl border border-border bg-card p-5 shadow-sm">
            <h2 className="font-semibold">Model output</h2>
            {!imageResult && !videoResult ? (
              <p className="mt-3 text-sm text-muted-foreground">Run a test to see detections.</p>
            ) : imageResult ? (
              <div className="mt-4 space-y-3">
                <div className="grid grid-cols-2 gap-3">
                  <Metric label="Detections" value={String(imageResult.detections_count)} />
                  <Metric label="Classes seen" value={String(detectionsByClass.length)} />
                </div>
                {detectionsByClass.map(([name, items]) => (
                  <div key={name} className="flex items-center justify-between rounded-lg bg-muted/35 px-3 py-2 text-sm">
                    <span>{name}</span>
                    <span className="text-muted-foreground">
                      {items.length} · best {confidencePercent(Math.max(...items.map((item) => item.confidence)))}
                    </span>
                  </div>
                ))}
              </div>
            ) : (
              <div className="mt-4 space-y-3">
                <div className="grid grid-cols-2 gap-3">
                  <Metric label="Duration" value={`${videoResult!.duration_seconds}s`} />
                  <Metric label="Sampled frames" value={String(videoResult!.sampled_frames)} />
                </div>
                {videoResult!.class_summary.map((item) => (
                  <div key={item.class_name} className="flex items-center justify-between rounded-lg bg-muted/35 px-3 py-2 text-sm">
                    <span>{item.class_name}</span>
                    <span className="text-muted-foreground">
                      {item.detections} hits · best {confidencePercent(item.max_confidence)}
                    </span>
                  </div>
                ))}
              </div>
            )}
          </section>

          <section className="rounded-xl border border-border bg-card p-5 shadow-sm">
            <h2 className="font-semibold">Rule engine</h2>
            <p className="mt-1 text-xs text-muted-foreground">
              Candidate rules require operational validation before automatic enforcement.
            </p>
            <div className="mt-4 space-y-3">
              {rules.length === 0 ? (
                <p className="text-sm text-muted-foreground">No rule conditions were met.</p>
              ) : (
                rules.map((rule) => <RuleCard key={rule.rule} rule={rule} />)
              )}
            </div>
          </section>
        </div>
      </section>
    </div>
  )
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg bg-muted/35 p-3">
      <p className="text-xs uppercase tracking-wide text-muted-foreground">{label}</p>
      <p className="mt-1 text-lg font-semibold">{value}</p>
    </div>
  )
}
