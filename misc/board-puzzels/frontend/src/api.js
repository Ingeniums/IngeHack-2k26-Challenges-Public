const defaultApiBaseUrl = `http://${window.location.hostname || '127.0.0.1'}:8000`

export const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL ?? defaultApiBaseUrl).replace(
  /\/$/,
  '',
)
export const TOKEN_STORAGE_KEY = 'are_you_a_robot_token'

export function getStoredToken() {
  const sessionToken = window.sessionStorage.getItem(TOKEN_STORAGE_KEY)
  if (sessionToken) {
    return sessionToken
  }

  const legacyToken = window.localStorage.getItem(TOKEN_STORAGE_KEY)
  if (!legacyToken) {
    return null
  }

  // Migrate away from shared cross-tab storage to avoid account bleed between tabs.
  window.sessionStorage.setItem(TOKEN_STORAGE_KEY, legacyToken)
  window.localStorage.removeItem(TOKEN_STORAGE_KEY)
  return legacyToken
}

export function setStoredToken(token) {
  window.sessionStorage.setItem(TOKEN_STORAGE_KEY, token)
  window.localStorage.removeItem(TOKEN_STORAGE_KEY)
}

export function clearStoredToken() {
  window.sessionStorage.removeItem(TOKEN_STORAGE_KEY)
  window.localStorage.removeItem(TOKEN_STORAGE_KEY)
}

export async function apiRequest(path, options = {}) {
  const {
    method = 'GET',
    body,
    token = getStoredToken(),
    requiresAuth = true,
  } = options

  const headers = {}

  if (body !== undefined) {
    headers['Content-Type'] = 'application/json'
  }

  if (requiresAuth) {
    if (!token) {
      const error = new Error('Missing authentication token')
      error.status = 401
      throw error
    }
    headers.Authorization = `Bearer ${token}`
  }

  const response = await fetch(`${API_BASE_URL}${path}`, {
    method,
    headers,
    body: body === undefined ? undefined : JSON.stringify(body),
  })

  const payload = await response.json().catch(() => null)

  if (!response.ok) {
    const detail = payload?.detail ?? `${method} ${path} failed (${response.status})`
    const error = new Error(detail)
    error.status = response.status
    throw error
  }

  return payload
}
