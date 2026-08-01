"use client"

import { useEffect } from "react"
import {
  usePathname,
  useRouter,
} from "next/navigation"
import { LoaderCircle } from "lucide-react"

import { useAuth } from "./auth-provider"

export function ProtectedRoute({
  children,
}: {
  children: React.ReactNode
}) {
  const { user, loading } = useAuth()

  const router = useRouter()
  const pathname = usePathname()

  useEffect(() => {
    if (loading) {
      return
    }

    if (!user) {
      router.replace(
        `/login?next=${encodeURIComponent(pathname)}`,
      )
      return
    }

    if (
      user.must_change_password &&
      pathname !== "/change-password"
    ) {
      router.replace("/change-password")
    }
  }, [
    loading,
    user,
    pathname,
    router,
  ])

  if (loading || !user) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-background">
        <LoaderCircle className="size-7 animate-spin text-primary" />
      </div>
    )
  }

  if (
    user.must_change_password &&
    pathname !== "/change-password"
  ) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-background">
        <LoaderCircle className="size-7 animate-spin text-primary" />
      </div>
    )
  }

  return <>{children}</>
}