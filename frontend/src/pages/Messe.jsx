import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'

const BASE = (import.meta.env.VITE_API_URL || '') + '/api'
import { customers as customersApi, options as optionsApi, offers as offersApi } from '../lib/api'

const STEPS = ['Kontakt', 'Optionen', 'Fertigstellen']

function money(n) {
  return new Intl.NumberFormat('de-AT', { style: 'currency', currency: 'EUR' }).format(n || 0)
}

export default function Messe() {
  const [step, setStep]               = useState(0)
  const [contact, setContact]         = useState({ company: '', contactName: '', email: '' })
  const [suggestions, setSuggestions] = useState([])
  const [allOptions, setAllOptions]   = useState([])
  const [templates, setTemplates]     = useState([])
  const [activeTemplate, setActiveTemplate] = useState(null)  // null = alle aktiven
  const [selectedIds, setSelectedIds] = useState(new Set())
  const [projectName, setProjectName]   = useState('')
  const [optionalIds, setOptionalIds]   = useState(new Set())  // Optionen die als optional markiert sind
  const [offerNo, setOfferNo]         = useState('')
  const [busy, setBusy]               = useState(false)
  const [done, setDone]               = useState(false)
  const [result, setResult]           = useState(null)  // Angebotsergebnis
  const [previewing, setPreviewing]   = useState(false)
  const navigate                      = useNavigate()
  const [error, setError]             = useState('')
  const [allCustomers, setAllCustomers] = useState([])
  const [customPrices, setCustomPrices] = useState({})  // option_id → angepasster Preis
  const [leasingEnabled, setLeasingEnabled] = useState(false)
  const [leasingKaufpreis, setLeasingKaufpreis] = useState(0)
  const [leasingSettings, setLeasingSettings] = useState(null)

  useEffect(() => {
    optionsApi.list().then(setAllOptions).catch(console.warn)
    fetch((import.meta.env.VITE_API_URL || '') + '/api/templates')
      .then(r => r.json()).then(setTemplates).catch(console.warn)
    customersApi.list().then(setAllCustomers).catch(console.warn)
    fetch((import.meta.env.VITE_API_URL || '') + '/api/settings')
      .then(r => r.json()).then(setLeasingSettings).catch(console.warn)
  }, [])

  // Live-Suche in Kunden
  useEffect(() => {
    if (contact.company.length < 2) { setSuggestions([]); return }
    const q = contact.company.toLowerCase()
    setSuggestions(allCustomers.filter(c => c.company.toLowerCase().includes(q)).slice(0, 4))
  }, [contact.company, allCustomers])

  function fillContact(c) {
    setContact({ company: c.company, contactName: c.contact || '', email: c.email || '' })
    setSuggestions([])
  }

  function toggleOption(id) {
    setSelectedIds(prev => {
      const next = new Set(prev)
      next.has(id) ? next.delete(id) : next.add(id)
      return next
    })
  }

  function validateStep0() {
    if (!contact.company.trim()) { setError('Firma ist erforderlich'); return false }
    if (!contact.email.trim() || !contact.email.includes('@')) { setError('Bitte gültige E-Mail angeben'); return false }
    setError(''); return true
  }

  function toggleOptional(id) {
    setOptionalIds(prev => {
      const next = new Set(prev)
      next.has(id) ? next.delete(id) : next.add(id)
      return next
    })
  }

  function validateStep1() {
    if (selectedIds.size === 0) { setError('Bitte mindestens eine Option wählen'); return false }
    setError(''); return true
  }

  async function previewPdf() {
    setPreviewing(true)
    try {
      const proj    = { customer: contact.company, contact: contact.contactName,
                        customerEmail: contact.email, project: projectName || 'Vorschau', date: '' }
      const items   = allOptions.filter(o => selectedIds.has(o.id))
      const res     = await fetch(`${BASE}/pdf/preview`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ project: proj, offer: items, provider: {}, attachments: [] })
      })
      const data = await res.json()
      if (data.download_url) {
        window.open((import.meta.env.VITE_API_URL || '') + data.download_url, '_blank')
      }
    } catch(e) {
      console.warn('Vorschau fehlgeschlagen:', e)
    } finally {
      setPreviewing(false)
    }
  }

  async function finalize() {
    if (busy) return
    setBusy(true); setError('')
    try {
      const rawItems = allOptions.filter(o => selectedIds.has(o.id))
      const proj  = {
        customer:      contact.company,
        contact:       contact.contactName,
        customerEmail: contact.email,
        project:       projectName || 'Messegespräch',
        date:          new Date().toLocaleDateString('de-AT'),
        valid:         new Date(Date.now() + 28*864e5).toLocaleDateString('de-AT'),
      }
      // offer_items mit optional-Flag und korrekten Preisen
      const offer_items = rawItems.map(o => {
        const base = customPrices[o.id] !== undefined ? Number(customPrices[o.id]) : (o.price || 0)
        return {
          option_id:      o.id,
          name:           o.name,
          cluster:        o.cluster      || '',
          short_text:     o.short_text   || '',
          long_text:      o.long_text    || '',
          original_price: base,
          price:          optionalIds.has(o.id) ? 0 : base,
          optional:       optionalIds.has(o.id),
          recurring:      o.recurring    || false,
          image_path:     o.image_path   || '',
          display_type:   o.display_type || '',
          documents:      o.documents    || [],
          qty:            1,
        }
      })
      const kp = leasingKaufpreis || oneTime
      const leasingPayload = leasingEnabled ? {
        enabled: true, kaufpreis: kp, durations: LEASING_DURATIONS,
      } : { enabled: false }

      const res  = await fetch(`${BASE}/offers/generate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ project: proj, offer_items, provider: {}, attachments: [], leasing: leasingPayload })
      })
      const data = await res.json()
      if (!res.ok) throw new Error(data.detail || `Server-Fehler ${res.status}`)
      if (!data.ok) throw new Error('Generierung fehlgeschlagen')
      setResult(data)
      setDone(true)
    } catch (e) {
      setError('Fehler: ' + e.message)
    } finally {
      setBusy(false)
    }
  }

  function reset() {
    setStep(0); setContact({ company: '', contactName: '', email: '' })
    setSelectedIds(new Set()); setProjectName(''); setOfferNo('')
    setDone(false); setError(''); setCustomPrices({})
  }

  // ── Cluster-Gruppen ────────────────────────────────────────────────────────
  // Nur aktive Optionen, gefiltert nach Vorlage
  const visibleOptions = allOptions.filter(o => {
    if (o.active === false) return false
    if (activeTemplate) {
      const ids = (activeTemplate.option_ids || []).map(String)
      return ids.includes(String(o.id))
    }
    return true
  })

  const byCluster = visibleOptions.reduce((acc, o) => {
    const cl = o.cluster || 'Sonstiges'
    acc[cl] = acc[cl] || []
    acc[cl].push(o)
    return acc
  }, {})

  const selected = visibleOptions.filter(o => selectedIds.has(o.id))
  const effectivePrice = o => customPrices[o.id] !== undefined ? Number(customPrices[o.id]) : (o.price || 0)
  const oneTime  = selected.filter(o => !o.recurring && !optionalIds.has(o.id)).reduce((s, o) => s + effectivePrice(o), 0)
  const monthly  = selected.filter(o =>  o.recurring && !optionalIds.has(o.id)).reduce((s, o) => s + effectivePrice(o), 0)

  // Leasing-Berechnung
  const LEASING_DURATIONS = [36, 48, 60]
  function calcLeasing(kaufpreis) {
    const s     = leasingSettings || {}
    const facs  = s.leasing_factors || {}
    const fee   = parseFloat(s.leasing_processing_fee || 100)
    const vat   = parseFloat(s.leasing_vat || 20) / 100
    const brks  = [10000, 20000, 30000, 50000, 999999]
    const brk   = (brks.find(b => kaufpreis <= b) || 999999).toString()
    return LEASING_DURATIONS.map(dur => {
      const factor  = parseFloat((facs[dur] || {})[brk] || 0)
      const monthly = Math.round(kaufpreis * factor / 100 * 100) / 100
      const legal   = Math.round((36 * monthly * (1 + vat) + fee * (1 + vat)) * 0.01 * 100) / 100
      return { dur, monthly, fee, legal }
    })
  }
  const leasingRows = calcLeasing(leasingKaufpreis || oneTime)

  // Nach Generieren direkt zur PDF-Vorschau
  if (done && result?.offer_no) {
    navigate(`/vorschau?no=${encodeURIComponent(result.offer_no)}`)
    return null
  }

  return (
    <div style={{ maxWidth: 720, margin: '0 auto' }}>
      {/* Header */}
      <div className="page-header">
        <div>
          <h1>🎯 Messe-Schnellerfassung</h1>
          <p className="subtitle">Kontakt → Optionen → Angebot in unter 60 Sekunden</p>
        </div>
      </div>

      {/* Step Bar */}
      <div style={{ display: 'flex', gap: 0, marginBottom: 32, borderRadius: 16, overflow: 'hidden', border: '1px solid var(--line)' }}>
        {STEPS.map((s, i) => (
          <div key={s} style={{
            flex: 1, padding: '13px 0', textAlign: 'center', fontSize: 13, fontWeight: 700,
            background: step === i ? 'var(--red)' : i < step ? 'var(--red-light)' : 'white',
            color: step === i ? 'white' : i < step ? 'var(--red)' : 'var(--muted)',
            borderRight: i < 2 ? '1px solid var(--line)' : 'none',
          }}>
            {i < step ? '✓ ' : ''}{s}
          </div>
        ))}
      </div>

      {/* ── Step 0: Kontakt ─────────────────────────────────────────────────── */}
      {step === 0 && (
        <div className="card">
          <div className="card-title">Kontaktdaten</div>

          <div className="field" style={{ position: 'relative' }}>
            <label>Firma *</label>
            <input
              value={contact.company}
              onChange={e => setContact(p => ({ ...p, company: e.target.value }))}
              placeholder="Firmenname …"
              style={{ fontSize: 18, padding: '14px 16px' }}
              autoFocus
            />
            {suggestions.length > 0 && (
              <div style={{ position: 'absolute', top: '100%', left: 0, right: 0, background: 'white', border: '1px solid var(--line)', borderRadius: 14, boxShadow: '0 8px 24px rgba(0,0,0,.1)', zIndex: 10, marginTop: 4 }}>
                {suggestions.map(c => (
                  <div key={c.id} onClick={() => fillContact(c)}
                    style={{ padding: '12px 16px', cursor: 'pointer', borderBottom: '1px solid var(--line)', fontSize: 14 }}
                    onMouseEnter={e => e.currentTarget.style.background = 'var(--red-light)'}
                    onMouseLeave={e => e.currentTarget.style.background = 'white'}
                  >
                    <b>{c.company}</b>
                    <div className="small muted">{c.contact} · {c.email}</div>
                  </div>
                ))}
              </div>
            )}
          </div>

          <div className="field">
            <label>Ansprechpartner</label>
            <input value={contact.contactName} onChange={e => setContact(p => ({ ...p, contactName: e.target.value }))} placeholder="Name" />
          </div>

          <div className="field">
            <label>E-Mail *</label>
            <input type="email" value={contact.email} onChange={e => setContact(p => ({ ...p, email: e.target.value }))} placeholder="email@firma.com" />
          </div>

          {error && <p style={{ color: 'var(--red)', fontSize: 13, marginBottom: 12 }}>⚠ {error}</p>}

          <button className="btn btn-red btn-lg" onClick={() => { if (validateStep0()) setStep(1) }}>
            Weiter zu den Optionen →
          </button>
        </div>
      )}

      {/* ── Step 1: Optionen ────────────────────────────────────────────────── */}
      {step === 1 && (
        <div>
          <div className="between" style={{ marginBottom: 12 }}>
            <p className="muted small">{selectedIds.size} Option(en) gewählt für <b>{contact.company}</b></p>
            <button className="btn" onClick={() => setStep(0)}>← zurück</button>
          </div>

          {/* Vorlagen-Auswahl */}
          {templates.length > 0 && (
            <div className="row" style={{ marginBottom: 16, gap: 8, flexWrap: 'wrap' }}>
              <button
                className="btn"
                style={{ fontSize: 12, background: !activeTemplate ? 'var(--dark)' : 'white',
                  color: !activeTemplate ? 'white' : 'var(--muted)' }}
                onClick={() => setActiveTemplate(null)}>
                Alle
              </button>
              {templates.map(tpl => (
                <button key={tpl.id}
                  className="btn"
                  style={{ fontSize: 12,
                    background: activeTemplate?.id === tpl.id ? 'var(--red)' : 'white',
                    color: activeTemplate?.id === tpl.id ? 'white' : 'var(--dark)',
                    border: `1px solid ${activeTemplate?.id === tpl.id ? 'var(--red)' : 'var(--line)'}` }}
                  onClick={() => setActiveTemplate(activeTemplate?.id === tpl.id ? null : tpl)}>
                  📋 {tpl.name}
                </button>
              ))}
            </div>
          )}

          {Object.entries(byCluster).map(([cluster, items]) => (
            <div key={cluster} style={{ marginBottom: 24 }}>
              <div className="nav-group-label" style={{ marginBottom: 10 }}>{cluster}</div>
              <div className="grid3" style={{ gap: 10 }}>
                {items.map(o => {
                  const sel = selectedIds.has(o.id)
                  return (
                    <div key={o.id} onClick={() => toggleOption(o.id)} style={{
                      border: `2px solid ${sel ? 'var(--red)' : 'var(--line)'}`,
                      borderRadius: 16, padding: 14, cursor: 'pointer',
                      background: sel ? 'var(--red-light)' : 'white',
                      transition: '.15s', userSelect: 'none',
                    }}>
                      <div className="between" style={{ alignItems: 'flex-start', gap: 8 }}>
                        <b style={{ fontSize: 13, lineHeight: 1.3 }}>{o.name}</b>
                        <div style={{
                          width: 20, height: 20, borderRadius: '50%', flex: 'none',
                          background: sel ? 'var(--red)' : 'var(--line)',
                          display: 'flex', alignItems: 'center', justifyContent: 'center',
                          color: 'white', fontSize: 12, fontWeight: 900,
                        }}>{sel ? '✓' : ''}</div>
                      </div>
                      {o.short_text && <p style={{ fontSize: 11, color: 'var(--muted)', marginTop: 6, lineHeight: 1.4 }}>{o.short_text}</p>}
                      <div style={{ marginTop: 8, display: 'flex', alignItems: 'center', gap: 6 }}>
                        <p style={{ margin: 0, fontWeight: 800, fontSize: 12, color: sel ? 'var(--red)' : 'var(--muted)' }}>
                          {o.price === 0 ? 'inklusive' : o.recurring ? money(o.price) + ' / Mo.' : money(o.price)}
                        </p>
                        {o.price_editable && (
                          <span title="Preis anpassbar in Schritt 3"
                            style={{ fontSize: 10, background: '#fff3e0', color: '#e65100',
                              borderRadius: 6, padding: '1px 5px', fontWeight: 700 }}>
                            ✏️ anpassbar
                          </span>
                        )}
                      </div>
                    </div>
                  )
                })}
              </div>
            </div>
          ))}

          {error && <p style={{ color: 'var(--red)', fontSize: 13, marginBottom: 12 }}>⚠ {error}</p>}
          <button className="btn btn-red btn-lg" onClick={() => { if (validateStep1()) setStep(2) }}>
            Weiter zum Abschluss →
          </button>
        </div>
      )}

      {/* ── Step 2: Fertigstellen ────────────────────────────────────────────── */}
      {step === 2 && (
        <div>
          <div className="between" style={{ marginBottom: 20 }}>
            <p className="muted small">{selected.length} Optionen für <b>{contact.company}</b></p>
            <button className="btn" onClick={() => setStep(1)}>← zurück</button>
          </div>

          <div className="card" style={{ marginBottom: 16 }}>
            <div className="card-title">Zusammenfassung</div>
            <div className="grid2" style={{ marginBottom: 16 }}>
              <div className="stat-card"><div className="value">{money(oneTime)}</div><div className="label">Einmalig</div></div>
              <div className="stat-card"><div className="value">{money(monthly)}</div><div className="label">Monatlich</div></div>
            </div>
            {selected.map(o => {
              const isOptional  = optionalIds.has(o.id)
              const hasCustom   = customPrices[o.id] !== undefined
              const displayPrice = hasCustom ? Number(customPrices[o.id]) : (o.price || 0)
              return (
                <div key={o.id} style={{ padding: '10px 0', borderBottom: '1px solid var(--line)' }}>
                  <div className="between small">
                    <span>
                      <b>{o.name}</b>
                      <span className="muted" style={{ marginLeft: 6 }}>{o.cluster}</span>
                      {isOptional && (
                        <span style={{ marginLeft: 8, fontSize: 10, background: 'var(--bg)',
                          border: '1px solid var(--line)', borderRadius: 6, padding: '1px 6px',
                          color: 'var(--muted)', fontWeight: 700 }}>
                          OPTIONAL
                        </span>
                      )}
                    </span>
                    <div className="row" style={{ gap: 8, alignItems: 'center' }}>
                      <b style={{ color: isOptional ? 'var(--muted)' : 'var(--red)',
                        textDecoration: isOptional ? 'line-through' : 'none' }}>
                        {displayPrice === 0 ? 'inkl.' : o.recurring ? money(displayPrice)+'/Mo.' : money(displayPrice)}
                      </b>
                      {/* Optional-Schalter */}
                      <button
                        onClick={() => toggleOptional(o.id)}
                        title={isOptional ? 'Als Pflicht markieren' : 'Als optional markieren'}
                        style={{
                          border: `1px solid ${isOptional ? 'var(--red)' : 'var(--line)'}`,
                          background: isOptional ? 'var(--red-light)' : 'white',
                          borderRadius: 6, padding: '2px 8px', fontSize: 10,
                          cursor: 'pointer', color: isOptional ? 'var(--red)' : 'var(--muted)',
                          fontWeight: 700,
                        }}>
                        {isOptional ? '✓ opt.' : 'opt.?'}
                      </button>
                    </div>
                  </div>

                  {/* Preis-Eingabefeld wenn price_editable */}
                  {o.price_editable && !isOptional && (
                    <div style={{ marginTop: 8, display: 'flex', alignItems: 'center', gap: 10 }}>
                      <label style={{ fontSize: 11, color: 'var(--muted)', whiteSpace: 'nowrap', fontWeight: 700 }}>
                        ✏️ Preis anpassen:
                      </label>
                      <div style={{ position: 'relative', display: 'flex', alignItems: 'center' }}>
                        <input
                          type="number"
                          min="0"
                          step="10"
                          value={hasCustom ? customPrices[o.id] : (o.price || 0)}
                          onChange={e => setCustomPrices(p => ({ ...p, [o.id]: e.target.value }))}
                          style={{
                            border: '1px solid var(--red)', borderRadius: 8,
                            padding: '5px 36px 5px 10px', fontSize: 13, width: 120,
                            fontWeight: 700, color: 'var(--red)',
                          }}
                        />
                        <span style={{ position: 'absolute', right: 10, fontSize: 12,
                          color: 'var(--muted)', pointerEvents: 'none' }}>€</span>
                      </div>
                      {hasCustom && customPrices[o.id] != o.price && (
                        <span style={{ fontSize: 11, color: 'var(--muted)' }}>
                          (Standardpreis: {money(o.price)})
                        </span>
                      )}
                      {o.price_hint && (
                        <span style={{ fontSize: 11, color: '#e65100', fontStyle: 'italic' }}>
                          {o.price_hint}
                        </span>
                      )}
                    </div>
                  )}
                </div>
              )
            })}
          </div>

          {/* ── Leasing ── */}
          <div className="card" style={{ marginBottom: 16 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 14, cursor: 'pointer', userSelect: 'none' }}
              onClick={() => { setLeasingEnabled(v => !v); if (!leasingKaufpreis) setLeasingKaufpreis(Math.round(oneTime)) }}>
              <div style={{
                width: 44, height: 24, borderRadius: 12, flexShrink: 0, transition: '.2s',
                background: leasingEnabled ? 'var(--red)' : '#ccc', position: 'relative',
              }}>
                <div style={{
                  position: 'absolute', top: 2, left: leasingEnabled ? 22 : 2,
                  width: 20, height: 20, borderRadius: '50%', background: 'white',
                  boxShadow: '0 1px 4px rgba(0,0,0,.25)', transition: '.2s',
                }} />
              </div>
              <span style={{ fontWeight: 700, fontSize: 14 }}>
                💶 Leasing-Finanzierung anbieten
              </span>
            </div>

            {leasingEnabled && (
              <div style={{ marginTop: 16 }}>
                <div className="field">
                  <label>Kaufpreis exkl. USt (€)</label>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                    <input
                      type="number" min="0" step="100"
                      value={leasingKaufpreis || Math.round(oneTime)}
                      onChange={e => setLeasingKaufpreis(Number(e.target.value))}
                      style={{ border: '1px solid var(--red)', borderRadius: 10,
                        padding: '10px 14px', fontSize: 14, fontWeight: 700,
                        color: 'var(--red)', width: 180 }}
                    />
                    {oneTime > 0 && (
                      <button className="btn" style={{ fontSize: 11 }}
                        onClick={() => setLeasingKaufpreis(Math.round(oneTime))}>
                        = Angebotssumme ({money(oneTime)})
                      </button>
                    )}
                  </div>
                </div>

                {/* Live-Vorschau Tabelle */}
                <div style={{ overflowX: 'auto', marginTop: 12 }}>
                  <table style={{ borderCollapse: 'collapse', fontSize: 12, width: '100%' }}>
                    <thead>
                      <tr style={{ background: 'var(--bg)' }}>
                        <th style={{ padding: '8px 12px', border: '1px solid var(--line)', textAlign: 'left' }}></th>
                        {leasingRows.map(r => (
                          <th key={r.dur} style={{ padding: '8px 14px', border: '1px solid var(--line)', textAlign: 'center', fontWeight: 700 }}>{r.dur} Monate</th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      <tr style={{ background: '#fff1f2' }}>
                        <td style={{ padding: '8px 12px', border: '1px solid var(--line)', fontWeight: 700 }}>Leasingrate p.M. exkl. USt</td>
                        {leasingRows.map(r => (
                          <td key={r.dur} style={{ padding: '8px 14px', border: '1px solid var(--line)', textAlign: 'center', fontWeight: 800, color: 'var(--red)' }}>{money(r.monthly)}</td>
                        ))}
                      </tr>
                      <tr>
                        <td style={{ padding: '8px 12px', border: '1px solid var(--line)', color: 'var(--muted)' }}>Bearbeitungsgebühr exkl. USt</td>
                        {leasingRows.map(r => (
                          <td key={r.dur} style={{ padding: '8px 14px', border: '1px solid var(--line)', textAlign: 'center', color: 'var(--muted)' }}>{money(r.fee)}</td>
                        ))}
                      </tr>
                      <tr>
                        <td style={{ padding: '8px 12px', border: '1px solid var(--line)', color: 'var(--muted)' }}>Gesetzl. Rechtsgeschäftsgebühr</td>
                        {leasingRows.map(r => (
                          <td key={r.dur} style={{ padding: '8px 14px', border: '1px solid var(--line)', textAlign: 'center', color: 'var(--muted)' }}>{money(r.legal)}</td>
                        ))}
                      </tr>
                    </tbody>
                  </table>
                </div>
                <p style={{ fontSize: 11, color: 'var(--muted)', marginTop: 6 }}>
                  Vorschau · Faktoren aus Einstellungen · alle Preise exkl. USt
                </p>
              </div>
            )}
          </div>

          <div className="card">

            <div className="field">
              <label>Projektbezeichnung (optional)</label>
              <input value={projectName} onChange={e => setProjectName(e.target.value)} placeholder="z.B. Standort Wien · Büro 3. OG" />
            </div>
            {error && <p style={{ color: 'var(--red)', fontSize: 13, marginBottom: 12 }}>⚠ {error}</p>}
            <button className="btn btn-red btn-lg" onClick={finalize} disabled={busy}>
              {busy ? '⏳ Wird erstellt …' : '🚀 Angebot erstellen'}
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
