"use client"

import {
  FormEvent,
  ReactNode,
  useCallback,
  useEffect,
  useMemo,
  useState,
} from "react"
import {
  AlertTriangle,
  ArrowRight,
  Building2,
  CalendarClock,
  CheckCircle2,
  ChevronLeft,
  ChevronRight,
  CircleDot,
  Download,
  Eye,
  FileImage,
  FileText,
  Filter,
  LoaderCircle,
  MapPin,
  Paperclip,
  Plus,
  RefreshCw,
  Search,
  ShieldCheck,
  Trash2,
  Upload,
  UserRoundCheck,
  X,
} from "lucide-react"

import { useAuth } from "@/components/auth/auth-provider"
import { apiDownload, apiFetch } from "@/lib/api"
import type {
  Department,
  Evidence,
  Incident,
  IncidentActivity,
  IncidentListResponse,
  IncidentPriority,
  IncidentSource,
  IncidentStatus,
  IncidentType,
  User,
} from "@/lib/types"
import { cn } from "@/lib/utils"

const INCIDENT_TYPES: Array<{ value: IncidentType; label: string }> = [
  { value: "illegal_dumping", label: "Illegal dumping" },
  { value: "skip_overflow", label: "Waste skip overflow" },
  { value: "noise_pollution", label: "Noise pollution" },
  { value: "unauthorized_vending", label: "Unauthorized vending" },
  {
    value: "street_cleaner_non_compliance",
    label: "Street cleaner non-compliance",
  },
  { value: "public_urination", label: "Public urination" },
  {
    value: "vehicle_smoke_emission",
    label: "Vehicle smoke emission",
  },
  { value: "road_damage", label: "Road damage" },
  { value: "pothole", label: "Pothole" },
  { value: "other", label: "Other" },
]

const PRIORITIES: IncidentPriority[] = [
  "low",
  "medium",
  "high",
  "critical",
]

const STATUSES: IncidentStatus[] = [
  "new",
  "under_review",
  "confirmed",
  "assigned",
  "in_progress",
  "resolved",
  "dismissed",
]

const STATUS_TRANSITIONS: Record<IncidentStatus, IncidentStatus[]> = {
  new: ["under_review", "confirmed", "assigned", "dismissed"],
  under_review: ["confirmed", "assigned", "dismissed"],
  confirmed: ["assigned", "in_progress", "dismissed"],
  assigned: ["in_progress", "resolved", "dismissed"],
  in_progress: ["resolved", "dismissed"],
  resolved: [],
  dismissed: [],
}

type IncidentForm = {
  incident_type: IncidentType
  title: string
  description: string
  priority: IncidentPriority
  source: IncidentSource
  department_id: string
  assigned_user_id: string
  location_name: string
  latitude: string
  longitude: string
}

const emptyIncidentForm: IncidentForm = {
  incident_type: "illegal_dumping",
  title: "",
  description: "",
  priority: "medium",
  source: "manual",
  department_id: "",
  assigned_user_id: "",
  location_name: "",
  latitude: "",
  longitude: "",
}

type EvidenceForm = {
  file: File | null
  description: string
  captured_at: string
  latitude: string
  longitude: string
  is_anonymized: boolean
  is_enforcement_evidence: boolean
}

const emptyEvidenceForm: EvidenceForm = {
  file: null,
  description: "",
  captured_at: "",
  latitude: "",
  longitude: "",
  is_anonymized: false,
  is_enforcement_evidence: true,
}

