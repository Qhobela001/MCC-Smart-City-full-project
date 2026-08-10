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
  const fallback = `Request failed (${response.status})`

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
    headers.set("Authorization", `Bearer ${token}`)
  }

  const response = await fetch(`${API_URL}${path}`, {
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
    headers.set("Authorization", `Bearer ${token}`)
  }

  const response = await fetch(`${API_URL}${path}`, {
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
