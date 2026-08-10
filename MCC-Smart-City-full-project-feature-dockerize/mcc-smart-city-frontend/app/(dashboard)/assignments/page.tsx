
Thu, Jul 30 at 9:21 PM

backend(11).zip
Zip Archive
good everything is up and running now, i just have this system, and would like to use it, or its code, to build dynamic navigation, and role based authentication, here is the zip file of the previous system, but this one, i want to have like superAdmin, who register people and add department, and roles, the system is for Maseru City council, and i know it has 5 departments, but i want it to allow the superadmin be able to add them, and roles, and in the backend.zip, just focus on authentication mostly


Pasted text(23).txt
Document
here is the full process

why is this failing because i am able to do other things, and download as well, like 1. something mbso its not my interneet, but something is the problem!!


frontend(9).zip
Zip Archive

backend(12).zip
Zip Archive
everything now works, can you now create the frontend, i currently have only this backend and frontend files, and have tested the authentication endpoints using the swagger, docs, and it works, so now i need help with frontend, lets create it for the superadmin, and , login, and dashboard and have proper menu items and keep the ui design as it or improve a little

so in what order should i now test this, like add departments, then users,then roles, permission, in what order should i test

Sat, Aug 1 at 8:43 PM
image(170).png
image(171).png
there's a bug here, what would the user use as identifier when logging in, n i just added but, its not shown as well, but when i add them again, it says they exist

now i get this whem i add IT manager again, and this one does not make sense, cos i did not add email, for the first it manager, for the above snippet, please give me full code , not snippets

image(173).png
image(174).png
it works, have logged in,  and changed the temporary password, and this is whas shown for IT Manager, and can we create a modal for superAdmin, so that they can click and maybe view all information of the user show,

    but now the IT manager is able to view super admin details and even his, is that a good things, like prffessianally, whats the flow here, this system is real and its going to be used by MCC, its not plaything or school project, and its sponsored by UNDP


backend(13).zip
Zip Archive
okay but its a norm for IT manager to help all the users at organisation, even if not SuperAdmin, but other users , so i think we should follow that, and thats latest modules, i have, what should i replace and change, remember full file!!!


srs_template-ieee (1).doc
Document
okay since we still struggling with camera, and waiting for nvidea jetson, lets work on other modules, that can be done with software, and this is the srs document we should follow


frontend(10).zip
Zip Archive

backend_modules(1).zip
Zip Archive
everything works, lets just consume them, and check also the latest files you gave me and how the backend is built, and how far we have come and whats needed

Screenshot 2026-08-10 100145.png
is it still building?


    Pasted text(20260810-104443).txt
Document

Screenshot 2026-08-10 143807.png

Screenshot 2026-08-10 144131.png
Screenshot 2026-08-10 144145.png

Worked for 1m 37s
Yes. Before moving on, we should make evidence upload a single reliable workflow everywhere it is needed.

    I checked the Evidence implementation we built, and there are two separate problems in the current design.

    First, the backend already allows evidence upload when a user either has evidence.upload, created the incident, or is the officer assigned to the incident. But the Incidents frontend only shows Add evidence when this returns true:

allowed("evidence.upload")
So an assigned officer can be legally allowed by FastAPI to upload evidence while the frontend hides the upload control from them. That is inconsistent.

    Second, the Assignments page currently does not actually upload files. When an officer submits completed work, it only lets them select Evidence that was previously uploaded through Incident Management. That is why it tells the officer to go elsewhere first. For field work, that is unnecessarily awkward. Our project roadmap explicitly expects the officer to upload completion evidence as part of the operational flow.


    The backend Evidence API itself is already designed for image/video/audio/PDF uploads, which is consistent with our roadmap.


    What I want us to change
We should have one reusable Evidence Uploader and use it in both places:

    Incident Management
    └── Add Evidence
            ↓
        EvidenceUploader

Assignments
    └── Submit Completion
            ↓
        Upload Completion Evidence
            ↓
        EvidenceUploader
            ↓
        Select uploaded evidence
            ↓
        Submit for verification
  The eligibility should also become:

    SuperAdmin
OR evidence.upload permission
OR incident creator
OR assigned officer
That matches the backend instead of having different rules in the UI.

    Before I replace your files, I don't want to overwrite the employee-selection corrections and other changes you now have in the current Incidents page.

Please give me these two current full files from your machine:

    mcc-smart-city-frontend/app/(dashboard)/incidents/page.tsx
mcc-smart-city-frontend/app/(dashboard)/assignments/page.tsx
You can upload them here, or if easier, paste them as files.

    I'll then return the complete corrected files plus a new reusable component such as:

components/evidence/evidence-uploader.tsx
and, if necessary, update:

lib/api.ts
lib/types.ts
I will make sure the result supports actual file selection and upload directly from both Incident Management and Assignments, rather than forcing the officer to jump between pages.

    One thing we can also verify immediately: in Swagger, POST /api/v1/evidence/incidents/{incident_id} should still accept a file. If that endpoint itself is now failing too, send me its exact Swagger response and we'll fix the backend as well.



Pasted text(20260810-141708).txt
Document

Pasted text (2)(20260810-141729).txt
Document

I’ve got both current files now, and I can see the upload flow that’s in place.




    The important part is this: your Incident page is already constructing a FormData request correctly and sending the file to:

    /evidence/incidents/{incident_id}
So the frontend form itself is not obviously wrong.


    And the Assignments page currently does not upload files at all during completion—it only submits IDs of evidence that already exists on the incident.


    Because you said you cannot upload anywhere, I don’t want to patch these two pages and leave the real transport problem untouched.

    The next files I need are the two pieces that actually determine whether multipart upload succeeds:

    mcc-smart-city-frontend/lib/api.ts
and:

    mcc-smart-city-backend/app/modules/evidence/router.py
If possible, also send:

    mcc-smart-city-backend/app/modules/evidence/service.py
The most important one is lib/api.ts, because if apiFetch() is forcing:

    Content-Type: application/json
even when body is a FormData, then every file upload in the whole frontend will fail, which matches exactly what you are seeing.

    Once you send those, I’ll fix the upload path properly and return the full files, including the Incident and Assignment pages, rather than giving you a workaround.



    Pasted text(20260810-142157).txt
Document

Pasted text (2)(20260810-142341).txt
Document

Pasted text (3)(4).txt
Document

Pasted text (4)(2).txt
Document
export const API_URL =
    process.env.NEXT_PUBLIC_API_URL ||
    "http://localhost:8000/api/v1"

export class ApiError extends Error {
  status: number

  constructor(message: string, status: number) {
    super(message)
    this.name = "ApiError"
    this.status = status
  }
}

function accessToken() {
  if (typeof window === "undefined") {
    return null
  }

  return localStorage.getItem("mcc_access_token")
}

function clearStoredSession() {
  if (typeof window === "undefined") {
    return
  }

  localStorage.removeItem("mcc_access_token")
  localStorage.removeItem("mcc_user")
}

async function errorMessage(response: Response) {
  const fallback = Request failed (${response.status})

  try {
    const data = await response.json()

    if (typeof data?.detail === "string") {
      return data.detail
    }

    if (Array.isArray(data?.detail)) {
      return data.detail
          .map((item: { msg?: string }) => item.msg || "Invalid value")
          .join("; ")
    }

    return data?.message || fallback
  } catch {
    return fallback
  }
}

export async function apiFetch<T>(
    path: string,
    options: RequestInit = {},
): Promise<T> {
  const headers = new Headers(options.headers)
  const token = accessToken()
  const bodyIsFormData = options.body instanceof FormData

  if (options.body && !bodyIsFormData && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json")
  }

  if (token) {
    headers.set("Authorization", Bearer ${token})
  }

  const response = await fetch(${API_URL}${path}, {
  ...options,
        headers,
        cache: "no-store",
  })

  if (!response.ok) {
    const message = await errorMessage(response)

    if (response.status === 401) {
      clearStoredSession()
    }

    throw new ApiError(message, response.status)
  }

  if (response.status === 204) {
    return undefined as T
  }

  return response.json() as Promise<T>
}

export async function apiDownload(
    path: string,
    suggestedFileName = "download",
): Promise<void> {
  const headers = new Headers()
  const token = accessToken()

  if (token) {
    headers.set("Authorization", Bearer ${token})
  }

  const response = await fetch(${API_URL}${path}, {
    headers,
        cache: "no-store",
  })

  if (!response.ok) {
    const message = await errorMessage(response)

    if (response.status === 401) {
      clearStoredSession()
    }

    throw new ApiError(message, response.status)
  }

  const blob = await response.blob()
  const objectUrl = URL.createObjectURL(blob)
  const anchor = document.createElement("a")

  anchor.href = objectUrl
  anchor.download = suggestedFileName
  document.body.appendChild(anchor)
  anchor.click()
  anchor.remove()
  URL.revokeObjectURL(objectUrl)
}

this is api.ts



Worked for 1m 47s
I checked the actual upload chain instead of changing things blindly.

    Your api.ts is already correct for file uploads: it detects FormData, avoids forcing Content-Type: application/json, and still adds the Bearer token. So do not replace api.ts.

    The backend Evidence service is also correctly set up to accept and save files, validate MIME type, enforce the size limit, calculate SHA-256, create the storage directory, write the file, and create the evidence record.


    The two frontend problems were:

    Incident Management only displayed Add evidence for users with the explicit evidence.upload permission, even though your backend also allows the incident creator and assigned officer.


    Assignments had no uploader whatsoever; it only allowed choosing previously uploaded evidence and told the officer to return to Incident Management.


    I corrected both current full files.

1. Incident Management
incidents-page-evidence-fixed.tsx

Replace:

    mcc-smart-city-frontend/app/(dashboard)/incidents/page.tsx
The Add evidence control is now available when the logged-in user is:

    SuperAdmin
OR has evidence.upload
OR created the incident
OR is the officer assigned to the incident
That now matches the backend's actual authorization policy. The backend explicitly allows SuperAdmin, evidence.upload, the incident creator, and the assigned officer.


2. Assignments
assignments-page-evidence-fixed.tsx

Replace:

    mcc-smart-city-frontend/app/(dashboard)/assignments/page.tsx
Now when the officer chooses:

    Submit completion
they get a proper workflow:

    Choose File
    ↓
Upload Evidence
    ↓
Evidence attached to Incident
    ↓
Automatically selected as completion proof
    ↓
Enter Completion Notes
    ↓
Submit for Verification
  They no longer need to leave Assignments and go back to Incident Management.

    The upload supports the same formats as your backend:

    JPEG
PNG
WebP
MP4
WebM
MP3
WAV
PDF
and your backend currently defaults to a maximum evidence size of 25 MB.


    After replacing both files, rebuild only the frontend:

    docker compose build frontend
docker compose up -d --force-recreate frontend
Then test Incident Management first with a small JPG or PNG. If that succeeds, test the same thing from Assignments → Start Work → Submit Completion → Upload Evidence.

    If either upload now produces an actual HTTP error, send me the Network request's status code + Response body. At that point we'll be testing the backend upload endpoint itself rather than guessing at the frontend.


    incidents-page-evidence-fixed.tsx
Code


assignments-page-evidence-fixed.tsx
Code


Library
/
assignments-page-evidence-fixed.tsx


"use client"

import Link from "next/link"
import {
  FormEvent,
  ReactNode,
  useCallback,
  useEffect,
  useState,
} from "react"
import {
  CalendarClock,
  Check,
  CheckCircle2,
  ClipboardCheck,
  Eye,
  FileImage,
  LoaderCircle,
  Play,
  Plus,
  RefreshCw,
  RotateCcw,
  Search,
  Send,
  ShieldCheck,
  Upload,
  UserCheck,
  X,
} from "lucide-react"

import { useAuth } from "@/components/auth/auth-provider"
import { apiFetch } from "@/lib/api"
import type {
  Assignment,
  AssignmentActivity,
  AssignmentListResponse,
  AssignmentStatus,
  AssignmentSummary,
  AssignmentUserSummary,
  Department,
  Evidence,
  Incident,
  IncidentListResponse,
  IncidentPriority,
  User,
} from "@/lib/types"


const EMPTY_SUMMARY: AssignmentSummary = {
  total_visible: 0,
  my_open: 0,
  pending_acceptance: 0,
  in_progress: 0,
  awaiting_verification: 0,
  overdue: 0,
  completed: 0,
}

type CreateForm = {
  incident_id: string
  department_id: string
  assigned_user_id: string
  title: string
  instructions: string
  priority: IncidentPriority | ""
  due_at: string
}