export default function IncidentsPage() {
  const { user } = useAuth()

  const [incidents, setIncidents] = useState<Incident[]>([])
  const [departments, setDepartments] = useState<Department[]>([])
  const [users, setUsers] = useState<User[]>([])

  const [selectedIncident, setSelectedIncident] =
      useState<Incident | null>(null)
  const [timeline, setTimeline] = useState<IncidentActivity[]>([])
  const [evidence, setEvidence] = useState<Evidence[]>([])

  const [createOpen, setCreateOpen] = useState(false)
  const [assignOpen, setAssignOpen] = useState(false)
  const [evidenceOpen, setEvidenceOpen] = useState(false)
  const [statusOpen, setStatusOpen] = useState(false)

  const [form, setForm] = useState<IncidentForm>(emptyIncidentForm)
  const [evidenceForm, setEvidenceForm] =
      useState<EvidenceForm>(emptyEvidenceForm)
  const [assignmentUserId, setAssignmentUserId] = useState("")
  const [assignmentDepartmentId, setAssignmentDepartmentId] =
      useState("")
  const [assignmentNotes, setAssignmentNotes] = useState("")
  const [nextStatus, setNextStatus] = useState<IncidentStatus | "">("")
  const [statusNotes, setStatusNotes] = useState("")
  const [resolutionNotes, setResolutionNotes] = useState("")

  const [search, setSearch] = useState("")
  const [statusFilter, setStatusFilter] = useState("")
  const [priorityFilter, setPriorityFilter] = useState("")
  const [typeFilter, setTypeFilter] = useState("")
  const [page, setPage] = useState(1)
  const [pages, setPages] = useState(0)
  const [total, setTotal] = useState(0)

  const [loading, setLoading] = useState(true)
  const [detailLoading, setDetailLoading] = useState(false)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState("")
  const [modalError, setModalError] = useState("")

  const permissions = useMemo(
      () => new Set(user?.role?.permissions?.map((item) => item.code) ?? []),
      [user],
  )

  const allowed = useCallback(
      (permission: string) =>
          Boolean(user?.is_superuser || permissions.has(permission)),
      [permissions, user?.is_superuser],
  )

  const loadReferenceData = useCallback(async () => {
    const requests: Promise<unknown>[] = [
      apiFetch<Department[]>("/departments"),
    ]

    if (allowed("users.view")) {
      requests.push(apiFetch<User[]>("/users"))
    }

    const results = await Promise.all(requests)
    setDepartments(results[0] as Department[])

    if (results[1]) {
      setUsers(results[1] as User[])
    }
  }, [allowed])

  const loadIncidents = useCallback(async () => {
    setLoading(true)
    setError("")

    const params = new URLSearchParams({
      page: String(page),
      page_size: "20",
    })

    if (search.trim()) params.set("search", search.trim())
    if (statusFilter) params.set("status", statusFilter)
    if (priorityFilter) params.set("priority", priorityFilter)
    if (typeFilter) params.set("incident_type", typeFilter)

    try {
      const response = await apiFetch<IncidentListResponse>(
          `/incidents?${params.toString()}`,
      )

      setIncidents(response.items)
      setPages(response.pages)
      setTotal(response.total)
    } catch (requestError) {
      setError(
          requestError instanceof Error
              ? requestError.message
              : "Unable to load incidents.",
      )
    } finally {
      setLoading(false)
    }
  }, [page, priorityFilter, search, statusFilter, typeFilter])

  useEffect(() => {
    void loadReferenceData().catch(() => undefined)
  }, [loadReferenceData])

  useEffect(() => {
    const timer = window.setTimeout(() => {
      void loadIncidents()
    }, 250)

    return () => window.clearTimeout(timer)
  }, [loadIncidents])

  async function openIncident(incident: Incident) {
    setSelectedIncident(incident)
    setDetailLoading(true)
    setError("")

    try {
      const [freshIncident, activities, evidenceItems] = await Promise.all([
        apiFetch<Incident>(`/incidents/${incident.id}`),
        apiFetch<IncidentActivity[]>(
            `/incidents/${incident.id}/timeline`,
        ),
        apiFetch<Evidence[]>(`/evidence/incidents/${incident.id}`),
      ])

      setSelectedIncident(freshIncident)
      setTimeline(activities)
      setEvidence(evidenceItems)
    } catch (requestError) {
      setError(
          requestError instanceof Error
              ? requestError.message
              : "Unable to load incident details.",
      )
    } finally {
      setDetailLoading(false)
    }
  }

  async function refreshSelectedIncident() {
    if (!selectedIncident) return

    const [freshIncident, activities, evidenceItems] = await Promise.all([
      apiFetch<Incident>(`/incidents/${selectedIncident.id}`),
      apiFetch<IncidentActivity[]>(
          `/incidents/${selectedIncident.id}/timeline`,
      ),
      apiFetch<Evidence[]>(
          `/evidence/incidents/${selectedIncident.id}`,
      ),
    ])

    setSelectedIncident(freshIncident)
    setTimeline(activities)
    setEvidence(evidenceItems)
    await loadIncidents()
  }

  async function createIncident(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setBusy(true)
    setModalError("")

    const hasLatitude = form.latitude.trim() !== ""
    const hasLongitude = form.longitude.trim() !== ""

    if (hasLatitude !== hasLongitude) {
      setModalError("Latitude and longitude must be supplied together.")
      setBusy(false)
      return
    }

    try {
      const incident = await apiFetch<Incident>("/incidents", {
        method: "POST",
        body: JSON.stringify({
          incident_type: form.incident_type,
          title: form.title.trim(),
          description: form.description.trim(),
          priority: form.priority,
          source: form.source,
          department_id: form.department_id
              ? Number(form.department_id)
              : null,
          assigned_user_id: form.assigned_user_id
              ? Number(form.assigned_user_id)
              : null,
          location_name: form.location_name.trim() || null,
          latitude: hasLatitude ? Number(form.latitude) : null,
          longitude: hasLongitude ? Number(form.longitude) : null,
          is_ai_generated: false,
        }),
      })

      setCreateOpen(false)
      setForm({ ...emptyIncidentForm })
      await loadIncidents()
      await openIncident(incident)
    } catch (requestError) {
      setModalError(
          requestError instanceof Error
              ? requestError.message
              : "Unable to create incident.",
      )
    } finally {
      setBusy(false)
    }
  }

  async function assignIncident(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!selectedIncident) return

    setBusy(true)
    setModalError("")

    try {
      await apiFetch<Incident>(
          `/incidents/${selectedIncident.id}/assign`,
          {
            method: "POST",
            body: JSON.stringify({
              assigned_user_id: Number(assignmentUserId),
              department_id: assignmentDepartmentId
                  ? Number(assignmentDepartmentId)
                  : null,
              notes: assignmentNotes.trim() || null,
            }),
          },
      )

      setAssignOpen(false)
      setAssignmentUserId("")
      setAssignmentDepartmentId("")
      setAssignmentNotes("")
      await refreshSelectedIncident()
    } catch (requestError) {
      setModalError(
          requestError instanceof Error
              ? requestError.message
              : "Unable to assign incident.",
      )
    } finally {
      setBusy(false)
    }
  }

  async function changeStatus(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!selectedIncident || !nextStatus) return

    setBusy(true)
    setModalError("")

    try {
      await apiFetch<Incident>(
          `/incidents/${selectedIncident.id}/status`,
          {
            method: "POST",
            body: JSON.stringify({
              status: nextStatus,
              notes: statusNotes.trim() || null,
              resolution_notes:
                  nextStatus === "resolved"
                      ? resolutionNotes.trim() || null
                      : null,
            }),
          },
      )

      setStatusOpen(false)
      setNextStatus("")
      setStatusNotes("")
      setResolutionNotes("")
      await refreshSelectedIncident()
    } catch (requestError) {
      setModalError(
          requestError instanceof Error
              ? requestError.message
              : "Unable to update incident status.",
      )
    } finally {
      setBusy(false)
    }
  }

  async function uploadEvidence(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!selectedIncident || !evidenceForm.file) return

    setBusy(true)
    setModalError("")

    const formData = new FormData()
    formData.append("file", evidenceForm.file)

    if (evidenceForm.description.trim()) {
      formData.append("description", evidenceForm.description.trim())
    }

    if (evidenceForm.captured_at) {
      formData.append(
          "captured_at",
          new Date(evidenceForm.captured_at).toISOString(),
      )
    }

    if (evidenceForm.latitude.trim()) {
      formData.append("latitude", evidenceForm.latitude.trim())
    }

    if (evidenceForm.longitude.trim()) {
      formData.append("longitude", evidenceForm.longitude.trim())
    }

    formData.append(
        "is_anonymized",
        String(evidenceForm.is_anonymized),
    )
    formData.append(
        "is_enforcement_evidence",
        String(evidenceForm.is_enforcement_evidence),
    )

    try {
      await apiFetch<Evidence>(
          `/evidence/incidents/${selectedIncident.id}`,
          {
            method: "POST",
            body: formData,
          },
      )

      setEvidenceOpen(false)
      setEvidenceForm({ ...emptyEvidenceForm })
      await refreshSelectedIncident()
    } catch (requestError) {
      setModalError(
          requestError instanceof Error
              ? requestError.message
              : "Unable to upload evidence.",
      )
    } finally {
      setBusy(false)
    }
  }

  async function deleteEvidence(item: Evidence) {
    const confirmed = window.confirm(
        `Delete evidence “${item.original_file_name}”?`,
    )

    if (!confirmed) return

    setBusy(true)
    setError("")

    try {
      await apiFetch<void>(`/evidence/${item.id}`, {
        method: "DELETE",
      })
      await refreshSelectedIncident()
    } catch (requestError) {
      setError(
          requestError instanceof Error
              ? requestError.message
              : "Unable to delete evidence.",
      )
    } finally {
      setBusy(false)
    }
  }

  const filteredAssignmentUsers = useMemo(() => {
    const departmentId = assignmentDepartmentId
        ? Number(assignmentDepartmentId)
        : selectedIncident?.department_id

    return users.filter(
        (item) =>
            item.is_active &&
            !item.is_superuser &&
            (!departmentId || item.department_id === departmentId),
    )
  }, [assignmentDepartmentId, selectedIncident?.department_id, users])

  const stats = useMemo(
      () => ({
        open: incidents.filter(
            (item) => !["resolved", "dismissed"].includes(item.status),
        ).length,
        critical: incidents.filter(
            (item) =>
                item.priority === "critical" &&
                !["resolved", "dismissed"].includes(item.status),
        ).length,
        unassigned: incidents.filter(
            (item) =>
                !item.assigned_user_id &&
                !["resolved", "dismissed"].includes(item.status),
        ).length,
        resolved: incidents.filter((item) => item.status === "resolved")
            .length,
      }),
      [incidents],
  )

  return (
      <div className="space-y-6">
        <div className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
          <div>
            <h1 className="text-2xl font-semibold tracking-tight">
              Incident Management
            </h1>
            <p className="mt-1 text-sm text-muted-foreground">
              Review, assign, investigate and resolve MCC operational incidents.
            </p>
          </div>

          {allowed("incidents.create") && (
              <button
                  type="button"
                  onClick={() => {
                    setForm({ ...emptyIncidentForm })
                    setModalError("")
                    setCreateOpen(true)
                  }}
                  className="flex h-10 items-center justify-center gap-2 rounded-md bg-primary px-4 text-sm font-medium text-primary-foreground transition hover:opacity-90"
              >
                <Plus className="size-4" />
                Report incident
              </button>
          )}
        </div>

        {error && (
            <div className="rounded-lg border border-destructive/30 bg-destructive/10 p-3 text-sm text-destructive">
              {error}
            </div>
        )}

        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
          <Metric icon={<CircleDot />} label="Open on this page" value={stats.open} />
          <Metric
              icon={<AlertTriangle />}
              label="Critical open"
              value={stats.critical}
          />
          <Metric
              icon={<UserRoundCheck />}
              label="Awaiting assignment"
              value={stats.unassigned}
          />
          <Metric
              icon={<CheckCircle2 />}
              label="Resolved on this page"
              value={stats.resolved}
          />
        </div>

        <section className="rounded-xl border bg-card">
          <div className="grid gap-3 border-b p-4 lg:grid-cols-[1fr_180px_160px_210px_auto]">
            <div className="flex h-10 items-center gap-2 rounded-md border bg-background px-3">
              <Search className="size-4 text-muted-foreground" />
              <input
                  value={search}
                  onChange={(event) => {
                    setSearch(event.target.value)
                    setPage(1)
                  }}
                  placeholder="Search incident number, title or location..."
                  className="w-full bg-transparent text-sm outline-none"
              />
            </div>

            <Select
                value={statusFilter}
                onChange={(value) => {
                  setStatusFilter(value)
                  setPage(1)
                }}
            >
              <option value="">All statuses</option>
              {STATUSES.map((value) => (
                  <option key={value} value={value}>
                    {humanize(value)}
                  </option>
              ))}
            </Select>

            <Select
                value={priorityFilter}
                onChange={(value) => {
                  setPriorityFilter(value)
                  setPage(1)
                }}
            >
              <option value="">All priorities</option>
              {PRIORITIES.map((value) => (
                  <option key={value} value={value}>
                    {humanize(value)}
                  </option>
              ))}
            </Select>

            <Select
                value={typeFilter}
                onChange={(value) => {
                  setTypeFilter(value)
                  setPage(1)
                }}
            >
              <option value="">All incident types</option>
              {INCIDENT_TYPES.map((item) => (
                  <option key={item.value} value={item.value}>
                    {item.label}
                  </option>
              ))}
            </Select>

            <button
                type="button"
                onClick={() => void loadIncidents()}
                className="flex h-10 items-center justify-center gap-2 rounded-md border px-3 text-sm transition hover:bg-muted"
            >
              <RefreshCw className={cn("size-4", loading && "animate-spin")} />
              Refresh
            </button>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-muted/30 text-left text-xs uppercase tracking-wide text-muted-foreground">
              <tr>
                <th className="px-4 py-3">Incident</th>
                <th className="px-4 py-3">Type</th>
                <th className="px-4 py-3">Location</th>
                <th className="px-4 py-3">Department / assignee</th>
                <th className="px-4 py-3">Priority</th>
                <th className="px-4 py-3">Status</th>
                <th className="px-4 py-3 text-right">Action</th>
              </tr>
              </thead>

              <tbody>
              {incidents.map((incident) => (
                  <tr
                      key={incident.id}
                      className="border-t transition hover:bg-muted/20"
                  >
                    <td className="px-4 py-3">
                      <button
                          type="button"
                          onClick={() => void openIncident(incident)}
                          className="text-left"
                      >
                        <p className="font-medium hover:text-primary hover:underline">
                          {incident.title}
                        </p>
                        <p className="mt-1 text-xs text-muted-foreground">
                          {incident.incident_number} · {formatDate(incident.reported_at)}
                        </p>
                      </button>
                    </td>
                    <td className="px-4 py-3">
                      {incidentTypeLabel(incident.incident_type)}
                    </td>
                    <td className="px-4 py-3 text-muted-foreground">
                      {incident.location_name || "Not specified"}
                    </td>
                    <td className="px-4 py-3">
                      <p>{incident.department?.name || "Unassigned department"}</p>
                      <p className="text-xs text-muted-foreground">
                        {incident.assigned_user?.full_name || "No officer assigned"}
                      </p>
                    </td>
                    <td className="px-4 py-3">
                      <PriorityBadge priority={incident.priority} />
                    </td>
                    <td className="px-4 py-3">
                      <StatusBadge status={incident.status} />
                    </td>
                    <td className="px-4 py-3 text-right">
                      <button
                          type="button"
                          onClick={() => void openIncident(incident)}
                          className="rounded-md border px-3 py-1.5 text-xs transition hover:bg-muted"
                      >
                        View
                      </button>
                    </td>
                  </tr>
              ))}
              </tbody>
            </table>

            {loading && (
                <div className="flex items-center justify-center gap-2 p-10 text-sm text-muted-foreground">
                  <LoaderCircle className="size-4 animate-spin" />
                  Loading incidents...
                </div>
            )}

            {!loading && incidents.length === 0 && (
                <div className="p-12 text-center">
                  <AlertTriangle className="mx-auto size-8 text-muted-foreground" />
                  <p className="mt-3 font-medium">No incidents found</p>
                  <p className="mt-1 text-sm text-muted-foreground">
                    Change the filters or report the first operational incident.
                  </p>
                </div>
            )}
          </div>

          <div className="flex items-center justify-between border-t px-4 py-3 text-sm">
            <p className="text-muted-foreground">
              {total} incident{total === 1 ? "" : "s"}
            </p>
            <div className="flex items-center gap-2">
              <button
                  type="button"
                  onClick={() => setPage((current) => Math.max(1, current - 1))}
                  disabled={page <= 1}
                  className="rounded-md border p-2 disabled:opacity-40"
              >
                <ChevronLeft className="size-4" />
              </button>
              <span>
              Page {page} of {Math.max(pages, 1)}
            </span>
              <button
                  type="button"
                  onClick={() => setPage((current) => current + 1)}
                  disabled={pages === 0 || page >= pages}
                  className="rounded-md border p-2 disabled:opacity-40"
              >
                <ChevronRight className="size-4" />
              </button>
            </div>
          </div>
        </section>

        {selectedIncident && (
            <IncidentDrawer
                incident={selectedIncident}
                evidence={evidence}
                timeline={timeline}
                loading={detailLoading}
                canAssign={allowed("incidents.assign")}
                canUploadEvidence={Boolean(
                    user?.is_superuser ||
                    allowed("evidence.upload") ||
                    selectedIncident.created_by_id === user?.id ||
                    selectedIncident.assigned_user_id === user?.id
                )}
                canDeleteEvidence={allowed("evidence.delete")}
                onClose={() => setSelectedIncident(null)}
                onAssign={() => {
                  setAssignmentDepartmentId(
                      selectedIncident.department_id
                          ? String(selectedIncident.department_id)
                          : "",
                  )
                  setAssignmentUserId(
                      selectedIncident.assigned_user_id
                          ? String(selectedIncident.assigned_user_id)
                          : "",
                  )
                  setModalError("")
                  setAssignOpen(true)
                }}
                onStatus={() => {
                  setNextStatus("")
                  setStatusNotes("")
                  setResolutionNotes("")
                  setModalError("")
                  setStatusOpen(true)
                }}
                onEvidence={() => {
                  setEvidenceForm({
                    ...emptyEvidenceForm,
                    latitude: selectedIncident.latitude?.toString() ?? "",
                    longitude: selectedIncident.longitude?.toString() ?? "",
                  })
                  setModalError("")
                  setEvidenceOpen(true)
                }}
                onDownload={(item) =>
                    void apiDownload(
                        `/evidence/${item.id}/download`,
                        item.original_file_name,
                    ).catch((downloadError) =>
                        setError(
                            downloadError instanceof Error
                                ? downloadError.message
                                : "Unable to download evidence.",
                        ),
                    )
                }
                onDelete={(item) => void deleteEvidence(item)}
            />
        )}

        {createOpen && (
            <Modal title="Report incident" onClose={() => !busy && setCreateOpen(false)}>
              <form onSubmit={createIncident} className="grid gap-4 sm:grid-cols-2">
                <ModalError message={modalError} />

                <LabeledSelect
                    label="Incident type"
                    value={form.incident_type}
                    onChange={(value) =>
                        setForm((current) => ({
                          ...current,
                          incident_type: value as IncidentType,
                        }))
                    }
                >
                  {INCIDENT_TYPES.map((item) => (
                      <option key={item.value} value={item.value}>
                        {item.label}
                      </option>
                  ))}
                </LabeledSelect>

                <LabeledSelect
                    label="Priority"
                    value={form.priority}
                    onChange={(value) =>
                        setForm((current) => ({
                          ...current,
                          priority: value as IncidentPriority,
                        }))
                    }
                >
                  {PRIORITIES.map((value) => (
                      <option key={value} value={value}>
                        {humanize(value)}
                      </option>
                  ))}
                </LabeledSelect>

                <Field
                    label="Title"
                    value={form.title}
                    onChange={(value) =>
                        setForm((current) => ({ ...current, title: value }))
                    }
                    className="sm:col-span-2"
                    required
                />

                <TextArea
                    label="Description"
                    value={form.description}
                    onChange={(value) =>
                        setForm((current) => ({ ...current, description: value }))
                    }
                    className="sm:col-span-2"
                    required
                />

                <LabeledSelect
                    label="Department"
                    value={form.department_id}
                    onChange={(value) =>
                        setForm((current) => ({
                          ...current,
                          department_id: value,
                          assigned_user_id: "",
                        }))
                    }
                >
                  <option value="">Unassigned</option>
                  {departments
                      .filter((department) => department.is_active)
                      .map((department) => (
                          <option key={department.id} value={department.id}>
                            {department.name}
                          </option>
                      ))}
                </LabeledSelect>

                <LabeledSelect
                    label="Assign officer now"
                    value={form.assigned_user_id}
                    onChange={(value) =>
                        setForm((current) => ({
                          ...current,
                          assigned_user_id: value,
                        }))
                    }
                    disabled={!form.department_id}
                >
                  <option value="">Assign later</option>
                  {users
                      .filter(
                          (item) =>
                              item.is_active &&
                              !item.is_superuser &&
                              item.department_id === Number(form.department_id),
                      )
                      .map((item) => (
                          <option key={item.id} value={item.id}>
                            {item.full_name}
                          </option>
                      ))}
                </LabeledSelect>

                <Field
                    label="Location name"
                    value={form.location_name}
                    onChange={(value) =>
                        setForm((current) => ({
                          ...current,
                          location_name: value,
                        }))
                    }
                    className="sm:col-span-2"
                    placeholder="Example: Kingsway Road, Maseru"
                />

                <Field
                    label="Latitude"
                    type="number"
                    step="any"
                    value={form.latitude}
                    onChange={(value) =>
                        setForm((current) => ({ ...current, latitude: value }))
                    }
                    placeholder="-29.3158"
                />

                <Field
                    label="Longitude"
                    type="number"
                    step="any"
                    value={form.longitude}
                    onChange={(value) =>
                        setForm((current) => ({ ...current, longitude: value }))
                    }
                    placeholder="27.4869"
                />

                <ModalActions
                    busy={busy}
                    submitLabel="Create incident"
                    onCancel={() => setCreateOpen(false)}
                />
              </form>
            </Modal>
        )}

        {assignOpen && selectedIncident && (
            <Modal title="Assign incident" onClose={() => !busy && setAssignOpen(false)}>
              <form onSubmit={assignIncident} className="space-y-4">
                <ModalError message={modalError} />

                <LabeledSelect
                    label="Department"
                    value={assignmentDepartmentId}
                    onChange={(value) => {
                      setAssignmentDepartmentId(value)
                      setAssignmentUserId("")
                    }}
                    required
                >
                  <option value="">Select department</option>
                  {departments
                      .filter((department) => department.is_active)
                      .map((department) => (
                          <option key={department.id} value={department.id}>
                            {department.name}
                          </option>
                      ))}
                </LabeledSelect>

                <LabeledSelect
                    label="Officer"
                    value={assignmentUserId}
                    onChange={setAssignmentUserId}
                    required
                >
                  <option value="">Select officer</option>
                  {filteredAssignmentUsers.map((item) => (
                      <option key={item.id} value={item.id}>
                        {item.full_name} {item.employee_number ? `(${item.employee_number})` : ""}
                      </option>
                  ))}
                </LabeledSelect>

                <TextArea
                    label="Assignment instructions"
                    value={assignmentNotes}
                    onChange={setAssignmentNotes}
                />

                <ModalActions
                    busy={busy}
                    submitLabel="Assign incident"
                    onCancel={() => setAssignOpen(false)}
                />
              </form>
            </Modal>
        )}

        {statusOpen && selectedIncident && (
            <Modal title="Update incident status" onClose={() => !busy && setStatusOpen(false)}>
              <form onSubmit={changeStatus} className="space-y-4">
                <ModalError message={modalError} />

                <LabeledSelect
                    label="New status"
                    value={nextStatus}
                    onChange={(value) => setNextStatus(value as IncidentStatus)}
                    required
                >
                  <option value="">Select next status</option>
                  {STATUS_TRANSITIONS[selectedIncident.status].map((value) => (
                      <option key={value} value={value}>
                        {humanize(value)}
                      </option>
                  ))}
                </LabeledSelect>

                <TextArea
                    label="Operational notes"
                    value={statusNotes}
                    onChange={setStatusNotes}
                />

                {nextStatus === "resolved" && (
                    <TextArea
                        label="Resolution notes"
                        value={resolutionNotes}
                        onChange={setResolutionNotes}
                        required
                    />
                )}

                <ModalActions
                    busy={busy}
                    submitLabel="Update status"
                    onCancel={() => setStatusOpen(false)}
                />
              </form>
            </Modal>
        )}

        {evidenceOpen && selectedIncident && (
            <Modal title="Upload incident evidence" onClose={() => !busy && setEvidenceOpen(false)}>
              <form onSubmit={uploadEvidence} className="grid gap-4 sm:grid-cols-2">
                <ModalError message={modalError} />

                <label className="text-sm font-medium sm:col-span-2">
                  Evidence file
                  <input
                      required
                      type="file"
                      accept="image/jpeg,image/png,image/webp,video/mp4,video/webm,audio/mpeg,audio/wav,application/pdf"
                      onChange={(event) =>
                          setEvidenceForm((current) => ({
                            ...current,
                            file: event.target.files?.[0] ?? null,
                          }))
                      }
                      className="mt-2 block w-full rounded-md border bg-background p-2 text-sm"
                  />
                  <span className="mt-1 block text-xs text-muted-foreground">
                JPG, PNG, WebP, MP4, WebM, MP3, WAV or PDF. Maximum 25 MiB.
              </span>
                </label>

                <TextArea
                    label="Description"
                    value={evidenceForm.description}
                    onChange={(value) =>
                        setEvidenceForm((current) => ({
                          ...current,
                          description: value,
                        }))
                    }
                    className="sm:col-span-2"
                />

                <Field
                    label="Captured at"
                    type="datetime-local"
                    value={evidenceForm.captured_at}
                    onChange={(value) =>
                        setEvidenceForm((current) => ({
                          ...current,
                          captured_at: value,
                        }))
                    }
                />

                <div />

                <Field
                    label="Latitude"
                    type="number"
                    step="any"
                    value={evidenceForm.latitude}
                    onChange={(value) =>
                        setEvidenceForm((current) => ({
                          ...current,
                          latitude: value,
                        }))
                    }
                />

                <Field
                    label="Longitude"
                    type="number"
                    step="any"
                    value={evidenceForm.longitude}
                    onChange={(value) =>
                        setEvidenceForm((current) => ({
                          ...current,
                          longitude: value,
                        }))
                    }
                />

                <label className="flex items-center gap-2 text-sm">
                  <input
                      type="checkbox"
                      checked={evidenceForm.is_anonymized}
                      onChange={(event) =>
                          setEvidenceForm((current) => ({
                            ...current,
                            is_anonymized: event.target.checked,
                          }))
                      }
                  />
                  Identity has been anonymized
                </label>

                <label className="flex items-center gap-2 text-sm">
                  <input
                      type="checkbox"
                      checked={evidenceForm.is_enforcement_evidence}
                      onChange={(event) =>
                          setEvidenceForm((current) => ({
                            ...current,
                            is_enforcement_evidence: event.target.checked,
                          }))
                      }
                  />
                  Mark as enforcement evidence
                </label>

                <ModalActions
                    busy={busy}
                    submitLabel="Upload evidence"
                    onCancel={() => setEvidenceOpen(false)}
                />
              </form>
            </Modal>
        )}
      </div>
  )
}

