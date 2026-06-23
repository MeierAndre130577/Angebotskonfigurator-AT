import { useState, useEffect } from 'react'
import { customers as customersApi } from '../lib/api'

export default function Projekt() {
  const [list, setList]         = useState([])
  const [editing, setEditing]   = useState(null)   // Kunden-Objekt im Bearbeitungsmodus
  const [search, setSearch]     = useState('')
  const [busy, setBusy]         = useState(false)
  const [expanded, setExpanded] = useState(null)   // id des aufgeklappten Kunden

  useEffect(() => { load() }, [])

  function load() {
    customersApi.list().then(setList).catch(console.warn)
  }

  async function save() {
    if (!editing.company.trim()) return
    setBusy(true)
    try {
      await customersApi.upsert(editing)
      setEditing(null)
      load()
    } finally {
      setBusy(false)
    }
  }

  async function remove(id) {
    if (!confirm('Kunden wirklich löschen?')) return
    await customersApi.delete(id)
    load()
  }

  const filtered = list.filter(c =>
    [c.company, c.contact, c.email, c.city].some(v => (v || '').toLowerCase().includes(search.toLowerCase()))
  )

  return (
    <div>
      <div className="page-header">
        <div>
          <h1>👤 Kundendaten</h1>
          <p className="subtitle">Alle Kontakte aus der Schnellerfassung</p>
        </div>
      </div>

      <div style={{ display: 'flex', gap: 8, marginBottom: 16 }}>
        <input
          className="input"
          placeholder="Suchen nach Firma, Name, E-Mail, Ort …"
          value={search}
          onChange={e => setSearch(e.target.value)}
          style={{ flex: 1 }}
        />
        <span className="muted small" style={{ alignSelf: 'center', whiteSpace: 'nowrap' }}>
          {filtered.length} Kontakt{filtered.length !== 1 ? 'e' : ''}
        </span>
      </div>

      {filtered.length === 0 && (
        <div className="card">
          <p className="muted small">Noch keine Kundendaten vorhanden. Kunden werden automatisch über die Schnellerfassung angelegt.</p>
        </div>
      )}

      {filtered.map(c => (
        <div key={c.id} className="card" style={{ marginBottom: 10 }}>
          {editing?.id === c.id ? (
            /* ── Bearbeitungsformular ── */
            <div>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px 16px', marginBottom: 12 }}>
                {[
                  ['Firma *',           'company'],
                  ['Ansprechpartner',   'contact'],
                  ['E-Mail',            'email'],
                  ['Position',          'position'],
                  ['Telefon',           'phone'],
                  ['Mobil',             'mobile'],
                  ['Website',           'website'],
                  ['Straße',            'street'],
                  ['PLZ',               'zip'],
                  ['Ort',               'city'],
                  ['Rechnungsadresse',  'billing'],
                  ['Lieferadresse',     'delivery'],
                ].map(([label, field]) => (
                  <div key={field} className="field">
                    <label>{label}</label>
                    <input
                      value={editing[field] || ''}
                      onChange={e => setEditing(p => ({ ...p, [field]: e.target.value }))}
                    />
                  </div>
                ))}
              </div>
              <div style={{ display: 'flex', gap: 8 }}>
                <button className="btn btn-red" onClick={save} disabled={busy}>Speichern</button>
                <button className="btn" onClick={() => setEditing(null)}>Abbrechen</button>
              </div>
            </div>
          ) : (
            /* ── Kurzansicht ── */
            <div>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                <div style={{ flex: 1 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 10, flexWrap: 'wrap' }}>
                    {c.logo_url && (
                      <img src={c.logo_url} alt="" style={{ height: 24, maxWidth: 60, objectFit: 'contain' }} />
                    )}
                    <strong style={{ fontSize: 15 }}>{c.company}</strong>
                    {c.customer_number && (
                      <span style={{ fontSize: 10, fontWeight: 700, color: 'var(--muted)',
                        background: 'var(--bg)', border: '1px solid var(--line)',
                        borderRadius: 6, padding: '1px 6px', fontFamily: 'var(--font-mono)' }}>
                        {c.customer_number}
                      </span>
                    )}
                    {c.city && <span className="muted small">{c.zip ? `${c.zip} ` : ''}{c.city}</span>}
                  </div>
                  {c.contact  && <div style={{ fontSize: 13, marginTop: 2 }}>{c.contact}{c.position ? ` · ${c.position}` : ''}</div>}
                  {c.email    && <div style={{ fontSize: 12, color: 'var(--muted)' }}>{c.email}</div>}
                  {(c.phone || c.mobile) && (
                    <div style={{ fontSize: 12, color: 'var(--muted)', marginTop: 2 }}>
                      {c.phone}{c.phone && c.mobile ? ' · ' : ''}{c.mobile}
                    </div>
                  )}
                </div>

                <div style={{ display: 'flex', gap: 6, flexShrink: 0 }}>
                  {(c.street || c.website || c.card_image_url) && (
                    <button
                      className="btn btn-sm"
                      onClick={() => setExpanded(expanded === c.id ? null : c.id)}
                      style={{ fontSize: 11, padding: '3px 8px' }}
                    >
                      {expanded === c.id ? '▲' : '▼'}
                    </button>
                  )}
                  <button className="btn btn-sm" onClick={() => setEditing({ ...c })} style={{ fontSize: 11, padding: '3px 8px' }}>Bearbeiten</button>
                  <button className="btn btn-sm" onClick={() => remove(c.id)} style={{ fontSize: 11, padding: '3px 8px', color: 'var(--red)' }}>Löschen</button>
                </div>
              </div>

              {expanded === c.id && (
                <div style={{ marginTop: 12, paddingTop: 12, borderTop: '1px solid var(--border)' }}>
                  <div style={{ display: 'flex', gap: 24, flexWrap: 'wrap' }}>
                    <div style={{ flex: 1, minWidth: 180 }}>
                      {c.street && <div style={{ fontSize: 12 }}>{c.street}</div>}
                      {(c.zip || c.city) && <div style={{ fontSize: 12 }}>{[c.zip, c.city].filter(Boolean).join(' ')}</div>}
                      {c.website && (
                        <div style={{ fontSize: 12, marginTop: 4 }}>
                          <a href={c.website.startsWith('http') ? c.website : `https://${c.website}`} target="_blank" rel="noreferrer" style={{ color: 'var(--red)' }}>
                            {c.website}
                          </a>
                        </div>
                      )}
                      {c.billing  && <div style={{ fontSize: 12, marginTop: 4 }}><span className="muted">Rechnung: </span>{c.billing}</div>}
                      {c.delivery && <div style={{ fontSize: 12 }}><span className="muted">Lieferung: </span>{c.delivery}</div>}
                    </div>
                    {c.card_image_url && (
                      <div>
                        <div style={{ fontSize: 11, color: 'var(--muted)', marginBottom: 4 }}>Visitenkarte</div>
                        <img
                          src={c.card_image_url}
                          alt="Visitenkarte"
                          style={{ maxWidth: 200, maxHeight: 120, borderRadius: 6, border: '1px solid var(--border)', objectFit: 'contain' }}
                        />
                      </div>
                    )}
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      ))}
    </div>
  )
}
