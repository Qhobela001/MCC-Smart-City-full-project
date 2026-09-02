export type Permission = {
  id: number
  name: string
  code: string
  description?: string | null
  is_active: boolean
  is_system: boolean
  created_at: string
}

export type Role = {
  id: number
  name: string
  description?: string | null
  is_system: boolean
  is_active: boolean
  permissions: Permission[]
  created_at: string
  updated_at: string
}

export type Department = {
  id: number
  name: string
  code: string
  description?: string | null
  is_active: boolean
  created_at: string
  updated_at: string
}

export type User = {
  id: number
  full_name: string
  employee_number?: string | null
  email: string
  phone_number?: string | null
  department_id?: number | null
  role_id?: number | null
  status: "active" | "suspended" | "deactivated"
  is_active: boolean
  is_superuser: boolean
  must_change_password: boolean
  department?: Department | null
  role?: Role | null
  created_at: string
  updated_at: string
}

export type NavigationItem = {
  id: number
  label: string
  href: string
  icon: string
  section: string
  sort_order: number
  permission_code?: string | null
  is_active: boolean
  is_system: boolean
  created_at: string
}

export type LoginResponse = {
  access_token: string
  token_type: string
  user: User
}

export type IncidentType =
  | "noise_pollution"
  | "illegal_dumping"
  | "skip_overflow"
  | "unauthorized_vending"
  | "street_cleaner_non_compliance"
  | "public_urination"
  | "vehicle_smoke_emission"
  | "road_damage"
  | "pothole"
  | "other"

export type IncidentPriority =
  | "low"
  | "medium"
  | "high"
  | "critical"

export type IncidentStatus =
  | "new"
  | "under_review"
  | "confirmed"
  | "assigned"
  | "in_progress"
  | "resolved"
  | "dismissed"

export type IncidentSource =
  | "manual"
  | "ai_detection"
  | "public_report"
  | "imported"

export type DepartmentSummary = {
  id: number
  name: string
  code: string
}

export type UserSummary = {
  id: number
  full_name: string
  email: string
  employee_number?: string | null
}

export type Incident = {
  id: number
  incident_number: string
  incident_type: IncidentType
  title: string
  description: string
  priority: IncidentPriority
  status: IncidentStatus
  source: IncidentSource
  department_id?: number | null
  assigned_user_id?: number | null
  created_by_id: number
  department?: DepartmentSummary | null
  assigned_user?: UserSummary | null
  created_by: UserSummary
  location_name?: string | null
  latitude?: number | null
  longitude?: number | null
  is_ai_generated: boolean
  reported_at: string
  acknowledged_at?: string | null
  resolved_at?: string | null
  resolution_notes?: string | null
  created_at: string
  updated_at: string
  evidence_count: number
}

export type IncidentListResponse = {
  items: Incident[]
  total: number
  page: number
  page_size: number
  pages: number
}

export type IncidentActivity = {
  id: number
  incident_id: number
  actor_user_id: number
  action: string
  previous_status?: IncidentStatus | null
  new_status?: IncidentStatus | null
  notes?: string | null
  actor: UserSummary
  created_at: string
}

export type EvidenceType =
  | "image"
  | "video"
  | "audio"
  | "document"
  | "other"

export type Evidence = {
  id: number
  incident_id: number
  uploaded_by_id: number
  uploaded_by: UserSummary
  evidence_type: EvidenceType
  original_file_name: string
  stored_file_name: string
  mime_type: string
  file_size_bytes: number
  sha256_hash: string
  description?: string | null
  captured_at?: string | null
  latitude?: number | null
  longitude?: number | null
  is_anonymized: boolean
  is_enforcement_evidence: boolean
  created_at: string
  download_url: string
}

export type AIDetectionReviewStatus = "unreviewed" | "confirmed" | "rejected"

export type AIDetection = {
  id: number
  detection_uuid: string
  detection_type: IncidentType
  class_name: string
  confidence: number
  detected_at: string
  source_type: "camera" | "uploaded_image" | "uploaded_video" | "test"
  camera_identifier?: string | null
  location_name?: string | null
  latitude?: number | null
  longitude?: number | null
  snapshot_path?: string | null
  clip_path?: string | null
  attributes: Record<string, unknown>
  incident_id?: number | null
  review_status: AIDetectionReviewStatus
  reviewed_at?: string | null
  is_test: boolean
}

export type AIDetectionListResponse = {
  items: AIDetection[]
  total: number
  page: number
  page_size: number
  pages: number
}


export type AlertType =
  | "incident_created"
  | "incident_assigned"
  | "incident_status_changed"
  | "incident_resolved"
  | "evidence_uploaded"
  | "system"

export type AlertSeverity =
  | "info"
  | "low"
  | "medium"
  | "high"
  | "critical"

export type AlertIncidentSummary = {
  id: number
  incident_number: string
  title: string
  status: string
  priority: string
}

export type Alert = {
  id: number
  recipient_user_id: number
  recipient_department_id?: number | null
  incident_id?: number | null
  alert_type: AlertType
  severity: AlertSeverity
  title: string
  message: string
  action_url?: string | null
  is_read: boolean
  read_at?: string | null
  is_acknowledged: boolean
  acknowledged_at?: string | null
  is_archived: boolean
  archived_at?: string | null
  created_at: string
  incident?: AlertIncidentSummary | null
}

export type AlertListResponse = {
  items: Alert[]
  total: number
  unread_count: number
}

export type UnreadCountResponse = {
  unread_count: number
}


export type AssignmentStatus =
  | "pending"
  | "accepted"
  | "in_progress"
  | "submitted"
  | "completed"
  | "rejected"
  | "cancelled"

export type AssignmentUserSummary = {
  id: number
  full_name: string
  email: string
  employee_number?: string | null
  department_id?: number | null
}

export type AssignmentDepartmentSummary = {
  id: number
  name: string
  code: string
}

export type AssignmentIncidentSummary = {
  id: number
  incident_number: string
  title: string
  incident_type: string
  priority: string
  status: string
  location_name?: string | null
}

export type AssignmentEvidenceSummary = {
  id: number
  original_file_name: string
  evidence_type: string
  mime_type: string
  file_size_bytes: number
  created_at: string
}

export type Assignment = {
  id: number
  assignment_number: string
  incident_id: number
  department_id: number
  assigned_user_id: number
  assigned_by_id: number
  title: string
  instructions?: string | null
  priority: IncidentPriority
  status: AssignmentStatus
  due_at?: string | null
  accepted_at?: string | null
  started_at?: string | null
  submitted_at?: string | null
  completed_at?: string | null
  cancelled_at?: string | null
  completion_notes?: string | null
  verification_notes?: string | null
  rejection_reason?: string | null
  cancellation_reason?: string | null
  created_at: string
  updated_at: string
  incident: AssignmentIncidentSummary
  department: AssignmentDepartmentSummary
  assigned_user: AssignmentUserSummary
  assigned_by: AssignmentUserSummary
  evidence: AssignmentEvidenceSummary[]
}

export type AssignmentListResponse = {
  items: Assignment[]
  total: number
  page: number
  page_size: number
  pages: number
}

export type AssignmentActivity = {
  id: number
  assignment_id: number
  actor_user_id: number
  action: string
  previous_status?: AssignmentStatus | null
  new_status?: AssignmentStatus | null
  notes?: string | null
  actor: AssignmentUserSummary
  created_at: string
}

export type AssignmentSummary = {
  total_visible: number
  my_open: number
  pending_acceptance: number
  in_progress: number
  awaiting_verification: number
  overdue: number
  completed: number
}