const EMPTY_CREATE: CreateForm = {
  incident_id: "",
  department_id: "",
  assigned_user_id: "",
  title: "",
  instructions: "",
  priority: "",
  due_at: "",
}

type ActionMode =
    | "reject"
    | "submit"
    | "verify"
    | "cancel"
    | null


export default function AssignmentsPage() {
  const { user } = useAuth()

  const [assignments, setAssignments] = useState<Assignment[]>([])
  const [summary, setSummary] = useState(EMPTY_SUMMARY)

  const [search, setSearch] = useState("")
  const [statusFilter, setStatusFilter] =
      useState<AssignmentStatus | "">("")
  const [mineOnly, setMineOnly] = useState(false)

  const [loading, setLoading] = useState(true)
  const [refreshing, setRefreshing] = useState(false)
  const [error, setError] = useState("")

  const [selected, setSelected] =
      useState<Assignment | null>(null)
  const [timeline, setTimeline] =
      useState<AssignmentActivity[]>([])
  const [incidentEvidence, setIncidentEvidence] =
      useState<Evidence[]>([])
  const [detailLoading, setDetailLoading] = useState(false)

  const [createOpen, setCreateOpen] = useState(false)
  const [createBusy, setCreateBusy] = useState(false)
  const [createError, setCreateError] = useState("")
  const [createForm, setCreateForm] =
      useState<CreateForm>(EMPTY_CREATE)

  const [incidents, setIncidents] = useState<Incident[]>([])
  const [departments, setDepartments] = useState<Department[]>([])
  const [assignees, setAssignees] =
      useState<AssignmentUserSummary[]>([])

  const [actionMode, setActionMode] =
      useState<ActionMode>(null)
  const [actionText, setActionText] = useState("")
  const [selectedEvidenceIds, setSelectedEvidenceIds] =
      useState<number[]>([])
  const [actionBusy, setActionBusy] = useState(false)
  const [actionError, setActionError] = useState("")

  const [completionFile, setCompletionFile] =
      useState<File | null>(null)
  const [completionDescription, setCompletionDescription] =
      useState("")
  const [completionUploadBusy, setCompletionUploadBusy] =
      useState(false)
  const [completionUploadError, setCompletionUploadError] =
      useState("")

  const canCreate = hasPermission(user, "assignments.create")
  const canVerify = hasPermission(user, "assignments.verify")
  const canManage =
      Boolean(user?.is_superuser) ||
      hasPermission(user, "assignments.manage_all") ||
      hasPermission(user, "assignments.manage_department")

  const load = useCallback(
      async (manual = false) => {
        if (manual) {
          setRefreshing(true)
        } else {
          setLoading(true)
        }

        setError("")

        const params = new URLSearchParams({
          page: "1",
          page_size: "100",
        })

        if (search.trim()) {
          params.set("search", search.trim())
        }
        if (statusFilter) {
          params.set("status", statusFilter)
        }
        if (mineOnly) {
          params.set("mine", "true")
        }

        try {
          const [list, counts] = await Promise.all([
            apiFetch<AssignmentListResponse>(
                `/assignments?${params.toString()}`,
            ),
            apiFetch<AssignmentSummary>(
                "/assignments/summary",
            ),
          ])

          setAssignments(list.items)
          setSummary(counts)
        } catch (requestError) {
          setError(
              requestError instanceof Error
                  ? requestError.message
                  : "Unable to load assignments.",
          )
        } finally {
          setLoading(false)
          setRefreshing(false)
        }
      },
      [mineOnly, search, statusFilter],
  )

  useEffect(() => {
    void load()
  }, [load])

  async function openAssignment(assignment: Assignment) {
    setSelected(assignment)
    setDetailLoading(true)
    setActionError("")

    try {
      const [fresh, activities, evidence] =
          await Promise.all([
            apiFetch<Assignment>(
                `/assignments/${assignment.id}`,
            ),
            apiFetch<AssignmentActivity[]>(
                `/assignments/${assignment.id}/timeline`,
            ),
            apiFetch<Evidence[]>(
                `/evidence/incidents/${assignment.incident_id}`,
            ),
          ])

      setSelected(fresh)
      setTimeline(activities)
      setIncidentEvidence(evidence)
    } catch (requestError) {
      setActionError(
          requestError instanceof Error
              ? requestError.message
              : "Unable to load assignment details.",
      )
    } finally {
      setDetailLoading(false)
    }
  }

  async function loadIncidentEvidence(
      incidentId: number,
  ) {
    const evidence = await apiFetch<Evidence[]>(
        `/evidence/incidents/${incidentId}`,
    )
    setIncidentEvidence(evidence)
    return evidence
  }

  async function uploadCompletionEvidence() {
    if (!selected || !completionFile) {
      setCompletionUploadError(
          "Choose a file before uploading.",
      )
      return
    }

    setCompletionUploadBusy(true)
    setCompletionUploadError("")

    try {
      const formData = new FormData()
      formData.append("file", completionFile)

      if (completionDescription.trim()) {
        formData.append(
            "description",
            completionDescription.trim(),
        )
      }

      formData.append(
          "is_anonymized",
          "false",
      )
      formData.append(
          "is_enforcement_evidence",
          "true",
      )

      const uploaded = await apiFetch<Evidence>(
          `/evidence/incidents/${selected.incident_id}`,
          {
            method: "POST",
            body: formData,
          },
      )

      const refreshedEvidence =
          await loadIncidentEvidence(
              selected.incident_id,
          )

      setSelectedEvidenceIds((current) =>
          current.includes(uploaded.id)
              ? current
              : [...current, uploaded.id],
      )

      setCompletionFile(null)
      setCompletionDescription("")

      if (
          !refreshedEvidence.some(
              (item) => item.id === uploaded.id,
          )
      ) {
        setIncidentEvidence((current) => [
          uploaded,
          ...current,
        ])
      }
    } catch (requestError) {
      setCompletionUploadError(
          requestError instanceof Error
              ? requestError.message
              : "Unable to upload completion evidence.",
      )
    } finally {
      setCompletionUploadBusy(false)
    }
  }

  async function refreshSelected(id: number) {
    const fresh = await apiFetch<Assignment>(
        `/assignments/${id}`,
    )
    const activities =
        await apiFetch<AssignmentActivity[]>(
            `/assignments/${id}/timeline`,
        )
    const evidence = await apiFetch<Evidence[]>(
        `/evidence/incidents/${fresh.incident_id}`,
    )

    setSelected(fresh)
    setTimeline(activities)
    setIncidentEvidence(evidence)
    await load()
  }

  async function simpleAction(
      action: "accept" | "start",
  ) {
    if (!selected) return

    setActionBusy(true)
    setActionError("")

    try {
      await apiFetch<Assignment>(
          `/assignments/${selected.id}/${action}`,
          { method: "POST" },
      )
      await refreshSelected(selected.id)
    } catch (requestError) {
      setActionError(
          requestError instanceof Error
              ? requestError.message
              : `Unable to ${action} assignment.`,
      )
    } finally {
      setActionBusy(false)
    }
  }

  async function performAction(approved?: boolean) {
    if (!selected || !actionMode) return

    setActionBusy(true)
    setActionError("")

    try {
      if (actionMode === "reject") {
        await apiFetch<Assignment>(
            `/assignments/${selected.id}/reject`,
            {
              method: "POST",
              body: JSON.stringify({
                reason: actionText.trim(),
              }),
            },
        )
      }

      if (actionMode === "cancel") {
        await apiFetch<Assignment>(
            `/assignments/${selected.id}/cancel`,
            {
              method: "POST",
              body: JSON.stringify({
                reason: actionText.trim(),
              }),
            },
        )
      }

      if (actionMode === "submit") {
        await apiFetch<Assignment>(
            `/assignments/${selected.id}/submit`,
            {
              method: "POST",
              body: JSON.stringify({
                completion_notes: actionText.trim(),
                evidence_ids: selectedEvidenceIds,
              }),
            },
        )
      }

      if (actionMode === "verify") {
        await apiFetch<Assignment>(
            `/assignments/${selected.id}/verify`,
            {
              method: "POST",
              body: JSON.stringify({
                approved: Boolean(approved),
                notes: actionText.trim(),
              }),
            },
        )
      }

      setActionMode(null)
      setActionText("")
      setSelectedEvidenceIds([])
      setCompletionFile(null)
      setCompletionDescription("")
      setCompletionUploadError("")
      await refreshSelected(selected.id)
    } catch (requestError) {
      setActionError(
          requestError instanceof Error
              ? requestError.message
              : "Unable to update assignment.",
      )
    } finally {
      setActionBusy(false)
    }
  }

  async function openCreate() {
    setCreateOpen(true)
    setCreateError("")
    setCreateForm({
      ...EMPTY_CREATE,
      department_id:
          user?.department_id?.toString() ?? "",
    })

    try {
      const incidentResponse =
          await apiFetch<IncidentListResponse>(
              "/incidents?page=1&page_size=100",
          )

      setIncidents(
          incidentResponse.items.filter(
              (incident) =>
                  !["resolved", "dismissed"].includes(
                      incident.status,
                  ),
          ),
      )

      if (user?.is_superuser) {
        try {
          const response =
              await apiFetch<Department[]>(
                  "/departments",
              )
          setDepartments(
              response.filter(
                  (department) => department.is_active,
              ),
          )
        } catch {
          setDepartments([])
        }
      } else if (user?.department) {
        setDepartments([user.department])
      }

      const departmentId = user?.department_id
      const response =
          await apiFetch<AssignmentUserSummary[]>(
              `/assignments/assignees${
                  departmentId
                      ? `?department_id=${departmentId}`
                      : ""
              }`,
          )
      setAssignees(response)
    } catch (requestError) {
      setCreateError(
          requestError instanceof Error
              ? requestError.message
              : "Unable to load assignment options.",
      )
    }
  }

  async function loadAssignees(departmentId: string) {
    setCreateForm((current) => ({
      ...current,
      department_id: departmentId,
      assigned_user_id: "",
    }))
    setAssignees([])

    if (!departmentId) return

    try {
      setAssignees(
          await apiFetch<AssignmentUserSummary[]>(
              `/assignments/assignees?department_id=${departmentId}`,
          ),
      )
    } catch (requestError) {
      setCreateError(
          requestError instanceof Error
              ? requestError.message
              : "Unable to load assignees.",
      )
    }
  }

  function chooseIncident(value: string) {
    const incident = incidents.find(
        (item) => item.id === Number(value),
    )

    const departmentId =
        incident?.department_id?.toString() ||
        createForm.department_id

    setCreateForm((current) => ({
      ...current,
      incident_id: value,
      department_id: departmentId,
      assigned_user_id: "",
      title: incident?.title ?? "",
      instructions: incident?.description ?? "",
      priority: incident?.priority ?? "",
    }))

    if (departmentId) {
      void loadAssignees(departmentId)
    }
  }

  async function submitCreate(
      event: FormEvent<HTMLFormElement>,
  ) {
    event.preventDefault()

    setCreateBusy(true)
    setCreateError("")

    try {
      const created = await apiFetch<Assignment>(
          "/assignments",
          {
            method: "POST",
            body: JSON.stringify({
              incident_id: Number(
                  createForm.incident_id,
              ),
              assigned_user_id: Number(
                  createForm.assigned_user_id,
              ),
              department_id: Number(
                  createForm.department_id,
              ),
              title:
                  createForm.title.trim() || null,
              instructions:
                  createForm.instructions.trim() ||
                  null,
              priority:
                  createForm.priority || null,
              due_at: createForm.due_at
                  ? new Date(
                      createForm.due_at,
                  ).toISOString()
                  : null,
            }),
          },
      )

      setCreateOpen(false)
      await load()
      await openAssignment(created)
    } catch (requestError) {
      setCreateError(
          requestError instanceof Error
              ? requestError.message
              : "Unable to create assignment.",
      )
    } finally {
      setCreateBusy(false)
    }
  }

  return (
      <>
        <div className="space-y-6">
          <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
            <div>
              <p className="text-sm font-medium text-primary">
                Core Operations
              </p>
              <h2 className="mt-1 text-2xl font-semibold">
                Assignments
              </h2>
              <p className="mt-1 max-w-3xl text-sm text-muted-foreground">
                Turn incidents into accountable work, track officer
                acceptance and progress, require completion evidence,
                and verify work before closing an incident.
              </p>
            </div>

            <div className="flex gap-2">
              <button
                  type="button"
                  onClick={() => void load(true)}
                  disabled={refreshing}
                  className="inline-flex h-10 items-center gap-2 rounded-md border px-4 text-sm font-medium hover:bg-muted disabled:opacity-50"
              >
                <RefreshCw
                    className={`size-4 ${
                        refreshing ? "animate-spin" : ""
                    }`}
                />
                Refresh
              </button>

              {canCreate && (
                  <button
                      type="button"
                      onClick={() => void openCreate()}
                      className="inline-flex h-10 items-center gap-2 rounded-md bg-primary px-4 text-sm font-medium text-primary-foreground"
                  >
                    <Plus className="size-4" />
                    Create assignment
                  </button>
              )}
            </div>
          </div>

          {error && <ErrorBox message={error} />}

          <div className="grid grid-cols-2 gap-3 xl:grid-cols-6">
            <SummaryCard
                label="Visible"
                value={summary.total_visible}
                icon={<ClipboardCheck className="size-5" />}
            />
            <SummaryCard
                label="My open"
                value={summary.my_open}
                icon={<UserCheck className="size-5" />}
            />
            <SummaryCard
                label="Awaiting acceptance"
                value={summary.pending_acceptance}
                icon={<CalendarClock className="size-5" />}
            />
            <SummaryCard
                label="In progress"
                value={summary.in_progress}
                icon={<Play className="size-5" />}
            />
            <SummaryCard
                label="Verification"
                value={summary.awaiting_verification}
                icon={<ShieldCheck className="size-5" />}
            />
            <SummaryCard
                label="Overdue"
                value={summary.overdue}
                icon={<CalendarClock className="size-5" />}
                critical={summary.overdue > 0}
            />
          </div>

          <div className="overflow-hidden rounded-xl border bg-card">
            <div className="flex flex-col gap-3 border-b p-4 lg:flex-row">
              <div className="relative flex-1">
                <Search className="absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
                <input
                    value={search}
                    onChange={(event) =>
                        setSearch(event.target.value)
                    }
                    placeholder="Search assignment number, title or instructions..."
                    className="h-10 w-full rounded-md border bg-background pl-9 pr-3 text-sm"
                />
              </div>

              <select
                  value={statusFilter}
                  onChange={(event) =>
                      setStatusFilter(
                          event.target.value as
                              | AssignmentStatus
                              | "",
                      )
                  }
                  className="h-10 rounded-md border bg-background px-3 text-sm"
              >
                <option value="">All statuses</option>
                <option value="pending">Pending</option>
                <option value="accepted">Accepted</option>
                <option value="in_progress">
                  In progress
                </option>
                <option value="submitted">
                  Awaiting verification
                </option>
                <option value="completed">
                  Completed
                </option>
                <option value="rejected">
                  Rejected
                </option>
                <option value="cancelled">
                  Cancelled
                </option>
              </select>

              <label className="flex h-10 items-center gap-2 rounded-md border px-3 text-sm">
                <input
                    type="checkbox"
                    checked={mineOnly}
                    onChange={(event) =>
                        setMineOnly(event.target.checked)
                    }
                />
                Assigned to me
              </label>
            </div>

            {loading ? (
                <Loading text="Loading assignments..." />
            ) : assignments.length === 0 ? (
                <div className="flex min-h-56 flex-col items-center justify-center p-8 text-center">
                  <ClipboardCheck className="size-8 text-muted-foreground/60" />
                  <p className="mt-3 text-sm font-medium">
                    No assignments found
                  </p>
                  <p className="mt-1 text-xs text-muted-foreground">
                    Assigned incident work will appear here.
                  </p>
                </div>
            ) : (
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead className="bg-muted/35 text-left text-xs uppercase tracking-wide text-muted-foreground">
                    <tr>
                      <th className="px-4 py-3">
                        Assignment
                      </th>
                      <th className="px-4 py-3">
                        Incident
                      </th>
                      <th className="px-4 py-3">
                        Assigned employee
                      </th>
                      <th className="px-4 py-3">
                        Due
                      </th>
                      <th className="px-4 py-3">
                        Status
                      </th>
                      <th className="px-4 py-3 text-right">
                        Action
                      </th>
                    </tr>
                    </thead>

                    <tbody>
                    {assignments.map((assignment) => (
                        <tr
                            key={assignment.id}
                            className="border-t hover:bg-muted/20"
                        >
                          <td className="px-4 py-3">
                            <p className="font-medium">
                              {assignment.title}
                            </p>
                            <p className="mt-1 font-mono text-[11px] text-muted-foreground">
                              {assignment.assignment_number}
                            </p>
                          </td>

                          <td className="px-4 py-3">
                            <p className="font-mono text-xs">
                              {assignment.incident.incident_number}
                            </p>
                            <p className="mt-1 max-w-[240px] truncate text-xs text-muted-foreground">
                              {assignment.incident.title}
                            </p>
                          </td>

                          <td className="px-4 py-3">
                            <p>
                              {assignment.assigned_user.full_name}
                            </p>
                            <p className="mt-1 text-xs text-muted-foreground">
                              {assignment.department.name}
                            </p>
                          </td>

                          <td className="px-4 py-3">
                            <DueDate
                                dueAt={assignment.due_at}
                                status={assignment.status}
                            />
                          </td>

                          <td className="px-4 py-3">
                            <StatusBadge
                                status={assignment.status}
                            />
                          </td>

                          <td className="px-4 py-3 text-right">
                            <button
                                type="button"
                                onClick={() =>
                                    void openAssignment(
                                        assignment,
                                    )
                                }
                                className="inline-flex h-8 items-center gap-1.5 rounded-md border px-3 text-xs font-medium hover:bg-muted"
                            >
                              <Eye className="size-3.5" />
                              Open
                            </button>
                          </td>
                        </tr>
                    ))}
                    </tbody>
                  </table>
                </div>
            )}
          </div>
        </div>

        {selected && (
            <Drawer
                title={selected.title}
                subtitle={selected.assignment_number}
                onClose={() => {
                  setSelected(null)
                  setActionMode(null)
                }}
            >
              {actionError && (
                  <ErrorBox message={actionError} />
              )}

              {detailLoading ? (
                  <Loading text="Loading assignment..." />
              ) : (
                  <div className="space-y-6">
                    <div className="flex flex-wrap gap-2">
                      <StatusBadge status={selected.status} />
                      <PriorityBadge
                          priority={selected.priority}
                      />
                      {selected.due_at && (
                          <span className="rounded-full border px-2.5 py-1 text-xs text-muted-foreground">
                    Due {formatDate(selected.due_at)}
                  </span>
                      )}
                    </div>

                    <div className="grid gap-3 sm:grid-cols-2">
                      <Detail
                          label="Assigned to"
                          value={selected.assigned_user.full_name}
                      />
                      <Detail
                          label="Assigned by"
                          value={selected.assigned_by.full_name}
                      />
                      <Detail
                          label="Department"
                          value={selected.department.name}
                      />
                      <Detail
                          label="Incident"
                          value={selected.incident.incident_number}
                      />
                    </div>

                    <Section title="Instructions">
                      <p className="whitespace-pre-wrap text-sm leading-6 text-muted-foreground">
                        {selected.instructions ||
                            "No additional instructions were provided."}
                      </p>
                    </Section>

                    {selected.completion_notes && (
                        <Section title="Completion submission">
                          <p className="whitespace-pre-wrap text-sm leading-6">
                            {selected.completion_notes}
                          </p>

                          {selected.evidence.length > 0 && (
                              <div className="mt-3 grid gap-2 sm:grid-cols-2">
                                {selected.evidence.map(
                                    (evidence) => (
                                        <div
                                            key={evidence.id}
                                            className="flex items-center gap-2 rounded-md border p-3 text-xs"
                                        >
                                          <FileImage className="size-4 text-primary" />
                                          <span className="truncate">
                              {evidence.original_file_name}
                            </span>
                                        </div>
                                    ),
                                )}
                              </div>
                          )}
                        </Section>
                    )}

                    {selected.verification_notes && (
                        <Section title="Verification notes">
                          <p className="whitespace-pre-wrap text-sm leading-6">
                            {selected.verification_notes}
                          </p>
                        </Section>
                    )}

                    {selected.rejection_reason && (
                        <div className="rounded-lg border border-amber-500/30 bg-amber-500/10 p-4 text-sm">
                          <p className="font-medium">
                            Return / rejection reason
                          </p>
                          <p className="mt-1 text-muted-foreground">
                            {selected.rejection_reason}
                          </p>
                        </div>
                    )}

                    <AssignmentActions
                        assignment={selected}
                        currentUser={user}
                        canVerify={canVerify}
                        canManage={canManage}
                        busy={actionBusy}
                        onAccept={() =>
                            void simpleAction("accept")
                        }
                        onStart={() =>
                            void simpleAction("start")
                        }
                        onReject={() =>
                            setActionMode("reject")
                        }
                        onSubmit={() => {
                          setActionMode("submit")
                          setCompletionFile(null)
                          setCompletionDescription("")
                          setCompletionUploadError("")
                          setSelectedEvidenceIds([])
                        }}
                        onVerify={() =>
                            setActionMode("verify")
                        }
                        onCancel={() =>
                            setActionMode("cancel")
                        }
                    />

                    <Section title="Assignment timeline">
                      <div className="space-y-4">
                        {timeline.map((activity) => (
                            <div
                                key={activity.id}
                                className="border-l-2 border-primary/30 pl-4"
                            >
                              <p className="text-sm font-medium">
                                {humanize(activity.action)}
                              </p>
                              <p className="mt-1 text-xs text-muted-foreground">
                                {activity.actor.full_name} ·{" "}
                                {formatDate(activity.created_at)}
                              </p>
                              {activity.notes && (
                                  <p className="mt-2 text-sm leading-6 text-muted-foreground">
                                    {activity.notes}
                                  </p>
                              )}
                            </div>
                        ))}
                      </div>
                    </Section>

                    <Link
                        href="/incidents"
                        className="inline-flex text-xs font-medium text-primary hover:underline"
                    >
                      Open related incident in Incident Management
                    </Link>
                  </div>
              )}
            </Drawer>
        )}

        {createOpen && (
            <Modal
                title="Create operational assignment"
                onClose={() => {
                  if (!createBusy) setCreateOpen(false)
                }}
            >
              <form
                  onSubmit={submitCreate}
                  className="space-y-4"
              >
                {createError && (
                    <ErrorBox message={createError} />
                )}

                <FieldLabel label="Incident">
                  <select
                      required
                      value={createForm.incident_id}
                      onChange={(event) =>
                          chooseIncident(event.target.value)
                      }
                      className={inputClass}
                  >
                    <option value="">
                      Select incident
                    </option>
                    {incidents.map((incident) => (
                        <option
                            key={incident.id}
                            value={incident.id}
                        >
                          {incident.incident_number} —{" "}
                          {incident.title}
                        </option>
                    ))}
                  </select>
                </FieldLabel>

                <div className="grid gap-4 sm:grid-cols-2">
                  <FieldLabel label="Department">
                    <select
                        required
                        value={createForm.department_id}
                        onChange={(event) =>
                            void loadAssignees(
                                event.target.value,
                            )
                        }
                        className={inputClass}
                    >
                      <option value="">
                        Select department
                      </option>
                      {departments.map((department) => (
                          <option
                              key={department.id}
                              value={department.id}
                          >
                            {department.name}
                          </option>
                      ))}
                    </select>
                  </FieldLabel>

                  <FieldLabel label="Assigned employee">
                    <select
                        required
                        value={
                          createForm.assigned_user_id
                        }
                        onChange={(event) =>
                            setCreateForm((current) => ({
                              ...current,
                              assigned_user_id:
                              event.target.value,
                            }))
                        }
                        className={inputClass}
                    >
                      <option value="">
                        Select employee
                      </option>
                      {assignees.map((employee) => (
                          <option
                              key={employee.id}
                              value={employee.id}
                          >
                            {employee.full_name}
                          </option>
                      ))}
                    </select>
                  </FieldLabel>
                </div>

                <FieldLabel label="Assignment title">
                  <input
                      required
                      value={createForm.title}
                      onChange={(event) =>
                          setCreateForm((current) => ({
                            ...current,
                            title: event.target.value,
                          }))
                      }
                      className={inputClass}
                  />
                </FieldLabel>

                <FieldLabel label="Instructions">
              <textarea
                  rows={4}
                  value={createForm.instructions}
                  onChange={(event) =>
                      setCreateForm((current) => ({
                        ...current,
                        instructions:
                        event.target.value,
                      }))
                  }
                  className={`${inputClass} h-auto py-2.5`}
              />
                </FieldLabel>

                <div className="grid gap-4 sm:grid-cols-2">
                  <FieldLabel label="Priority">
                    <select
                        value={createForm.priority}
                        onChange={(event) =>
                            setCreateForm((current) => ({
                              ...current,
                              priority:
                                  event.target
                                      .value as
                                      | IncidentPriority
                                      | "",
                            }))
                        }
                        className={inputClass}
                    >
                      <option value="">
                        Use incident priority
                      </option>
                      <option value="low">Low</option>
                      <option value="medium">
                        Medium
                      </option>
                      <option value="high">High</option>
                      <option value="critical">
                        Critical
                      </option>
                    </select>
                  </FieldLabel>

                  <FieldLabel label="Due date/time">
                    <input
                        type="datetime-local"
                        value={createForm.due_at}
                        onChange={(event) =>
                            setCreateForm((current) => ({
                              ...current,
                              due_at: event.target.value,
                            }))
                        }
                        className={inputClass}
                    />
                  </FieldLabel>
                </div>

                <div className="flex justify-end gap-2 border-t pt-4">
                  <button
                      type="button"
                      onClick={() =>
                          setCreateOpen(false)
                      }
                      disabled={createBusy}
                      className="h-10 rounded-md border px-4 text-sm font-medium"
                  >
                    Cancel
                  </button>
                  <button
                      type="submit"
                      disabled={createBusy}
                      className="h-10 rounded-md bg-primary px-4 text-sm font-medium text-primary-foreground disabled:opacity-50"
                  >
                    {createBusy
                        ? "Creating..."
                        : "Create assignment"}
                  </button>
                </div>
              </form>
            </Modal>
        )}

        {actionMode && selected && (
            <Modal
                title={actionTitle(actionMode)}
                onClose={() => {
                  if (!actionBusy) setActionMode(null)
                }}
            >
              <div className="space-y-4">
                {actionError && (
                    <ErrorBox message={actionError} />
                )}

                {actionMode === "submit" && (
                    <div className="space-y-4">
                      <div>
                        <p className="text-sm font-medium">
                          Upload completion evidence
                        </p>
                        <p className="mt-1 text-xs leading-5 text-muted-foreground">
                          Upload evidence here without leaving the assignment.
                          The file is attached to the related incident and
                          automatically selected as proof of completion.
                        </p>
                      </div>

                      {completionUploadError && (
                          <ErrorBox
                              message={completionUploadError}
                          />
                      )}

                      <div className="rounded-lg border bg-muted/15 p-4">
                        <div className="grid gap-3">
                          <input
                              type="file"
                              accept="image/jpeg,image/png,image/webp,video/mp4,video/webm,audio/mpeg,audio/wav,application/pdf"
                              onChange={(event) =>
                                  setCompletionFile(
                                      event.target.files?.[0] ?? null,
                                  )
                              }
                              className="block w-full text-sm file:mr-3 file:rounded-md file:border-0 file:bg-primary file:px-3 file:py-2 file:text-xs file:font-medium file:text-primary-foreground"
                          />

                          <input
                              type="text"
                              value={completionDescription}
                              onChange={(event) =>
                                  setCompletionDescription(
                                      event.target.value,
                                  )
                              }
                              placeholder="Evidence description (optional)"
                              className={inputClass}
                          />

                          <div className="flex items-center justify-between gap-3">
                            <p className="min-w-0 truncate text-xs text-muted-foreground">
                              {completionFile
                                  ? completionFile.name
                                  : "No file selected"}
                            </p>

                            <button
                                type="button"
                                onClick={() =>
                                    void uploadCompletionEvidence()
                                }
                                disabled={
                                    completionUploadBusy ||
                                    !completionFile
                                }
                                className="inline-flex h-9 shrink-0 items-center gap-2 rounded-md bg-primary px-3 text-xs font-medium text-primary-foreground disabled:opacity-40"
                            >
                              {completionUploadBusy ? (
                                  <LoaderCircle className="size-4 animate-spin" />
                              ) : (
                                  <Upload className="size-4" />
                              )}
                              {completionUploadBusy
                                  ? "Uploading..."
                                  : "Upload evidence"}
                            </button>
                          </div>
                        </div>
                      </div>

                      <div>
                        <p className="text-sm font-medium">
                          Evidence for this incident
                        </p>
                        <p className="mt-1 text-xs text-muted-foreground">
                          Select at least one item as completion proof.
                          Newly uploaded evidence is selected automatically.
                        </p>
                      </div>

                      {incidentEvidence.length === 0 ? (
                          <div className="rounded-lg border border-dashed p-4 text-sm text-muted-foreground">
                            No evidence has been uploaded yet. Choose a file
                            above and upload it before submitting the work.
                          </div>
                      ) : (
                          <div className="max-h-52 space-y-2 overflow-y-auto rounded-lg border p-3">
                            {incidentEvidence.map(
                                (evidence) => (
                                    <label
                                        key={evidence.id}
                                        className="flex items-center gap-3 rounded-md p-2 text-sm hover:bg-muted"
                                    >
                                      <input
                                          type="checkbox"
                                          checked={selectedEvidenceIds.includes(
                                              evidence.id,
                                          )}
                                          onChange={() =>
                                              setSelectedEvidenceIds(
                                                  (current) =>
                                                      current.includes(
                                                          evidence.id,
                                                      )
                                                          ? current.filter(
                                                              (id) =>
                                                                  id !== evidence.id,
                                                          )
                                                          : [
                                                            ...current,
                                                            evidence.id,
                                                          ],
                                              )
                                          }
                                      />
                                      <FileImage className="size-4 text-primary" />
                                      <div className="min-w-0 flex-1">
                                        <p className="truncate">
                                          {evidence.original_file_name}
                                        </p>
                                        <p className="mt-0.5 text-[11px] text-muted-foreground">
                                          {evidence.evidence_type} ·{" "}
                                          {formatFileSize(
                                              evidence.file_size_bytes,
                                          )}
                                        </p>
                                      </div>
                                    </label>
                                ),
                            )}
                          </div>
                      )}
                    </div>
                )}

                <FieldLabel
                    label={actionPrompt(actionMode)}
                >
              <textarea
                  rows={5}
                  value={actionText}
                  onChange={(event) =>
                      setActionText(event.target.value)
                  }
                  className={`${inputClass} h-auto py-2.5`}
              />
                </FieldLabel>

                <div className="flex flex-wrap justify-end gap-2">
                  <button
                      type="button"
                      onClick={() =>
                          setActionMode(null)
                      }
                      disabled={actionBusy}
                      className="h-10 rounded-md border px-4 text-sm font-medium"
                  >
                    Cancel
                  </button>

                  {actionMode === "verify" ? (
                      <>
                        <button
                            type="button"
                            onClick={() =>
                                void performAction(false)
                            }
                            disabled={
                                actionBusy ||
                                actionText.trim().length < 3
                            }
                            className="inline-flex h-10 items-center gap-2 rounded-md border border-amber-500/40 px-4 text-sm font-medium text-amber-500 disabled:opacity-40"
                        >
                          <RotateCcw className="size-4" />
                          Return for work
                        </button>

                        <button
                            type="button"
                            onClick={() =>
                                void performAction(true)
                            }
                            disabled={
                                actionBusy ||
                                actionText.trim().length < 3
                            }
                            className="inline-flex h-10 items-center gap-2 rounded-md bg-emerald-600 px-4 text-sm font-medium text-white disabled:opacity-40"
                        >
                          <CheckCircle2 className="size-4" />
                          Verify & close incident
                        </button>
                      </>
                  ) : (
                      <button
                          type="button"
                          onClick={() =>
                              void performAction()
                          }
                          disabled={
                              actionBusy ||
                              actionText.trim().length < 3 ||
                              (actionMode === "submit" &&
                                  selectedEvidenceIds.length === 0)
                          }
                          className="h-10 rounded-md bg-primary px-4 text-sm font-medium text-primary-foreground disabled:opacity-40"
                      >
                        Confirm
                      </button>
                  )}
                </div>
              </div>
            </Modal>
        )}
      </>
  )
}


