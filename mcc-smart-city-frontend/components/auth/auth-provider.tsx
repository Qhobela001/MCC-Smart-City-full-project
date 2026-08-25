"use client"

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
} from "react"
import { useRouter } from "next/navigation"

import { apiFetch } from "@/lib/api"
import type { LoginResponse, User } from "@/lib/types"

type AuthContextValue = {
  user: User | null
  loading: boolean
  login: (
    identifier: string,
    password: string,
  ) => Promise<User>
  logout: () => void
  refreshUser: () => Promise<User | null>
}

const AuthContext = createContext<AuthContextValue | null>(null)

export function AuthProvider({
  children,
}: {
  children: React.ReactNode
}) {
  const [user, setUser] = useState<User | null>(null)
  const [loading, setLoading] = useState(true)

  const router = useRouter()

  const refreshUser = useCallback(async (): Promise<User | null> => {
    const token = localStorage.getItem("mcc_access_token")

    if (!token) {
      setUser(null)
      setLoading(false)
      return null
    }

    try {
      const currentUser = await apiFetch<User>("/auth/me")

      setUser(currentUser)

      localStorage.setItem(
        "mcc_user",
        JSON.stringify(currentUser),
      )

      return currentUser
    } catch {
      localStorage.removeItem("mcc_access_token")
      localStorage.removeItem("mcc_user")

      setUser(null)

      return null
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    void refreshUser()
  }, [refreshUser])

  const login = useCallback(
    async (
      identifier: string,
      password: string,
    ): Promise<User> => {
      const data = await apiFetch<LoginResponse>(
        "/auth/login",
        {
          method: "POST",
          body: JSON.stringify({
            identifier,
            password,
          }),
        },
      )

      localStorage.setItem(
        "mcc_access_token",
        data.access_token,
      )

      localStorage.setItem(
        "mcc_user",
        JSON.stringify(data.user),
      )

      setUser(data.user)

      return data.user
    },
    [],
  )

  const logout = useCallback(() => {
    localStorage.removeItem("mcc_access_token")
    localStorage.removeItem("mcc_user")

    setUser(null)

    router.replace("/login")
  }, [router])

  const value = useMemo(
    () => ({
      user,
      loading,
      login,
      logout,
      refreshUser,
    }),
    [
      user,
      loading,
      login,
      logout,
      refreshUser,
    ],
  )

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const context = useContext(AuthContext)

  if (!context) {
    throw new Error(
      "useAuth must be used within AuthProvider",
    )
  }

  return context
}