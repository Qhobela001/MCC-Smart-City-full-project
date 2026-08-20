"use client"

import Image from "next/image"
import Link from "next/link"
import {
  FormEvent,
  useState,
} from "react"
import {
  ArrowLeft,
  CheckCircle2,
  LoaderCircle,
  Mail,
  ShieldCheck,
} from "lucide-react"

import { apiFetch } from "@/lib/api"


type MessageResponse = {
  message: string
}


export default function ForgotPasswordPage() {
  const [email, setEmail] = useState("")
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState("")
  const [message, setMessage] = useState("")

  async function submit(
    event: FormEvent<HTMLFormElement>,
  ) {
    event.preventDefault()

    setBusy(true)
    setError("")
    setMessage("")

    try {
      const response = await apiFetch<MessageResponse>(
        "/auth/forgot-password",
        {
          method: "POST",
          body: JSON.stringify({
            email,
          }),
        },
      )

      setMessage(response.message)
    } catch (error) {
      setError(
        error instanceof Error
          ? error.message
          : "Unable to request a password reset",
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
              Secure account recovery
            </div>

            <h1 className="text-5xl font-semibold leading-tight">
              Restore access without exposing municipal
              account information.
            </h1>

            <p className="mt-5 max-w-lg text-lg leading-8 text-slate-400">
              Password recovery uses a short-lived reset
              link sent to the employee email address
              registered with MCC.
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
              Forgot your password?
            </h1>

            <p className="mt-3 text-sm leading-6 text-slate-400">
              Enter the email address registered on your MCC
              account. If an active account exists, reset
              instructions will be sent to that address.
            </p>

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
                  className="mt-6 flex h-12 w-full items-center justify-center gap-2 rounded-lg border border-white/10 bg-white/[.06] font-medium text-white transition hover:bg-white/[.1]"
                >
                  <ArrowLeft className="size-4" />
                  Back to sign in
                </Link>
              </div>
            ) : (
              <form
                onSubmit={submit}
                className="mt-7"
              >
                {error && (
                  <div className="mb-5 rounded-lg border border-red-400/30 bg-red-400/10 px-4 py-3 text-sm text-red-200">
                    {error}
                  </div>
                )}

                <label className="block text-sm text-slate-300">
                  MCC email address
                </label>

                <div className="mt-2 flex items-center rounded-lg border border-white/10 bg-black/20 px-3 focus-within:border-cyan-400/60">
                  <Mail className="size-4 text-slate-500" />

                  <input
                    type="email"
                    value={email}
                    onChange={(event) =>
                      setEmail(event.target.value)
                    }
                    required
                    autoComplete="email"
                    className="h-12 flex-1 bg-transparent px-3 text-sm outline-none placeholder:text-slate-600"
                    placeholder="name@mcc.org.ls"
                  />
                </div>

                <button
                  type="submit"
                  disabled={busy}
                  className="mt-6 flex h-12 w-full items-center justify-center gap-2 rounded-lg bg-cyan-500 font-medium text-slate-950 transition hover:bg-cyan-400 disabled:cursor-not-allowed disabled:opacity-60"
                >
                  {busy && (
                    <LoaderCircle className="size-4 animate-spin" />
                  )}

                  Send reset instructions
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
