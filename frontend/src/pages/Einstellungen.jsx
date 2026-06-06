import React, { useState, useEffect, useRef } from 'react'

const BASE = (import.meta.env.VITE_API_URL || '') + '/api'

const DEFAULTS = {
  // Kopf-/Fußzeile
  header_height_mm:    26,
  footer_distance_mm:  14,
  // Seitenränder Inhaltsseiten
  margin_top_mm:       39,   // = HEADER_H + 13mm
  margin_bottom_mm:    22,
  margin_left_mm:      20,
  margin_right_mm:     12,
  // Anbieter
  company:   'Sielaff Austria GmbH',
  address:   'Weissenbachweg 7, AT-6067 Absam (Tirol)',
  email:     'info@at.sielaff.com',
  phone:     '0676/6570301',
  // AGB
  legal_notice: 'Die ausgewiesenen Preise sind Nettopreise und verstehen sich zuzüglich der gesetzlichen Mehrwertsteuer. Die Distribution entscheidet Sielaff Austria GmbH.',
  // Pflichtanlagen
  mandatory_documents: [],
  // E-Mail Vorlage
  email_subject: 'Angebot {{angebotsnummer}} – {{projekt}} für {{kunde}}',
  email_body: `Sehr geehrte(r) {{ansprechpartner}},

vielen Dank für Ihr Interesse. Anbei finden Sie unser Angebot {{angebotsnummer}} für {{projekt}}.

Das Angebot ist gültig bis {{gueltigBis}}.

Bei Fragen stehen wir Ihnen gerne zur Verfügung.

Mit freundlichen Grüßen
{{anbieter}}`,
}

function Field({ label, hint, children }) {
  return (
    <div className="field">
      <label>{label}</label>
      {children}
      {hint && <p style={{ fontSize: 11, color: 'var(--muted)', marginTop: 2 }}>{hint}</p>}
    </div>
  )
}

function NumberInput({ value, onChange, min = 0, max = 100, unit = 'mm' }) {
  return (
    <div className="row" style={{ gap: 8 }}>
      <input
        type="number" value={value} min={min} max={max}
        onChange={e => onChange(Number(e.target.value))}
        style={{ width: 80, border: '1px solid var(--line)', borderRadius: 10,
          padding: '9px 12px', fontSize: 14, fontFamily: 'var(--font-mono)' }}
      />
      <span style={{ fontSize: 13, color: 'var(--muted)' }}>{unit}</span>
    </div>
  )
}

