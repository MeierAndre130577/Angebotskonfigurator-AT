import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'

const BASE = (import.meta.env.VITE_API_URL || '') + '/api'

function money(n) {
  return new Intl.NumberFormat('de-AT', { style: 'currency', currency: 'EUR' }).format(n || 0)
}

function formatDateTime(iso) {
  if (!iso) return '—'
  try {
    return new Date(iso).toLocaleString('de-AT', {
      day: '2-digit', month: '2-digit', year: 'numeric',
      hour: '2-digit', minute: '2-digit'
    })
  } catch { return '—' }
}

function getField(a, key) {
  const p = a.project
  if (!p) return ''
  if (typeof p === 'object') return p[key] || ''
  try { return JSON.parse(p)[key] || '' } catch { return '' }
}

export default function Angebote() {
  const [angebote, setAngebote]     = useState([])
  const [loading, setLoading]       = useState(true)
  const [search, setSearch]         = useState('')
  const [showArchiv, setShowArchiv] = useState(false)
  const [toast, setToast]           = useState('')
  const navigate = useNavigate()

  useEffect(() => {
    load()
    // Abgelaufene archivieren beim Laden
    fetch(`${BASE}/offers/archive-expired`, { method: 'POST' }).catch(() => {})
  }, [])

  async function load() {
    setLoading(true)
    try {
      const res  = await fetch(`${BASE}/offers`)
      const data = await res.json()
      setAngebote(Array.isArray(data)
        ? data.sort((a,b) => new Date(b.created_at) - new Date(a.created_at))
        : [])
    } catch(e) { console.warn(e) }
    finally { setLoading(false) }
  }

  function showToast(msg) { setToast(msg); setTimeout(() => setToast(''), 2500) }

  async function handleDelete(e, a) {
    e.stopPropagation()
    if (!confirm(`Angebot ${a.offer_no} wirklich löschen?\nDas ZIP wird ebenfalls gelöscht.`)) return
    try {
      // ZIP löschen
      if (a.zip_filename) {
        await fetch(`${BASE}/offers/${a.id}/zip`, { method: 'DELETE' }).catch(() => {})
      }
      await fetch(`${BASE}/offers/${a.id}`, { method: 'DELETE' })
      setAngebote(prev => prev.filter(x => x.id !== a.id))
      showToast('Angebot gelöscht')
    } catch { showToast('Fehler beim Löschen') }
  }

  async function handleDownload(e, a) {
    e.stopPropagation()
    if (!a.zip_url) return
    // Zähler erhöhen
    const res = await fetch(`${BASE}/offers/${a.id}/download`, { method: 'POST' })
    const data = await res.json()
    // Aktuellen Zähler updaten
    setAngebote(prev => prev.map(x => x.id === a.id ? { ...x, zip_downloads: data.zip_downloads } : x))
    window.open(a.zip_url, '_blank')
  }

  function copyLink(e, url) {
    e.stopPropagation()
    navigator.clipboard.writeText(url)
    showToast('Link kopiert ✓')
  }

  function openEmail(e, a) {
    e.stopPropagation()
    const p = a.project || {}
    const proj = typeof p === 'string' ? JSON.parse(p) : p
    const to      = proj.customerEmail || ''
    const subject = encodeURIComponent(`Angebot ${a.offer_no} – ${proj.project || ''} für ${proj.customer || ''}`)
    const body    = encodeURIComponent(
      `Sehr geehrte(r) ${proj.contact || proj.customer || ''},\n\n` +
      `anbei unser Angebot ${a.offer_no}.\n\n` +
      (a.zip_url ? `Alle Dokumente zum Download (30 Tage gültig):\n${a.zip_url}\n\n` : '') +
      `Mit freundlichen Grüßen`
    )
    window.open(`${(import.meta.env.VITE_API_URL || '') + a.pdf_url}`, '_blank')
    setTimeout(() => { window.location.href = `mailto:${to}?subject=${subject}&body=${body}` }, 500)
  }

  function calcSums(a) {
    const items = Array.isArray(a.offer_items) ? a.offer_items : []
    return {
      oneTime: items.filter(i => !i.recurring).reduce((s,i) => s+(Number(i.price)||0), 0),
      monthly: items.filter(i =>  i.recurring).reduce((s,i) => s+(Number(i.price)||0), 0),
    }
  }

  const filtered = angebote.filter(a => {
    const isArchived = a.status === 'archived'
    if (!showArchiv && isArchived) return false
    if (showArchiv && !isArchived) return false
    const q = search.toLowerCase()
    return (
      (a.offer_no              || '').toLowerCase().includes(q) ||
      getField(a,'customer').toLowerCase().includes(q) ||
      getField(a,'project').toLowerCase().includes(q)
    )
  })

  const activeCount  = angebote.filter(a => a.status !== 'archived').length
  const archivCount  = angebote.filter(a => a.status === 'archived').length

  return (
    <div>
      {toast && (
        <div style={{
          position: 'fixed', bottom: 24, right: 24, background: 'var(--dark)',
          color: 'white', padding: '12px 20px', borderRadius: 12,
          fontSize: 13, fontWeight: 600, zIndex: 9999
        }}>{toast}</div>
      )}

      <div className="page-header">
        <div>
          <h1>📋 Angebote</h1>
          <p className="subtitle">
            {activeCount} aktive · {archivCount} archivierte
          </p>
        </div>
        {/* Archiv Toggle */}
        <button
          onClick={() => setShowArchiv(v => !v)}
          className="btn"
          style={{
            background: showArchiv ? 'var(--dark)' : 'white',
            color:      showArchiv ? 'white'       : 'var(--muted)',
            fontWeight: 700,
          }}>
          📦 {showArchiv ? 'Archiv (aktiv)' : 'Archiv anzeigen'}
        </button>
      </div>

      {showArchiv && (
        <div style={{ background: 'var(--bg)', border: '1px solid var(--line)', borderRadius: 12,
          padding: '10px 16px', marginBottom: 16, fontSize: 13, color: 'var(--muted)' }}>
          📦 <b>Archiv</b> – ZIP abgelaufen, nur PDF verfügbar
        </div>
      )}

      <div style={{ marginBottom: 20 }}>
        <input
          placeholder="🔍 Nach Angebotsnummer, Kunde oder Projekt suchen …"
          value={search} onChange={e => setSearch(e.target.value)}
          style={{ width: '100%', border: '1px solid var(--line)', borderRadius: 10,
            padding: '10px 14px', fontSize: 13 }}
        />
      </div>

      {loading ? <p className="muted">Lädt …</p> : filtered.length === 0 ? (
        <div className="card">
          <p className="muted small">
            {search ? 'Keine Angebote gefunden.'
              : showArchiv ? 'Keine archivierten Angebote.'
              : 'Noch keine Angebote vorhanden.'}
          </p>
        </div>
      ) : (
        <div className="card" style={{ padding: 0, overflow: 'hidden' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
            <thead>
              <tr style={{ borderBottom: '1px solid var(--line)', background: 'var(--bg)' }}>
                {[
                  { label: 'Nr.',          align: 'left'  },
                  { label: 'Kunde',        align: 'left'  },
                  { label: 'Projekt',      align: 'left'  },
                  { label: 'Erstellt',     align: 'left'  },
                  { label: 'Einmalig',     align: 'right' },
                  { label: 'Monatlich',    align: 'right' },
                  { label: '↓ Downloads',  align: 'right' },
                  { label: '',             align: 'right' },
                ].map(h => (
                  <th key={h.label} style={{
                    padding: '11px 12px', textAlign: h.align,
                    fontWeight: 700, color: 'var(--muted)', fontSize: 11,
                    textTransform: 'uppercase', letterSpacing: '.04em'
                  }}>{h.label}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {filtered.map(a => {
                const sums      = calcSums(a)
                const archived  = a.status === 'archived'
                const customer  = getField(a, 'customer')
                const contact   = getField(a, 'contact')
                const project   = getField(a, 'project')
                const pdfUrl    = a.pdf_url
                  ? (import.meta.env.VITE_API_URL || '') + a.pdf_url
                  : null

                return (
                  <tr key={a.id}
                    style={{ borderBottom: '1px solid var(--line)',
                      background: archived ? 'var(--bg)' : 'white' }}
                    onMouseEnter={e => e.currentTarget.style.background = '#f0f0f0'}
                    onMouseLeave={e => e.currentTarget.style.background = archived ? 'var(--bg)' : 'white'}
                  >
                    <td style={{ padding: '10px 12px' }}>
                      <div style={{ fontFamily: 'var(--font-mono)', fontWeight: 700,
                        color: archived ? 'var(--muted)' : 'var(--red)', fontSize: 11 }}>
                        {a.offer_no}
                      </div>
                      {archived && <div style={{ fontSize: 10, color: 'var(--muted)' }}>📦 Archiv</div>}
                    </td>
                    <td style={{ padding: '10px 12px' }}>
                      <b>{customer || '—'}</b>
                      {contact && <div style={{ fontSize: 11, color: 'var(--muted)' }}>{contact}</div>}
                    </td>
                    <td style={{ padding: '10px 12px', color: 'var(--muted)' }}>{project || '—'}</td>
                    <td style={{ padding: '10px 12px', color: 'var(--muted)', fontSize: 11, whiteSpace: 'nowrap' }}>
                      {formatDateTime(a.created_at)}
                    </td>
                    <td style={{ padding: '10px 12px', textAlign: 'right', fontWeight: 700 }}>
                      {sums.oneTime > 0 ? money(sums.oneTime) : <span style={{ color: 'var(--muted)' }}>—</span>}
                    </td>
                    <td style={{ padding: '10px 12px', textAlign: 'right', fontWeight: 700, color: 'var(--red)' }}>
                      {sums.monthly > 0 ? money(sums.monthly)+'/Mo.' : <span style={{ color: 'var(--muted)' }}>—</span>}
                    </td>
                    <td style={{ padding: '10px 12px', textAlign: 'right', color: 'var(--muted)', fontSize: 12 }}>
                      {a.zip_downloads > 0
                        ? <b style={{ color: 'var(--dark)' }}>{a.zip_downloads}×</b>
                        : '—'}
                    </td>
                    <td style={{ padding: '10px 12px', textAlign: 'right' }}>
                      <div className="row" style={{ justifyContent: 'flex-end', gap: 4 }}>
                        {/* PDF öffnen */}
                        {pdfUrl && (
                          <a href={pdfUrl} target="_blank" rel="noopener noreferrer"
                            className="btn" style={{ padding: '5px 8px', fontSize: 11, textDecoration: 'none' }}
                            onClick={e => e.stopPropagation()}>
                            📄
                          </a>
                        )}
                        {/* Download-Link kopieren (nur aktive) */}
                        {!archived && a.zip_url && (
                          <button className="btn" style={{ padding: '5px 8px', fontSize: 11 }}
                            onClick={e => copyLink(e, a.zip_url)} title="Download-Link kopieren">
                            📋
                          </button>
                        )}
                        {/* ZIP herunterladen (nur aktive) */}
                        {!archived && a.zip_url && (
                          <button className="btn" style={{ padding: '5px 8px', fontSize: 11 }}
                            onClick={e => handleDownload(e, a)} title="ZIP herunterladen">
                            📦
                          </button>
                        )}
                        {/* E-Mail */}
                        {pdfUrl && (
                          <button className="btn" style={{ padding: '5px 8px', fontSize: 11 }}
                            onClick={e => openEmail(e, a)} title="E-Mail öffnen">
                            ✉️
                          </button>
                        )}
                        {/* Löschen */}
                        <button className="btn" style={{ padding: '5px 8px', fontSize: 11, color: 'var(--red)' }}
                          onClick={e => handleDelete(e, a)}>
                          🗑️
                        </button>
                      </div>
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