function AssignmentActions({
                             assignment,
                             currentUser,
                             canVerify,
                             canManage,
                             busy,
                             onAccept,
                             onStart,
                             onReject,
                             onSubmit,
                             onVerify,
                             onCancel,
                           }: {
  assignment: Assignment
  currentUser: User | null
  canVerify: boolean
  canManage: boolean
  busy: boolean
  onAccept: () => void
  onStart: () => void
  onReject: () => void
  onSubmit: () => void
  onVerify: () => void
  onCancel: () => void
}) {
  const mine =
      currentUser?.id === assignment.assigned_user_id

  return (
      <Section title="Available actions">
        <div className="flex flex-wrap gap-2">
          {mine && assignment.status === "pending" && (
              <>
                <ActionButton
                    label="Accept"
                    icon={<Check className="size-4" />}
                    onClick={onAccept}
                    disabled={busy}
                    primary
                />
                <ActionButton
                    label="Reject"
                    icon={<X className="size-4" />}
                    onClick={onReject}
                    disabled={busy}
                />
              </>
          )}

          {mine &&
              assignment.status === "accepted" && (
                  <ActionButton
                      label="Start work"
                      icon={<Play className="size-4" />}
                      onClick={onStart}
                      disabled={busy}
                      primary
                  />
              )}

          {mine &&
              assignment.status ===
              "in_progress" && (
                  <ActionButton
                      label="Submit completion"
                      icon={<Send className="size-4" />}
                      onClick={onSubmit}
                      disabled={busy}
                      primary
                  />
              )}

          {canVerify &&
              assignment.status === "submitted" && (
                  <ActionButton
                      label="Verify work"
                      icon={<ShieldCheck className="size-4" />}
                      onClick={onVerify}
                      disabled={busy}
                      primary
                  />
              )}

          {canManage &&
              ![
                "completed",
                "rejected",
                "cancelled",
              ].includes(assignment.status) && (
                  <ActionButton
                      label="Cancel assignment"
                      icon={<X className="size-4" />}
                      onClick={onCancel}
                      disabled={busy}
                  />
              )}
        </div>
      </Section>
  )
}


