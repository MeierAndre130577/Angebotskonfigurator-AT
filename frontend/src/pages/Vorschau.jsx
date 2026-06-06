import { useState } from 'react'
import { offers, pdf } from '../lib/api'

function money(n) {
  return new Intl.NumberFormat('de-AT', { style: 'currency', currency: 'EUR' }).format(n || 0)
}

const DEFAULT_PROJECT = {
  offerNo: '', customer: '', contact: '', customerEmail: '',
  project: '', date: '', valid: ''
}
const DEFAULT_PROVIDER = {
  company: 'Sielaff Austria GmbH',
  address: 'Weissenbachweg 7, AT-6067 Absam (Tirol)',
  email: 'info@at.sielaff.com',
  phone: '0676/6570301'
}

export default function Vorschau() {
  const [offerNo, setOfferNo]     = useState('')
  const [offerData, setOfferData] = useState(null)
  const [loading, setLoading]     = useState(false)
  const [generating, setGenerating] = useState(false)
  const [translating, setTranslating] = useState(false)
  const [pdfUrl, setPdfUrl]       = useState('')
  const [toast, setToast]         = useState('')
  const [error, setError]         = useState('')

  function showToast(msg) {
    setToast(msg)
    setTimeout(() => setToast(''), 3000)
  }

  async function loadOffer() {
    if (!offerNo.trim()) return
    setLoading(true); setError('')
    try {
      const data = await offers.getByNumber(offerNo.trim())
      setOfferData(data)
      setPdfUrl('')
    } catch(e) {
      setError('Angebot nicht gefunden: ' + offerNo)
    } finally {
      setLoading(false)
    }
  }

  async function generatePdf(lang = 'de') {
    if (!offerData) return
    setGenerating(true); setPdfUrl('')
    try {
      const payload = {
        project:     offerData.project     || DEFAULT_PROJECT,
        provider:    DEFAULT_PROVIDER,
        offer:       offerData.offer_items || [],
        attachments: [],
        legal_notice: '',
        pages:       [],
        clusters:    [],
      }
      const result = await pdf.generate(payload)
      if (result.ok && result.download_url) {
        const fullUrl = (import.meta.env.VITE_API_URL || '') + result.download_url
        setPdfUrl(fullUrl)
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

  async function translateAndGenerate() {
    if (!offerData) return
    setTranslating(true); setPdfUrl(''); setError('')
    try {
      // KI-Übersetzung via Anthropic API
      const items = offerData.offer_items || []
      const textsToTranslate = items.map(i => ({
        name: i.name || '',
        short_text: i.short_text || '',
        long_text: i.long_text || '',
      }))

      const response = await fetch('https://api.anthropic.com/v1/messages', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          model: 'claude-sonnet-4-20250514',
          max_tokens: 4000,
          messages: [{
            role: 'user',
            content: `Translate the following JSON array from German to English. 
Translate only the values of "name", "short_text", and "long_text" fields.
Keep all other fields exactly as they are.
Return ONLY valid JSON, no markdown, no explanation.

${JSON.stringify(textsToTranslate)}`
          }]
        })
      })
      const aiData = await response.json()
      const translated = JSON.parse(aiData.content[0].text)

      const translatedItems = items.map((item, i) => ({
        ...item,
        name:       translated[i]?.name       || item.name,
        short_text: translated[i]?.short_text || item.short_text,
        long_text:  translated[i]?.long_text  || item.long_text,
      }))

      // Englisches PDF generieren
      const payload = {
        project: {
          ...(offerData.project || DEFAULT_PROJECT),
          project: offerData.project?.project + ' (EN)' || 'Offer',
        },
        provider: DEFAULT_PROVIDER,
        offer: translatedItems,
        attachments: [],
        legal_notice: 'All prices are net prices excluding statutory VAT. Distribution is at the discretion of Sielaff Austria GmbH.',
        pages: [],
        clusters: [],
      }
      const result = await pdf.generate(payload)
      if (result.ok && result.download_url) {
        const fullUrl = (import.meta.env.VITE_API_URL || '') + result.download_url
        setPdfUrl(fullUrl)
        showToast('Englisches PDF erstellt ✓')
      }
    } catch(e) {
      setError('Übersetzung fehlgeschlagen: ' + e.message)
    } finally {
      setTranslating(false)
    }
  }

  const items     = offerData?.offer_items || []
  const oneTime   = items.filter(i => !i.recurring).reduce((s,i) => s+(i.price||0), 0)
  const monthly   = items.filter(i => i.recurring).reduce((s,i) => s+(i.price||0), 0)
  const project   = offerData?.project || {}

  return (
    <div style={{ maxWidth: 800 }}>
      {/* Toast */}
      {toast && (
        <div style={{
          position: 'fixed', bottom: 24, right: 24, background: 'var(--dark)',
          color: 'white', padding: '12px 20px', borderRadius: 12,
          fontSize: 13, fontWeight: 600, zIndex: 9999
        }}>{toast}</div>
      )}

      <div className="page-header">
        <div>
          <h1>👁️ PDF-Vorschau</h1>
          <p className="subtitle">Angebot laden und PDF generieren</p>
        </div>
      </div>

      {/* Angebot laden */}
      <div className="card" style={{ marginBottom: 16 }}>
        <div className="card-title">Angebot laden</div>
        <div className="row">
          <input
            value={offerNo}
            onChange={e => setOfferNo(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && loadOffer()}
            placeholder="Angebotsnummer z.B. ANG-2026-1001"
            style={{ flex: 1, border: '1px solid var(--line)', borderRadius: 10, padding: '10px 14px', fontSize: 14 }}
          />
          <button className="btn btn-red" onClick={loadOffer} disabled={loading}>
            {loading ? '⏳ Lädt …' : '🔍 Laden'}
          </button>
        </div>
        {error && <p style={{ color: 'var(--red)', fontSize: 13, marginTop: 8 }}>⚠ {error}</p>}
      </div>

      {/* Angebot Vorschau */}
      {offerData && (
        <>
          <div className="card" style={{ marginBottom: 16 }}>
            <div className="card-title">Angebotsvorschau</div>

            {/* Kopfdaten */}
            <div className="grid2" style={{ marginBottom: 16 }}>
              <div className="stat-card">
                <div className="value" style={{ fontSize: 20 }}>{project.customer || '—'}</div>
                <div className="label">Kunde · {project.contact}</div>
              </div>
              <div className="stat-card">
                <div className="value" style={{ fontSize: 16, fontFamily: 'var(--font-mono)' }}>{project.offerNo || '—'}</div>
                <div className="label">Angebotsnummer · {project.date}</div>
              </div>
            </div>

            {/* Optionen */}
            <div style={{ marginBottom: 16 }}>
              {items.map((item, i) => (
                <div key={i} className="between small" style={{ padding: '8px 0', borderBottom: '1px solid var(--line)' }}>
                  <span><b>{item.name}</b> <span className="muted pill" style={{ marginLeft: 6 }}>{item.cluster}</span></span>
                  <b style={{ color: 'var(--red)' }}>
                    {(item.price||0) === 0 ? 'inkl.' : item.recurring ? money(item.price)+'/Mo.' : money(item.price)}
                  </b>
                </div>
              ))}
            </div>

            {/* Summen */}
            <div className="grid2">
              <div style={{ background: 'var(--bg)', borderRadius: 12, padding: '12px 16px' }}>
                <div style={{ fontSize: 20, fontWeight: 850, color: 'var(--red)' }}>{money(oneTime)}</div>
                <div style={{ fontSize: 12, color: 'var(--muted)', marginTop: 2 }}>Einmalig</div>
              </div>
              <div style={{ background: 'var(--bg)', borderRadius: 12, padding: '12px 16px' }}>
                <div style={{ fontSize: 20, fontWeight: 850, color: 'var(--red)' }}>{money(monthly)}</div>
                <div style={{ fontSize: 12, color: 'var(--muted)', marginTop: 2 }}>Monatlich</div>
              </div>
            </div>
          </div>

          {/* PDF Buttons */}
          <div className="card">
            <div className="card-title">PDF generieren</div>
            <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap' }}>
              <button className="btn btn-red" onClick={() => generatePdf('de')} disabled={generating || translating}
                style={{ flex: 1, justifyContent: 'center', padding: '14px' }}>
                {generating ? '⏳ Erstellt …' : '📄 PDF auf Deutsch'}
              </button>
              <button className="btn" onClick={translateAndGenerate} disabled={generating || translating}
                style={{ flex: 1, justifyContent: 'center', padding: '14px' }}>
                {translating ? '🤖 Übersetzt …' : '🌍 PDF auf Englisch (KI)'}
              </button>
            </div>

            {pdfUrl && (
              <div style={{ marginTop: 16, padding: 16, background: 'var(--bg)', borderRadius: 12 }}>
                <p style={{ fontSize: 13, marginBottom: 10 }}>✅ PDF ist bereit:</p>
                <div className="row">
                  <a href={pdfUrl} target="_blank" rel="noopener noreferrer" className="btn btn-red"
                    style={{ textDecoration: 'none' }}>
                    📥 PDF herunterladen
                  </a>
                  <a href={pdfUrl} target="_blank" rel="noopener noreferrer" className="btn"
                    style={{ textDecoration: 'none' }}>
                    👁️ Im Browser öffnen
                  </a>
                </div>
              </div>
            )}
          </div>
        </>
      )}

      {!offerData && !loading && (
        <div className="card">
          <p className="muted small">Gib eine Angebotsnummer ein und klicke „Laden" um das Angebot anzuzeigen.<br/>
          Angebote werden im Messe-Modus oder über die Konfiguration erstellt.</p>
        </div>
      )}
    </div>
  )
}