function IncidentDrawer({
                          incident,
                          evidence,
                          timeline,
                          loading,
                          canAssign,
                          canUploadEvidence,
                          canDeleteEvidence,
                          onClose,
                          onAssign,
                          onStatus,
                          onEvidence,
                          onDownload,
                          onDelete,
                        }: {
  incident: Incident
  evidence: Evidence[]
  timeline: IncidentActivity[]
  loading: boolean
  canAssign: boolean
  canUploadEvidence: boolean
  canDeleteEvidence: boolean
  onClose: () => void
  onAssign: () => void
  onStatus: () => void
  onEvidence: () => void
  onDownload: (item: Evidence) => void
  onDelete: (item: Evidence) => void
}) {
  return (
      <div className="fixed inset-0 z-[90] flex justify-end bg-black/60 backdrop-blur-sm">
        <button
            type="button"
            aria-label="Close incident details"
            className="flex-1"
            onClick={onClose}
        />

        <aside className="h-full w-full max-w-3xl overflow-y-auto border-l bg-background shadow-2xl">
          <div className="sticky top-0 z-10 flex items-center justify-between border-b bg-background/95 px-5 py-4 backdrop-blur">
            <div>
              <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                {incident.incident_number}
              </p>
              <h2 className="mt-1 text-lg font-semibold">{incident.title}</h2>
            </div>
            <button
                type="button"
                onClick={onClose}
                className="rounded-md p-2 transition hover:bg-muted"
            >
              <X className="size-5" />
            </button>
          </div>

          {loading ? (
              <div className="flex h-64 items-center justify-center gap-2 text-muted-foreground">
                <LoaderCircle className="size-5 animate-spin" />
                Loading incident...
              </div>
          ) : (
              <div className="space-y-6 p-5">
                <div className="flex flex-wrap gap-2">
                  <StatusBadge status={incident.status} />
                  <PriorityBadge priority={incident.priority} />
                  {incident.is_ai_generated && (
                      <span className="rounded-full bg-violet-500/12 px-2.5 py-1 text-xs font-medium text-violet-400">
                  AI generated
                </span>
                  )}
                </div>

                <div className="flex flex-wrap gap-2">
                  {canAssign && !["resolved", "dismissed"].includes(incident.status) && (
                      <ActionButton icon={<UserRoundCheck />} onClick={onAssign}>
                        Assign
                      </ActionButton>
                  )}
                  {STATUS_TRANSITIONS[incident.status].length > 0 && (
                      <ActionButton icon={<ArrowRight />} onClick={onStatus}>
                        Change status
                      </ActionButton>
                  )}
                  {canUploadEvidence && !["resolved", "dismissed"].includes(incident.status) && (
                      <ActionButton icon={<Upload />} onClick={onEvidence}>
                        Add evidence
                      </ActionButton>
                  )}
                </div>

                <Section title="Incident information">
                  <div className="grid gap-3 sm:grid-cols-2">
                    <Info label="Type" value={incidentTypeLabel(incident.incident_type)} />
                    <Info label="Source" value={humanize(incident.source)} />
                    <Info
                        label="Department"
                        value={incident.department?.name || "Not assigned"}
                    />
                    <Info
                        label="Assigned officer"
                        value={incident.assigned_user?.full_name || "Not assigned"}
                    />
                    <Info
                        label="Reported by"
                        value={incident.created_by.full_name}
                    />
                    <Info label="Reported" value={formatDate(incident.reported_at)} />
                  </div>

                  <div className="mt-3 rounded-lg border bg-card p-4">
                    <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                      Description
                    </p>
                    <p className="mt-2 whitespace-pre-wrap text-sm leading-6">
                      {incident.description}
                    </p>
                  </div>
                </Section>

                <Section title="Location">
                  <div className="rounded-lg border bg-card p-4">
                    <div className="flex gap-3">
                      <MapPin className="mt-0.5 size-5 text-primary" />
                      <div>
                        <p className="font-medium">
                          {incident.location_name || "Location not specified"}
                        </p>
                        {incident.latitude != null && incident.longitude != null && (
                            <p className="mt-1 text-sm text-muted-foreground">
                              {incident.latitude}, {incident.longitude}
                            </p>
                        )}
                      </div>
                    </div>
                  </div>
                </Section>

                {incident.resolution_notes && (
                    <Section title="Resolution">
                      <div className="rounded-lg border border-emerald-500/20 bg-emerald-500/5 p-4 text-sm leading-6">
                        {incident.resolution_notes}
                      </div>
                    </Section>
                )}

                <Section title={`Evidence (${evidence.length})`}>
                  {evidence.length === 0 ? (
                      canUploadEvidence &&
                      !["resolved", "dismissed"].includes(incident.status) ? (
                          <button
                              type="button"
                              onClick={onEvidence}
                              className="group w-full rounded-lg border border-dashed p-6 text-center transition hover:border-primary/50 hover:bg-primary/[0.03]"
                          >
                            <div className="mx-auto flex size-10 items-center justify-center rounded-full bg-muted text-muted-foreground transition group-hover:bg-primary/10 group-hover:text-primary">
                              <Paperclip className="size-5" />
                            </div>
                            <p className="mt-3 text-sm font-medium">
                              No evidence uploaded
                            </p>
                            <p className="mt-1 text-xs text-muted-foreground">
                              Attach enforcement images, video, audio or documents.
                            </p>
                            <span className="mt-4 inline-flex h-9 items-center gap-2 rounded-md bg-primary px-3 text-xs font-medium text-primary-foreground">
                              <Upload className="size-4" />
                              Upload evidence
                            </span>
                          </button>
                      ) : (
                          <EmptyState
                              icon={<Paperclip />}
                              title="No evidence uploaded"
                              description="No evidence is currently attached to this incident."
                          />
                      )
                  ) : (
                      <div className="space-y-3">
                        {canUploadEvidence &&
                          !["resolved", "dismissed"].includes(incident.status) && (
                              <div className="flex justify-end">
                                <button
                                    type="button"
                                    onClick={onEvidence}
                                    className="inline-flex h-9 items-center gap-2 rounded-md border px-3 text-xs font-medium transition hover:bg-muted"
                                >
                                  <Upload className="size-4" />
                                  Add evidence
                                </button>
                              </div>
                          )}

                        {evidence.map((item) => (
                            <div
                                key={item.id}
                                className="flex flex-col gap-3 rounded-lg border bg-card p-4 sm:flex-row sm:items-center"
                            >
                              <div className="flex size-10 shrink-0 items-center justify-center rounded-lg bg-primary/10 text-primary">
                                {item.evidence_type === "image" ? (
                                    <FileImage className="size-5" />
                                ) : (
                                    <FileText className="size-5" />
                                )}
                              </div>
                              <div className="min-w-0 flex-1">
                                <p className="truncate font-medium">
                                  {item.original_file_name}
                                </p>
                                <p className="mt-1 text-xs text-muted-foreground">
                                  {formatBytes(item.file_size_bytes)} · uploaded by {item.uploaded_by.full_name}
                                </p>
                                {item.description && (
                                    <p className="mt-1 text-sm text-muted-foreground">
                                      {item.description}
                                    </p>
                                )}
                              </div>
                              <div className="flex gap-2">
                                <button
                                    type="button"
                                    onClick={() => onDownload(item)}
                                    className="rounded-md border p-2 transition hover:bg-muted"
                                    title="Download"
                                >
                                  <Download className="size-4" />
                                </button>
                                {canDeleteEvidence && (
                                    <button
                                        type="button"
                                        onClick={() => onDelete(item)}
                                        className="rounded-md border p-2 text-destructive transition hover:bg-destructive/10"
                                        title="Delete"
                                    >
                                      <Trash2 className="size-4" />
                                    </button>
                                )}
                              </div>
                            </div>
                        ))}
                      </div>
                  )}
                </Section>

                <Section title="Incident timeline">
                  {timeline.length === 0 ? (
                      <EmptyState
                          icon={<CalendarClock />}
                          title="No timeline activity"
                          description="Operational changes will be recorded here."
                      />
                  ) : (
                      <div className="space-y-0">
                        {timeline.map((activity, index) => (
                            <div key={activity.id} className="relative flex gap-4 pb-6">
                              {index < timeline.length - 1 && (
                                  <div className="absolute left-[7px] top-5 h-full w-px bg-border" />
                              )}
                              <div className="relative mt-1 size-4 shrink-0 rounded-full border-4 border-background bg-primary" />
                              <div className="min-w-0 flex-1">
                                <div className="flex flex-col gap-1 sm:flex-row sm:items-center sm:justify-between">
                                  <p className="font-medium">{humanize(activity.action)}</p>
                                  <p className="text-xs text-muted-foreground">
                                    {formatDate(activity.created_at)}
                                  </p>
                                </div>
                                <p className="mt-1 text-sm text-muted-foreground">
                                  {activity.actor.full_name}
                                  {activity.previous_status && activity.new_status
                                      ? ` · ${humanize(activity.previous_status)} → ${humanize(activity.new_status)}`
                                      : ""}
                                </p>
                                {activity.notes && (
                                    <p className="mt-2 rounded-md bg-muted/40 p-3 text-sm leading-6">
                                      {activity.notes}
                                    </p>
                                )}
                              </div>
                            </div>
                        ))}
                      </div>
                  )}
                </Section>
              </div>
          )}
        </aside>
      </div>
  )
}

