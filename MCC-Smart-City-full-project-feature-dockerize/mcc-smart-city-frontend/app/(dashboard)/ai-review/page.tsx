"use client"

import { useCallback, useEffect, useMemo, useState } from "react"
import { CheckCircle2, LoaderCircle, RefreshCw, ShieldAlert, XCircle } from "lucide-react"
import { useAuth } from "@/components/auth/auth-provider"
import { apiFetch, apiObjectUrl } from "@/lib/api"
import type { AIDetection, AIDetectionListResponse, Department, IncidentPriority } from "@/lib/types"

export default function AIReviewPage() {
  const { user } = useAuth()
  const [items, setItems] = useState<AIDetection[]>([])
  const [departments, setDepartments] = useState<Department[]>([])
  const [selected, setSelected] = useState<AIDetection | null>(null)
  const [snapshotUrl, setSnapshotUrl] = useState("")
  const [clipUrl, setClipUrl] = useState("")
  const [notes, setNotes] = useState("")
  const [departmentId, setDepartmentId] = useState("")
  const [priority, setPriority] = useState<IncidentPriority | "">("")
  const [loading, setLoading] = useState(true)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState("")
  const permissions = useMemo(() => new Set(user?.role?.permissions?.map(p => p.code) ?? []), [user])
  const canReview = Boolean(user?.is_superuser || permissions.has("ai_detections.review"))
  const canPromote = Boolean(user?.is_superuser || permissions.has("ai_detections.promote"))
  const canViewDepartments = Boolean(user?.is_superuser || permissions.has("departments.view"))

  const load = useCallback(async () => {
    setLoading(true); setError("")
    try {
      const [detections, departmentRows] = await Promise.all([
        apiFetch<AIDetectionListResponse>("/ai-detections?review_status=unreviewed&is_test=false&page_size=100"),
        canViewDepartments ? apiFetch<Department[]>("/departments") : Promise.resolve([]),
      ])
      setItems(detections.items.filter((item) => item.incident_id === null)); setDepartments(departmentRows.filter(d => d.is_active))
    } catch (e) { setError(e instanceof Error ? e.message : "Unable to load AI review queue.") }
    finally { setLoading(false) }
  }, [canViewDepartments])

  useEffect(() => { void load() }, [load])
  useEffect(() => {
    if (!selected?.snapshot_path) { setSnapshotUrl(""); setClipUrl(""); return }
    let snapshot = ""; let clip = ""; let active = true
    void Promise.all([
      apiObjectUrl(`/ai-detections/${selected.id}/staged-evidence/snapshot`),
      apiObjectUrl(`/ai-detections/${selected.id}/staged-evidence/clip`),
    ]).then(([snapshotValue, clipValue]) => {
      snapshot = snapshotValue; clip = clipValue
      if (active) { setSnapshotUrl(snapshotValue); setClipUrl(clipValue) }
      else { URL.revokeObjectURL(snapshotValue); URL.revokeObjectURL(clipValue) }
    }).catch(e => setError(e instanceof Error ? e.message : "Unable to preview evidence."))
    return () => { active = false; if (snapshot) URL.revokeObjectURL(snapshot); if (clip) URL.revokeObjectURL(clip) }
  }, [selected])

  async function decide(decision: "confirmed" | "rejected") {
    if (!selected || !notes.trim()) { setError("Enter review notes before deciding."); return }
    setBusy(true); setError("")
    try {
      const updated = await apiFetch<AIDetection>(`/ai-detections/${selected.id}/review`, {
        method: "PATCH",
        body: JSON.stringify({ review_status: decision, notes: notes.trim(), department_id: departmentId ? Number(departmentId) : null, priority: priority || null }),
      })
      setItems(current => current.filter(item => item.id !== updated.id)); setSelected(null); setNotes("")
      if (updated.incident_id) window.location.href = `/incidents?incident=${updated.incident_id}`
    } catch (e) { setError(e instanceof Error ? e.message : "Review decision failed.") }
    finally { setBusy(false) }
  }

  return <div className="space-y-6">
    <div className="flex flex-wrap items-end justify-between gap-3"><div><p className="text-sm font-medium text-primary">Operations</p><h2 className="text-2xl font-semibold">AI review queue</h2><p className="text-sm text-muted-foreground">Human verification gate before incidents, evidence and alerts enter MCC operations.</p></div><button onClick={() => void load()} className="inline-flex h-10 items-center gap-2 rounded-md border px-4 text-sm"><RefreshCw className="size-4"/>Refresh</button></div>
    {error && <div className="rounded-lg border border-destructive/30 bg-destructive/10 p-3 text-sm text-destructive">{error}</div>}
    {!canReview && <div className="rounded-lg border p-4"><ShieldAlert className="mb-2 size-5"/>Your role cannot review AI detections.</div>}
    <div className="grid gap-4 lg:grid-cols-[360px_1fr]">
      <div className="space-y-2">{loading ? <LoaderCircle className="animate-spin"/> : items.length === 0 ? <div className="rounded-lg border bg-card p-5 text-sm text-muted-foreground">No detections are waiting for review.</div> : items.map(item => <button key={item.id} onClick={() => setSelected(item)} className={`w-full rounded-lg border p-4 text-left ${selected?.id === item.id ? "border-primary bg-primary/5" : "bg-card"}`}><div className="flex justify-between gap-2"><strong>{item.detection_type.replaceAll("_", " ")}</strong><span>{Math.round(item.confidence * 100)}%</span></div><p className="mt-1 text-sm text-muted-foreground">{item.camera_identifier || "Unknown camera"} · {new Date(item.detected_at).toLocaleString()}</p>{item.is_test && <span className="mt-2 inline-block rounded bg-amber-500/15 px-2 py-1 text-xs text-amber-600">TEST — promotion blocked</span>}</button>)}</div>
      <div className="rounded-lg border bg-card p-5">{!selected ? <p className="text-sm text-muted-foreground">Select a detection to inspect its evidence and qualification details.</p> : <div className="space-y-4"><div><h3 className="text-lg font-semibold">{selected.detection_type.replaceAll("_", " ")}</h3><p className="text-sm text-muted-foreground">{selected.location_name || "Location not assigned"}</p></div><div className="grid gap-3 xl:grid-cols-2">{snapshotUrl ? <img src={snapshotUrl} alt="AI evidence snapshot" className="h-72 w-full rounded-lg bg-black object-contain"/> : <div className="rounded-lg bg-muted p-8 text-center text-sm">Snapshot unavailable</div>}{clipUrl ? <video src={clipUrl} controls preload="metadata" className="h-72 w-full rounded-lg bg-black object-contain">Evidence clip playback is unsupported.</video> : <div className="rounded-lg bg-muted p-8 text-center text-sm">Clip unavailable</div>}</div><div className="grid gap-3 sm:grid-cols-2"><select value={departmentId} onChange={e => setDepartmentId(e.target.value)} className="h-10 rounded-md border bg-background px-3"><option value="">No department yet</option>{departments.map(d => <option key={d.id} value={d.id}>{d.name}</option>)}</select><select value={priority} onChange={e => setPriority(e.target.value as IncidentPriority | "")} className="h-10 rounded-md border bg-background px-3"><option value="">Rule-based priority</option>{["low","medium","high","critical"].map(p => <option key={p} value={p}>{p}</option>)}</select></div><textarea value={notes} onChange={e => setNotes(e.target.value)} placeholder="Required review reason and observations" className="min-h-24 w-full rounded-md border bg-background p-3 text-sm"/><div className="flex flex-wrap gap-2"><button disabled={busy || !canReview} onClick={() => void decide("rejected")} className="inline-flex h-10 items-center gap-2 rounded-md border border-destructive px-4 text-sm text-destructive"><XCircle className="size-4"/>Reject</button><button disabled={busy || !canPromote || selected.is_test} onClick={() => void decide("confirmed")} className="inline-flex h-10 items-center gap-2 rounded-md bg-primary px-4 text-sm text-primary-foreground disabled:opacity-50"><CheckCircle2 className="size-4"/>Approve and create incident</button></div></div>}</div>
    </div>
  </div>
}