function ActionButton({
                        label,
                        icon,
                        onClick,
                        disabled,
                        primary = false,
                      }: {
  label: string
  icon: ReactNode
  onClick: () => void
  disabled: boolean
  primary?: boolean
}) {
  return (
      <button
          type="button"
          onClick={onClick}
          disabled={disabled}
          className={`inline-flex h-9 items-center gap-2 rounded-md px-3 text-xs font-medium disabled:opacity-40 ${
              primary
                  ? "bg-primary text-primary-foreground"
                  : "border hover:bg-muted"
          }`}
      >
        {icon}
        {label}
      </button>
  )
}


function SummaryCard({
                       label,
                       value,
                       icon,
                       critical = false,
                     }: {
  label: string
  value: number
  icon: ReactNode
  critical?: boolean
}) {
  return (
      <div className="rounded-xl border bg-card p-4">
        <div className="flex items-start justify-between">
          <div>
            <p className="text-xs text-muted-foreground">
              {label}
            </p>
            <p className="mt-2 font-mono text-2xl font-semibold">
              {value}
            </p>
          </div>
          <div
              className={`rounded-lg p-2.5 ${
                  critical
                      ? "bg-destructive/10 text-destructive"
                      : "bg-primary/10 text-primary"
              }`}
          >
            {icon}
          </div>
        </div>
      </div>
  )
}


function Detail({
                  label,
                  value,
                }: {
  label: string
  value: string
}) {
  return (
      <div className="rounded-lg border p-4">
        <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
          {label}
        </p>
        <p className="mt-2 text-sm font-medium">
          {value}
        </p>
      </div>
  )
}


function Section({
                   title,
                   children,
                 }: {
  title: string
  children: ReactNode
}) {
  return (
      <section>
        <h4 className="mb-3 text-sm font-semibold">
          {title}
        </h4>
        {children}
      </section>
  )
}


