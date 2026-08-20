"use client"

import Image from "next/image"
import Link from "next/link"
import {
  FormEvent,
  useEffect,
  useState,
} from "react"
import {
  ArrowLeft,
  CheckCircle2,
  Eye,
  EyeOff,
  LoaderCircle,
  LockKeyhole,
  ShieldCheck,
} from "lucide-react"

import { apiFetch } from "@/lib/api"


type MessageResponse = {
  message: string
}


export default function ResetPasswordPage() {
  const [token, setToken] = useState("")
  const [tokenLoaded, setTokenLoaded] = useState(false)
  const [newPassword, setNewPassword] = useState("")
  const [confirmPassword, setConfirmPassword] = useState("")
  const [showPassword, setShowPassword] = useState(false)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState("")
  const [message, setMessage] = useState("")

  useEffect(() => {
    const params = new URLSearchParams(
      window.location.search,
    )

    setToken(params.get("token") || "")
    setTokenLoaded(true)
  }, [])

  async function submit(
    event: FormEvent<HTMLFormElement>,
  ) {
    event.preventDefault()

    setError("")
    setMessage("")

    if (newPassword.length < 12) {
      setError(
        "Password must contain at least 12 characters",
      )
      return
    }

    if (newPassword !== confirmPassword) {
      setError("Passwords do not match")
      return
    }

    setBusy(true)

    try {
      const response = await apiFetch<MessageResponse>(
        "/auth/reset-password",
        {
          method: "POST",
          body: JSON.stringify({
            token,
            new_password: newPassword,
            confirm_password: confirmPassword,
          }),
        },
      )

      setMessage(response.message)
      setNewPassword("")
      setConfirmPassword("")
    } catch (error) {
      setError(
        error instanceof Error
          ? error.message
          : "Unable to reset your password",
      )
    } finally {
      setBusy(false)
    }
  }

  const missingToken = tokenLoaded && !token

  return (
    <main className="relative min-h-screen overflow-hidden bg-[#07111f] text-white">
      <div className="absolute inset-0 bg-[radial-gradient(circle_at_20%_10%,rgba(36,129,197,.24),transparent_34%),radial-gradient(circle_at_90%_90%,rgba(14,116,144,.22),transparent_35%)]" />

      <div className="relative grid min-h-screen lg:grid-cols-[1.1fr_.9fr]">
        <section className="hidden flex-col justify-between border-r border-white/10 p-12 lg:flex">
          <div className="flex items-center gap-4">
            <Image
              src="/mcc-logo1.png"
              alt="MCC logo"
              width={78}
              height={92}
            />

            <div>
              <p className="text-xl font-semibold">
                MCC Command Center
              </p>

              <p className="text-sm text-slate-400">
                Maseru City Council
              </p>
            </div>
          </div>

          <div className="max-w-xl">
            <div className="mb-6 inline-flex items-center gap-2 rounded-full border border-cyan-400/20 bg-cyan-400/10 px-4 py-2 text-sm text-cyan-200">
              <ShieldCheck className="size-4" />
              Protected password reset
            </div>

            <h1 className="text-5xl font-semibold leading-tight">
              Set a new password for your MCC Command Center
              account.
            </h1>

            <p className="mt-5 max-w-lg text-lg leading-8 text-slate-400">
              Reset links are time-limited and become invalid
              once your password has successfully changed.
            </p>
          </div>

          <p className="text-xs text-slate-500">
            Authorised MCC personnel only
          </p>
        </section>

        <section className="flex items-center justify-center p-6">
          <div className="w-full max-w-md rounded-2xl border border-white/10 bg-white/[.06] p-7 shadow-2xl backdrop-blur-xl sm:p-9">
            <div className="mb-8 lg:hidden">
              <Image
                src="/mcc-logo1.png"
                alt="MCC logo"
                width={64}
                height={76}
              />
            </div>

            <p className="text-sm font-medium text-cyan-300">
              Account recovery
            </p>

            <h1 className="mt-2 text-3xl font-semibold">
              Reset password
            </h1>

            {message ? (
              <div className="mt-7">
                <div className="rounded-lg border border-emerald-400/30 bg-emerald-400/10 px-4 py-4 text-sm text-emerald-100">
                  <div className="flex items-start gap-3">
                    <CheckCircle2 className="mt-0.5 size-5 shrink-0" />
                    <p>{message}</p>
                  </div>
                </div>

                <Link
                  href="/login"
                  className="mt-6 flex h-12 w-full items-center justify-center rounded-lg bg-cyan-500 font-medium text-slate-950 transition hover:bg-cyan-400"
                >
                  Sign in with new password
                </Link>
              </div>
            ) : missingToken ? (
              <div className="mt-7">
                <div className="rounded-lg border border-red-400/30 bg-red-400/10 px-4 py-4 text-sm text-red-200">
                  This reset link is incomplete. Request a new
                  password reset link from the sign-in page.
                </div>

                <Link
                  href="/forgot-password"
                  className="mt-6 flex h-12 w-full items-center justify-center rounded-lg bg-cyan-500 font-medium text-slate-950 transition hover:bg-cyan-400"
                >
                  Request a new reset link
                </Link>
              </div>
            ) : (
              <form
                onSubmit={submit}
                className="mt-7"
              >
                <p className="mb-5 text-sm leading-6 text-slate-400">
                  Choose a password containing at least 12
                  characters. It must be different from your
                  current password.
                </p>

                {error && (
                  <div className="mb-5 rounded-lg border border-red-400/30 bg-red-400/10 px-4 py-3 text-sm text-red-200">
                    {error}
                  </div>
                )}

                <label className="block text-sm text-slate-300">
                  New password
                </label>

                <div className="mt-2 flex items-center rounded-lg border border-white/10 bg-black/20 px-3 focus-within:border-cyan-400/60">
                  <LockKeyhole className="size-4 text-slate-500" />

                  <input
                    type={showPassword ? "text" : "password"}
                    value={newPassword}
                    onChange={(event) =>
                      setNewPassword(event.target.value)
                    }
                    minLength={12}
                    maxLength={128}
                    required
                    autoComplete="new-password"
                    className="h-12 flex-1 bg-transparent px-3 text-sm outline-none"
                  />

                  <button
                    type="button"
                    onClick={() =>
                      setShowPassword(
                        (current) => !current,
                      )
                    }
                    className="text-slate-500 hover:text-white"
                    aria-label={
                      showPassword
                        ? "Hide password"
                        : "Show password"
                    }
                  >
                    {showPassword ? (
                      <EyeOff className="size-4" />
                    ) : (
                      <Eye className="size-4" />
                    )}
                  </button>
                </div>

                <label className="mt-5 block text-sm text-slate-300">
                  Confirm new password
                </label>

                <div className="mt-2 flex items-center rounded-lg border border-white/10 bg-black/20 px-3 focus-within:border-cyan-400/60">
                  <LockKeyhole className="size-4 text-slate-500" />

                  <input
                    type={showPassword ? "text" : "password"}
                    value={confirmPassword}
                    onChange={(event) =>
                      setConfirmPassword(event.target.value)
                    }
                    minLength={12}
                    maxLength={128}
                    required
                    autoComplete="new-password"
                    className="h-12 flex-1 bg-transparent px-3 text-sm outline-none"
                  />
                </div>

                <button
                  type="submit"
                  disabled={busy || !tokenLoaded || !token}
                  className="mt-6 flex h-12 w-full items-center justify-center gap-2 rounded-lg bg-cyan-500 font-medium text-slate-950 transition hover:bg-cyan-400 disabled:cursor-not-allowed disabled:opacity-60"
                >
                  {busy && (
                    <LoaderCircle className="size-4 animate-spin" />
                  )}

                  Reset password
                </button>

                <Link
                  href="/login"
                  className="mt-5 flex items-center justify-center gap-2 text-sm text-slate-400 transition hover:text-white"
                >
                  <ArrowLeft className="size-4" />
                  Back to sign in
                </Link>
              </form>
            )}
          </div>
        </section>
      </div>
    </main>
  )
}
