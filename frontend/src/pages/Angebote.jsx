import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'

const BASE = (import.meta.env.VITE_API_URL || '') + '/api'

function money(n) {
  return new Intl.NumberFormat('de-AT', { style: 'currency', currency: 'EUR' }).format(n || 0)
}

function formatDate(iso) {
  if (!iso) return '—'
  try {
    return new Date(iso).toLocaleDateString('de-AT', { day: '2-digit', month: '2-digit', year: 'numeric' })
  } catch { return '—' }
}

export default function Angebote() {
  const [angebote, setAngebote] = useState([])
  const [loading, setLoading]   = useState(true)
  const [search, setSearch]     = useState('')
  const [toast, setToast]       = useState('')
  const navigate = useNavigate()

  useEffect(() => { load() }, [])

  async function load() {
    setLoading(true)
    try {
      const res  = await fetch(`${BASE}/offers`)
      const data = await res.json()
      setAngebote(Array.isArray(data) ? data.sort((a,b) => new Date(b.created_at) - new Date(a.created_at)) : [])
    } catch(e) {
      console.warn('Fehler:', e)
    } finally {
      setLoading(false)
    }
  }

  function showToast(msg) {
    setToast(msg)
    setTimeout(() => setToast(''), 2500)
  }

  async function handleDelete(e, id, offerNo) {
    e.stopPropagation()
    if (!confirm(`Angebot ${offerNo} wirklich löschen?`)) return
    try {
      await fetch(`${BASE}/offers/${id}`, { method: 'DELETE' })
      setAngebote(prev => prev.filter(a => a.id !== id))
      showToast('Angebot gelöscht')
    } catch { showToast('Fehler beim Löschen') }
  }

  const filtered = angebote.filter(a => {
    const q = search.toLowerCase()
    // Kunde steht in a.project (JSONB/Objekt)
    const p = a.project || {}
    return (
      (a.offer_no       || '').toLowerCase().includes(q) ||
      (p.customer       || '').toLowerCase().includes(q) ||
      (p.project        || '').toLowerCase().includes(q) ||
      (p.contact        || '').toLowerCase().includes(q)
    )
  })

  function calcSums(a) {
    const items = Array.isArray(a.offer_items) ? a.offer_items : []
    return {
      oneTime: items.filter(i => !i.recurring).reduce((s,i) => s+(Number(i.price)||0), 0),
      monthly: items.filter(i =>  i.recurring).reduce((s,i) => s+(Number(i.price)||0), 0),
    }
  }

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
          <p className="subtitle">{angebote.length} Angebote gesamt</p>
        </div>
      </div>

      <div style={{ marginBottom: 20 }}>
        <input
          placeholder="🔍 Nach Angebotsnummer, Kunde, Projekt oder Ansprechpartner suchen …"
          value={search}
          onChange={e => setSearch(e.target.value)}
          style={{ width: '100%', border: '1px solid var(--line)', borderRadius: 10, padding: '10px 14px', fontSize: 13 }}
        />
      </div>

      {loading ? (
        <p className="muted">Lädt …</p>
      ) : filtered.length === 0 ? (
        <div className="card">
          <p className="muted small">
            {search ? 'Keine Angebote gefunden.' : 'Noch keine Angebote vorhanden. Erstelle dein erstes Angebot über den Messe-Modus.'}
          </p>
        </div>
      ) : (
        <div className="card" style={{ padding: 0, overflow: 'hidden' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
            <thead>
              <tr style={{ borderBottom: '1px solid var(--line)', background: 'var(--bg)' }}>
                {[
                  { label: 'Angebotsnummer', align: 'left' },
                  { label: 'Kunde',          align: 'left' },
                  { label: 'Projekt',        align: 'left' },
                  { label: 'Erstellt',       align: 'left' },
                  { label: 'Angebotsdatum',  align: 'left' },
                  { label: 'Einmalig',       align: 'right' },
                  { label: 'Monatlich',      align: 'right' },
                  { label: '',               align: 'right' },
                ].map(h => (
                  <th key={h.label} style={{
                    padding: '11px 14px', textAlign: h.align,
                    fontWeight: 700, color: 'var(--muted)', fontSize: 11,
                    textTransform: 'uppercase', letterSpacing: '.04em'
                  }}>{h.label}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {filtered.map(a => {
                const p    = a.project || {}
                const sums = calcSums(a)
                return (
                  <tr key={a.id}
                    onClick={() => navigate(`/vorschau?no=${encodeURIComponent(a.offer_no)}`)}
                    style={{ borderBottom: '1px solid var(--line)', cursor: 'pointer' }}
                    onMouseEnter={e => e.currentTarget.style.background = 'var(--bg)'}
                    onMouseLeave={e => e.currentTarget.style.background = 'white'}
                  >
                    {/* Angebotsnummer */}
                    <td style={{ padding: '12px 14px' }}>
                      <span style={{ fontFamily: 'var(--font-mono)', fontWeight: 700, color: 'var(--red)', fontSize: 12 }}>
                        {a.offer_no || '—'}
                      </span>
                    </td>
                    {/* Kunde */}
                    <td style={{ padding: '12px 14px' }}>
                      <b>{p.customer || '—'}</b>
                      {p.contact && <div style={{ fontSize: 11, color: 'var(--muted)', marginTop: 1 }}>{p.contact}</div>}
                    </td>
                    {/* Projekt */}
                    <td style={{ padding: '12px 14px', color: 'var(--muted)' }}>
                      {p.project || '—'}
                    </td>
                    {/* Erstellt (DB Timestamp) */}
                    <td style={{ padding: '12px 14px', color: 'var(--muted)', whiteSpace: 'nowrap', fontSize: 12 }}>
                      {formatDate(a.created_at)}
                    </td>
                    {/* Angebotsdatum (aus Projektdaten) */}
                    <td style={{ padding: '12px 14px', color: 'var(--muted)', whiteSpace: 'nowrap', fontSize: 12 }}>
                      {p.date || '—'}
                    </td>
                    {/* Einmalig */}
                    <td style={{ padding: '12px 14px', textAlign: 'right', fontWeight: 700 }}>
                      {sums.oneTime > 0
                        ? money(sums.oneTime)
                        : <span style={{ color: 'var(--muted)' }}>—</span>}
                    </td>
                    {/* Monatlich */}
                    <td style={{ padding: '12px 14px', textAlign: 'right', fontWeight: 700, color: 'var(--red)' }}>
                      {sums.monthly > 0
                        ? money(sums.monthly)+'/Mo.'
                        : <span style={{ color: 'var(--muted)' }}>—</span>}
                    </td>
                    {/* Aktionen */}
                    <td style={{ padding: '12px 14px', textAlign: 'right' }} onClick={e => e.stopPropagation()}>
                      <div className="row" style={{ justifyContent: 'flex-end' }}>
                        <button className="btn" style={{ padding: '5px 10px', fontSize: 11 }}
                          onClick={() => navigate(`/vorschau?no=${encodeURIComponent(a.offer_no)}`)}>
                          👁️ PDF
                        </button>
                        <button className="btn" style={{ padding: '5px 10px', fontSize: 11, color: 'var(--red)' }}
                          onClick={e => handleDelete(e, a.id, a.offer_no)}>
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