export default function Einstellungen() {
  const [settings, setSettings] = useState(DEFAULTS)
  const [saving, setSaving]     = useState(false)
  const [toast, setToast]       = useState('')
  const [loading, setLoading]       = useState(true)
  const [uploadingDoc, setUploadingDoc] = useState(false)
  const docRef = useRef()

  useEffect(() => { loadSettings() }, [])

  async function loadSettings() {
    try {
      const res  = await fetch(`${BASE}/settings`)
      if (res.ok) {
        const data = await res.json()
        setSettings({ ...DEFAULTS, ...data })
      }
    } catch(e) {
      console.warn('Einstellungen nicht ladbar, verwende Defaults')
    } finally {
      setLoading(false)
    }
  }

  async function save() {
    setSaving(true)
    try {
      await fetch(`${BASE}/settings`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(settings),
      })
      showToast('Einstellungen gespeichert ✓')
    } catch(e) {
      showToast('Fehler: ' + e.message)
    } finally {
      setSaving(false)
    }
  }

  function set(key, value) {
    setSettings(s => ({ ...s, [key]: value }))
  }

  function showToast(msg) {
    setToast(msg)
    setTimeout(() => setToast(''), 2500)
  }

  async function uploadMandatoryDoc(file) {
    if (!file) return
    setUploadingDoc(true)
    try {
      const formData = new FormData()
      formData.append('file', file, file.name)
      const res  = await fetch(`${BASE}/upload/document`, { method: 'POST', body: formData })
      const data = await res.json().catch(() => ({}))
      if (!res.ok) throw new Error(data.error || 'Upload fehlgeschlagen')
      const newDoc = {
        id:        crypto.randomUUID(),
        title:     file.name.replace(/\.[^.]+$/, ''),
        file_name: file.name,
        file_url:  data.url || '',
      }
      setSettings(s => ({ ...s, mandatory_documents: [...(s.mandatory_documents || []), newDoc] }))
      showToast('Dokument hochgeladen ✓')
    } catch(e) {
      showToast('Fehler: ' + e.message)
    } finally {
      setUploadingDoc(false)
      if (docRef.current) docRef.current.value = ''
    }
  }

  function removeMandatoryDoc(id) {
    setSettings(s => ({ ...s, mandatory_documents: (s.mandatory_documents || []).filter(d => d.id !== id) }))
  }

  function updateMandatoryDocTitle(id, title) {
    setSettings(s => ({
      ...s,
      mandatory_documents: (s.mandatory_documents || []).map(d => d.id === id ? { ...d, title } : d)
    }))
  }

  if (loading) return <p className="muted">Lädt …</p>

  return (
    <div style={{ maxWidth: 720 }}>
      {toast && (
        <div style={{
          position: 'fixed', bottom: 24, right: 24, background: 'var(--dark)',
          color: 'white', padding: '12px 20px', borderRadius: 12,
          fontSize: 13, fontWeight: 600, zIndex: 9999
        }}>{toast}</div>
      )}

      <div className="page-header">
        <div><h1>⚙️ Einstellungen</h1><p className="subtitle">PDF-Layout, Firmenangaben und Texte</p></div>
        <button className="btn btn-red" onClick={save} disabled={saving}>
          {saving ? '⏳ Speichert …' : '💾 Speichern'}
        </button>
      </div>

      {/* ── PDF Layout ─────────────────────────────────────────────────────── */}
      <div className="card" style={{ marginBottom: 16 }}>
        <div className="card-title">📐 PDF-Layout</div>

        {/* Visualisierung */}
        <div style={{
          width: '100%', aspectRatio: '1/1.41', background: 'white',
          border: '1px solid var(--line)', borderRadius: 12, position: 'relative',
          marginBottom: 20, overflow: 'hidden', maxWidth: 280, margin: '0 auto 20px'
        }}>
          {/* Roter Streifen links */}
          <div style={{ position: 'absolute', left: 0, top: 0, bottom: 0, width: '2%', background: 'var(--red)' }} />
          {/* Kopfzeile */}
          <div style={{
            position: 'absolute', top: 0, left: '2%', right: 0,
            height: `${(settings.header_height_mm / 297) * 100}%`,
            background: '#fff1f2', borderBottom: '1px solid var(--red)',
            display: 'flex', alignItems: 'center', paddingLeft: 8,
            fontSize: 8, color: 'var(--red)', fontWeight: 700,
          }}>Kopfzeile {settings.header_height_mm}mm</div>
          {/* Inhalt */}
          <div style={{
            position: 'absolute',
            top: `${(settings.margin_top_mm / 297) * 100}%`,
            bottom: `${(settings.margin_bottom_mm / 297) * 100}%`,
            left: `${(settings.margin_left_mm / 210) * 100}%`,
            right: `${(settings.margin_right_mm / 210) * 100}%`,
            background: 'var(--bg)', borderRadius: 4,
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            fontSize: 8, color: 'var(--muted)',
          }}>Inhalt</div>
          {/* Fußzeile */}
          <div style={{
            position: 'absolute', bottom: 0, left: '2%', right: 0,
            height: `${(settings.footer_distance_mm / 297) * 100}%`,
            background: '#fff1f2', borderTop: '1px solid var(--red)',
            display: 'flex', alignItems: 'center', paddingLeft: 8,
            fontSize: 8, color: 'var(--red)', fontWeight: 700,
          }}>Fußzeile {settings.footer_distance_mm}mm</div>
        </div>

        <div className="grid2">
          <Field label="Kopfzeile – Höhe" hint="Abstand vom oberen Seitenrand">
            <NumberInput value={settings.header_height_mm} min={15} max={40}
              onChange={v => set('header_height_mm', v)} />
          </Field>
          <Field label="Fußzeile – Abstand" hint="Abstand vom unteren Seitenrand">
            <NumberInput value={settings.footer_distance_mm} min={8} max={30}
              onChange={v => set('footer_distance_mm', v)} />
          </Field>
        </div>

        <div style={{ borderTop: '1px solid var(--line)', paddingTop: 16, marginTop: 4 }}>
          <div className="card-title" style={{ fontSize: 13 }}>Inhaltsbereich</div>
          <div className="grid2">
            <Field label="Abstand oben (Inhalt startet ab …)" hint="Empfohlen: Kopfzeile + mind. 8mm">
              <NumberInput value={settings.margin_top_mm} min={20} max={60}
                onChange={v => set('margin_top_mm', v)} />
            </Field>
            <Field label="Abstand unten">
              <NumberInput value={settings.margin_bottom_mm} min={10} max={40}
                onChange={v => set('margin_bottom_mm', v)} />
            </Field>
            <Field label="Abstand links">
              <NumberInput value={settings.margin_left_mm} min={10} max={40}
                onChange={v => set('margin_left_mm', v)} />
            </Field>
            <Field label="Abstand rechts">
              <NumberInput value={settings.margin_right_mm} min={8} max={30}
                onChange={v => set('margin_right_mm', v)} />
            </Field>
          </div>
        </div>
      </div>

      {/* ── Firmenangaben ───────────────────────────────────────────────────── */}
      <div className="card" style={{ marginBottom: 16 }}>
        <div className="card-title">🏢 Firmenangaben</div>
        <p style={{ fontSize: 12, color: 'var(--muted)', marginBottom: 16 }}>
          Diese Angaben erscheinen in Kopf- und Fußzeile sowie auf dem Deckblatt.
        </p>
        <Field label="Firmenname">
          <input value={settings.company} onChange={e => set('company', e.target.value)}
            style={{ border: '1px solid var(--line)', borderRadius: 10, padding: '10px 14px', fontSize: 14 }} />
        </Field>
        <Field label="Adresse">
          <input value={settings.address} onChange={e => set('address', e.target.value)}
            style={{ border: '1px solid var(--line)', borderRadius: 10, padding: '10px 14px', fontSize: 14 }} />
        </Field>
        <div className="grid2">
          <Field label="E-Mail">
            <input value={settings.email} onChange={e => set('email', e.target.value)}
              style={{ border: '1px solid var(--line)', borderRadius: 10, padding: '10px 14px', fontSize: 14 }} />
          </Field>
          <Field label="Telefon">
            <input value={settings.phone} onChange={e => set('phone', e.target.value)}
              style={{ border: '1px solid var(--line)', borderRadius: 10, padding: '10px 14px', fontSize: 14 }} />
          </Field>
        </div>
      </div>

      {/* ── AGB ─────────────────────────────────────────────────────────────── */}
      <div className="card" style={{ marginBottom: 16 }}>
        <div className="card-title">📋 Rechtliche Hinweise / AGB</div>
        <p style={{ fontSize: 12, color: 'var(--muted)', marginBottom: 12 }}>
          Erscheint als Text auf der letzten Seite des Angebots.
        </p>
        <Field label="">
          <textarea value={settings.legal_notice} onChange={e => set('legal_notice', e.target.value)}
            style={{ minHeight: 120, border: '1px solid var(--line)', borderRadius: 10,
              padding: '10px 14px', fontSize: 13, lineHeight: 1.6 }} />
        </Field>
      </div>

      {/* ── Pflichtanlagen ───────────────────────────────────────────────────── */}
      <div className="card">
        <div className="between" style={{ marginBottom: 12 }}>
          <div>
            <div className="card-title" style={{ marginBottom: 2 }}>📎 Pflichtanlagen</div>
            <p style={{ fontSize: 12, color: 'var(--muted)' }}>
              Diese Dokumente werden <b>immer</b> beigefügt – bei jedem Angebot, unabhängig von den gewählten Optionen.
            </p>
          </div>
          <button className="btn" style={{ padding: '7px 14px', fontSize: 12, flex: 'none' }}
            onClick={() => docRef.current?.click()} disabled={uploadingDoc}>
            {uploadingDoc ? '⏳' : '📎 Dokument hinzufügen'}
          </button>
        </div>
        <input ref={docRef} type="file" accept=".pdf,.doc,.docx"
          onChange={e => uploadMandatoryDoc(e.target.files[0])} style={{ display: 'none' }} />

        {(settings.mandatory_documents || []).length === 0 ? (
          <p style={{ fontSize: 12, color: 'var(--muted)', fontStyle: 'italic' }}>
            Noch keine Pflichtanlagen – z.B. AGB als PDF hochladen.
          </p>
        ) : (
          <div>
            {(settings.mandatory_documents || []).map(doc => (
              <div key={doc.id} style={{ marginBottom: 10 }}>
                <div style={{
                  display: 'flex', alignItems: 'center', gap: 10,
                  padding: '8px 12px', background: 'var(--bg)', borderRadius: 10,
                  border: '1px solid var(--line)', marginBottom: 4
                }}>
                  <span style={{ fontSize: 18 }}>📄</span>
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div style={{ fontSize: 12, color: 'var(--muted)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                      {doc.file_name}
                    </div>
                  </div>
                  {doc.file_url && (
                    <a href={doc.file_url} target="_blank" rel="noopener noreferrer"
                      className="btn" style={{ padding: '3px 8px', fontSize: 11, textDecoration: 'none', flex: 'none' }}>
                      👁️
                    </a>
                  )}
                  <button onClick={() => removeMandatoryDoc(doc.id)}
                    style={{ border: 'none', background: 'none', cursor: 'pointer', color: 'var(--red)', fontSize: 16, flex: 'none' }}>
                    ✕
                  </button>
                </div>
                <input
                  value={doc.title}
                  onChange={e => updateMandatoryDocTitle(doc.id, e.target.value)}
                  placeholder="Titel (erscheint in Anlagen)"
                  style={{ width: '100%', border: '1px solid var(--line)', borderRadius: 8,
                    padding: '6px 12px', fontSize: 12 }}
                />
              </div>
            ))}
          </div>
        )}
      </div>

      {/* ── E-Mail Vorlage ───────────────────────────────────────────────────── */}
      <div className="card" style={{ marginBottom: 16, marginTop: 16 }}>
        <div className="card-title">✉️ E-Mail Vorlage</div>
        <p style={{ fontSize: 12, color: 'var(--muted)', marginBottom: 12 }}>
          Verfügbare Platzhalter: <code>{'{{kunde}}'}</code> <code>{'{{ansprechpartner}}'}</code> <code>{'{{angebotsnummer}}'}</code> <code>{'{{projekt}}'}</code> <code>{'{{datum}}'}</code> <code>{'{{gueltigBis}}'}</code> <code>{'{{anbieter}}'}</code>
        </p>
        <Field label="Betreff">
          <input value={settings.email_subject || ''} onChange={e => set('email_subject', e.target.value)}
            style={{ border: '1px solid var(--line)', borderRadius: 10, padding: '10px 14px', fontSize: 13 }} />
        </Field>
        <Field label="E-Mail Text">
          <textarea value={settings.email_body || ''} onChange={e => set('email_body', e.target.value)}
            style={{ minHeight: 180, border: '1px solid var(--line)', borderRadius: 10,
              padding: '10px 14px', fontSize: 12, lineHeight: 1.6, fontFamily: 'var(--font-mono)' }} />
        </Field>
      </div>

      <div style={{ marginTop: 8 }}>
        <button className="btn btn-red btn-lg" onClick={save} disabled={saving}>
          {saving ? '⏳ Speichert …' : '💾 Alle Einstellungen speichern'}
        </button>
      </div>
    </div>
  )
}
