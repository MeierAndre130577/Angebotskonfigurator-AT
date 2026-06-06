import { useState, useEffect } from 'react'
import { useSearchParams } from 'react-router-dom'
import { offers, pdf } from '../lib/api'

const BASE = (import.meta.env.VITE_API_URL || '') + '/api'

function money(n) {
  return new Intl.NumberFormat('de-AT', { style: 'currency', currency: 'EUR' }).format(n || 0)
}

const DEFAULT_PROVIDER = {
  company: 'Sielaff Austria GmbH',
  address: 'Weissenbachweg 7, AT-6067 Absam (Tirol)',
  email: 'info@at.sielaff.com',
  phone: '0676/6570301'
}

export default function Vorschau() {
  const [searchParams] = useSearchParams()
  const [offerNo, setOfferNo]       = useState('')
  const [offerData, setOfferData]   = useState(null)
  const [loading, setLoading]       = useState(false)
  const [generating, setGenerating] = useState(false)
  const [pdfUrl, setPdfUrl]         = useState('')
  const [toast, setToast]           = useState('')
  const [error, setError]           = useState('')
  const [loadingLatest, setLoadingLatest] = useState(false)
  const [settings, setSettings]           = useState(null)

  useEffect(() => {
    fetch(`${BASE}/settings`).then(r => r.json()).then(setSettings).catch(() => {})
  }, [])
  // Dank key={location.search} in App.jsx wird die Komponente neu gemountet
  // wenn sich die URL ändert – dieser useEffect läuft also genau einmal
  useEffect(() => {
    const no = (searchParams.get('no') || '').trim()
    if (no) {
      setOfferNo(no)
      doLoad(no)
    }
  }, [])

  function showToast(msg) {
    setToast(msg)
    setTimeout(() => setToast(''), 3000)
  }

  async function loadLatest() {
    setLoadingLatest(true); setError('')
    try {
      const res  = await fetch(`${BASE}/offers`)
      const data = await res.json()
      if (!Array.isArray(data) || data.length === 0) {
        setError('Keine Angebote vorhanden')
        return
      }
      // Neuestes anhand created_at
      const latest = data.sort((a,b) => new Date(b.created_at) - new Date(a.created_at))[0]
      const no = latest.offer_no
      setOfferNo(no)
      await doLoad(no)
    } catch(e) {
      setError('Fehler: ' + e.message)
    } finally {
      setLoadingLatest(false)
    }
  }

  function buildMailtoLink(pdfUrl) {
    const s       = settings || {}
    const proj    = offerData?.project || {}
    const replace = (tpl) => (tpl || '')
      .replace(/{{kunde}}/g,          proj.customer   || '')
      .replace(/{{ansprechpartner}}/g, proj.contact    || proj.customer || '')
      .replace(/{{angebotsnummer}}/g,  proj.offerNo    || '')
      .replace(/{{projekt}}/g,         proj.project    || '')
      .replace(/{{datum}}/g,           proj.date       || '')
      .replace(/{{gueltigBis}}/g,      proj.valid      || '')
      .replace(/{{anbieter}}/g,        s.company       || 'Sielaff Austria GmbH')

    const to      = proj.customerEmail || ''
    const subject = encodeURIComponent(replace(
      s.email_subject || 'Angebot {{angebotsnummer}} – {{projekt}} für {{kunde}}'
    ))
    const body    = encodeURIComponent(replace(
      s.email_body ||
`Sehr geehrte(r) {{ansprechpartner}},

vielen Dank für Ihr Interesse. Anbei finden Sie unser Angebot {{angebotsnummer}} für {{projekt}}.

Das Angebot ist gültig bis {{gueltigBis}}.

Bei Fragen stehen wir Ihnen gerne zur Verfügung.

Mit freundlichen Grüßen
{{anbieter}}`
    ))
    // Hinweis: Anhänge können über mailto: nicht automatisch beigefügt werden.
    // Das PDF muss manuell angehängt werden – wir öffnen es gleichzeitig zum Download.
    return `mailto:${to}?subject=${subject}&body=${body}`
  }

  function handleSendEmail() {
    if (!pdfUrl) return
    // PDF öffnen damit es heruntergeladen wird
    window.open(pdfUrl, '_blank')
    // E-Mail-Client öffnen
    setTimeout(() => {
      window.location.href = buildMailtoLink(pdfUrl)
    }, 500)
  }

  async function doLoad(no) {
    const num = (no || offerNo || '').trim()
    if (!num) return
    setLoading(true); setError(''); setOfferData(null); setPdfUrl('')
    try {
      const data = await offers.getByNumber(num)
      setOfferData(data)
    } catch(e) {
      setError(`Angebot „${num}" nicht gefunden`)
    } finally {
      setLoading(false)
    }
  }

  async function generatePdf() {
    if (!offerData) return
    setGenerating(true); setPdfUrl('')
    try {
      // Aktuelle Optionen laden um Dokumente zu ergänzen
      let offerItems = offerData.offer_items || []
      try {
        const optRes  = await fetch(`${BASE}/options`)
        const optData = await optRes.json()
        // Dokumente aus aktueller Bibliothek in offer_items ergänzen
        offerItems = offerItems.map(item => {
          const currentOpt = optData.find(o => o.id === item.option_id || o.name === item.name)
          return currentOpt
            ? { ...item, documents: currentOpt.documents || item.documents || [] }
            : item
        })
      } catch(e) {
        console.warn('Optionen nicht ladbar:', e)
      }

      const result = await pdf.generate({
        project:      offerData.project || {},
        provider:     DEFAULT_PROVIDER,
        offer:        offerItems,
        attachments:  [],
        legal_notice: '',
        pages: [], clusters: [],
      })
      if (result.ok && result.download_url) {
        setPdfUrl((import.meta.env.VITE_API_URL || '') + result.download_url)
        showToast('PDF erstellt ✓')
      } else {
        setError('PDF-Generierung fehlgeschlagen')
      }
    } catch(e) {
      setError('Fehler: ' + e.message)
    } finally {
      setGenerating(false)
    }
  }

  const items   = offerData?.offer_items || []
  const oneTime = items.filter(i => !i.recurring).reduce((s,i) => s+(i.price||0), 0)
  const monthly = items.filter(i =>  i.recurring).reduce((s,i) => s+(i.price||0), 0)
  const project = offerData?.project || {}

  return (
    <div style={{ maxWidth: 800 }}>
      {toast && (
        <div style={{
          position: 'fixed', bottom: 24, right: 24, background: 'var(--dark)',
          color: 'white', padding: '12px 20px', borderRadius: 12,
          fontSize: 13, fontWeight: 600, zIndex: 9999
        }}>{toast}</div>
      )}

      <div className="page-header">
        <div><h1>👁️ PDF-Vorschau</h1><p className="subtitle">Angebot laden und PDF generieren</p></div>
      </div>

      <div className="card" style={{ marginBottom: 16 }}>
        <div className="card-title">Angebotsnummer</div>
        <div className="row">
          <input
            value={offerNo}
            onChange={e => setOfferNo(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && doLoad()}
            placeholder="z.B. ANG-2026-06-483921"
            style={{ flex: 1, border: '1px solid var(--line)', borderRadius: 10,
              padding: '10px 14px', fontSize: 14, fontFamily: 'var(--font-mono)' }}
          />
          <button className="btn btn-red" onClick={() => doLoad()} disabled={loading}>
            {loading ? '⏳ Lädt …' : '🔍 Laden'}
          </button>
          <button className="btn" onClick={loadLatest} disabled={loadingLatest || loading}
            title="Lädt das zuletzt erstellte Angebot">
            {loadingLatest ? '⏳' : '⭐ Neuestes'}
          </button>
        </div>
        {loading && <p style={{ color: 'var(--muted)', fontSize: 13, marginTop: 8 }}>⏳ Wird geladen …</p>}
        {error   && <p style={{ color: 'var(--red)',   fontSize: 13, marginTop: 8 }}>⚠ {error}</p>}
      </div>

      {offerData && (
        <>
          <div className="card" style={{ marginBottom: 16 }}>
            <div className="card-title">Vorschau</div>
            <div className="grid2" style={{ marginBottom: 16 }}>
              <div className="stat-card">
                <div className="value" style={{ fontSize: 18 }}>{project.customer || '—'}</div>
                <div className="label">{project.contact}</div>
              </div>
              <div className="stat-card">
                <div className="value" style={{ fontSize: 14, fontFamily: 'var(--font-mono)' }}>{project.offerNo || '—'}</div>
                <div className="label">{project.date}</div>
              </div>
            </div>
            {items.map((item, i) => (
              <div key={i} className="between small" style={{ padding: '8px 0', borderBottom: '1px solid var(--line)' }}>
                <span><b>{item.name}</b><span className="pill muted" style={{ marginLeft: 8 }}>{item.cluster}</span></span>
                <b style={{ color: 'var(--red)' }}>
                  {(item.price||0) === 0 ? 'inkl.' : item.recurring ? money(item.price)+'/Mo.' : money(item.price)}
                </b>
              </div>
            ))}
            <div className="grid2" style={{ marginTop: 16 }}>
              <div style={{ background: 'var(--red-light)', borderRadius: 12, padding: '12px 16px' }}>
                <div style={{ fontSize: 20, fontWeight: 850, color: 'var(--red)' }}>{money(oneTime)}</div>
                <div style={{ fontSize: 12, color: 'var(--muted)', marginTop: 2 }}>Einmalig gesamt</div>
              </div>
              {monthly > 0 && (
                <div style={{ background: 'var(--red-light)', borderRadius: 12, padding: '12px 16px' }}>
                  <div style={{ fontSize: 20, fontWeight: 850, color: 'var(--red)' }}>{money(monthly)}</div>
                  <div style={{ fontSize: 12, color: 'var(--muted)', marginTop: 2 }}>Monatlich gesamt</div>
                </div>
              )}
            </div>
          </div>

          <div className="card">
            <div className="card-title">PDF generieren</div>
            <button className="btn btn-red btn-lg" onClick={generatePdf} disabled={generating}>
              {generating ? '⏳ PDF wird erstellt …' : '📄 PDF erstellen'}
            </button>
            {pdfUrl && (
              <div style={{ marginTop: 16, padding: 16, background: 'var(--bg)', borderRadius: 12 }}>
                <p style={{ fontSize: 13, marginBottom: 10 }}>✅ PDF ist bereit:</p>
                <div className="row" style={{ flexWrap: 'wrap' }}>
                  <a href={pdfUrl} target="_blank" rel="noopener noreferrer" className="btn btn-red" style={{ textDecoration: 'none' }}>📥 Herunterladen</a>
                  <a href={pdfUrl} target="_blank" rel="noopener noreferrer" className="btn" style={{ textDecoration: 'none' }}>👁️ Im Browser öffnen</a>
                  <button className="btn" onClick={handleSendEmail} style={{ background: 'var(--dark)', color: 'white', border: 'none' }}>
                    ✉️ Per E-Mail senden
                  </button>
                </div>
                <p style={{ fontSize: 11, color: 'var(--muted)', marginTop: 8 }}>
                  💡 Das PDF wird heruntergeladen und dein E-Mail-Programm öffnet sich mit vorausgefülltem Betreff und Text. Anhänge bitte manuell beifügen.
                </p>
              </div>
            )}
          </div>
        </>
      )}

      {!offerData && !loading && (
        <div className="card">
          <p className="muted small">Gib eine Angebotsnummer ein oder wähle ein Angebot aus der Übersicht.</p>
        </div>
      )}
    </div>
  )
}
