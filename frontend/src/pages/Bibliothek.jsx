import { useState, useEffect } from 'react'
import { options as optionsApi } from '../lib/api'

function money(n) {
  return new Intl.NumberFormat('de-AT', { style: 'currency', currency: 'EUR' }).format(n || 0)
}

export default function Bibliothek() {
  const [items, setItems]   = useState([])
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState('')

  useEffect(() => {
    optionsApi.list()
      .then(setItems)
      .catch(console.warn)
      .finally(() => setLoading(false))
  }, [])

  const filtered = items.filter(o =>
    o.name.toLowerCase().includes(search.toLowerCase()) ||
    (o.cluster || '').toLowerCase().includes(search.toLowerCase())
  )

  const clusters = [...new Set(items.map(o => o.cluster || 'Sonstiges'))]

  return (
    <div>
      <div className="page-header">
        <div><h1>📚 Optionsbibliothek</h1><p className="subtitle">{items.length} Optionen in {clusters.length} Clustern</p></div>
        <div className="row">
          <input
            placeholder="Suchen …"
            value={search}
            onChange={e => setSearch(e.target.value)}
            style={{ border: '1px solid var(--line)', borderRadius: 10, padding: '9px 14px', fontSize: 13 }}
          />
        </div>
      </div>

      {loading ? (
        <p className="muted">Lädt …</p>
      ) : filtered.length === 0 ? (
        <div className="card"><p className="muted small">Keine Optionen gefunden. Bitte zuerst Optionen im Backend anlegen.</p></div>
      ) : (
        <div className="card" style={{ padding: 0, overflow: 'hidden' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
            <thead>
              <tr style={{ borderBottom: '1px solid var(--line)', background: 'var(--bg)' }}>
                <th style={{ padding: '12px 20px', textAlign: 'left', fontWeight: 700, color: 'var(--muted)' }}>Option</th>
                <th style={{ padding: '12px 20px', textAlign: 'left', fontWeight: 700, color: 'var(--muted)' }}>Cluster</th>
                <th style={{ padding: '12px 20px', textAlign: 'left', fontWeight: 700, color: 'var(--muted)' }}>Beschreibung</th>
                <th style={{ padding: '12px 20px', textAlign: 'right', fontWeight: 700, color: 'var(--muted)' }}>Preis</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map(o => (
                <tr key={o.id} style={{ borderBottom: '1px solid var(--line)' }}>
                  <td style={{ padding: '12px 20px' }}><b>{o.name}</b></td>
                  <td style={{ padding: '12px 20px' }}><span className="pill">{o.cluster || '—'}</span></td>
                  <td style={{ padding: '12px 20px', color: 'var(--muted)' }}>{o.short_text || '—'}</td>
                  <td style={{ padding: '12px 20px', textAlign: 'right', fontWeight: 700 }}>
                    {o.price === 0 ? <span style={{ color: 'var(--muted)' }}>inklusive</span>
                      : o.recurring ? <span style={{ color: 'var(--red)' }}>{money(o.price)} / Mo.</span>
                      : money(o.price)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