function Drawer({
                  title,
                  subtitle,
                  children,
                  onClose,
                }: {
  title: string
  subtitle: string
  children: ReactNode
  onClose: () => void
}) {
  return (
      <div className="fixed inset-0 z-50 flex justify-end bg-black/50">
        <div className="h-full w-full max-w-3xl overflow-y-auto border-l bg-background shadow-2xl">
          <div className="sticky top-0 z-10 flex items-center justify-between border-b bg-background/95 px-5 py-4 backdrop-blur">
            <div>
              <p className="font-mono text-xs text-muted-foreground">
                {subtitle}
              </p>
              <h3 className="mt-1 text-lg font-semibold">
                {title}
              </h3>
            </div>
            <button
                type="button"
                onClick={onClose}
                className="flex size-9 items-center justify-center rounded-md border hover:bg-muted"
            >
              <X className="size-4" />
            </button>
          </div>
          <div className="p-5">{children}</div>
        </div>
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
      <div className="fixed inset-0 z-[60] flex items-center justify-center bg-black/55 p-4">
        <div className="max-h-[90vh] w-full max-w-2xl overflow-y-auto rounded-xl border bg-background shadow-2xl">
          <div className="sticky top-0 z-10 flex items-center justify-between border-b bg-background/95 px-5 py-4 backdrop-blur">
            <h3 className="font-semibold">{title}</h3>
            <button
                type="button"
                onClick={onClose}
                className="flex size-8 items-center justify-center rounded-md border"
            >
              <X className="size-4" />
            </button>
          </div>
          <div className="p-5">{children}</div>
        </div>
      </div>
  )
}


function FieldLabel({
                      label,
                      children,
                    }: {
  label: string
  children: ReactNode
}) {
  return (
      <label className="block text-sm font-medium">
        {label}
        <div className="mt-1">{children}</div>
      </label>
  )
}


function ErrorBox({ message }: { message: string }) {
  return (
      <div className="rounded-lg border border-destructive/30 bg-destructive/10 p-3 text-sm text-destructive">
        {message}
      </div>
  )
}


function Loading({ text }: { text: string }) {
  return (
      <div className="flex min-h-56 items-center justify-center gap-2 text-sm text-muted-foreground">
        <LoaderCircle className="size-4 animate-spin" />
        {text}
      </div>
  )
}


function StatusBadge({
                       status,
                     }: {
  status: AssignmentStatus
}) {
  const classes: Record<AssignmentStatus, string> = {
    pending: "bg-amber-500/10 text-amber-500",
    accepted: "bg-blue-500/10 text-blue-500",
    in_progress: "bg-primary/10 text-primary",
    submitted: "bg-violet-500/10 text-violet-500",
    completed: "bg-emerald-500/10 text-emerald-500",
    rejected: "bg-destructive/10 text-destructive",
    cancelled: "bg-muted text-muted-foreground",
  }

  return (
      <span
          className={`rounded-full px-2.5 py-1 text-xs font-medium ${classes[status]}`}
      >
      {humanize(status)}
    </span>
  )
}


function PriorityBadge({ priority }: { priority: string }) {
  const classes: Record<string, string> = {
    low: "bg-blue-500/10 text-blue-500",
    medium: "bg-amber-500/10 text-amber-500",
    high: "bg-orange-500/10 text-orange-500",
    critical: "bg-destructive/10 text-destructive",
  }

  return (
      <span
          className={`rounded-full px-2.5 py-1 text-xs font-medium ${
              classes[priority] ||
              "bg-muted text-muted-foreground"
          }`}
      >
      {humanize(priority)}
    </span>
  )
}


function DueDate({
                   dueAt,
                   status,
                 }: {
  dueAt?: string | null
  status: AssignmentStatus
}) {
  if (!dueAt) {
    return (
        <span className="text-xs text-muted-foreground">
        No deadline
      </span>
    )
  }

  const overdue =
      new Date(dueAt).getTime() < Date.now() &&
      !["completed", "cancelled", "rejected"].includes(
          status,
      )

  return (
      <span
          className={`text-xs ${
              overdue
                  ? "font-medium text-destructive"
                  : "text-muted-foreground"
          }`}
      >
      {formatDate(dueAt)}
        {overdue ? " · Overdue" : ""}
    </span>
  )
}


function hasPermission(
    user: User | null,
    code: string,
) {
  if (!user) return false
  if (user.is_superuser) return true

  return Boolean(
      user.role?.is_active &&
      user.role.permissions?.some(
          (permission) =>
              permission.code === code &&
              permission.is_active,
      ),
  )
}


function actionTitle(
    mode: Exclude<ActionMode, null>,
) {
  return {
    reject: "Reject assignment",
    submit: "Submit completed work",
    verify: "Verify assignment completion",
    cancel: "Cancel assignment",
  }[mode]
}


function actionPrompt(
    mode: Exclude<ActionMode, null>,
) {
  return {
    reject: "Reason for rejection",
    submit: "Completion notes",
    verify: "Supervisor verification notes",
    cancel: "Reason for cancellation",
  }[mode]
}


function humanize(value: string) {
  return value
      .replace(/\./g, " ")
      .replace(/_/g, " ")
      .replace(/\b\w/g, (character) =>
          character.toUpperCase(),
      )
}