function Modal({
                 title,
                 children,
                 onClose,
               }: {
  title: string
  children: ReactNode
  onClose: () => void
}) {
  return (
      <div className="fixed inset-0 z-[110] flex items-center justify-center bg-black/65 p-4 backdrop-blur-sm">
        <div className="max-h-[92vh] w-full max-w-2xl overflow-y-auto rounded-xl border bg-card shadow-2xl">
          <div className="sticky top-0 z-10 flex items-center justify-between border-b bg-card px-6 py-4">
            <h2 className="text-lg font-semibold">{title}</h2>
            <button
                type="button"
                onClick={onClose}
                className="rounded-md p-2 transition hover:bg-muted"
            >
              <X className="size-4" />
            </button>
          </div>
          <div className="p-6">{children}</div>
        </div>
      </div>
  )
}

function Metric({
                  icon,
                  label,
                  value,
                }: {
  icon: ReactNode
  label: string
  value: number
}) {
  return (
      <div className="flex items-center gap-4 rounded-xl border bg-card p-4">
        <div className="flex size-11 items-center justify-center rounded-lg bg-primary/10 text-primary [&>svg]:size-5">
          {icon}
        </div>
        <div>
          <p className="text-2xl font-semibold">{value}</p>
          <p className="text-xs text-muted-foreground">{label}</p>
        </div>
      </div>
  )
}

