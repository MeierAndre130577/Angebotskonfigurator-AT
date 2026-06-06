import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'

const BASE = (import.meta.env.VITE_API_URL || '') + '/api'

function money(n) {
  return new Intl.NumberFormat('de-AT', { style: 'currency', currency: 'EUR' }).format(n || 0)
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
      // Neueste zuerst
      setAngebote(data.sort((a, b) => new Date(b.created_at) - new Date(a.created_at)))
    } catch(e) {
      console.warn('Fehler beim Laden:', e)
    } finally {
      setLoading(false)
    }
  }

  function showToast(msg) {
    setToast(msg)
    setTimeout(() => setToast(''), 2500)
  }

  async function handleDelete(id, offerNo) {
    if (!confirm(`Angebot ${offerNo} wirklich löschen?`)) return
    try {
      await fetch(`${BASE}/offers/${id}`, { method: 'DELETE' })
      setAngebote(prev => prev.filter(a => a.id !== id))
      showToast('Angebot gelöscht')
    } catch(e) {
      showToast('Fehler beim Löschen')
    }
  }

  function openPdf(offerNo) {
    navigate(`/vorschau?no=${encodeURIComponent(offerNo)}`)
  }

  const filtered = angebote.filter(a => {
    const q = search.toLowerCase()
    const p = a.project || {}
    return (
      (a.offer_no || '').toLowerCase().includes(q) ||
      (p.customer || '').toLowerCase().includes(q) ||
      (p.project  || '').toLowerCase().includes(q)
    )
  })

  // Summen berechnen
  function calcSums(a) {
    const items = a.offer_items || []
    return {
      oneTime: items.filter(i => !i.recurring).reduce((s,i) => s+(i.price||0), 0),
      monthly: items.filter(i =>  i.recurring).reduce((s,i) => s+(i.price||0), 0),
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

      {/* Suche */}
      <div style={{ marginBottom: 20 }}>
        <input
          placeholder="🔍 Nach Angebotsnummer, Kunde oder Projekt suchen …"
          value={search}
          onChange={e => setSearch(e.target.value)}
          style={{ width: '100%', border: '1px solid var(--line)', borderRadius: 10,
            padding: '10px 14px', fontSize: 13 }}
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
                {['Angebotsnummer', 'Kunde', 'Projekt', 'Datum', 'Einmalig', 'Monatlich', ''].map(h => (
                  <th key={h} style={{
                    padding: '12px 16px', textAlign: h === 'Einmalig' || h === 'Monatlich' || h === '' ? 'right' : 'left',
                    fontWeight: 700, color: 'var(--muted)', fontSize: 12
                  }}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {filtered.map(a => {
                const p    = a.project || {}
                const sums = calcSums(a)
                return (
                  <tr key={a.id}
                    style={{ borderBottom: '1px solid var(--line)', cursor: 'pointer' }}
                    onMouseEnter={e => e.currentTarget.style.background = 'var(--bg)'}
                    onMouseLeave={e => e.currentTarget.style.background = 'white'}
                    onClick={() => openPdf(a.offer_no)}
                  >
                    <td style={{ padding: '12px 16px' }}>
                      <span style={{ fontFamily: 'var(--font-mono)', fontWeight: 700, color: 'var(--red)', fontSize: 12 }}>
                        {a.offer_no}
                      </span>
                    </td>
                    <td style={{ padding: '12px 16px' }}>
                      <b>{p.customer || '—'}</b>
                      {p.contact && <div style={{ fontSize: 11, color: 'var(--muted)' }}>{p.contact}</div>}
                    </td>
                    <td style={{ padding: '12px 16px', color: 'var(--muted)' }}>{p.project || '—'}</td>
                    <td style={{ padding: '12px 16px', color: 'var(--muted)', whiteSpace: 'nowrap' }}>{p.date || '—'}</td>
                    <td style={{ padding: '12px 16px', textAlign: 'right', fontWeight: 700 }}>
                      {sums.oneTime > 0 ? money(sums.oneTime) : <span style={{ color: 'var(--muted)' }}>—</span>}
                    </td>
                    <td style={{ padding: '12px 16px', textAlign: 'right', fontWeight: 700, color: 'var(--red)' }}>
                      {sums.monthly > 0 ? money(sums.monthly)+'/Mo.' : <span style={{ color: 'var(--muted)' }}>—</span>}
                    </td>
                    <td style={{ padding: '12px 16px', textAlign: 'right' }} onClick={e => e.stopPropagation()}>
                      <div className="row" style={{ justifyContent: 'flex-end' }}>
                        <button className="btn" style={{ padding: '6px 12px', fontSize: 12 }}
                          onClick={() => openPdf(a.offer_no)}>
                          👁️ PDF
                        </button>
                        <button className="btn" style={{ padding: '6px 12px', fontSize: 12, color: 'var(--red)' }}
                          onClick={() => handleDelete(a.id, a.offer_no)}>
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