function formatDate(value: string) {
  const date = new Date(value)

  if (Number.isNaN(date.getTime())) {
    return "Unknown"
  }

  return new Intl.DateTimeFormat("en-LS", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(date)
}


function formatFileSize(bytes: number) {
  if (!Number.isFinite(bytes) || bytes <= 0) {
    return "0 B"
  }

  const units = ["B", "KB", "MB", "GB"]
  const index = Math.min(
      Math.floor(Math.log(bytes) / Math.log(1024)),
      units.length - 1,
  )
  const value = bytes / 1024 ** index

  return `${value.toFixed(index === 0 ? 0 : 1)} ${units[index]}`
}


const inputClass =
    "h-10 w-full rounded-md border bg-background px-3 text-sm outline-none ring-offset-background focus:ring-2 focus:ring-ring"
Library
/
assignments-page-evidence-fixed.tsx


"use client"

import Link from "next/link"
import {
  FormEvent,
  ReactNode,
  useCallback,
  useEffect,
  useState,
} from "react"
import {
  CalendarClock,
  Check,
  CheckCircle2,
  ClipboardCheck,
  Eye,
  FileImage,
  LoaderCircle,
  Play,
  Plus,
  RefreshCw,
  RotateCcw,
  Search,
  Send,
  ShieldCheck,
  Upload,
  UserCheck,
  X,
} from "lucide-react"

import { useAuth } from "@/components/auth/auth-provider"
import { apiFetch } from "@/lib/api"
import type {
  Assignment,
  AssignmentActivity,
  AssignmentListResponse,
  AssignmentStatus,
  AssignmentSummary,
  AssignmentUserSummary,
  Department,
  Evidence,
  Incident,
  IncidentListResponse,
  IncidentPriority,
  User,
} from "@/lib/types"


const EMPTY_SUMMARY: AssignmentSummary = {
  total_visible: 0,
  my_open: 0,
  pending_acceptance: 0,
  in_progress: 0,
  awaiting_verification: 0,
  overdue: 0,
  completed: 0,
}

type CreateForm = {
  incident_id: string
  department_id: string
  assigned_user_id: string
  title: string
  instructions: string
  priority: IncidentPriority | ""
  due_at: string
}

const EMPTY_CREATE: CreateForm = {
  incident_id: "",
  department_id: "",
  assigned_user_id: "",
  title: "",
  instructions: "",
  priority: "",
  due_at: "",
}

type ActionMode =
    | "reject"
    | "submit"
    | "verify"
    | "cancel"
    | null


export default function AssignmentsPage() {
  const { user } = useAuth()

  const [assignments, setAssignments] = useState<Assignment[]>([])
  const [summary, setSummary] = useState(EMPTY_SUMMARY)

  const [search, setSearch] = useState("")
  const [statusFilter, setStatusFilter] =
      useState<AssignmentStatus | "">("")
  const [mineOnly, setMineOnly] = useState(false)

  const [loading, setLoading] = useState(true)
  const [refreshing, setRefreshing] = useState(false)
  const [error, setError] = useState("")

  const [selected, setSelected] =
      useState<Assignment | null>(null)
  const [timeline, setTimeline] =
      useState<AssignmentActivity[]>([])
  const [incidentEvidence, setIncidentEvidence] =
      useState<Evidence[]>([])
  const [detailLoading, setDetailLoading] = useState(false)

  const [createOpen, setCreateOpen] = useState(false)
  const [createBusy, setCreateBusy] = useState(false)
  const [createError, setCreateError] = useState("")
  const [createForm, setCreateForm] =
      useState<CreateForm>(EMPTY_CREATE)

  const [incidents, setIncidents] = useState<Incident[]>([])
  const [departments, setDepartments] = useState<Department[]>([])
  const [assignees, setAssignees] =
      useState<AssignmentUserSummary[]>([])

  const [actionMode, setActionMode] =
      useState<ActionMode>(null)
  const [actionText, setActionText] = useState("")
  const [selectedEvidenceIds, setSelectedEvidenceIds] =
      useState<number[]>([])
  const [actionBusy, setActionBusy] = useState(false)
  const [actionError, setActionError] = useState("")

  const [completionFile, setCompletionFile] =
      useState<File | null>(null)
  const [completionDescription, setCompletionDescription] =
      useState("")
  const [completionUploadBusy, setCompletionUploadBusy] =
      useState(false)
  const [completionUploadError, setCompletionUploadError] =
      useState("")

  const canCreate = hasPermission(user, "assignments.create")
  const canVerify = hasPermission(user, "assignments.verify")
  const canManage =
      Boolean(user?.is_superuser) ||
      hasPermission(user, "assignments.manage_all") ||
      hasPermission(user, "assignments.manage_department")

  const load = useCallback(
      async (manual = false) => {
        if (manual) {
          setRefreshing(true)
        } else {
          setLoading(true)
        }

        setError("")

        const params = new URLSearchParams({
          page: "1",
          page_size: "100",
        })

        if (search.trim()) {
          params.set("search", search.trim())
        }
        if (statusFilter) {
          params.set("status", statusFilter)
        }
        if (mineOnly) {
          params.set("mine", "true")
        }

        try {
          const [list, counts] = await Promise.all([
            apiFetch<AssignmentListResponse>(
                `/assignments?${params.toString()}`,
            ),
            apiFetch<AssignmentSummary>(
                "/assignments/summary",
            ),
          ])

          setAssignments(list.items)
          setSummary(counts)
        } catch (requestError) {
          setError(
              requestError instanceof Error
                  ? requestError.message
                  : "Unable to load assignments.",
          )
        } finally {
          setLoading(false)
          setRefreshing(false)
        }
      },
      [mineOnly, search, statusFilter],
  )

  useEffect(() => {
    void load()
  }, [load])

  async function openAssignment(assignment: Assignment) {
    setSelected(assignment)
    setDetailLoading(true)
    setActionError("")

    try {
      const [fresh, activities, evidence] =
          await Promise.all([
            apiFetch<Assignment>(
                `/assignments/${assignment.id}`,
            ),
            apiFetch<AssignmentActivity[]>(
                `/assignments/${assignment.id}/timeline`,
            ),
            apiFetch<Evidence[]>(
                `/evidence/incidents/${assignment.incident_id}`,
            ),
          ])

      setSelected(fresh)
      setTimeline(activities)
      setIncidentEvidence(evidence)
    } catch (requestError) {
      setActionError(
          requestError instanceof Error
              ? requestError.message
              : "Unable to load assignment details.",
      )
    } finally {
      setDetailLoading(false)
    }
  }

  async function loadIncidentEvidence(
      incidentId: number,
  ) {
    const evidence = await apiFetch<Evidence[]>(
        `/evidence/incidents/${incidentId}`,
    )
    setIncidentEvidence(evidence)
    return evidence
  }

  async function uploadCompletionEvidence() {
    if (!selected || !completionFile) {
      setCompletionUploadError(
          "Choose a file before uploading.",
      )
      return
    }

    setCompletionUploadBusy(true)
    setCompletionUploadError("")

    try {
      const formData = new FormData()
      formData.append("file", completionFile)

      if (completionDescription.trim()) {
        formData.append(
            "description",
            completionDescription.trim(),
        )
      }

      formData.append(
          "is_anonymized",
          "false",
      )
      formData.append(
          "is_enforcement_evidence",
          "true",
      )

      const uploaded = await apiFetch<Evidence>(
          `/evidence/incidents/${selected.incident_id}`,
          {
            method: "POST",
            body: formData,
          },
      )

      const refreshedEvidence =
          await loadIncidentEvidence(
              selected.incident_id,
          )

      setSelectedEvidenceIds((current) =>
          current.includes(uploaded.id)
              ? current
              : [...current, uploaded.id],
      )

      setCompletionFile(null)
      setCompletionDescription("")

      if (
          !refreshedEvidence.some(
              (item) => item.id === uploaded.id,
          )
      ) {
        setIncidentEvidence((current) => [
          uploaded,
          ...current,
        ])
      }
    } catch (requestError) {
      setCompletionUploadError(
          requestError instanceof Error
              ? requestError.message
              : "Unable to upload completion evidence.",
      )
    } finally {
      setCompletionUploadBusy(false)
    }
  }

  async function refreshSelected(id: number) {
    const fresh = await apiFetch<Assignment>(
        `/assignments/${id}`,
    )
    const activities =
        await apiFetch<AssignmentActivity[]>(
            `/assignments/${id}/timeline`,
        )
    const evidence = await apiFetch<Evidence[]>(
        `/evidence/incidents/${fresh.incident_id}`,
    )

    setSelected(fresh)
    setTimeline(activities)
    setIncidentEvidence(evidence)
    await load()
  }

  async function simpleAction(
      action: "accept" | "start",
  ) {
    if (!selected) return

    setActionBusy(true)
    setActionError("")

    try {
      await apiFetch<Assignment>(
          `/assignments/${selected.id}/${action}`,
          { method: "POST" },
      )
      await refreshSelected(selected.id)
    } catch (requestError) {
      setActionError(
          requestError instanceof Error
              ? requestError.message
              : `Unable to ${action} assignment.`,
      )
    } finally {
      setActionBusy(false)
    }
  }

  async function performAction(approved?: boolean) {
    if (!selected || !actionMode) return

    setActionBusy(true)
    setActionError("")

    try {
      if (actionMode === "reject") {
        await apiFetch<Assignment>(
            `/assignments/${selected.id}/reject`,
            {
              method: "POST",
              body: JSON.stringify({
                reason: actionText.trim(),
              }),
            },
        )
      }

      if (actionMode === "cancel") {
        await apiFetch<Assignment>(
            `/assignments/${selected.id}/cancel`,
            {
              method: "POST",
              body: JSON.stringify({
                reason: actionText.trim(),
              }),
            },
        )
      }

      if (actionMode === "submit") {
        await apiFetch<Assignment>(
            `/assignments/${selected.id}/submit`,
            {
              method: "POST",
              body: JSON.stringify({
                completion_notes: actionText.trim(),
                evidence_ids: selectedEvidenceIds,
              }),
            },
        )
      }

      if (actionMode === "verify") {
        await apiFetch<Assignment>(
            `/assignments/${selected.id}/verify`,
            {
              method: "POST",
              body: JSON.stringify({
                approved: Boolean(approved),
                notes: actionText.trim(),
              }),
            },
        )
      }

      setActionMode(null)
      setActionText("")
      setSelectedEvidenceIds([])
      setCompletionFile(null)
      setCompletionDescription("")
      setCompletionUploadError("")
      await refreshSelected(selected.id)
    } catch (requestError) {
      setActionError(
          requestError instanceof Error
              ? requestError.message
              : "Unable to update assignment.",
      )
    } finally {
      setActionBusy(false)
    }
  }

  async function openCreate() {
    setCreateOpen(true)
    setCreateError("")
    setCreateForm({
      ...EMPTY_CREATE,
      department_id:
          user?.department_id?.toString() ?? "",
    })

    try {
      const incidentResponse =
          await apiFetch<IncidentListResponse>(
              "/incidents?page=1&page_size=100",
          )

      setIncidents(
          incidentResponse.items.filter(
              (incident) =>
                  !["resolved", "dismissed"].includes(
                      incident.status,
                  ),
          ),
      )

      if (user?.is_superuser) {
        try {
          const response =
              await apiFetch<Department[]>(
                  "/departments",
              )
          setDepartments(
              response.filter(
                  (department) => department.is_active,
              ),
          )
        } catch {
          setDepartments([])
        }
      } else if (user?.department) {
        setDepartments([user.department])
      }

      const departmentId = user?.department_id
      const response =
          await apiFetch<AssignmentUserSummary[]>(
              `/assignments/assignees${
                  departmentId
                      ? `?department_id=${departmentId}`
                      : ""
              }`,
          )
      setAssignees(response)
    } catch (requestError) {
      setCreateError(
          requestError instanceof Error
              ? requestError.message
              : "Unable to load assignment options.",
      )
    }
  }

  async function loadAssignees(departmentId: string) {
    setCreateForm((current) => ({
      ...current,
      department_id: departmentId,
      assigned_user_id: "",
    }))
    setAssignees([])

    if (!departmentId) return

    try {
      setAssignees(
          await apiFetch<AssignmentUserSummary[]>(
              `/assignments/assignees?department_id=${departmentId}`,
          ),
      )
    } catch (requestError) {
      setCreateError(
          requestError instanceof Error
              ? requestError.message
              : "Unable to load assignees.",
      )
    }
  }

  function chooseIncident(value: string) {
    const incident = incidents.find(
        (item) => item.id === Number(value),
    )

    const departmentId =
        incident?.department_id?.toString() ||
        createForm.department_id

    setCreateForm((current) => ({
      ...current,
      incident_id: value,
      department_id: departmentId,
      assigned_user_id: "",
      title: incident?.title ?? "",
      instructions: incident?.description ?? "",
      priority: incident?.priority ?? "",
    }))

    if (departmentId) {
      void loadAssignees(departmentId)
    }
  }

  async function submitCreate(
      event: FormEvent<HTMLFormElement>,
  ) {
    event.preventDefault()

    setCreateBusy(true)
    setCreateError("")

    try {
      const created = await apiFetch<Assignment>(
          "/assignments",
          {
            method: "POST",
            body: JSON.stringify({
              incident_id: Number(
                  createForm.incident_id,
              ),
              assigned_user_id: Number(
                  createForm.assigned_user_id,
              ),
              department_id: Number(
                  createForm.department_id,
              ),
              title:
                  createForm.title.trim() || null,
              instructions:
                  createForm.instructions.trim() ||
                  null,
              priority:
                  createForm.priority || null,
              due_at: createForm.due_at
                  ? new Date(
                      createForm.due_at,
                  ).toISOString()
                  : null,
            }),
          },
      )

      setCreateOpen(false)
      await load()
      await openAssignment(created)
    } catch (requestError) {
      setCreateError(
          requestError instanceof Error
              ? requestError.message
              : "Unable to create assignment.",
      )
    } finally {
      setCreateBusy(false)
    }
  }

  return (
      <>
        <div className="space-y-6">
          <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
            <div>
              <p className="text-sm font-medium text-primary">
                Core Operations
              </p>
              <h2 className="mt-1 text-2xl font-semibold">
                Assignments
              </h2>
              <p className="mt-1 max-w-3xl text-sm text-muted-foreground">
                Turn incidents into accountable work, track officer
                acceptance and progress, require completion evidence,
                and verify work before closing an incident.
              </p>
            </div>

            <div className="flex gap-2">
              <button
                  type="button"
                  onClick={() => void load(true)}
                  disabled={refreshing}
                  className="inline-flex h-10 items-center gap-2 rounded-md border px-4 text-sm font-medium hover:bg-muted disabled:opacity-50"
              >
                <RefreshCw
                    className={`size-4 ${
                        refreshing ? "animate-spin" : ""
                    }`}
                />
                Refresh
              </button>

              {canCreate && (
                  <button
                      type="button"
                      onClick={() => void openCreate()}
                      className="inline-flex h-10 items-center gap-2 rounded-md bg-primary px-4 text-sm font-medium text-primary-foreground"
                  >
                    <Plus className="size-4" />
                    Create assignment
                  </button>
              )}
            </div>
          </div>

          {error && <ErrorBox message={error} />}

          <div className="grid grid-cols-2 gap-3 xl:grid-cols-6">
            <SummaryCard
                label="Visible"
                value={summary.total_visible}
                icon={<ClipboardCheck className="size-5" />}
            />
            <SummaryCard
                label="My open"
                value={summary.my_open}
                icon={<UserCheck className="size-5" />}
            />
            <SummaryCard
                label="Awaiting acceptance"
                value={summary.pending_acceptance}
                icon={<CalendarClock className="size-5" />}
            />
            <SummaryCard
                label="In progress"
                value={summary.in_progress}
                icon={<Play className="size-5" />}
            />
            <SummaryCard
                label="Verification"
                value={summary.awaiting_verification}
                icon={<ShieldCheck className="size-5" />}
            />
            <SummaryCard
                label="Overdue"
                value={summary.overdue}
                icon={<CalendarClock className="size-5" />}
                critical={summary.overdue > 0}
            />
          </div>

          <div className="overflow-hidden rounded-xl border bg-card">
            <div className="flex flex-col gap-3 border-b p-4 lg:flex-row">
              <div className="relative flex-1">
                <Search className="absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
                <input
                    value={search}
                    onChange={(event) =>
                        setSearch(event.target.value)
                    }
                    placeholder="Search assignment number, title or instructions..."
                    className="h-10 w-full rounded-md border bg-background pl-9 pr-3 text-sm"
                />
              </div>

              <select
                  value={statusFilter}
                  onChange={(event) =>
                      setStatusFilter(
                          event.target.value as
                              | AssignmentStatus
                              | "",
                      )
                  }
                  className="h-10 rounded-md border bg-background px-3 text-sm"
              >
                <option value="">All statuses</option>
                <option value="pending">Pending</option>
                <option value="accepted">Accepted</option>
                <option value="in_progress">
                  In progress
                </option>
                <option value="submitted">
                  Awaiting verification
                </option>
                <option value="completed">
                  Completed
                </option>
                <option value="rejected">
                  Rejected
                </option>
                <option value="cancelled">
                  Cancelled
                </option>
              </select>

              <label className="flex h-10 items-center gap-2 rounded-md border px-3 text-sm">
                <input
                    type="checkbox"
                    checked={mineOnly}
                    onChange={(event) =>
                        setMineOnly(event.target.checked)
                    }
                />
                Assigned to me
              </label>
            </div>

            {loading ? (
                <Loading text="Loading assignments..." />
            ) : assignments.length === 0 ? (
                <div className="flex min-h-56 flex-col items-center justify-center p-8 text-center">
                  <ClipboardCheck className="size-8 text-muted-foreground/60" />
                  <p className="mt-3 text-sm font-medium">
                    No assignments found
                  </p>
                  <p className="mt-1 text-xs text-muted-foreground">
                    Assigned incident work will appear here.
                  </p>
                </div>
            ) : (
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead className="bg-muted/35 text-left text-xs uppercase tracking-wide text-muted-foreground">
                    <tr>
                      <th className="px-4 py-3">
                        Assignment
                      </th>
                      <th className="px-4 py-3">
                        Incident
                      </th>
                      <th className="px-4 py-3">
                        Assigned employee
                      </th>
                      <th className="px-4 py-3">
                        Due
                      </th>
                      <th className="px-4 py-3">
                        Status
                      </th>
                      <th className="px-4 py-3 text-right">
                        Action
                      </th>
                    </tr>
                    </thead>

                    <tbody>
                    {assignments.map((assignment) => (
                        <tr
                            key={assignment.id}
                            className="border-t hover:bg-muted/20"
                        >
                          <td className="px-4 py-3">
                            <p className="font-medium">
                              {assignment.title}
                            </p>
                            <p className="mt-1 font-mono text-[11px] text-muted-foreground">
                              {assignment.assignment_number}
                            </p>
                          </td>

                          <td className="px-4 py-3">
                            <p className="font-mono text-xs">
                              {assignment.incident.incident_number}
                            </p>
                            <p className="mt-1 max-w-[240px] truncate text-xs text-muted-foreground">
                              {assignment.incident.title}
                            </p>
                          </td>

                          <td className="px-4 py-3">
                            <p>
                              {assignment.assigned_user.full_name}
                            </p>
                            <p className="mt-1 text-xs text-muted-foreground">
                              {assignment.department.name}
                            </p>
                          </td>

                          <td className="px-4 py-3">
                            <DueDate
                                dueAt={assignment.due_at}
                                status={assignment.status}
                            />
                          </td>

                          <td className="px-4 py-3">
                            <StatusBadge
                                status={assignment.status}
                            />
                          </td>

                          <td className="px-4 py-3 text-right">
                            <button
                                type="button"
                                onClick={() =>
                                    void openAssignment(
                                        assignment,
                                    )
                                }
                                className="inline-flex h-8 items-center gap-1.5 rounded-md border px-3 text-xs font-medium hover:bg-muted"
                            >
                              <Eye className="size-3.5" />
                              Open
                            </button>
                          </td>
                        </tr>
                    ))}
                    </tbody>
                  </table>
                </div>
            )}
          </div>
        </div>

        {selected && (
            <Drawer
                title={selected.title}
                subtitle={selected.assignment_number}
                onClose={() => {
                  setSelected(null)
                  setActionMode(null)
                }}
            >
              {actionError && (
                  <ErrorBox message={actionError} />
              )}

              {detailLoading ? (
                  <Loading text="Loading assignment..." />
              ) : (
                  <div className="space-y-6">
                    <div className="flex flex-wrap gap-2">
                      <StatusBadge status={selected.status} />
                      <PriorityBadge
                          priority={selected.priority}
                      />
                      {selected.due_at && (
                          <span className="rounded-full border px-2.5 py-1 text-xs text-muted-foreground">
                    Due {formatDate(selected.due_at)}
                  </span>
                      )}
                    </div>

                    <div className="grid gap-3 sm:grid-cols-2">
                      <Detail
                          label="Assigned to"
                          value={selected.assigned_user.full_name}
                      />
                      <Detail
                          label="Assigned by"
                          value={selected.assigned_by.full_name}
                      />
                      <Detail
                          label="Department"
                          value={selected.department.name}
                      />
                      <Detail
                          label="Incident"
                          value={selected.incident.incident_number}
                      />
                    </div>

                    <Section title="Instructions">
                      <p className="whitespace-pre-wrap text-sm leading-6 text-muted-foreground">
                        {selected.instructions ||
                            "No additional instructions were provided."}
                      </p>
                    </Section>

                    {selected.completion_notes && (
                        <Section title="Completion submission">
                          <p className="whitespace-pre-wrap text-sm leading-6">
                            {selected.completion_notes}
                          </p>

                          {selected.evidence.length > 0 && (
                              <div className="mt-3 grid gap-2 sm:grid-cols-2">
                                {selected.evidence.map(
                                    (evidence) => (
                                        <div
                                            key={evidence.id}
                                            className="flex items-center gap-2 rounded-md border p-3 text-xs"
                                        >
                                          <FileImage className="size-4 text-primary" />
                                          <span className="truncate">
                              {evidence.original_file_name}
                            </span>
                                        </div>
                                    ),
                                )}
                              </div>
                          )}
                        </Section>
                    )}

                    {selected.verification_notes && (
                        <Section title="Verification notes">
                          <p className="whitespace-pre-wrap text-sm leading-6">
                            {selected.verification_notes}
                          </p>
                        </Section>
                    )}

                    {selected.rejection_reason && (
                        <div className="rounded-lg border border-amber-500/30 bg-amber-500/10 p-4 text-sm">
                          <p className="font-medium">
                            Return / rejection reason
                          </p>
                          <p className="mt-1 text-muted-foreground">
                            {selected.rejection_reason}
                          </p>
                        </div>
                    )}

                    <AssignmentActions
                        assignment={selected}
                        currentUser={user}
                        canVerify={canVerify}
                        canManage={canManage}
                        busy={actionBusy}
                        onAccept={() =>
                            void simpleAction("accept")
                        }
                        onStart={() =>
                            void simpleAction("start")
                        }
                        onReject={() =>
                            setActionMode("reject")
                        }
                        onSubmit={() => {
                          setActionMode("submit")
                          setCompletionFile(null)
                          setCompletionDescription("")
                          setCompletionUploadError("")
                          setSelectedEvidenceIds([])
                        }}
                        onVerify={() =>
                            setActionMode("verify")
                        }
                        onCancel={() =>
                            setActionMode("cancel")
                        }
                    />

                    <Section title="Assignment timeline">
                      <div className="space-y-4">
                        {timeline.map((activity) => (
                            <div
                                key={activity.id}
                                className="border-l-2 border-primary/30 pl-4"
                            >
                              <p className="text-sm font-medium">
                                {humanize(activity.action)}
                              </p>
                              <p className="mt-1 text-xs text-muted-foreground">
                                {activity.actor.full_name} ·{" "}
                                {formatDate(activity.created_at)}
                              </p>
                              {activity.notes && (
                                  <p className="mt-2 text-sm leading-6 text-muted-foreground">
                                    {activity.notes}
                                  </p>
                              )}
                            </div>
                        ))}
                      </div>
                    </Section>

                    <Link
                        href="/incidents"
                        className="inline-flex text-xs font-medium text-primary hover:underline"
                    >
                      Open related incident in Incident Management
                    </Link>
                  </div>
              )}
            </Drawer>
        )}

        {createOpen && (
            <Modal
                title="Create operational assignment"
                onClose={() => {
                  if (!createBusy) setCreateOpen(false)
                }}
            >
              <form
                  onSubmit={submitCreate}
                  className="space-y-4"
              >
                {createError && (
                    <ErrorBox message={createError} />
                )}

                <FieldLabel label="Incident">
                  <select
                      required
                      value={createForm.incident_id}
                      onChange={(event) =>
                          chooseIncident(event.target.value)
                      }
                      className={inputClass}
                  >
                    <option value="">
                      Select incident
                    </option>
                    {incidents.map((incident) => (
                        <option
                            key={incident.id}
                            value={incident.id}
                        >
                          {incident.incident_number} —{" "}
                          {incident.title}
                        </option>
                    ))}
                  </select>
                </FieldLabel>

                <div className="grid gap-4 sm:grid-cols-2">
                  <FieldLabel label="Department">
                    <select
                        required
                        value={createForm.department_id}
                        onChange={(event) =>
                            void loadAssignees(
                                event.target.value,
                            )
                        }
                        className={inputClass}
                    >
                      <option value="">
                        Select department
                      </option>
                      {departments.map((department) => (
                          <option
                              key={department.id}
                              value={department.id}
                          >
                            {department.name}
                          </option>
                      ))}
                    </select>
                  </FieldLabel>

                  <FieldLabel label="Assigned employee">
                    <select
                        required
                        value={
                          createForm.assigned_user_id
                        }
                        onChange={(event) =>
                            setCreateForm((current) => ({
                              ...current,
                              assigned_user_id:
                              event.target.value,
                            }))
                        }
                        className={inputClass}
                    >
                      <option value="">
                        Select employee
                      </option>
                      {assignees.map((employee) => (
                          <option
                              key={employee.id}
                              value={employee.id}
                          >
                            {employee.full_name}
                          </option>
                      ))}
                    </select>
                  </FieldLabel>
                </div>

                <FieldLabel label="Assignment title">
                  <input
                      required
                      value={createForm.title}
                      onChange={(event) =>
                          setCreateForm((current) => ({
                            ...current,
                            title: event.target.value,
                          }))
                      }
                      className={inputClass}
                  />
                </FieldLabel>

                <FieldLabel label="Instructions">
              <textarea
                  rows={4}
                  value={createForm.instructions}
                  onChange={(event) =>
                      setCreateForm((current) => ({
                        ...current,
                        instructions:
                        event.target.value,
                      }))
                  }
                  className={`${inputClass} h-auto py-2.5`}
              />
                </FieldLabel>

                <div className="grid gap-4 sm:grid-cols-2">
                  <FieldLabel label="Priority">
                    <select
                        value={createForm.priority}
                        onChange={(event) =>
                            setCreateForm((current) => ({
                              ...current,
                              priority:
                                  event.target
                                      .value as
                                      | IncidentPriority
                                      | "",
                            }))
                        }
                        className={inputClass}
                    >
                      <option value="">
                        Use incident priority
                      </option>
                      <option value="low">Low</option>
                      <option value="medium">
                        Medium
                      </option>
                      <option value="high">High</option>
                      <option value="critical">
                        Critical
                      </option>
                    </select>
                  </FieldLabel>

                  <FieldLabel label="Due date/time">
                    <input
                        type="datetime-local"
                        value={createForm.due_at}
                        onChange={(event) =>
                            setCreateForm((current) => ({
                              ...current,
                              due_at: event.target.value,
                            }))
                        }
                        className={inputClass}
                    />
                  </FieldLabel>
                </div>

                <div className="flex justify-end gap-2 border-t pt-4">
                  <button
                      type="button"
                      onClick={() =>
                          setCreateOpen(false)
                      }
                      disabled={createBusy}
                      className="h-10 rounded-md border px-4 text-sm font-medium"
                  >
                    Cancel
                  </button>
                  <button
                      type="submit"
                      disabled={createBusy}
                      className="h-10 rounded-md bg-primary px-4 text-sm font-medium text-primary-foreground disabled:opacity-50"
                  >
                    {createBusy
                        ? "Creating..."
                        : "Create assignment"}
                  </button>
                </div>
              </form>
            </Modal>
        )}

        {actionMode && selected && (
            <Modal
                title={actionTitle(actionMode)}
                onClose={() => {
                  if (!actionBusy) setActionMode(null)
                }}
            >
              <div className="space-y-4">
                {actionError && (
                    <ErrorBox message={actionError} />
                )}

                {actionMode === "submit" && (
                    <div className="space-y-4">
                      <div>
                        <p className="text-sm font-medium">
                          Upload completion evidence
                        </p>
                        <p className="mt-1 text-xs leading-5 text-muted-foreground">
                          Upload evidence here without leaving the assignment.
                          The file is attached to the related incident and
                          automatically selected as proof of completion.
                        </p>
                      </div>

                      {completionUploadError && (
                          <ErrorBox
                              message={completionUploadError}
                          />
                      )}

                      <div className="rounded-lg border bg-muted/15 p-4">
                        <div className="grid gap-3">
                          <input
                              type="file"
                              accept="image/jpeg,image/png,image/webp,video/mp4,video/webm,audio/mpeg,audio/wav,application/pdf"
                              onChange={(event) =>
                                  setCompletionFile(
                                      event.target.files?.[0] ?? null,
                                  )
                              }
                              className="block w-full text-sm file:mr-3 file:rounded-md file:border-0 file:bg-primary file:px-3 file:py-2 file:text-xs file:font-medium file:text-primary-foreground"
                          />

                          <input
                              type="text"
                              value={completionDescription}
                              onChange={(event) =>
                                  setCompletionDescription(
                                      event.target.value,
                                  )
                              }
                              placeholder="Evidence description (optional)"
                              className={inputClass}
                          />

                          <div className="flex items-center justify-between gap-3">
                            <p className="min-w-0 truncate text-xs text-muted-foreground">
                              {completionFile
                                  ? completionFile.name
                                  : "No file selected"}
                            </p>

                            <button
                                type="button"
                                onClick={() =>
                                    void uploadCompletionEvidence()
                                }
                                disabled={
                                    completionUploadBusy ||
                                    !completionFile
                                }
                                className="inline-flex h-9 shrink-0 items-center gap-2 rounded-md bg-primary px-3 text-xs font-medium text-primary-foreground disabled:opacity-40"
                            >
                              {completionUploadBusy ? (
                                  <LoaderCircle className="size-4 animate-spin" />
                              ) : (
                                  <Upload className="size-4" />
                              )}
                              {completionUploadBusy
                                  ? "Uploading..."
                                  : "Upload evidence"}
                            </button>
                          </div>
                        </div>
                      </div>

                      <div>
                        <p className="text-sm font-medium">
                          Evidence for this incident
                        </p>
                        <p className="mt-1 text-xs text-muted-foreground">
                          Select at least one item as completion proof.
                          Newly uploaded evidence is selected automatically.
                        </p>
                      </div>

                      {incidentEvidence.length === 0 ? (
                          <div className="rounded-lg border border-dashed p-4 text-sm text-muted-foreground">
                            No evidence has been uploaded yet. Choose a file
                            above and upload it before submitting the work.
                          </div>
                      ) : (
                          <div className="max-h-52 space-y-2 overflow-y-auto rounded-lg border p-3">
                            {incidentEvidence.map(
                                (evidence) => (
                                    <label
                                        key={evidence.id}
                                        className="flex items-center gap-3 rounded-md p-2 text-sm hover:bg-muted"
                                    >
                                      <input
                                          type="checkbox"
                                          checked={selectedEvidenceIds.includes(
                                              evidence.id,
                                          )}
                                          onChange={() =>
                                              setSelectedEvidenceIds(
                                                  (current) =>
                                                      current.includes(
                                                          evidence.id,
                                                      )
                                                          ? current.filter(
                                                              (id) =>
                                                                  id !== evidence.id,
                                                          )
                                                          : [
                                                            ...current,
                                                            evidence.id,
                                                          ],
                                              )
                                          }
                                      />
                                      <FileImage className="size-4 text-primary" />
                                      <div className="min-w-0 flex-1">
                                        <p className="truncate">
                                          {evidence.original_file_name}
                                        </p>
                                        <p className="mt-0.5 text-[11px] text-muted-foreground">
                                          {evidence.evidence_type} ·{" "}
                                          {formatFileSize(
                                              evidence.file_size_bytes,
                                          )}
                                        </p>
                                      </div>
                                    </label>
                                ),
                            )}
                          </div>
                      )}
                    </div>
                )}

                <FieldLabel
                    label={actionPrompt(actionMode)}
                >
              <textarea
                  rows={5}
                  value={actionText}
                  onChange={(event) =>
                      setActionText(event.target.value)
                  }
                  className={`${inputClass} h-auto py-2.5`}
              />
                </FieldLabel>

                <div className="flex flex-wrap justify-end gap-2">
                  <button
                      type="button"
                      onClick={() =>
                          setActionMode(null)
                      }
                      disabled={actionBusy}
                      className="h-10 rounded-md border px-4 text-sm font-medium"
                  >
                    Cancel
                  </button>

                  {actionMode === "verify" ? (
                      <>
                        <button
                            type="button"
                            onClick={() =>
                                void performAction(false)
                            }
                            disabled={
                                actionBusy ||
                                actionText.trim().length < 3
                            }
                            className="inline-flex h-10 items-center gap-2 rounded-md border border-amber-500/40 px-4 text-sm font-medium text-amber-500 disabled:opacity-40"
                        >
                          <RotateCcw className="size-4" />
                          Return for work
                        </button>

                        <button
                            type="button"
                            onClick={() =>
                                void performAction(true)
                            }
                            disabled={
                                actionBusy ||
                                actionText.trim().length < 3
                            }
                            className="inline-flex h-10 items-center gap-2 rounded-md bg-emerald-600 px-4 text-sm font-medium text-white disabled:opacity-40"
                        >
                          <CheckCircle2 className="size-4" />
                          Verify & close incident
                        </button>
                      </>
                  ) : (
                      <button
                          type="button"
                          onClick={() =>
                              void performAction()
                          }
                          disabled={
                              actionBusy ||
                              actionText.trim().length < 3 ||
                              (actionMode === "submit" &&
                                  selectedEvidenceIds.length === 0)
                          }
                          className="h-10 rounded-md bg-primary px-4 text-sm font-medium text-primary-foreground disabled:opacity-40"
                      >
                        Confirm
                      </button>
                  )}
                </div>
              </div>
            </Modal>
        )}
      </>
  )
}


function AssignmentActions({
                             assignment,
                             currentUser,
                             canVerify,
                             canManage,
                             busy,
                             onAccept,
                             onStart,
                             onReject,
                             onSubmit,
                             onVerify,
                             onCancel,
                           }: {
  assignment: Assignment
  currentUser: User | null
  canVerify: boolean
  canManage: boolean
  busy: boolean
  onAccept: () => void
  onStart: () => void
  onReject: () => void
  onSubmit: () => void
  onVerify: () => void
  onCancel: () => void
}) {
  const mine =
      currentUser?.id === assignment.assigned_user_id

  return (
      <Section title="Available actions">
        <div className="flex flex-wrap gap-2">
          {mine && assignment.status === "pending" && (
              <>
                <ActionButton
                    label="Accept"
                    icon={<Check className="size-4" />}
                    onClick={onAccept}
                    disabled={busy}
                    primary
                />
                <ActionButton
                    label="Reject"
                    icon={<X className="size-4" />}
                    onClick={onReject}
                    disabled={busy}
                />
              </>
          )}

          {mine &&
              assignment.status === "accepted" && (
                  <ActionButton
                      label="Start work"
                      icon={<Play className="size-4" />}
                      onClick={onStart}
                      disabled={busy}
                      primary
                  />
              )}

          {mine &&
              assignment.status ===
              "in_progress" && (
                  <ActionButton
                      label="Submit completion"
                      icon={<Send className="size-4" />}
                      onClick={onSubmit}
                      disabled={busy}
                      primary
                  />
              )}

          {canVerify &&
              assignment.status === "submitted" && (
                  <ActionButton
                      label="Verify work"
                      icon={<ShieldCheck className="size-4" />}
                      onClick={onVerify}
                      disabled={busy}
                      primary
                  />
              )}

          {canManage &&
              ![
                "completed",
                "rejected",
                "cancelled",
              ].includes(assignment.status) && (
                  <ActionButton
                      label="Cancel assignment"
                      icon={<X className="size-4" />}
                      onClick={onCancel}
                      disabled={busy}
                  />
              )}
        </div>
      </Section>
  )
}


function ActionButton({
                        label,
                        icon,
                        onClick,
                        disabled,
                        primary = false,
                      }: {
  label: string
  icon: ReactNode
  onClick: () => void
  disabled: boolean
  primary?: boolean
}) {
  return (
      <button
          type="button"
          onClick={onClick}
          disabled={disabled}
          className={`inline-flex h-9 items-center gap-2 rounded-md px-3 text-xs font-medium disabled:opacity-40 ${
              primary
                  ? "bg-primary text-primary-foreground"
                  : "border hover:bg-muted"
          }`}
      >
        {icon}
        {label}
      </button>
  )
}


function SummaryCard({
                       label,
                       value,
                       icon,
                       critical = false,
                     }: {
  label: string
  value: number
  icon: ReactNode
  critical?: boolean
}) {
  return (
      <div className="rounded-xl border bg-card p-4">
        <div className="flex items-start justify-between">
          <div>
            <p className="text-xs text-muted-foreground">
              {label}
            </p>
            <p className="mt-2 font-mono text-2xl font-semibold">
              {value}
            </p>
          </div>
          <div
              className={`rounded-lg p-2.5 ${
                  critical
                      ? "bg-destructive/10 text-destructive"
                      : "bg-primary/10 text-primary"
              }`}
          >
            {icon}
          </div>
        </div>
      </div>
  )
}


function Detail({
                  label,
                  value,
                }: {
  label: string
  value: string
}) {
  return (
      <div className="rounded-lg border p-4">
        <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
          {label}
        </p>
        <p className="mt-2 text-sm font-medium">
          {value}
        </p>
      </div>
  )
}


function Section({
                   title,
                   children,
                 }: {
  title: string
  children: ReactNode
}) {
  return (
      <section>
        <h4 className="mb-3 text-sm font-semibold">
          {title}
        </h4>
        {children}
      </section>
  )
}


function Drawer({
                  title,
                  subtitle,
                  children,
                  onClose,
                }: {
  title: string
  subtitle: string
  children: ReactNode
  onClose: () => void
}) {
  return (
      <div className="fixed inset-0 z-50 flex justify-end bg-black/50">
        <div className="h-full w-full max-w-3xl overflow-y-auto border-l bg-background shadow-2xl">
          <div className="sticky top-0 z-10 flex items-center justify-between border-b bg-background/95 px-5 py-4 backdrop-blur">
            <div>
              <p className="font-mono text-xs text-muted-foreground">
                {subtitle}
              </p>
              <h3 className="mt-1 text-lg font-semibold">
                {title}
              </h3>
            </div>
            <button
                type="button"
                onClick={onClose}
                className="flex size-9 items-center justify-center rounded-md border hover:bg-muted"
            >
              <X className="size-4" />
            </button>
          </div>
          <div className="p-5">{children}</div>
        </div>
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
      <div className="fixed inset-0 z-[60] flex items-center justify-center bg-black/55 p-4">
        <div className="max-h-[90vh] w-full max-w-2xl overflow-y-auto rounded-xl border bg-background shadow-2xl">
          <div className="sticky top-0 z-10 flex items-center justify-between border-b bg-background/95 px-5 py-4 backdrop-blur">
            <h3 className="font-semibold">{title}</h3>
            <button
                type="button"
                onClick={onClose}
                className="flex size-8 items-center justify-center rounded-md border"
            >
              <X className="size-4" />
            </button>
          </div>
          <div className="p-5">{children}</div>
        </div>
      </div>
  )
}


function FieldLabel({
                      label,
                      children,
                    }: {
  label: string
  children: ReactNode
}) {
  return (
      <label className="block text-sm font-medium">
        {label}
        <div className="mt-1">{children}</div>
      </label>
  )
}


function ErrorBox({ message }: { message: string }) {
  return (
      <div className="rounded-lg border border-destructive/30 bg-destructive/10 p-3 text-sm text-destructive">
        {message}
      </div>
  )
}


function Loading({ text }: { text: string }) {
  return (
      <div className="flex min-h-56 items-center justify-center gap-2 text-sm text-muted-foreground">
        <LoaderCircle className="size-4 animate-spin" />
        {text}
      </div>
  )
}


function StatusBadge({
                       status,
                     }: {
  status: AssignmentStatus
}) {
  const classes: Record<AssignmentStatus, string> = {
    pending: "bg-amber-500/10 text-amber-500",
    accepted: "bg-blue-500/10 text-blue-500",
    in_progress: "bg-primary/10 text-primary",
    submitted: "bg-violet-500/10 text-violet-500",
    completed: "bg-emerald-500/10 text-emerald-500",
    rejected: "bg-destructive/10 text-destructive",
    cancelled: "bg-muted text-muted-foreground",
  }

  return (
      <span
          className={`rounded-full px-2.5 py-1 text-xs font-medium ${classes[status]}`}
      >
      {humanize(status)}
    </span>
  )
}


function PriorityBadge({ priority }: { priority: string }) {
  const classes: Record<string, string> = {
    low: "bg-blue-500/10 text-blue-500",
    medium: "bg-amber-500/10 text-amber-500",
    high: "bg-orange-500/10 text-orange-500",
    critical: "bg-destructive/10 text-destructive",
  }

  return (
      <span
          className={`rounded-full px-2.5 py-1 text-xs font-medium ${
              classes[priority] ||
              "bg-muted text-muted-foreground"
          }`}
      >
      {humanize(priority)}
    </span>
  )
}


function DueDate({
                   dueAt,
                   status,
                 }: {
  dueAt?: string | null
  status: AssignmentStatus
}) {
  if (!dueAt) {
    return (
        <span className="text-xs text-muted-foreground">
        No deadline
      </span>
    )
  }

  const overdue =
      new Date(dueAt).getTime() < Date.now() &&
      !["completed", "cancelled", "rejected"].includes(
          status,
      )

  return (
      <span
          className={`text-xs ${
              overdue
                  ? "font-medium text-destructive"
                  : "text-muted-foreground"
          }`}
      >
      {formatDate(dueAt)}
        {overdue ? " · Overdue" : ""}
    </span>
  )
}


function hasPermission(
    user: User | null,
    code: string,
) {
  if (!user) return false
  if (user.is_superuser) return true

  return Boolean(
      user.role?.is_active &&
      user.role.permissions?.some(
          (permission) =>
              permission.code === code &&
              permission.is_active,
      ),
  )
}


function actionTitle(
    mode: Exclude<ActionMode, null>,
) {
  return {
    reject: "Reject assignment",
    submit: "Submit completed work",
    verify: "Verify assignment completion",
    cancel: "Cancel assignment",
  }[mode]
}


function actionPrompt(
    mode: Exclude<ActionMode, null>,
) {
  return {
    reject: "Reason for rejection",
    submit: "Completion notes",
    verify: "Supervisor verification notes",
    cancel: "Reason for cancellation",
  }[mode]
}


function humanize(value: string) {
  return value
      .replace(/\./g, " ")
      .replace(/_/g, " ")
      .replace(/\b\w/g, (character) =>
          character.toUpperCase(),
      )
}


function formatDate(value: string) {
  const date = new Date(value)

  if (Number.isNaN(date.getTime())) {
    return "Unknown"
  }

  return new Intl.DateTimeFormat("en-LS", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(date)
}


function formatFileSize(bytes: number) {
  if (!Number.isFinite(bytes) || bytes <= 0) {
    return "0 B"
  }

  const units = ["B", "KB", "MB", "GB"]
  const index = Math.min(
      Math.floor(Math.log(bytes) / Math.log(1024)),
      units.length - 1,
  )
  const value = bytes / 1024 ** index

  return `${value.toFixed(index === 0 ? 0 : 1)} ${units[index]}`
}


const inputClass =
    "h-10 w-full rounded-md border bg-background px-3 text-sm outline-none ring-offset-background focus:ring-2 focus:ring-ring"