function StatusBadge({ status }: { status: IncidentStatus }) {
  const styles: Record<IncidentStatus, string> = {
    new: "bg-sky-500/12 text-sky-400",
    under_review: "bg-violet-500/12 text-violet-400",
    confirmed: "bg-cyan-500/12 text-cyan-400",
    assigned: "bg-indigo-500/12 text-indigo-400",
    in_progress: "bg-amber-500/12 text-amber-400",
    resolved: "bg-emerald-500/12 text-emerald-400",
    dismissed: "bg-slate-500/12 text-slate-400",
  }

  return (
      <span className={cn("inline-flex rounded-full px-2.5 py-1 text-xs font-medium", styles[status])}>
      {humanize(status)}
    </span>
  )
}

function PriorityBadge({ priority }: { priority: IncidentPriority }) {
  const styles: Record<IncidentPriority, string> = {
    low: "bg-slate-500/12 text-slate-400",
    medium: "bg-sky-500/12 text-sky-400",
    high: "bg-orange-500/12 text-orange-400",
    critical: "bg-red-500/12 text-red-400",
  }

  return (
      <span className={cn("inline-flex rounded-full px-2.5 py-1 text-xs font-medium", styles[priority])}>
      {humanize(priority)}
    </span>
  )
}

function ActionButton({
                        icon,
                        children,
                        onClick,
                      }: {
  icon: ReactNode
  children: ReactNode
  onClick: () => void
}) {
  return (
      <button
          type="button"
          onClick={onClick}
          className="flex h-9 items-center gap-2 rounded-md border px-3 text-sm transition hover:bg-muted [&>svg]:size-4"
      >
        {icon}
        {children}
      </button>
  )
}

