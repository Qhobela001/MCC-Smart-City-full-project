"use client"

import {
  FormEvent,
  useEffect,
  useState,
} from "react"
import { useRouter } from "next/navigation"
import {
  KeyRound,
  LoaderCircle,
  ShieldCheck,
} from "lucide-react"

import { apiFetch } from "@/lib/api"
import { useAuth } from "@/components/auth/auth-provider"
import { ProtectedRoute } from "@/components/auth/protected-route"

function ChangePasswordForm() {
  const {
    user,
    refreshUser,
  } = useAuth()

  const router = useRouter()

  const [currentPassword, setCurrentPassword] =
    useState("")
  const [newPassword, setNewPassword] = useState("")
  const [confirmPassword, setConfirmPassword] =
    useState("")
  const [error, setError] = useState("")
  const [success, setSuccess] = useState("")
  const [busy, setBusy] = useState(false)

  useEffect(() => {
    if (
      user &&
      !user.must_change_password
    ) {
      router.replace("/")
    }
  }, [
    user,
    router,
  ])

  async function submit(
    event: FormEvent<HTMLFormElement>,
  ) {
    event.preventDefault()

    setError("")
    setSuccess("")

    if (newPassword !== confirmPassword) {
      setError("New passwords do not match.")
      return
    }

    if (newPassword.length < 8) {
      setError(
        "The new password must contain at least 8 characters.",
      )
      return
    }

    if (newPassword === currentPassword) {
      setError(
        "The new password must be different from the temporary password.",
      )
      return
    }

    setBusy(true)

    try {
      await apiFetch(
        "/users/change-password",
        {
          method: "POST",
          body: JSON.stringify({
            current_password: currentPassword,
            new_password: newPassword,
          }),
        },
      )

      const updatedUser = await refreshUser()

      if (
        !updatedUser ||
        updatedUser.must_change_password
      ) {
        throw new Error(
          "The password was changed, but the account status could not be refreshed.",
        )
      }

      setSuccess(
        "Password changed successfully. Opening the command center...",
      )

      router.replace("/")
      router.refresh()
    } catch (error) {
      setError(
        error instanceof Error
          ? error.message
          : "Unable to change password",
      )
    } finally {
      setBusy(false)
    }
  }

  return (
    <main className="relative flex min-h-screen items-center justify-center overflow-hidden bg-[#07111f] p-6 text-white">
      <div className="absolute inset-0 bg-[radial-gradient(circle_at_20%_10%,rgba(36,129,197,.24),transparent_34%),radial-gradient(circle_at_90%_90%,rgba(14,116,144,.22),transparent_35%)]" />

      <form
        onSubmit={submit}
        className="relative w-full max-w-md rounded-2xl border border-white/10 bg-white/[.06] p-7 shadow-2xl backdrop-blur-xl sm:p-9"
      >
        <div className="flex size-12 items-center justify-center rounded-xl bg-cyan-400/10 text-cyan-300">
          <KeyRound className="size-6" />
        </div>

        <h1 className="mt-6 text-2xl font-semibold">
          Change temporary password
        </h1>

        <p className="mt-2 text-sm leading-6 text-slate-400">
          For security, you must create a private password
          before entering the MCC Command Center.
        </p>

        {error && (
          <div className="mt-5 rounded-lg border border-red-400/30 bg-red-400/10 p-3 text-sm text-red-200">
            {error}
          </div>
        )}

        {success && (
          <div className="mt-5 flex items-center gap-2 rounded-lg border border-emerald-400/30 bg-emerald-400/10 p-3 text-sm text-emerald-200">
            <ShieldCheck className="size-4" />
            {success}
          </div>
        )}

        <label className="mt-6 block text-sm text-slate-300">
          Current temporary password
        </label>

        <input
          type="password"
          required
          value={currentPassword}
          onChange={(event) =>
            setCurrentPassword(
              event.target.value,
            )
          }
          autoComplete="current-password"
          className="mt-2 h-12 w-full rounded-lg border border-white/10 bg-black/20 px-3 outline-none focus:border-cyan-400/60"
        />

        <label className="mt-5 block text-sm text-slate-300">
          New password
        </label>

        <input
          type="password"
          required
          minLength={8}
          value={newPassword}
          onChange={(event) =>
            setNewPassword(event.target.value)
          }
          autoComplete="new-password"
          className="mt-2 h-12 w-full rounded-lg border border-white/10 bg-black/20 px-3 outline-none focus:border-cyan-400/60"
        />

        <label className="mt-5 block text-sm text-slate-300">
          Confirm new password
        </label>

        <input
          type="password"
          required
          minLength={8}
          value={confirmPassword}
          onChange={(event) =>
            setConfirmPassword(
              event.target.value,
            )
          }
          autoComplete="new-password"
          className="mt-2 h-12 w-full rounded-lg border border-white/10 bg-black/20 px-3 outline-none focus:border-cyan-400/60"
        />

        <button
          type="submit"
          disabled={busy}
          className="mt-7 flex h-12 w-full items-center justify-center gap-2 rounded-lg bg-cyan-500 font-medium text-slate-950 transition hover:bg-cyan-400 disabled:cursor-not-allowed disabled:opacity-60"
        >
          {busy && (
            <LoaderCircle className="size-4 animate-spin" />
          )}

          Save new password
        </button>
      </form>
    </main>
  )
}

export default function ChangePasswordPage() {
  return (
    <ProtectedRoute>
      <ChangePasswordForm />
    </ProtectedRoute>
  )
}