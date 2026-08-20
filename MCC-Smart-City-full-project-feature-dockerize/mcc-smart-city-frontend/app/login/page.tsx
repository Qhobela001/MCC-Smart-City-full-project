"use client"

import Image from "next/image"
import Link from "next/link"
import {
  FormEvent,
  useEffect,
  useState,
} from "react"
import { useRouter } from "next/navigation"
import {
  Eye,
  EyeOff,
  LoaderCircle,
  LockKeyhole,
  ShieldCheck,
  UserRound,
} from "lucide-react"

import { useAuth } from "@/components/auth/auth-provider"

export default function LoginPage() {
  const {
    login,
    user,
    loading,
  } = useAuth()

  const router = useRouter()

  const [identifier, setIdentifier] = useState("")
  const [password, setPassword] = useState("")
  const [showPassword, setShowPassword] =
    useState(false)
  const [error, setError] = useState("")
  const [busy, setBusy] = useState(false)

  useEffect(() => {
    if (loading || !user) {
      return
    }

    router.replace(
      user.must_change_password
        ? "/change-password"
        : "/",
    )
  }, [
    loading,
    user,
    router,
  ])

  async function submit(
    event: FormEvent<HTMLFormElement>,
  ) {
    event.preventDefault()

    setError("")
    setBusy(true)

    try {
      const authenticatedUser = await login(
        identifier,
        password,
      )

      if (authenticatedUser.must_change_password) {
        router.replace("/change-password")
      } else {
        router.replace("/")
      }
    } catch (error) {
      setError(
        error instanceof Error
          ? error.message
          : "Unable to sign in",
      )
    } finally {
      setBusy(false)
    }
  }

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
              Secure municipal operations
            </div>

            <h1 className="text-5xl font-semibold leading-tight">
              Smart city oversight, administration and
              incident response.
            </h1>

            <p className="mt-5 max-w-lg text-lg leading-8 text-slate-400">
              Manage departments, roles, employees,
              infrastructure and live city operations from
              one secure command platform.
            </p>
          </div>

          <p className="text-xs text-slate-500">
            Authorised MCC personnel only
          </p>
        </section>

        <section className="flex items-center justify-center p-6">
          <form
            onSubmit={submit}
            className="w-full max-w-md rounded-2xl border border-white/10 bg-white/[.06] p-7 shadow-2xl backdrop-blur-xl sm:p-9"
          >
            <div className="mb-8 lg:hidden">
              <Image
                src="/mcc-logo1.png"
                alt="MCC logo"
                width={64}
                height={76}
              />
            </div>

            <p className="text-sm font-medium text-cyan-300">
              Welcome back
            </p>

            <h2 className="mt-2 text-3xl font-semibold">
              Sign in to MCC
            </h2>

            <p className="mt-2 text-sm text-slate-400">
              Use your email, employee number, or phone
              number.
            </p>

            {error && (
              <div className="mt-5 rounded-lg border border-red-400/30 bg-red-400/10 px-4 py-3 text-sm text-red-200">
                {error}
              </div>
            )}

            <label className="mt-7 block text-sm text-slate-300">
              Identifier
            </label>

            <div className="mt-2 flex items-center rounded-lg border border-white/10 bg-black/20 px-3 focus-within:border-cyan-400/60">
              <UserRound className="size-4 text-slate-500" />

              <input
                value={identifier}
                onChange={(event) =>
                  setIdentifier(event.target.value)
                }
                required
                autoComplete="username"
                className="h-12 flex-1 bg-transparent px-3 text-sm outline-none placeholder:text-slate-600"
                placeholder="admin@mcc.org.ls"
              />
            </div>

            <label className="mt-5 block text-sm text-slate-300">
              Password
            </label>

            <div className="mt-2 flex items-center rounded-lg border border-white/10 bg-black/20 px-3 focus-within:border-cyan-400/60">
              <LockKeyhole className="size-4 text-slate-500" />

              <input
                type={
                  showPassword
                    ? "text"
                    : "password"
                }
                value={password}
                onChange={(event) =>
                  setPassword(event.target.value)
                }
                required
                autoComplete="current-password"
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

            <div className="mt-3 flex justify-end">
              <Link
                href="/forgot-password"
                className="text-sm font-medium text-cyan-300 transition hover:text-cyan-200"
              >
                Forgot password?
              </Link>
            </div>

            <button
              type="submit"
              disabled={busy || loading}
              className="mt-6 flex h-12 w-full items-center justify-center gap-2 rounded-lg bg-cyan-500 font-medium text-slate-950 transition hover:bg-cyan-400 disabled:cursor-not-allowed disabled:opacity-60"
            >
              {busy && (
                <LoaderCircle className="size-4 animate-spin" />
              )}

              Sign in
            </button>
          </form>
        </section>
      </div>
    </main>
  )
}
