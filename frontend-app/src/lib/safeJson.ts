// Wraps response.json() so a malformed body (e.g. an HTML error page
// returned by a misconfigured proxy, or an empty 204 body) never throws a
// raw, potentially detail-leaking parse exception up into UI code. Use this
// everywhere an API response needs to be parsed instead of calling
// `response.json()` directly.

export type SafeJsonResult<T> = { ok: true; data: T } | { ok: false; error: string }

export async function safeJson<T = unknown>(response: Response): Promise<SafeJsonResult<T>> {
  const text = await response.text().catch(() => '')

  if (!text) {
    return { ok: false, error: 'Empty response body' }
  }

  try {
    return { ok: true, data: JSON.parse(text) as T }
  } catch {
    return { ok: false, error: 'Response was not valid JSON' }
  }
}
