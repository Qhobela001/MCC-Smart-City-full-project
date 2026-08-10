"use client"

import {
  FormEvent,
  ReactNode,
  useEffect,
  useMemo,
  useState,
} from "react"
import {
  BadgeCheck,
  Building2,
  CalendarDays,
  Eye,
  EyeOff,
  Fingerprint,
  KeyRound,
  Mail,
  Phone,
  Plus,
  RefreshCw,
  ShieldCheck,
  UserCog,
  Users as UsersIcon,
} from "lucide-react"

import {
  Modal,
  PageIntro,
  SearchBox,
  StatusBadge,
  inputClass,
  labelClass,
} from "@/components/admin/admin-ui"
import { apiFetch } from "@/lib/api"
import type {
  Department,
  Permission,
  Role,
  User,
} from "@/lib/types"

type UserForm = {
  full_name: string
  employee_number: string
  email: string
  phone_number: string
  department_id: string
  role_id: string
  temporary_password: string
  is_superuser: boolean
}

const emptyUserForm: UserForm = {
  full_name: "",
  employee_number: "",
  email: "",
  phone_number: "",
  department_id: "",
  role_id: "",
  temporary_password: "",
  is_superuser: false,
}

export default function UsersPage() {
  const [users, setUsers] = useState<User[]>([])
  const [departments, setDepartments] = useState<Department[]>([])
  const [roles, setRoles] = useState<Role[]>([])

  const [search, setSearch] = useState("")
  const [registrationOpen, setRegistrationOpen] = useState(false)
  const [selectedUser, setSelectedUser] = useState<User | null>(null)

  const [pageError, setPageError] = useState("")
  const [formError, setFormError] = useState("")

  const [loading, setLoading] = useState(true)
  const [busy, setBusy] = useState(false)
  const [actionUserId, setActionUserId] = useState<number | null>(null)
  const [showTemporaryPassword, setShowTemporaryPassword] =
    useState(false)

  const [form, setForm] = useState<UserForm>(emptyUserForm)

  async function loadUsers() {
    setLoading(true)
    setPageError("")

    try {
      const [
        usersResponse,
        departmentsResponse,
        rolesResponse,
      ] = await Promise.all([
        apiFetch<User[]>("/users"),
        apiFetch<Department[]>("/departments"),
        apiFetch<Role[]>("/roles"),
      ])

      setUsers(usersResponse)
      setDepartments(departmentsResponse)
      setRoles(rolesResponse)

      setSelectedUser((current) => {
        if (!current) {
          return null
        }

        return (
          usersResponse.find((user) => user.id === current.id) ??
          null
        )
      })
    } catch (error) {
      setPageError(
        error instanceof Error
          ? error.message
          : "Failed to load employees.",
      )
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    void loadUsers()
  }, [])

  const filteredUsers = useMemo(() => {
    const query = search.trim().toLowerCase()

    if (!query) {
      return users
    }

    return users.filter((user) => {
      const searchableValue = [
        user.full_name,
        user.email,
        user.employee_number ?? "",
        user.phone_number ?? "",
        user.department?.name ?? "",
        user.department?.code ?? "",
        user.role?.name ?? "",
        user.status,
        user.is_superuser ? "superadmin" : "",
      ]
        .join(" ")
        .toLowerCase()

      return searchableValue.includes(query)
    })
  }, [search, users])

  const activeUsers = users.filter((user) => user.is_active).length
  const passwordChangesRequired = users.filter(
    (user) => user.must_change_password,
  ).length

  function openRegistrationModal() {
    setForm({ ...emptyUserForm })
    setFormError("")
    setPageError("")
    setShowTemporaryPassword(false)
    setRegistrationOpen(true)
  }

  function closeRegistrationModal() {
    if (busy) {
      return
    }

    setRegistrationOpen(false)
    setForm({ ...emptyUserForm })
    setFormError("")
    setShowTemporaryPassword(false)
  }

  function updateForm<K extends keyof UserForm>(
    field: K,
    value: UserForm[K],
  ) {
    setForm((current) => ({
      ...current,
      [field]: value,
    }))
  }

  async function submitRegistration(
    event: FormEvent<HTMLFormElement>,
  ) {
    event.preventDefault()

    setBusy(true)
    setFormError("")
    setPageError("")

    const fullName = form.full_name.trim()
    const employeeNumber = form.employee_number.trim()
    const email = form.email.trim().toLowerCase()
    const phoneNumber = form.phone_number.trim()
    const temporaryPassword = form.temporary_password

    if (!fullName) {
      setFormError("Full name is required.")
      setBusy(false)
      return
    }

    if (!email) {
      setFormError(
        "Email is required because it is a login identifier.",
      )
      setBusy(false)
      return
    }

    if (!form.department_id && !form.is_superuser) {
      setFormError("Select a department.")
      setBusy(false)
      return
    }

    if (!form.role_id && !form.is_superuser) {
      setFormError("Select a role.")
      setBusy(false)
      return
    }

    if (temporaryPassword.length < 8) {
      setFormError(
        "The temporary password must contain at least 8 characters.",
      )
      setBusy(false)
      return
    }

    try {
      const createdUser = await apiFetch<User>("/users", {
        method: "POST",
        body: JSON.stringify({
          full_name: fullName,
          employee_number: employeeNumber || null,
          email,
          phone_number: phoneNumber || null,
          department_id: form.department_id
            ? Number(form.department_id)
            : null,
          role_id: form.role_id
            ? Number(form.role_id)
            : null,
          temporary_password: temporaryPassword,
          is_superuser: form.is_superuser,
          status: "active",
        }),
      })

      setUsers((currentUsers) =>
        [...currentUsers, createdUser].sort((first, second) =>
          first.full_name.localeCompare(second.full_name),
        ),
      )

      setRegistrationOpen(false)
      setForm({ ...emptyUserForm })
      setFormError("")
      setShowTemporaryPassword(false)

      await loadUsers()
    } catch (error) {
      setFormError(
        error instanceof Error
          ? error.message
          : "Unable to create employee.",
      )
    } finally {
      setBusy(false)
    }
  }

  async function toggleUser(user: User) {
    setActionUserId(user.id)
    setPageError("")

    try {
      const updatedUser = await apiFetch<User>(
        `/users/${user.id}`,
        {
          method: "PATCH",
          body: JSON.stringify({
            is_active: !user.is_active,
            status: user.is_active
              ? "deactivated"
              : "active",
          }),
        },
      )

      setUsers((currentUsers) =>
        currentUsers.map((currentUser) =>
          currentUser.id === updatedUser.id
            ? updatedUser
            : currentUser,
        ),
      )

      setSelectedUser((current) =>
        current?.id === updatedUser.id ? updatedUser : current,
      )
    } catch (error) {
      setPageError(
        error instanceof Error
          ? error.message
          : "Unable to update the employee account.",
      )
    } finally {
      setActionUserId(null)
    }
  }

  function canDeactivate(user: User) {
    return !(
      user.is_superuser &&
      user.email.toLowerCase() === "admin@mcc.org.ls"
    )
  }

  return (
    <>
      <PageIntro
        title="User Management"
        description="Register MCC employees, inspect their profiles, and manage department, role and account access."
        action={
          <button
            type="button"
            onClick={openRegistrationModal}
            className="flex h-10 items-center gap-2 rounded-md bg-primary px-4 text-sm font-medium text-primary-foreground transition hover:opacity-90"
          >
            <Plus className="size-4" />
            Register employee
          </button>
        }
      />

      {pageError && (
        <div className="rounded-md border border-destructive/30 bg-destructive/10 p-3 text-sm text-destructive">
          {pageError}
        </div>
      )}

      <div className="grid gap-4 sm:grid-cols-3">
        <Stat
          icon={<UsersIcon className="size-5" />}
          label="Total employees"
          value={users.length}
        />

        <Stat
          icon={<UserCog className="size-5" />}
          label="Active accounts"
          value={activeUsers}
        />

        <Stat
          icon={<RefreshCw className="size-5" />}
          label="Password change required"
          value={passwordChangesRequired}
        />
      </div>

      <div className="rounded-xl border bg-card">
        <div className="border-b p-4">
          <SearchBox
            value={search}
            onChange={setSearch}
            placeholder="Search by name, email, employee number, department or role..."
          />
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-muted/40 text-left text-xs uppercase tracking-wide text-muted-foreground">
              <tr>
                <th className="px-4 py-3">Employee</th>
                <th className="px-4 py-3">Login identifiers</th>
                <th className="px-4 py-3">Department</th>
                <th className="px-4 py-3">Role</th>
                <th className="px-4 py-3">Status</th>
                <th className="px-4 py-3 text-right">Action</th>
              </tr>
            </thead>

            <tbody>
              {filteredUsers.map((user) => (
                <tr
                  key={user.id}
                  className="border-t transition hover:bg-muted/20"
                >
                  <td className="px-4 py-3">
                    <button
                      type="button"
                      onClick={() => setSelectedUser(user)}
                      className="text-left"
                    >
                      <p className="font-medium transition hover:text-primary hover:underline">
                        {user.full_name}
                      </p>

                      {user.must_change_password && (
                        <p className="mt-1 text-xs text-amber-500">
                          Temporary password active
                        </p>
                      )}
                    </button>
                  </td>

                  <td className="px-4 py-3">
                    <p className="font-medium">{user.email}</p>

                    {user.employee_number && (
                      <p className="text-xs text-muted-foreground">
                        Employee number: {user.employee_number}
                      </p>
                    )}

                    {user.phone_number && (
                      <p className="text-xs text-muted-foreground">
                        Phone: {user.phone_number}
                      </p>
                    )}
                  </td>

                  <td className="px-4 py-3 text-muted-foreground">
                    {user.department?.name ?? "—"}
                  </td>

                  <td className="px-4 py-3">
                    {user.is_superuser
                      ? "SuperAdmin"
                      : user.role?.name ?? "—"}
                  </td>

                  <td className="px-4 py-3">
                    <StatusBadge
                      active={user.is_active}
                      label={user.status}
                    />
                  </td>

                  <td className="px-4 py-3 text-right">
                    <div className="flex justify-end gap-2">
                      <button
                        type="button"
                        onClick={() => setSelectedUser(user)}
                        className="rounded-md border px-3 py-1.5 text-xs transition hover:bg-muted"
                      >
                        View
                      </button>

                      <button
                        type="button"
                        onClick={() => void toggleUser(user)}
                        disabled={
                          !canDeactivate(user) ||
                          actionUserId === user.id
                        }
                        className="rounded-md border px-3 py-1.5 text-xs transition hover:bg-muted disabled:cursor-not-allowed disabled:opacity-40"
                      >
                        {actionUserId === user.id
                          ? "Updating..."
                          : user.is_active
                            ? "Deactivate"
                            : "Activate"}
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>

          {loading && (
            <p className="p-8 text-center text-sm text-muted-foreground">
              Loading employees...
            </p>
          )}

          {!loading && filteredUsers.length === 0 && (
            <p className="p-8 text-center text-sm text-muted-foreground">
              No employees found.
            </p>
          )}
        </div>
      </div>

      {registrationOpen && (
        <Modal
          title="Register MCC employee"
          onClose={closeRegistrationModal}
        >
          <form
            onSubmit={submitRegistration}
            autoComplete="off"
            className="grid gap-4 sm:grid-cols-2"
          >
            <div className="hidden" aria-hidden="true">
              <input
                type="text"
                name="fake-username"
                autoComplete="username"
                tabIndex={-1}
              />
              <input
                type="password"
                name="fake-password"
                autoComplete="current-password"
                tabIndex={-1}
              />
            </div>

            {formError && (
              <div className="rounded-md border border-destructive/30 bg-destructive/10 p-3 text-sm text-destructive sm:col-span-2">
                {formError}
              </div>
            )}

            <Field
              label="Full name"
              name="new-employee-full-name"
              value={form.full_name}
              onChange={(value) =>
                updateForm("full_name", value)
              }
              autoComplete="off"
              required
            />

            <Field
              label="Employee number"
              name="new-employee-number"
              value={form.employee_number}
              onChange={(value) =>
                updateForm("employee_number", value)
              }
              autoComplete="off"
              placeholder="Example: MCC-IT-001"
            />

            <Field
              label="Email"
              name="new-employee-email"
              type="email"
              value={form.email}
              onChange={(value) => updateForm("email", value)}
              autoComplete="off"
              placeholder="employee@mcc.org.ls"
              required
            />

            <Field
              label="Phone number"
              name="new-employee-phone"
              type="tel"
              value={form.phone_number}
              onChange={(value) =>
                updateForm("phone_number", value)
              }
              autoComplete="off"
              placeholder="+266..."
            />

            <label className={labelClass}>
              Department

              <select
                required={!form.is_superuser}
                disabled={form.is_superuser}
                className={inputClass}
                value={form.department_id}
                onChange={(event) =>
                  updateForm(
                    "department_id",
                    event.target.value,
                  )
                }
              >
                <option value="">
                  {form.is_superuser
                    ? "Not required for SuperAdmin"
                    : "Select department"}
                </option>

                {departments
                  .filter((department) => department.is_active)
                  .map((department) => (
                    <option
                      key={department.id}
                      value={department.id}
                    >
                      {department.name}
                    </option>
                  ))}
              </select>
            </label>

            <label className={labelClass}>
              Role

              <select
                required={!form.is_superuser}
                disabled={form.is_superuser}
                className={inputClass}
                value={form.role_id}
                onChange={(event) =>
                  updateForm("role_id", event.target.value)
                }
              >
                <option value="">
                  {form.is_superuser
                    ? "Not required for SuperAdmin"
                    : "Select role"}
                </option>

                {roles
                  .filter((role) => role.is_active)
                  .map((role) => (
                    <option key={role.id} value={role.id}>
                      {role.name}
                    </option>
                  ))}
              </select>
            </label>

            <label className={labelClass}>
              Temporary password

              <div className="relative">
                <input
                  required
                  minLength={8}
                  name="new-employee-temporary-password"
                  type={
                    showTemporaryPassword ? "text" : "password"
                  }
                  value={form.temporary_password}
                  onChange={(event) =>
                    updateForm(
                      "temporary_password",
                      event.target.value,
                    )
                  }
                  autoComplete="new-password"
                  className={`${inputClass} pr-10`}
                  placeholder="At least 8 characters"
                />

                <button
                  type="button"
                  onClick={() =>
                    setShowTemporaryPassword(
                      (current) => !current,
                    )
                  }
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground transition hover:text-foreground"
                  aria-label={
                    showTemporaryPassword
                      ? "Hide temporary password"
                      : "Show temporary password"
                  }
                >
                  {showTemporaryPassword ? (
                    <EyeOff className="size-4" />
                  ) : (
                    <Eye className="size-4" />
                  )}
                </button>
              </div>
            </label>

            <label className="flex items-center gap-2 self-end pb-2 text-sm">
              <input
                type="checkbox"
                checked={form.is_superuser}
                onChange={(event) => {
                  const isSuperuser = event.target.checked

                  setForm((current) => ({
                    ...current,
                    is_superuser: isSuperuser,
                    department_id: isSuperuser
                      ? ""
                      : current.department_id,
                    role_id: isSuperuser
                      ? ""
                      : current.role_id,
                  }))
                }}
              />
              Grant SuperAdmin access
            </label>

            <div className="rounded-md border bg-muted/30 p-3 text-xs leading-5 text-muted-foreground sm:col-span-2">
              The employee may sign in using their email,
              employee number, or phone number. A normal employee
              must change the temporary password during first
              login.
            </div>

            <div className="flex justify-end gap-2 pt-2 sm:col-span-2">
              <button
                type="button"
                onClick={closeRegistrationModal}
                disabled={busy}
                className="h-10 rounded-md border px-4 transition hover:bg-muted disabled:opacity-50"
              >
                Cancel
              </button>

              <button
                type="submit"
                disabled={busy}
                className="h-10 rounded-md bg-primary px-4 font-medium text-primary-foreground transition hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-50"
              >
                {busy ? "Creating..." : "Create user"}
              </button>
            </div>
          </form>
        </Modal>
      )}

      {selectedUser && (
        <Modal
          title="Employee profile"
          onClose={() => setSelectedUser(null)}
        >
          <EmployeeProfile
            user={selectedUser}
            actionBusy={actionUserId === selectedUser.id}
            canDeactivate={canDeactivate(selectedUser)}
            onClose={() => setSelectedUser(null)}
            onToggle={() => void toggleUser(selectedUser)}
          />
        </Modal>
      )}
    </>
  )
}

function EmployeeProfile({
  user,
  actionBusy,
  canDeactivate,
  onClose,
  onToggle,
}: {
  user: User
  actionBusy: boolean
  canDeactivate: boolean
  onClose: () => void
  onToggle: () => void
}) {
  const permissions = useMemo(() => {
    if (user.is_superuser) {
      return []
    }

    return user.role?.permissions ?? []
  }, [user])

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-4 rounded-xl border bg-muted/20 p-4 sm:flex-row sm:items-center">
        <div className="flex size-16 shrink-0 items-center justify-center rounded-full bg-primary/10 text-xl font-semibold text-primary">
          {initials(user.full_name)}
        </div>

        <div className="min-w-0 flex-1">
          <h3 className="truncate text-xl font-semibold">
            {user.full_name}
          </h3>

          <p className="mt-1 text-sm text-muted-foreground">
            {user.is_superuser
              ? "MCC Super Administrator"
              : user.role?.name ?? "No role assigned"}
          </p>

          <div className="mt-3 flex flex-wrap gap-2">
            <StatusBadge
              active={user.is_active}
              label={user.status}
            />

            {user.is_superuser && (
              <span className="inline-flex items-center gap-1 rounded-full bg-primary/10 px-2.5 py-1 text-xs font-medium text-primary">
                <ShieldCheck className="size-3.5" />
                Full system access
              </span>
            )}

            {user.must_change_password && (
              <span className="inline-flex items-center gap-1 rounded-full bg-amber-500/12 px-2.5 py-1 text-xs font-medium text-amber-500">
                <KeyRound className="size-3.5" />
                Password change required
              </span>
            )}
          </div>
        </div>
      </div>

      <ProfileSection title="Personal and login information">
        <div className="grid gap-3 sm:grid-cols-2">
          <DetailItem
            icon={<Mail className="size-4" />}
            label="Email address"
            value={user.email}
          />

          <DetailItem
            icon={<Fingerprint className="size-4" />}
            label="Employee number"
            value={user.employee_number ?? "Not provided"}
          />

          <DetailItem
            icon={<Phone className="size-4" />}
            label="Phone number"
            value={user.phone_number ?? "Not provided"}
          />

          <DetailItem
            icon={<BadgeCheck className="size-4" />}
            label="Available login identifiers"
            value={loginIdentifiers(user)}
          />
        </div>
      </ProfileSection>

      <ProfileSection title="Employment and access">
        <div className="grid gap-3 sm:grid-cols-2">
          <DetailItem
            icon={<Building2 className="size-4" />}
            label="Department"
            value={user.department?.name ?? "Not assigned"}
          />

          <DetailItem
            icon={<UserCog className="size-4" />}
            label="Role"
            value={
              user.is_superuser
                ? "SuperAdmin"
                : user.role?.name ?? "Not assigned"
            }
          />

          <DetailItem
            icon={<ShieldCheck className="size-4" />}
            label="Access level"
            value={
              user.is_superuser
                ? "Unrestricted SuperAdmin access"
                : "Role-based access"
            }
          />

          <DetailItem
            icon={<KeyRound className="size-4" />}
            label="Password status"
            value={
              user.must_change_password
                ? "Temporary password active"
                : "Password updated"
            }
          />
        </div>
      </ProfileSection>

      <ProfileSection title="Account information">
        <div className="grid gap-3 sm:grid-cols-2">
          <DetailItem
            icon={<CalendarDays className="size-4" />}
            label="Created"
            value={formatDate(user.created_at)}
          />

          <DetailItem
            icon={<CalendarDays className="size-4" />}
            label="Last updated"
            value={formatDate(user.updated_at)}
          />
        </div>
      </ProfileSection>

      <ProfileSection
        title={
          user.is_superuser
            ? "Permissions"
            : `Role permissions (${permissions.length})`
        }
      >
        {user.is_superuser ? (
          <div className="rounded-lg border border-primary/20 bg-primary/5 p-4 text-sm">
            This account bypasses role permission checks and has
            full access to all system modules.
          </div>
        ) : permissions.length > 0 ? (
          <PermissionList permissions={permissions} />
        ) : (
          <div className="rounded-lg border bg-muted/20 p-4 text-sm text-muted-foreground">
            No active permissions are assigned to this employee&apos;s
            role.
          </div>
        )}
      </ProfileSection>

      <div className="flex flex-col-reverse gap-2 border-t pt-5 sm:flex-row sm:justify-end">
        <button
          type="button"
          onClick={onClose}
          className="h-10 rounded-md border px-4 transition hover:bg-muted"
        >
          Close
        </button>

        <button
          type="button"
          onClick={onToggle}
          disabled={!canDeactivate || actionBusy}
          className="h-10 rounded-md bg-primary px-4 font-medium text-primary-foreground transition hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-40"
        >
          {actionBusy
            ? "Updating..."
            : user.is_active
              ? "Deactivate account"
              : "Activate account"}
        </button>
      </div>
    </div>
  )
}

function PermissionList({
  permissions,
}: {
  permissions: Permission[]
}) {
  const groupedPermissions = useMemo(() => {
    return permissions
      .filter((permission) => permission.is_active)
      .reduce<Record<string, Permission[]>>(
        (groups, permission) => {
          const group =
            permission.code.split(".")[0] || "general"

          if (!groups[group]) {
            groups[group] = []
          }

          groups[group].push(permission)
          return groups
        },
        {},
      )
  }, [permissions])

  return (
    <div className="space-y-4">
      {Object.entries(groupedPermissions)
        .sort(([first], [second]) =>
          first.localeCompare(second),
        )
        .map(([group, groupPermissions]) => (
          <div key={group}>
            <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
              {humanize(group)}
            </p>

            <div className="flex flex-wrap gap-2">
              {groupPermissions
                .sort((first, second) =>
                  first.code.localeCompare(second.code),
                )
                .map((permission) => (
                  <span
                    key={permission.id}
                    title={permission.description ?? permission.name}
                    className="rounded-md border bg-muted/20 px-2.5 py-1.5 text-xs"
                  >
                    {permission.code}
                  </span>
                ))}
            </div>
          </div>
        ))}
    </div>
  )
}

function ProfileSection({
  title,
  children,
}: {
  title: string
  children: ReactNode
}) {
  return (
    <section>
      <h4 className="mb-3 text-sm font-semibold">{title}</h4>
      {children}
    </section>
  )
}

function DetailItem({
  icon,
  label,
  value,
}: {
  icon: ReactNode
  label: string
  value: string
}) {
  return (
    <div className="rounded-lg border bg-card p-4">
      <div className="flex items-center gap-2 text-muted-foreground">
        {icon}
        <p className="text-xs font-semibold uppercase tracking-wide">
          {label}
        </p>
      </div>

      <p className="mt-2 break-words text-sm font-medium">
        {value}
      </p>
    </div>
  )
}

type FieldProps = {
  label: string
  name: string
  value: string
  onChange: (value: string) => void
  type?: string
  autoComplete?: string
  placeholder?: string
  required?: boolean
}

function Field({
  label,
  name,
  value,
  onChange,
  type = "text",
  autoComplete = "off",
  placeholder,
  required = false,
}: FieldProps) {
  return (
    <label className={labelClass}>
      {label}

      <input
        name={name}
        required={required}
        type={type}
        value={value}
        onChange={(event) => onChange(event.target.value)}
        autoComplete={autoComplete}
        placeholder={placeholder}
        className={inputClass}
      />
    </label>
  )
}

function Stat({
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
      <div className="rounded-lg bg-primary/10 p-3 text-primary">
        {icon}
      </div>

      <div>
        <p className="text-2xl font-semibold">{value}</p>
        <p className="text-xs text-muted-foreground">{label}</p>
      </div>
    </div>
  )
}

function initials(fullName: string) {
  return fullName
    .split(/\s+/)
    .filter(Boolean)
    .map((part) => part[0])
    .join("")
    .slice(0, 2)
    .toUpperCase()
}

function loginIdentifiers(user: User) {
  const identifiers = [
    user.email,
    user.employee_number,
    user.phone_number,
  ].filter(Boolean)

  return identifiers.join(", ")
}

function formatDate(value: string) {
  const date = new Date(value)

  if (Number.isNaN(date.getTime())) {
    return "Not available"
  }

  return new Intl.DateTimeFormat("en-LS", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(date)
}

function humanize(value: string) {
  return value
    .replace(/[_-]+/g, " ")
    .replace(/\b\w/g, (character) => character.toUpperCase())
}