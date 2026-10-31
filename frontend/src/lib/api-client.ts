import { API_BASE_URL } from "@/lib/env"

export class ApiError extends Error {
  constructor(
    message: string,
    readonly status: number,
    readonly body: Record<string, unknown> = {}
  ) {
    super(message)
    this.name = "ApiError"
  }
}

type RequestOptions = Omit<RequestInit, "body"> & { json?: unknown; body?: BodyInit }

export async function apiRequest<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const { json, headers, ...init } = options
  let response: Response
  try {
    response = await fetch(`${API_BASE_URL}${path}`, {
      ...init,
      headers: json === undefined ? headers : { "Content-Type": "application/json", ...headers },
      body: json === undefined ? init.body : JSON.stringify(json),
    })
  } catch {
    throw new ApiError(
      `Cannot reach the ScholarLens API at ${API_BASE_URL}. Check that the backend is running.`,
      0
    )
  }

  if (response.status === 204) return undefined as T

  const payload = await response.json().catch(() => ({}))
  if (!response.ok) {
    throw new ApiError(readDetail(payload, response.status), response.status, payload)
  }
  return payload as T
}

function readDetail(payload: unknown, status: number): string {
  const detail = (payload as { detail?: unknown })?.detail
  if (typeof detail === "string") return detail
  // FastAPI validation errors arrive as a list of {msg} objects.
  if (Array.isArray(detail) && detail.length > 0) {
    const message = String(detail[0]?.msg ?? "")
    return message.replace(/^Value error, /, "") || "The request was not valid."
  }
  return `Request failed with status ${status}.`
}

export function apiUrl(path: string): string {
  return `${API_BASE_URL}${path}`
}