function Section({ title, children }: { title: string; children: ReactNode }) {
  return (
      <section>
        <h3 className="mb-3 text-sm font-semibold">{title}</h3>
        {children}
      </section>
  )
}

function Info({ label, value }: { label: string; value: string }) {
  return (
      <div className="rounded-lg border bg-card p-4">
        <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
          {label}
        </p>
        <p className="mt-2 text-sm font-medium">{value}</p>
      </div>
  )
}

function EmptyState({
                      icon,
                      title,
                      description,
                    }: {
  icon: ReactNode
  title: string
  description: string
}) {
  return (
      <div className="rounded-lg border border-dashed p-6 text-center">
        <div className="mx-auto flex size-10 items-center justify-center rounded-full bg-muted text-muted-foreground [&>svg]:size-5">
          {icon}
        </div>
        <p className="mt-3 text-sm font-medium">{title}</p>
        <p className="mt-1 text-xs text-muted-foreground">{description}</p>
      </div>
  )
}

function Select({
                  value,
                  onChange,
                  children,
                }: {
  value: string
  onChange: (value: string) => void
  children: ReactNode
}) {
  return (
      <div className="relative">
        <Filter className="pointer-events-none absolute left-3 top-3 size-4 text-muted-foreground" />
        <select
            value={value}
            onChange={(event) => onChange(event.target.value)}
            className="h-10 w-full rounded-md border bg-background pl-9 pr-3 text-sm outline-none"
        >
          {children}
        </select>
      </div>
  )
}

