/**
 * api.js – zentraler API-Client
 * Lokal: Vite Proxy leitet /api → localhost:8000
 * Produktion: VITE_API_URL zeigt auf das Backend
 */

const BASE = (import.meta.env.VITE_API_URL || '') + '/api'

async function request(method, path, body) {
  const res = await fetch(`${BASE}${path}`, {
    method,
    headers: { 'Content-Type': 'application/json' },
    body: body ? JSON.stringify(body) : undefined,
  })
  const data = await res.json().catch(() => ({}))
  if (!res.ok) throw new Error(data.detail || `HTTP ${res.status}`)
  return data
}

export async function uploadImage(file) {
  const formData = new FormData()
  formData.append('file', file, file.name || 'paste.png')
  const res = await fetch(`${BASE}/upload/image`, {
    method: 'POST',
    body: formData,
  })
  const data = await res.json().catch(() => ({}))
  if (!res.ok) throw new Error(data.error || 'Upload fehlgeschlagen')
  return data.url
}

// ── Kunden ────────────────────────────────────────────────────────────────────
export const customers = {
  list:   ()     => request('GET',    '/customers'),
  upsert: (data) => request('POST',   '/customers', data),
  delete: (id)   => request('DELETE', `/customers/${id}`),
}

// ── Optionen ──────────────────────────────────────────────────────────────────
export const options = {
  list:   ()     => request('GET',    '/options'),
  upsert: (data) => request('POST',   '/options', data),
  delete: (id)   => request('DELETE', `/options/${id}`),
}

// ── Anlagen ───────────────────────────────────────────────────────────────────
export const attachments = {
  list:   ()     => request('GET',    '/attachments'),
  upsert: (data) => request('POST',   '/attachments', data),
  delete: (id)   => request('DELETE', `/attachments/${id}`),
}

// ── Angebote ──────────────────────────────────────────────────────────────────
export const offers = {
  generateNumber: ()        => request('POST', '/offers/number', {}),
  upsert:         (data)    => request('POST', '/offers', data),
  getByNumber:    (offerNo) => request('GET',  `/offers/${encodeURIComponent(offerNo)}`),
}

// ── PDF ───────────────────────────────────────────────────────────────────────
export const pdf = {
  generate: (data) => request('POST', '/pdf/design', data),
}

// ── Health ────────────────────────────────────────────────────────────────────
export const health = () => request('GET', '/health')
