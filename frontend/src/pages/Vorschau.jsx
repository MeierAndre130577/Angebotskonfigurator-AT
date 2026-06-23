import { useState, useEffect } from 'react'
import { useSearchParams, useNavigate } from 'react-router-dom'
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
  const navigate = useNavigate()
  const [offerNo, setOfferNo]       = useState('')
  const [offerData, setOfferData]   = useState(null)
  const [loading, setLoading]       = useState(false)
  const [generating, setGenerating] = useState(false)
  const [pdfUrl, setPdfUrl]         = useState('')
  const [toast, setToast]           = useState('')
  const [error, setError]           = useState('')
  const [packageUrl, setPackageUrl]   = useState('')
  const [qrVisible, setQrVisible]     = useState(false)
  const [copied, setCopied]           = useState(false)
  const [loadingLatest, setLoadingLatest] = useState(false)
  const [settings, setSettings]           = useState(null)
  const [landingUrl, setLandingUrl]       = useState('')
  const [landingBusy, setLandingBusy]     = useState(false)
  const [landingCopied, setLandingCopied] = useState(false)
  const [emailModal, setEmailModal]       = useState(false)
  const [emailTo, setEmailTo]             = useState('')
  const [emailHtml, setEmailHtml]         = useState('')
  const [emailSending, setEmailSending]   = useState(false)
  const [emailError, setEmailError]       = useState('')

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

  function copyLink() {
    if (!packageUrl) return
    navigator.clipboard.writeText(packageUrl)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  async function openEmailModal() {
    setEmailError('')
    setEmailHtml('')
    setEmailTo(offerData?.project?.customerEmail || '')
    setEmailModal(true)
    try {
      const res = await fetch(`${BASE}/email/preview`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          project:      offerData?.project || {},
          download_url: packageUrl || ''
        })
      })
      if (!res.ok) throw new Error('Vorschau-Fehler ' + res.status)
      const html = await res.text()
      setEmailHtml(html)
    } catch (e) {
      setEmailError('Vorschau konnte nicht geladen werden: ' + e.message)
    }
  }

  async function sendEmail() {
    if (!emailTo.trim()) { setEmailError('Bitte E-Mail-Adresse eingeben'); return }
    setEmailSending(true); setEmailError('')
    try {
      const res = await fetch(`${BASE}/email/send`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          to:           emailTo.trim(),
          project:      offerData?.project || {},
          download_url: packageUrl || ''
        })
      })
      if (!res.ok) {
        const err = await res.json().catch(() => ({}))
        throw new Error(err.detail || `Fehler ${res.status}`)
      }
      setEmailModal(false)
      showToast('✅ E-Mail gesendet!')
    } catch (e) {
      setEmailError('Fehler: ' + e.message)
    } finally {
      setEmailSending(false)
    }
  }

  async function newVersionSameCustomer() {
    try {
      const baseNo = offerNo.trim()
      if (!baseNo) { showToast('Bitte zuerst ein Angebot laden'); return }

      const res  = await fetch(`${BASE}/offers/next-version`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ offer_no: baseNo })
      })
      const data = await res.json()
      if (!res.ok || !data.offer_no) {
        showToast('Fehler: ' + (data.detail || 'Versionsnummer konnte nicht ermittelt werden'))
        return
      }
      showToast(`Neue Version: ${data.offer_no}`)
      sessionStorage.setItem('messe_prefill', JSON.stringify({
        mode:    'revision',
        offerNo: data.offer_no,
        contact: {
          company:     project.customer      || '',
          contactName: project.contact       || '',
          email:       project.customerEmail || '',
        },
        itemIds: (offerData.offer_items || []).map(i => i.option_id).filter(Boolean),
      }))
      setTimeout(() => navigate('/messe'), 1200)
    } catch(e) { showToast('Fehler: ' + e.message) }
  }

  function newOfferSameConfig() {
    sessionStorage.setItem('messe_prefill', JSON.stringify({
      mode:    'template',
      itemIds: (offerData.offer_items || []).map(i => i.option_id).filter(Boolean),
    }))
    navigate('/messe')
  }

  async function doLoad(no) {
    const num = (no || offerNo || '').trim()
    if (!num) return
    setLoading(true); setError(''); setOfferData(null); setPdfUrl(''); setPackageUrl(''); setLandingUrl('')
    try {
      const data = await offers.getByNumber(num)
      setOfferData(data)
      // PDF-URL und Package-URL aus DB direkt setzen
      if (data.pdf_url) {
        // Wenn absolute URL (Supabase) → direkt verwenden, sonst Backend-Prefix
        const url = data.pdf_url.startsWith('http')
          ? data.pdf_url
          : (import.meta.env.VITE_API_URL || '') + data.pdf_url
        setPdfUrl(url)
      }
      if (data.zip_url) {
        setPackageUrl(data.zip_url)
      }
      if (data.landing_url) {
        setLandingUrl(data.landing_url)
      } else {
        setLandingUrl('')
      }
    } catch(e) {
      setError(`Angebot „${num}" nicht gefunden`)
    } finally {
      setLoading(false)
    }
  }

  async function generateLanding() {
    if (!offerData || landingBusy) return
    setLandingBusy(true)
    try {
      const res = await fetch(`${BASE}/offers/${encodeURIComponent(offerData.offer_no)}/landing`, { method: 'POST' })
      const data = await res.json()
      if (!res.ok) throw new Error(data.detail || `Fehler ${res.status}`)
      setLandingUrl(data.landing_url)
      navigator.clipboard.writeText(data.landing_url).catch(() => {})
      setLandingCopied(true)
      setTimeout(() => setLandingCopied(false), 3000)
      showToast('Landing Page erstellt ✓')
    } catch(e) {
      showToast('Fehler: ' + e.message)
    } finally {
      setLandingBusy(false)
    }
  }

  function copyLandingUrl() {
    if (!landingUrl) return
    navigator.clipboard.writeText(landingUrl)
    setLandingCopied(true)
    setTimeout(() => setLandingCopied(false), 2000)
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
        const pUrl = result.download_url.startsWith('http')
          ? result.download_url
          : (import.meta.env.VITE_API_URL || '') + result.download_url
        setPdfUrl(pUrl)
        if (result.package_url) setPackageUrl(result.package_url)
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
  const oneTime      = items.filter(i => !i.recurring && !i.optional).reduce((s,i) => s+(i.original_price||i.price||0), 0)
  const monthly      = items.filter(i =>  i.recurring && !i.optional).reduce((s,i) => s+(i.original_price||i.price||0), 0)
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
            placeholder="Nummer eingeben + Enter"
            style={{ flex: 1, border: '1px solid var(--line)', borderRadius: 10,
              padding: '10px 14px', fontSize: 14, fontFamily: 'var(--font-mono)' }}
          />
          <button className="btn" onClick={loadLatest} disabled={loadingLatest || loading}>
            {loadingLatest ? '⏳' : '⭐ Neuestes'}
          </button>
        </div>
        {loading && <p style={{ color: 'var(--muted)', fontSize: 13, marginTop: 8 }}>⏳ Wird geladen …</p>}
        {error   && <p style={{ color: 'var(--red)',   fontSize: 13, marginTop: 8 }}>⚠ {error}</p>}

        {offerData && (
          <div style={{ display: 'flex', gap: 10, marginTop: 12, paddingTop: 12, borderTop: '1px solid var(--line)' }}>
            <button className="btn" style={{ flex: 1, justifyContent: 'center', fontSize: 13 }}
              onClick={newVersionSameCustomer}>
              🔄 Neue Version – gleicher Kunde
            </button>
            <button className="btn" style={{ flex: 1, justifyContent: 'center', fontSize: 13 }}
              onClick={newOfferSameConfig}>
              📋 Vorlage – neuer Kunde
            </button>
          </div>
        )}
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
                  {item.optional
                    ? <span style={{ color: 'var(--muted)' }}>
                        optional ({money(item.original_price || item.price)}{item.recurring ? '/Mo.' : ''})
                      </span>
                    : (item.original_price||item.price||0) === 0
                      ? 'inkl.'
                      : item.recurring
                        ? money(item.original_price||item.price)+'/Mo.'
                        : money(item.original_price||item.price)
                  }
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
            <div className="card-title">Aktionen</div>

            {!pdfUrl ? (
              <button className="btn btn-red btn-lg" onClick={generatePdf} disabled={generating}
                style={{ width: '100%', justifyContent: 'center' }}>
                {generating ? '⏳ PDF wird erstellt …' : '📄 PDF erstellen'}
              </button>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>

                {/* Primär: PDF öffnen */}
                <a href={pdfUrl} target="_blank" rel="noopener noreferrer"
                  className="btn btn-red btn-lg" style={{ textDecoration: 'none', justifyContent: 'center' }}>
                  📄 PDF öffnen
                </a>

                {/* 3×2 Grid: sekundäre Aktionen */}
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 10 }}>

                  <a href={packageUrl || '#'} target="_blank" rel="noopener noreferrer"
                    className="btn" style={{ textDecoration: 'none', justifyContent: 'center',
                      flexDirection: 'column', gap: 4, padding: '14px 10px', opacity: packageUrl ? 1 : .4 }}>
                    <span style={{ fontSize: 20 }}>📦</span>
                    <span style={{ fontSize: 12 }}>ZIP laden</span>
                  </a>

                  <div style={{ position: 'relative' }}>
                    <div className="btn" style={{ flexDirection: 'column', gap: 4, padding: '14px 10px',
                      justifyContent: 'center', opacity: .35, pointerEvents: 'none',
                      cursor: 'default', width: '100%', boxSizing: 'border-box' }}>
                      <span style={{ fontSize: 20 }}>✉️</span>
                      <span style={{ fontSize: 12 }}>E-Mail senden</span>
                    </div>
                    <span style={{
                      position: 'absolute', top: 6, right: 8,
                      fontSize: 9, fontWeight: 700, letterSpacing: '.5px',
                      color: 'var(--muted)', textTransform: 'uppercase',
                    }}>Coming soon</span>
                  </div>

                  <button className="btn" onClick={copyLink}
                    style={{ flexDirection: 'column', gap: 4, padding: '14px 10px',
                      justifyContent: 'center', opacity: packageUrl ? 1 : .4 }}>
                    <span style={{ fontSize: 20 }}>{copied ? '✅' : '📋'}</span>
                    <span style={{ fontSize: 12 }}>{copied ? 'Kopiert!' : 'Link kopieren'}</span>
                  </button>

                  <button className="btn" onClick={() => setQrVisible(v => !v)}
                    style={{ flexDirection: 'column', gap: 4, padding: '14px 10px',
                      justifyContent: 'center', opacity: packageUrl ? 1 : .4,
                      background: qrVisible ? 'var(--red-light)' : undefined,
                      border: qrVisible ? '1px solid var(--red)' : undefined }}>
                    <span style={{ fontSize: 20 }}>🔳</span>
                    <span style={{ fontSize: 12 }}>QR-Code</span>
                  </button>

                  {/* Landing Page – nur für aktive Angebote */}
                  {offerData?.status === 'active' && (
                    landingUrl ? (
                      <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                        <a href={landingUrl} target="_blank" rel="noopener noreferrer"
                          className="btn" style={{ textDecoration: 'none', justifyContent: 'center',
                            flexDirection: 'column', gap: 4, padding: '14px 10px',
                            background: 'var(--red-light)', border: '1px solid var(--red)' }}>
                          <span style={{ fontSize: 20 }}>🌐</span>
                          <span style={{ fontSize: 12, color: 'var(--red)' }}>Landing Page</span>
                        </a>
                        <button className="btn" onClick={copyLandingUrl}
                          style={{ fontSize: 11, padding: '6px', justifyContent: 'center' }}>
                          {landingCopied ? '✅ Link kopiert' : '📋 Link kopieren'}
                        </button>
                      </div>
                    ) : (
                      <button className="btn" onClick={generateLanding} disabled={landingBusy}
                        style={{ flexDirection: 'column', gap: 4, padding: '14px 10px', justifyContent: 'center' }}>
                        <span style={{ fontSize: 20 }}>{landingBusy ? '⏳' : '🌐'}</span>
                        <span style={{ fontSize: 12 }}>{landingBusy ? 'Wird erstellt…' : 'Landing Page'}</span>
                      </button>
                    )
                  )}

                </div>

                {/* QR-Code Bild */}
                {qrVisible && packageUrl && (
                  <div style={{ textAlign: 'center', padding: 16, background: 'var(--bg)',
                    borderRadius: 12, border: '1px solid var(--line)' }}>
                    <img
                      src={`https://api.qrserver.com/v1/create-qr-code/?size=200x200&data=${encodeURIComponent(packageUrl)}`}
                      alt="QR-Code" style={{ width: 180, height: 180, borderRadius: 8 }}
                    />
                    <p style={{ fontSize: 11, color: 'var(--muted)', marginTop: 8 }}>
                      Gültig 30 Tage · Alle Dokumente als ZIP
                    </p>
                    <a href={`https://api.qrserver.com/v1/create-qr-code/?size=400x400&data=${encodeURIComponent(packageUrl)}`}
                      download="QR-Code.png" target="_blank" rel="noopener noreferrer"
                      className="btn" style={{ textDecoration: 'none', marginTop: 8, fontSize: 12 }}>
                      ⬇️ QR-Code herunterladen
                    </a>
                  </div>
                )}

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

      {/* ── E-Mail Modal ─────────────────────────────────────────────────────── */}
      {emailModal && (
        <div style={{
          position: 'fixed', inset: 0, background: 'rgba(0,0,0,.55)',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          zIndex: 9999, padding: 16
        }}>
          <div style={{
            background: '#fff', borderRadius: 16, width: '100%', maxWidth: 680,
            maxHeight: '92vh', display: 'flex', flexDirection: 'column',
            boxShadow: '0 12px 48px rgba(0,0,0,.25)'
          }}>

            {/* Titelzeile */}
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between',
              padding: '16px 20px', borderBottom: '1px solid var(--line)', flexShrink: 0 }}>
              <h3 style={{ margin: 0, fontSize: 16 }}>✉️ E-Mail Vorschau &amp; Senden</h3>
              <button onClick={() => setEmailModal(false)}
                style={{ border: 'none', background: 'none', cursor: 'pointer',
                  fontSize: 20, color: 'var(--muted)', lineHeight: 1 }}>✕</button>
            </div>

            {/* Empfänger */}
            <div style={{ padding: '12px 20px', borderBottom: '1px solid var(--line)', flexShrink: 0 }}>
              <label style={{ fontSize: 12, color: 'var(--muted)', display: 'block', marginBottom: 4 }}>
                Empfänger
              </label>
              <input
                type="email" value={emailTo}
                onChange={e => setEmailTo(e.target.value)}
                placeholder="kunde@firma.com"
                style={{ width: '100%', border: '1px solid var(--line)', borderRadius: 8,
                  padding: '9px 12px', fontSize: 14, boxSizing: 'border-box' }}
              />
            </div>

            {/* Vorschau-Bereich */}
            <div style={{ flex: 1, overflow: 'hidden', padding: '12px 20px', minHeight: 0 }}>
              {!emailHtml && !emailError && (
                <div style={{ textAlign: 'center', padding: '48px 0', color: 'var(--muted)', fontSize: 13 }}>
                  ⏳ Vorschau wird geladen …
                </div>
              )}
              {emailError && (
                <div style={{ color: 'var(--red)', fontSize: 13, padding: '8px 0' }}>⚠ {emailError}</div>
              )}
              {emailHtml && (
                <iframe
                  srcDoc={emailHtml}
                  title="E-Mail Vorschau"
                  style={{ width: '100%', height: '100%', minHeight: 360, border: '1px solid var(--line)',
                    borderRadius: 8, background: '#fff', display: 'block' }}
                  sandbox="allow-same-origin"
                />
              )}
            </div>

            {/* Buttons */}
            <div style={{ padding: '12px 20px', borderTop: '1px solid var(--line)',
              display: 'flex', gap: 10, justifyContent: 'flex-end', flexShrink: 0 }}>
              <button className="btn btn-lg" onClick={() => setEmailModal(false)}
                style={{ minWidth: 110 }}>
                Abbrechen
              </button>
              <button className="btn btn-red btn-lg" onClick={sendEmail}
                disabled={emailSending || !emailHtml}
                style={{ minWidth: 160 }}>
                {emailSending ? '⏳ Wird gesendet …' : '📤 E-Mail senden'}
              </button>
            </div>

          </div>
        </div>
      )}

    </div>
  )
}