function LabeledSelect({
                         label,
                         value,
                         onChange,
                         children,
                         required = false,
                         disabled = false,
                       }: {
  label: string
  value: string
  onChange: (value: string) => void
  children: ReactNode
  required?: boolean
  disabled?: boolean
}) {
  return (
      <label className="block text-sm font-medium">
        {label}
        <select
            value={value}
            required={required}
            disabled={disabled}
            onChange={(event) => onChange(event.target.value)}
            className="mt-2 h-10 w-full rounded-md border bg-background px-3 text-sm outline-none focus:ring-2 focus:ring-ring disabled:opacity-50"
        >
          {children}
        </select>
      </label>
  )
}

function Field({
                 label,
                 value,
                 onChange,
                 type = "text",
                 step,
                 placeholder,
                 required = false,
                 className,
               }: {
  label: string
  value: string
  onChange: (value: string) => void
  type?: string
  step?: string
  placeholder?: string
  required?: boolean
  className?: string
}) {
  return (
      <label className={cn("block text-sm font-medium", className)}>
        {label}
        <input
            type={type}
            step={step}
            value={value}
            required={required}
            placeholder={placeholder}
            onChange={(event) => onChange(event.target.value)}
            className="mt-2 h-10 w-full rounded-md border bg-background px-3 text-sm outline-none focus:ring-2 focus:ring-ring"
        />
      </label>
  )
}

