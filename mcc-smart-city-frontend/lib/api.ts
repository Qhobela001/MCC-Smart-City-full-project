export const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1"

export class ApiError extends Error {
  status: number
  constructor(message: string, status: number) { super(message); this.status = status }
}

export async function apiFetch<T>(path: string, options: RequestInit = {}): Promise<T> {
  const token = typeof window !== "undefined" ? localStorage.getItem("mcc_access_token") : null
  const headers = new Headers(options.headers)
  if (!headers.has("Content-Type") && options.body) headers.set("Content-Type", "application/json")
  if (token) headers.set("Authorization", `Bearer ${token}`)
  const response = await fetch(`${API_URL}${path}`, { ...options, headers, cache: "no-store" })
  if (!response.ok) {
    let message = `Request failed (${response.status})`
    try { const data = await response.json(); message = data.detail || data.message || message } catch {}
    if (response.status === 401 && typeof window !== "undefined") {
      localStorage.removeItem("mcc_access_token")
      localStorage.removeItem("mcc_user")
    }
    throw new ApiError(message, response.status)
  }
  if (response.status === 204) return undefined as T
  return response.json() as Promise<T>
}
