import { useState, useEffect, useRef } from 'react'
import { customers as customersApi } from '../lib/api'

const BASE = (import.meta.env.VITE_API_URL || '') + '/api'

function AddressSearch({ value, onChange, placeholder }) {
  const [query, setQuery]           = useState(value || '')
  const [suggestions, setSuggestions] = useState([])
  const [loading, setLoading]       = useState(false)
  const timer = useRef(null)

  useEffect(() => { setQuery(value || '') }, [value])

  function onInput(val) {
    setQuery(val)
    onChange(val)
    if (timer.current) clearTimeout(timer.current)
    if (val.length < 3) { setSuggestions([]); return }
    timer.current = setTimeout(async () => {
      setLoading(true)
      try {
        const res  = await fetch(`https://photon.komoot.io/api/?q=${encodeURIComponent(val)}&lang=de&limit=6&countrycode=at`)
        const data = await res.json()
        setSuggestions(data.features || [])
      } catch {}
      setLoading(false)
    }, 350)
  }

  function select(feature) {
    const p = feature.properties
    const street = [p.street, p.housenumber].filter(Boolean).join(' ')
    const parts  = [street || p.name, p.postcode, p.city || p.town || p.village].filter(Boolean)
    const addr   = parts.join(', ')
    setQuery(addr)
    onChange(addr)
    setSuggestions([])
  }

  return (
    <div style={{ position: 'relative' }}>
      <input
        value={query}
        onChange={e => onInput(e.target.value)}
        placeholder={placeholder}
        style={{ width: '100%', boxSizing: 'border-box' }}
      />
      {loading && <p style={{ fontSize: 11, color: 'var(--muted)', margin: '2px 0 0' }}>Suche …</p>}
      {suggestions.length > 0 && (
        <div style={{ position: 'absolute', top: '100%', left: 0, right: 0, zIndex: 50,
          background: 'white', border: '1px solid var(--line)', borderRadius: 10,
          boxShadow: '0 4px 16px rgba(0,0,0,.12)', overflow: 'hidden', marginTop: 2 }}>
          {suggestions.map((f, i) => {
            const p = f.properties
            const line1 = [p.street, p.housenumber].filter(Boolean).join(' ') || p.name || ''
            const line2 = [p.postcode, p.city || p.town || p.village].filter(Boolean).join(' ')
            return (
              <div key={i} onClick={() => select(f)}
                style={{ padding: '9px 14px', cursor: 'pointer', fontSize: 13,
                  borderBottom: '1px solid var(--line)' }}
                onMouseEnter={e => e.currentTarget.style.background = '#f8f8f8'}
                onMouseLeave={e => e.currentTarget.style.background = 'white'}>
                <b>{line1}</b>
                {line2 && <span style={{ color: 'var(--muted)', marginLeft: 6 }}>{line2}</span>}
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}

export default function Projekt() {
  const [list, setList]         = useState([])
  const [offers, setOffers]     = useState([])
  const [editing, setEditing]   = useState(null)
  const [search, setSearch]     = useState('')
  const [busy, setBusy]         = useState(false)
  const [expanded, setExpanded] = useState(null)

  useEffect(() => { load() }, [])

  function load() {
    customersApi.list().then(setList).catch(console.warn)
    fetch(`${BASE}/offers`).then(r => r.json()).then(setOffers).catch(console.warn)
  }

  function offersFor(company) {
    return offers.filter(o => (o.project?.customer || '') === company)
  }

  function fmtDate(iso) {
    if (!iso) return ''
    return new Date(iso).toLocaleDateString('de-AT', { day: '2-digit', month: '2-digit', year: 'numeric' })
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
                ].map(([label, field]) => (
                  <div key={field} className="field">
                    <label>{label}</label>
                    <input
                      value={editing[field] || ''}
                      onChange={e => setEditing(p => ({ ...p, [field]: e.target.value }))}
                    />
                  </div>
                ))}
                <div className="field">
                  <label>Rechnungsadresse</label>
                  <AddressSearch
                    value={editing.billing || ''}
                    onChange={val => setEditing(p => ({ ...p, billing: val }))}
                    placeholder="Straße, PLZ, Ort suchen …"
                  />
                </div>
                <div className="field">
                  <label>Lieferadresse</label>
                  <AddressSearch
                    value={editing.delivery || ''}
                    onChange={val => setEditing(p => ({ ...p, delivery: val }))}
                    placeholder="Straße, PLZ, Ort suchen …"
                  />
                </div>
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
                  {/* Angebote */}
                  {(() => {
                    const co = offersFor(c.company)
                    if (co.length === 0) return (
                      <div style={{ fontSize: 11, color: 'var(--muted)', marginTop: 6, fontStyle: 'italic' }}>
                        Noch kein Angebot
                      </div>
                    )
                    return (
                      <div style={{ marginTop: 8, display: 'flex', flexDirection: 'column', gap: 3 }}>
                        {co.map(o => (
                          <div key={o.id} style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 11 }}>
                            <span style={{
                              background: o.status === 'active' ? '#f0fdf4' : '#f4f4f5',
                              color:      o.status === 'active' ? '#16a34a' : '#71717a',
                              border:     `1px solid ${o.status === 'active' ? '#86efac' : '#e4e4e7'}`,
                              borderRadius: 5, padding: '1px 6px', fontWeight: 700, flexShrink: 0,
                            }}>
                              {o.status === 'active' ? 'Offen' : 'Archiv'}
                            </span>
                            <span style={{ fontFamily: 'var(--font-mono)', color: 'var(--dark)', fontWeight: 600 }}>
                              {o.offer_no}
                            </span>
                            <span style={{ color: 'var(--muted)' }}>{fmtDate(o.created_at)}</span>
                            {o.project?.project && (
                              <span style={{ color: 'var(--muted)' }}>· {o.project.project}</span>
                            )}
                          </div>
                        ))}
                      </div>
                    )
                  })()}
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
