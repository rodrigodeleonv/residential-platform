const API_PREFIX = "/api/v0";

export class ApiError extends Error {
  constructor(
    public readonly status: number,
    detail: string,
  ) {
    super(detail);
    this.name = "ApiError";
  }
}

/** Call the backend API; the session travels in an httpOnly cookie. */
export async function api<T = void>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_PREFIX}${path}`, {
    ...init,
    headers: init?.body != null ? { "Content-Type": "application/json" } : undefined,
  });
  if (!response.ok) {
    let detail = response.statusText;
    try {
      detail = ((await response.json()) as { detail?: string }).detail ?? detail;
    } catch {
      // non-JSON error body; keep the status text
    }
    throw new ApiError(response.status, detail);
  }
  if (response.status === 204) {
    return undefined as T;
  }
  return (await response.json()) as T;
}
