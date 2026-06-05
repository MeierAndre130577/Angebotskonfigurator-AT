import { useState, useEffect } from 'react'
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
  const [selectedIds, setSelectedIds] = useState(new Set())
  const [projectName, setProjectName] = useState('')
  const [offerNo, setOfferNo]         = useState('')
  const [busy, setBusy]               = useState(false)
  const [done, setDone]               = useState(false)
  const [error, setError]             = useState('')
  const [allCustomers, setAllCustomers] = useState([])

  useEffect(() => {
    optionsApi.list().then(setAllOptions).catch(console.warn)
    customersApi.list().then(setAllCustomers).catch(console.warn)
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

  function validateStep1() {
    if (selectedIds.size === 0) { setError('Bitte mindestens eine Option wählen'); return false }
    setError(''); return true
  }

  async function finalize() {
    if (busy) return
    setBusy(true); setError('')
    try {
      const { offer_no } = await offersApi.generateNumber()
      setOfferNo(offer_no)
      const items = allOptions.filter(o => selectedIds.has(o.id))
      await offersApi.upsert({
        offer_no,
        project: { ...contact, project: projectName || 'Messegespräch', offerNo: offer_no },
        offer_items: items.map(o => ({ option_id: o.id, name: o.name, price: o.price, recurring: o.recurring, qty: 1 })),
        status: 'draft',
      })
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
    setDone(false); setError('')
  }

  // ── Cluster-Gruppen ────────────────────────────────────────────────────────
  const byCluster = allOptions.reduce((acc, o) => {
    const cl = o.cluster || 'Sonstiges'
    acc[cl] = acc[cl] || []
    acc[cl].push(o)
    return acc
  }, {})

  const selected = allOptions.filter(o => selectedIds.has(o.id))
  const oneTime  = selected.filter(o => !o.recurring).reduce((s, o) => s + (o.price || 0), 0)
  const monthly  = selected.filter(o => o.recurring).reduce((s, o) => s + (o.price || 0), 0)

  // ── Done Screen ───────────────────────────────────────────────────────────
  if (done) return (
    <div style={{ maxWidth: 560, margin: '60px auto', textAlign: 'center' }}>
      <div style={{ fontSize: 64, marginBottom: 16 }}>✅</div>
      <h1 style={{ fontSize: 28, fontWeight: 850, marginBottom: 8 }}>Angebot erstellt!</h1>
      <p className="muted" style={{ marginBottom: 8 }}><b>{contact.company}</b> · {contact.email}</p>
      <p style={{ marginBottom: 32 }}>
        Angebotsnummer: <b style={{ color: 'var(--red)', fontFamily: 'var(--font-mono)' }}>{offerNo}</b>
      </p>
      <button className="btn btn-red btn-lg" style={{ marginBottom: 12 }} onClick={reset}>
        ＋ Neues Messegespräch
      </button>
    </div>
  )

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
          <div className="between" style={{ marginBottom: 20 }}>
            <p className="muted small">{selectedIds.size} Option(en) gewählt für <b>{contact.company}</b></p>
            <button className="btn" onClick={() => setStep(0)}>← zurück</button>
          </div>

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
                      <p style={{ marginTop: 8, fontWeight: 800, fontSize: 12, color: sel ? 'var(--red)' : 'var(--muted)' }}>
                        {o.price === 0 ? 'inklusive' : o.recurring ? money(o.price) + ' / Mo.' : money(o.price)}
                      </p>
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
            {selected.map(o => (
              <div key={o.id} className="between small" style={{ padding: '8px 0', borderBottom: '1px solid var(--line)' }}>
                <span><b>{o.name}</b> <span className="muted">{o.cluster}</span></span>
                <b style={{ color: 'var(--red)' }}>{o.price === 0 ? 'inkl.' : o.recurring ? money(o.price) + '/Mo.' : money(o.price)}</b>
              </div>
            ))}
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