function TextArea({
                    label,
                    value,
                    onChange,
                    required = false,
                    className,
                  }: {
  label: string
  value: string
  onChange: (value: string) => void
  required?: boolean
  className?: string
}) {
  return (
      <label className={cn("block text-sm font-medium", className)}>
        {label}
        <textarea
            value={value}
            required={required}
            rows={4}
            onChange={(event) => onChange(event.target.value)}
            className="mt-2 w-full resize-y rounded-md border bg-background px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-ring"
        />
      </label>
  )
}

function ModalActions({
                        busy,
                        submitLabel,
                        onCancel,
                      }: {
  busy: boolean
  submitLabel: string
  onCancel: () => void
}) {
  return (
      <div className="flex justify-end gap-2 pt-2 sm:col-span-2">
        <button
            type="button"
            onClick={onCancel}
            disabled={busy}
            className="h-10 rounded-md border px-4 transition hover:bg-muted disabled:opacity-50"
        >
          Cancel
        </button>
        <button
            type="submit"
            disabled={busy}
            className="flex h-10 items-center gap-2 rounded-md bg-primary px-4 font-medium text-primary-foreground transition hover:opacity-90 disabled:opacity-50"
        >
          {busy && <LoaderCircle className="size-4 animate-spin" />}
          {busy ? "Please wait..." : submitLabel}
        </button>
      </div>
  )
}

function ModalError({ message }: { message: string }) {
  if (!message) return null

  return (
      <div className="rounded-md border border-destructive/30 bg-destructive/10 p-3 text-sm text-destructive sm:col-span-2">
        {message}
      </div>
  )
}

function incidentTypeLabel(value: IncidentType) {
  return INCIDENT_TYPES.find((item) => item.value === value)?.label || humanize(value)
}

function humanize(value: string) {
  return value
      .replace(/^incident\./, "")
      .replace(/[._-]+/g, " ")
      .replace(/\b\w/g, (character) => character.toUpperCase())
}

function formatDate(value: string) {
  const date = new Date(value)

  if (Number.isNaN(date.getTime())) return "Not available"

  return new Intl.DateTimeFormat("en-LS", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(date)
}

function formatBytes(bytes: number) {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KiB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MiB`
}
