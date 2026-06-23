import { useState, useEffect, useRef } from 'react'
import { useNavigate } from 'react-router-dom'

const BASE = (import.meta.env.VITE_API_URL || '') + '/api'
import { customers as customersApi, options as optionsApi, offers as offersApi } from '../lib/api'

const STEPS = ['Kontakt', 'Optionen', 'Fertigstellen']

function money(n) {
  return new Intl.NumberFormat('de-AT', { style: 'currency', currency: 'EUR' }).format(n || 0)
}

export default function Messe() {
  const [step, setStep]               = useState(0)
  const [contact, setContact]         = useState({ company: '', contactName: '', email: '', position: '', phone: '', mobile: '', street: '', zip: '', city: '', website: '' })
  const [scanning, setScanning]       = useState(false)
  const [cardImageFile, setCardImageFile] = useState(null)
  const [logoUrl, setLogoUrl]         = useState('')
  const [logoFallback, setLogoFallback] = useState('')
  const [useLogo, setUseLogo]         = useState(false)
  const [suggestions, setSuggestions] = useState([])
  const [allOptions, setAllOptions]   = useState([])
  const [selectedIds, setSelectedIds] = useState(new Set())
  const [projectName, setProjectName]   = useState('')
  const [optionalIds, setOptionalIds]   = useState(new Set())  // Optionen die als optional markiert sind
  const [offerNo, setOfferNo]         = useState('')
  const revisionNoRef                 = useRef('')   // Versionsnummer – Ref statt State wegen Closure
  const deliveryTimerRef              = useRef(null)
  const [deliveryEnabled, setDeliveryEnabled]         = useState(false)
  const [deliveryQuery, setDeliveryQuery]             = useState('')
  const [deliverySuggestions, setDeliverySuggestions] = useState([])
  const [deliveryAddress, setDeliveryAddress]         = useState('')
  const [deliveryLoading, setDeliveryLoading]         = useState(false)
  const [busy, setBusy]               = useState(false)
  const [done, setDone]               = useState(false)
  const [result, setResult]           = useState(null)  // Angebotsergebnis
  const [previewing, setPreviewing]   = useState(false)
  const navigate                      = useNavigate()
  const [error, setError]             = useState('')
  const [allCustomers, setAllCustomers] = useState([])
  const [customPrices, setCustomPrices] = useState({})  // option_id → angepasster Preis
  const [customNotes, setCustomNotes]   = useState({})  // option_id → Freitext-Notiz
  const [leasingEnabled, setLeasingEnabled] = useState(false)
  const [leasingKaufpreis, setLeasingKaufpreis] = useState(0)
  const [leasingSettings, setLeasingSettings] = useState(null)
  const [selectedPaymentTerm, setSelectedPaymentTerm] = useState('')
  const [discountPercent, setDiscountPercent]         = useState(0)
  const [selectedVatCountry, setSelectedVatCountry]   = useState(null)
  const [dupModal, setDupModal]                       = useState(null)
  const [newModal, setNewModal]                       = useState(false)
  const [newCustomerSource, setNewCustomerSource]     = useState('')
  const [allOffers, setAllOffers]                     = useState([])

  useEffect(() => {
    optionsApi.list().then(opts => {
      setAllOptions(opts)
      // sessionStorage Vorausfüllung (aus PDF-Vorschau)
      const raw = sessionStorage.getItem('messe_prefill')
      if (raw) {
        sessionStorage.removeItem('messe_prefill')
        try {
          const pre = JSON.parse(raw)
          if (pre.contact) setContact(p => ({ ...p, ...pre.contact }))
          if (pre.offerNo) { setOfferNo(pre.offerNo); revisionNoRef.current = pre.offerNo }
          if (pre.itemIds?.length) setSelectedIds(new Set(pre.itemIds))
        } catch {}
      }
    }).catch(console.warn)
    customersApi.list().then(setAllCustomers).catch(console.warn)
    fetch(`${BASE}/offers`).then(r => r.json()).then(setAllOffers).catch(console.warn)
    fetch((import.meta.env.VITE_API_URL || '') + '/api/settings')
      .then(r => r.json()).then(data => {
        setLeasingSettings(data)
        const active = (data.payment_terms || []).filter(t => t.active)
        if (active.length === 1) setSelectedPaymentTerm(active[0].label)
      }).catch(console.warn)
  }, [])

  // Live-Suche in Kunden
  useEffect(() => {
    if (contact.company.length < 2) { setSuggestions([]); return }
    const q = contact.company.toLowerCase()
    setSuggestions(allCustomers.filter(c => c.company.toLowerCase().includes(q)).slice(0, 4))
  }, [contact.company, allCustomers])

  function fillContact(c) {
    setContact(p => ({ ...p, company: c.company, contactName: c.contact || '', email: c.email || '' }))
    setSuggestions([])
  }

  const FREE_MAIL_DOMAINS = new Set([
    'gmail.com','googlemail.com','outlook.com','hotmail.com','hotmail.de',
    'live.com','live.de','msn.com','yahoo.com','yahoo.de','yahoo.at',
    'gmx.de','gmx.at','gmx.net','gmx.ch','web.de','t-online.de',
    'icloud.com','me.com','mac.com','aol.com','protonmail.com',
    'pm.me','tutanota.com','mailbox.org',
  ])

  function extractDomain(website) {
    if (!website) return ''
    return website.replace(/^https?:\/\//, '').replace(/^www\./, '').split('/')[0]
  }

  function emailDomain(email) {
    if (!email) return ''
    const d = email.split('@')[1] || ''
    return FREE_MAIL_DOMAINS.has(d.toLowerCase()) ? '' : d
  }

  async function scanCard(file) {
    if (!file) return
    setScanning(true)
    setCardImageFile(file)
    setLogoUrl(''); setLogoFallback(''); setUseLogo(false); setError('')
    try {
      const fd = new FormData()
      fd.append('file', file)
      const res  = await fetch(`${BASE}/scan/business-card`, { method: 'POST', body: fd })
      const data = await res.json()
      if (!res.ok) throw new Error(data.detail || 'Fehler beim Scannen')
      const d = data.data || {}
      setContact(p => ({
        company:     d.company     || p.company,
        contactName: d.contactName || p.contactName,
        email:       d.email       || p.email,
        position:    d.position    || p.position,
        phone:       d.phone       || p.phone,
        mobile:      d.mobile      || p.mobile,
        street:      d.street      || p.street,
        zip:         d.zip         || p.zip,
        city:        d.city        || p.city,
        website:     d.website     || p.website,
      }))
      // Logo suchen – Website-Domain, sonst Firmen-E-Mail-Domain (keine Freemailer)
      const domain = extractDomain(d.website || '') || emailDomain(d.email || '')
      if (domain) {
        setLogoUrl(`https://logo.clearbit.com/${domain}`)
        setLogoFallback(`https://www.google.com/s2/favicons?domain=${domain}&sz=256`)
      } else {
        setLogoUrl('__no_domain__')
        setLogoFallback('')
      }
    } catch(e) {
      setError('Scan fehlgeschlagen: ' + e.message)
    } finally {
      setScanning(false)
    }
  }

  function toggleOption(id) {
    setSelectedIds(prev => {
      const next = new Set(prev)
      next.has(id) ? next.delete(id) : next.add(id)
      return next
    })
  }

  async function doSaveAndProceed(source = '') {
    let cardImageUrl = ''
    if (cardImageFile) {
      try {
        const fd = new FormData()
        fd.append('file', cardImageFile)
        const r = await fetch(`${BASE}/upload/card-image`, { method: 'POST', body: fd })
        if (r.ok) cardImageUrl = (await r.json()).url || ''
      } catch { /* nicht kritisch */ }
    }
    try {
      await customersApi.upsert({
        company:        contact.company,
        contact:        contact.contactName,
        email:          contact.email,
        position:       contact.position,
        phone:          contact.phone,
        mobile:         contact.mobile,
        street:         contact.street,
        zip:            contact.zip,
        city:           contact.city,
        website:        contact.website,
        card_image_url: cardImageUrl,
        logo_url:       (logoUrl && !logoUrl.startsWith('__')) ? logoUrl : '',
        source:         source || '',
      })
    } catch { /* nicht kritisch */ }
    setStep(1)
  }

  async function useExistingCustomer(c) {
    // Eingetippte Daten gewinnen – Stammdaten füllen nur leere Felder auf
    const merged = {
      company:     contact.company.trim()      || c.company   || '',
      contactName: contact.contactName.trim()  || c.contact   || '',
      email:       contact.email.trim()        || c.email     || '',
      position:    contact.position.trim()     || c.position  || '',
      phone:       contact.phone.trim()        || c.phone     || '',
      mobile:      contact.mobile.trim()       || c.mobile    || '',
      street:      contact.street.trim()       || c.street    || '',
      zip:         contact.zip.trim()          || c.zip       || '',
      city:        contact.city.trim()         || c.city      || '',
      website:     contact.website.trim()      || c.website   || '',
    }
    setContact(merged)
    // Kunden mit zusammengeführten Daten + ID aktualisieren (bekommt Nummer falls noch keine)
    try {
      await customersApi.upsert({
        id:              c.id,
        customer_number: c.customer_number || '',
        company:         merged.company,
        contact:         merged.contactName,
        email:           merged.email,
        position:        merged.position,
        phone:           merged.phone,
        mobile:          merged.mobile,
        street:          merged.street,
        zip:             merged.zip,
        city:            merged.city,
        website:         merged.website,
        logo_url:        (logoUrl && !logoUrl.startsWith('__')) ? logoUrl : (c.logo_url || ''),
      })
    } catch { /* nicht kritisch */ }
    setDupModal(null)
    setStep(1)
  }

  function offersFor(company) {
    return allOffers.filter(o => (o.project?.customer || '') === company)
  }

  function fmtDate(iso) {
    if (!iso) return ''
    return new Date(iso).toLocaleDateString('de-AT', { day: '2-digit', month: '2-digit', year: 'numeric' })
  }

  function getContactDiffs(c) {
    return [
      { label: 'Ansprechpartner', userVal: contact.contactName, storedVal: c.contact  },
      { label: 'Position',        userVal: contact.position,    storedVal: c.position },
      { label: 'E-Mail',          userVal: contact.email,       storedVal: c.email    },
      { label: 'Telefon',         userVal: contact.phone,       storedVal: c.phone    },
      { label: 'Mobil',           userVal: contact.mobile,      storedVal: c.mobile   },
      { label: 'Straße',          userVal: contact.street,      storedVal: c.street   },
      { label: 'PLZ',             userVal: contact.zip,         storedVal: c.zip      },
      { label: 'Ort',             userVal: contact.city,        storedVal: c.city     },
      { label: 'Website',         userVal: contact.website,     storedVal: c.website  },
    ].filter(f => {
      const u = (f.userVal || '').trim()
      const s = (f.storedVal || '').trim()
      return u && u !== s
    }).map(f => ({
      label:    f.label,
      userVal:  (f.userVal || '').trim(),
      storedVal:(f.storedVal || '').trim(),
      isNew:    !(f.storedVal || '').trim(),
    }))
  }

  async function goToOptions() {
    if (!contact.company.trim()) { setError('Firma ist erforderlich'); return }
    if (!contact.email.trim() || !contact.email.includes('@')) { setError('Bitte gültige E-Mail angeben'); return }
    setError('')

    // Ähnliche Kunden suchen
    try {
      const res = await fetch(`${BASE}/customers/search?q=${encodeURIComponent(contact.company.trim())}`)
      const matches = await res.json()
      if (matches.length > 0) {
        setDupModal({ matches, onNew: doSaveAndProceed })
        return
      }
    } catch { /* Suche fehlgeschlagen – trotzdem weitermachen */ }
    // Kein Treffer → Bestätigungs-Modal für neuen Kunden
    setNewModal(true)
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

  function onDeliveryInput(val) {
    setDeliveryQuery(val)
    setDeliveryAddress('')
    if (deliveryTimerRef.current) clearTimeout(deliveryTimerRef.current)
    if (val.length < 3) { setDeliverySuggestions([]); return }
    deliveryTimerRef.current = setTimeout(async () => {
      setDeliveryLoading(true)
      try {
        const res = await fetch(`https://photon.komoot.io/api/?q=${encodeURIComponent(val)}&lang=de&limit=6&countrycode=at`)
        const data = await res.json()
        setDeliverySuggestions(data.features || [])
      } catch {}
      setDeliveryLoading(false)
    }, 350)
  }

  function selectDelivery(feature) {
    const p = feature.properties
    const street = [p.street, p.housenumber].filter(Boolean).join(' ')
    const parts  = [street || p.name, p.postcode, p.city || p.town || p.village].filter(Boolean)
    const addr   = parts.join(', ')
    setDeliveryAddress(addr)
    setDeliveryQuery(addr)
    setDeliverySuggestions([])
  }

  async function finalize() {
    if (busy) return
    setBusy(true); setError('')
    try {
      const rawItems = allOptions.filter(o => selectedIds.has(o.id))
      const effectiveLogo = useLogo
        ? (logoUrl && !logoUrl.startsWith('__') ? logoUrl
           : logoFallback && !logoFallback.startsWith('__') ? logoFallback : '')
        : ''
      const discountActive = leasingSettings?.discount_enabled && discountPercent > 0
      const proj  = {
        customer:           contact.company,
        contact:            contact.contactName,
        customerEmail:      contact.email,
        project:            projectName,
        date:               new Date().toLocaleDateString('de-AT'),
        valid:              new Date(Date.now() + 28*864e5).toLocaleDateString('de-AT'),
        payment_term:       selectedPaymentTerm || undefined,
        customer_position:  contact.position  || undefined,
        customer_phone:     contact.phone     || undefined,
        customer_mobile:    contact.mobile    || undefined,
        customer_street:    contact.street    || undefined,
        customer_zip:       contact.zip       || undefined,
        customer_city:      contact.city      || undefined,
        customer_website:   contact.website   || undefined,
        customer_logo:      effectiveLogo     || undefined,
        delivery_address:   deliveryEnabled && deliveryAddress ? deliveryAddress : undefined,
        discount_percent:   discountActive ? discountPercent : undefined,
        vat_country:        selectedVatCountry?.country || undefined,
        vat_rate:           selectedVatCountry?.rate ?? undefined,
      }
      // offer_items mit optional-Flag und korrekten Preisen
      const offer_items = rawItems.map(o => {
        const base   = customPrices[o.id] !== undefined ? Number(customPrices[o.id]) : (o.price || 0)
        const isOpt  = optionalIds.has(o.id)
        const applyDiscount = discountActive && o.discountable && !isOpt
        const discounted = applyDiscount ? Math.round(base * (1 - discountPercent / 100) * 100) / 100 : base
        return {
          option_id:      o.id,
          name:           o.name,
          cluster:        o.cluster      || '',
          short_text:     customNotes[o.id] ? `${o.short_text || ''}\n${customNotes[o.id]}`.trim() : (o.short_text || ''),
          long_text:      o.long_text    || '',
          original_price: base,
          price:          isOpt ? 0 : discounted,
          optional:       isOpt,
          recurring:      o.recurring    || false,
          image_path:     o.image_path   || '',
          display_type:   o.display_type || '',
          documents:      o.documents    || [],
          discountable:   o.discountable || false,
          discount_pct:   applyDiscount ? discountPercent : 0,
          qty:            1,
        }
      })
      const leasingPayload = leasingEnabled ? {
        enabled: true, kaufpreis: oneTime, durations: LEASING_DURATIONS,
      } : { enabled: false }

      const res  = await fetch(`${BASE}/offers/generate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ project: proj, offer_items, provider: {}, attachments: [], leasing: leasingPayload, offer_no: revisionNoRef.current || undefined })
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
    setStep(0); setContact({ company: '', contactName: '', email: '', position: '', phone: '', mobile: '', street: '', zip: '', city: '', website: '' })
    setCardImageFile(null); revisionNoRef.current = ''
    setLogoUrl(''); setLogoFallback(''); setUseLogo(false)
    setSelectedIds(new Set()); setProjectName(''); setOfferNo('')
    setDone(false); setError(''); setCustomPrices({}); setSelectedPaymentTerm('')
    setDeliveryEnabled(false); setDeliveryQuery(''); setDeliveryAddress(''); setDeliverySuggestions([])
    setDiscountPercent(0); setSelectedVatCountry(null); setDupModal(null); setNewModal(false); setNewCustomerSource('')
  }

  // ── Cluster-Gruppen ────────────────────────────────────────────────────────
  const visibleOptions = allOptions.filter(o => o.active !== false)

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
  const LEASING_DEFAULT_FACTORS = {
    36: { '10000': 3.2,  '20000': 3.2,  '30000': 3.2,  '50000': 3.2,  '999999': 3.2  },
    48: { '10000': 2.41, '20000': 2.41, '30000': 2.41, '50000': 2.41, '999999': 2.41 },
    60: { '10000': 2.0,  '20000': 2.0,  '30000': 2.0,  '50000': 2.0,  '999999': 2.0  },
  }
  function calcLeasing(kaufpreis) {
    const s     = leasingSettings || {}
    const facs  = (s.leasing_factors && Object.keys(s.leasing_factors).length > 0)
                    ? s.leasing_factors : LEASING_DEFAULT_FACTORS
    const fee   = parseFloat(s.leasing_processing_fee || 100)
    const vat   = parseFloat(s.leasing_vat || 20) / 100
    const brks  = [10000, 20000, 30000, 50000, 999999]
    const brk   = (brks.find(b => kaufpreis <= b) || 999999).toString()
    return LEASING_DURATIONS.map(dur => {
      const factor  = parseFloat(((facs[dur] || facs[String(dur)]) || {})[brk] || 0)
      const monthly = Math.round(kaufpreis * factor / 100 * 100) / 100
      const legal   = Math.round((36 * monthly * (1 + vat) + fee * (1 + vat)) * 0.01 * 100) / 100
      return { dur, monthly, fee, legal }
    })
  }
  const leasingRows = calcLeasing(oneTime)

  // Nach Generieren direkt zur PDF-Vorschau
  if (done && result?.offer_no) {
    navigate(`/vorschau?no=${encodeURIComponent(result.offer_no)}`)
    return null
  }

  return (
    <div style={{ maxWidth: 720, margin: '0 auto' }}>

      {/* ── Duplikat-Modal ──────────────────────────────────────────────────── */}
      {dupModal && (
        <div onClick={() => setDupModal(null)} style={{
          position: 'fixed', inset: 0, background: 'rgba(0,0,0,.5)',
          zIndex: 999, display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 24,
        }}>
          <div onClick={e => e.stopPropagation()} style={{
            background: 'white', borderRadius: 20, width: '100%', maxWidth: 520,
            maxHeight: '85vh', display: 'flex', flexDirection: 'column',
            boxShadow: '0 8px 40px rgba(0,0,0,.2)',
          }}>
            <div style={{ padding: '22px 24px 16px', borderBottom: '1px solid var(--line)' }}>
              <div style={{ fontWeight: 800, fontSize: 17, color: 'var(--dark)', marginBottom: 4 }}>
                🔍 Kunde bereits bekannt?
              </div>
              <div style={{ fontSize: 13, color: 'var(--muted)' }}>
                Wir haben ähnliche Einträge gefunden. Bitte prüfen und entscheiden.
              </div>
            </div>

            <div style={{ overflowY: 'auto', flex: 1 }}>
              {dupModal.matches.map(c => {
                const diffs = getContactDiffs(c)
                return (
                  <div key={c.id} style={{ padding: '16px 24px', borderBottom: '1px solid var(--line)' }}>
                    {/* Kopfzeile */}
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: 12, marginBottom: 10 }}>
                      <div>
                        <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
                          <b style={{ fontSize: 15, color: 'var(--dark)' }}>{c.company}</b>
                          {c.customer_number
                            ? <span style={{ fontSize: 10, fontWeight: 700, color: 'var(--red)',
                                background: '#fff1f2', border: '1px solid #fecdd3',
                                borderRadius: 6, padding: '1px 7px', fontFamily: 'var(--font-mono)' }}>
                                {c.customer_number}
                              </span>
                            : <span style={{ fontSize: 10, color: 'var(--muted)', fontStyle: 'italic' }}>
                                noch keine Kundennummer
                              </span>
                          }
                        </div>
                        {/* Gespeicherte Kerndaten */}
                        <div style={{ fontSize: 12, color: 'var(--muted)', marginTop: 4, lineHeight: 1.6 }}>
                          {[c.contact, c.position].filter(Boolean).join(' · ')}
                          {c.email && <><br />{c.email}</>}
                          {c.city  && <> · {c.zip ? `${c.zip} ` : ''}{c.city}</>}
                        </div>
                      </div>
                      <button onClick={() => useExistingCustomer(c)} className="btn btn-red"
                        style={{ fontSize: 12, padding: '7px 14px', whiteSpace: 'nowrap', flexShrink: 0 }}>
                        Diesen verwenden
                      </button>
                    </div>

                    {/* Diff-Anzeige */}
                    {diffs.length > 0 && (
                      <div style={{ background: '#f8faff', border: '1px solid #e0e7ff',
                        borderRadius: 10, padding: '10px 14px' }}>
                        <div style={{ fontSize: 10, fontWeight: 800, color: '#4f46e5',
                          textTransform: 'uppercase', letterSpacing: '.05em', marginBottom: 6 }}>
                          Neue Angaben von dir
                        </div>
                        {diffs.map((d, i) => (
                          <div key={i} style={{ display: 'flex', gap: 8, fontSize: 12,
                            marginBottom: i < diffs.length - 1 ? 5 : 0, alignItems: 'baseline' }}>
                            <span style={{ flexShrink: 0, fontWeight: 700,
                              color: d.isNew ? '#16a34a' : '#d97706' }}>
                              {d.isNew ? '➕' : '✏️'}
                            </span>
                            <span style={{ color: 'var(--muted)', minWidth: 110, flexShrink: 0 }}>
                              {d.label}:
                            </span>
                            <span style={{ fontWeight: 700,
                              color: d.isNew ? '#16a34a' : '#d97706' }}>
                              {d.userVal}
                            </span>
                            {!d.isNew && (
                              <span style={{ fontSize: 11, color: 'var(--muted)' }}>
                                (war: {d.storedVal})
                              </span>
                            )}
                          </div>
                        ))}
                      </div>
                    )}
                    {diffs.length === 0 && (
                      <div style={{ fontSize: 11, color: 'var(--muted)', fontStyle: 'italic' }}>
                        Keine neuen Angaben gegenüber dem gespeicherten Eintrag.
                      </div>
                    )}

                    {/* Angebote */}
                    {(() => {
                      const co = offersFor(c.company)
                      if (co.length === 0) return (
                        <div style={{ fontSize: 11, color: 'var(--muted)', marginTop: 8, fontStyle: 'italic' }}>
                          Noch kein Angebot
                        </div>
                      )
                      return (
                        <div style={{ marginTop: 10, display: 'flex', flexDirection: 'column', gap: 3 }}>
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
                )
              })}
            </div>

            <div style={{ padding: '16px 24px', borderTop: '1px solid var(--line)',
              display: 'flex', gap: 10, flexDirection: 'column' }}>
              <button
                onClick={() => { setDupModal(null); dupModal.onNew() }}
                style={{ background: 'none', border: '1px solid var(--line)', borderRadius: 10,
                  padding: '10px 16px', fontSize: 13, fontWeight: 700, cursor: 'pointer',
                  color: 'var(--text)', width: '100%' }}>
                ➕ Keiner passt – als neuen Kunden anlegen
              </button>
              <button onClick={() => setDupModal(null)}
                style={{ background: 'none', border: 'none', fontSize: 12,
                  color: 'var(--muted)', cursor: 'pointer', padding: '4px' }}>
                Abbrechen
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ── Neuer Kunde Modal ───────────────────────────────────────────────── */}
      {newModal && (
        <div onClick={() => setNewModal(false)} style={{
          position: 'fixed', inset: 0, background: 'rgba(0,0,0,.5)',
          zIndex: 999, display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 24,
        }}>
          <div onClick={e => e.stopPropagation()} style={{
            background: 'white', borderRadius: 20, width: '100%', maxWidth: 440,
            boxShadow: '0 8px 40px rgba(0,0,0,.2)',
          }}>
            <div style={{ padding: '22px 24px 16px', borderBottom: '1px solid var(--line)' }}>
              <div style={{ fontWeight: 800, fontSize: 17, color: 'var(--dark)', marginBottom: 4 }}>
                ➕ Neuer Kunde wird angelegt
              </div>
              <div style={{ fontSize: 13, color: 'var(--muted)' }}>
                Kein bestehender Eintrag gefunden. Bitte prüfen und bestätigen.
              </div>
            </div>
            <div style={{ padding: '16px 24px' }}>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 6, marginBottom: 16 }}>
                {[
                  { label: 'Firma',           val: contact.company },
                  { label: 'Ansprechpartner', val: contact.contactName },
                  { label: 'E-Mail',          val: contact.email },
                  { label: 'Position',        val: contact.position },
                  { label: 'Telefon',         val: contact.phone },
                  { label: 'Mobil',           val: contact.mobile },
                  { label: 'Ort',             val: [contact.zip, contact.city].filter(Boolean).join(' ') },
                  { label: 'Website',         val: contact.website },
                ].filter(f => f.val?.trim()).map((f, i) => (
                  <div key={i} style={{ display: 'flex', gap: 8, fontSize: 13 }}>
                    <span style={{ color: 'var(--muted)', minWidth: 130, flexShrink: 0 }}>{f.label}:</span>
                    <span style={{ fontWeight: 600, color: 'var(--dark)' }}>{f.val}</span>
                  </div>
                ))}
              </div>
              <div style={{ borderTop: '1px solid var(--line)', paddingTop: 14 }}>
                <label style={{ fontSize: 12, fontWeight: 700, color: 'var(--muted)',
                  display: 'block', marginBottom: 6 }}>
                  Woher kenne ich diesen Kunden? (optional)
                </label>
                <input
                  value={newCustomerSource}
                  onChange={e => setNewCustomerSource(e.target.value)}
                  placeholder="z.B. Messe Wien 2026, Empfehlung, …"
                  list="source-vorschlaege"
                  style={{ width: '100%', boxSizing: 'border-box' }}
                />
                <datalist id="source-vorschlaege">
                  {(leasingSettings?.project_templates || []).map(t => (
                    <option key={t.id} value={t.label} />
                  ))}
                </datalist>
              </div>
            </div>
            <div style={{ padding: '0 24px 20px', display: 'flex', flexDirection: 'column', gap: 8 }}>
              <button className="btn btn-red btn-lg"
                onClick={() => { setNewModal(false); doSaveAndProceed(newCustomerSource) }}>
                ✓ Anlegen & weiter zu den Optionen
              </button>
              <button onClick={() => setNewModal(false)}
                style={{ background: 'none', border: 'none', fontSize: 12,
                  color: 'var(--muted)', cursor: 'pointer', padding: '4px' }}>
                Abbrechen – Daten korrigieren
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Header */}
      <div className="page-header">
        <div>
          <h1>🎯 Schnellerfassung</h1>
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
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
            <div className="card-title" style={{ marginBottom: 0 }}>Kontaktdaten</div>
            {/* Visitenkarten-Scan */}
            <label style={{
              display: 'flex', alignItems: 'center', gap: 7, cursor: 'pointer',
              background: scanning ? 'var(--bg)' : 'var(--dark)', color: scanning ? 'var(--muted)' : 'white',
              border: 'none', borderRadius: 10, padding: '8px 14px', fontSize: 13, fontWeight: 600,
              userSelect: 'none', transition: '.15s',
            }}>
              <input type="file" accept="image/*" capture="environment" style={{ display: 'none' }}
                onChange={e => scanCard(e.target.files[0])} disabled={scanning} />
              {scanning ? '⏳ Scannt …' : '📷 Visitenkarte scannen'}
            </label>
          </div>

          {/* Pflichtfelder */}
          <div style={{ fontSize: 10, fontWeight: 800, textTransform: 'uppercase', letterSpacing: '.06em',
            color: 'var(--red)', marginBottom: 8 }}>Pflichtfelder</div>

          <div className="field" style={{ position: 'relative' }}>
            <label style={{ color: 'var(--red)', fontWeight: 700 }}>Firma *</label>
            <input
              value={contact.company}
              onChange={e => setContact(p => ({ ...p, company: e.target.value }))}
              placeholder="Firmenname …"
              style={{ fontSize: 18, padding: '14px 16px', borderColor: 'var(--red)' }}
              autoFocus
            />
            {suggestions.length > 0 && (
              <div style={{ position: 'absolute', top: '100%', left: 0, right: 0, background: 'white',
                border: '1px solid var(--line)', borderRadius: 14, boxShadow: '0 8px 24px rgba(0,0,0,.1)', zIndex: 10, marginTop: 4 }}>
                {suggestions.map(c => (
                  <div key={c.id} onClick={() => fillContact(c)}
                    style={{ padding: '12px 16px', cursor: 'pointer', borderBottom: '1px solid var(--line)', fontSize: 14 }}
                    onMouseEnter={e => e.currentTarget.style.background = 'var(--red-light)'}
                    onMouseLeave={e => e.currentTarget.style.background = 'white'}>
                    <b>{c.company}</b>
                    <div className="small muted">{c.contact} · {c.email}</div>
                  </div>
                ))}
              </div>
            )}
          </div>

          <div className="grid2">
            <div className="field">
              <label style={{ color: 'var(--red)', fontWeight: 700 }}>Ansprechpartner *</label>
              <input value={contact.contactName} onChange={e => setContact(p => ({ ...p, contactName: e.target.value }))} placeholder="Vor- und Nachname" />
            </div>
            <div className="field">
              <label style={{ color: 'var(--red)', fontWeight: 700 }}>E-Mail *</label>
              <input type="email" value={contact.email} onChange={e => setContact(p => ({ ...p, email: e.target.value }))} placeholder="email@firma.com" />
            </div>
          </div>

          {/* Optionale Felder */}
          <div style={{ fontSize: 10, fontWeight: 800, textTransform: 'uppercase', letterSpacing: '.06em',
            color: 'var(--muted)', margin: '16px 0 8px' }}>Weitere Angaben (optional)</div>

          <div className="grid2">
            <div className="field">
              <label style={{ color: 'var(--muted)' }}>Position / Titel</label>
              <input value={contact.position} onChange={e => setContact(p => ({ ...p, position: e.target.value }))} placeholder="z.B. Geschäftsführer" />
            </div>
            <div className="field">
              <label style={{ color: 'var(--muted)' }}>Website</label>
              <input value={contact.website} onChange={e => setContact(p => ({ ...p, website: e.target.value }))} placeholder="www.firma.at" />
            </div>
            <div className="field">
              <label style={{ color: 'var(--muted)' }}>Telefon</label>
              <input value={contact.phone} onChange={e => setContact(p => ({ ...p, phone: e.target.value }))} placeholder="+43 1 234 5678" />
            </div>
            <div className="field">
              <label style={{ color: 'var(--muted)' }}>Mobil</label>
              <input value={contact.mobile} onChange={e => setContact(p => ({ ...p, mobile: e.target.value }))} placeholder="+43 664 ..." />
            </div>
          </div>

          {/* Logo-Vorschau nach Scan */}
          {logoUrl === '__no_domain__' && (
            <div style={{ fontSize: 12, color: 'var(--muted)', marginBottom: 8 }}>
              Kein Logo gefunden – keine Website oder E-Mail erkannt.
            </div>
          )}
          {logoUrl && logoUrl !== '__no_domain__' && (
            <div style={{ display: 'flex', alignItems: 'center', gap: 14, padding: '12px 14px',
              background: useLogo ? '#f0fdf4' : 'var(--bg)', borderRadius: 12,
              border: `1px solid ${useLogo ? '#86efac' : 'var(--border)'}`, marginBottom: 8, transition: '.2s' }}>
              <img src={logoUrl} alt="Logo"
                style={{ height: 44, maxWidth: 120, objectFit: 'contain', borderRadius: 4 }}
                onError={() => {
                  if (logoFallback) { setLogoUrl(logoFallback); setLogoFallback('') }
                  else setLogoUrl('__not_found__')
                }} />
              <div style={{ flex: 1 }}>
                <div style={{ fontWeight: 700, fontSize: 13 }}>Firmenlogo gefunden</div>
                <div style={{ fontSize: 11, color: 'var(--muted)' }}>Soll dieses Logo im Angebot verwendet werden?</div>
              </div>
              <div onClick={() => setUseLogo(v => !v)}
                style={{ display: 'flex', alignItems: 'center', gap: 8, cursor: 'pointer', userSelect: 'none' }}>
                <div style={{ width: 40, height: 22, borderRadius: 11, background: useLogo ? '#22c55e' : '#ccc',
                  position: 'relative', transition: '.2s', flexShrink: 0 }}>
                  <div style={{ position: 'absolute', top: 2, left: useLogo ? 20 : 2,
                    width: 18, height: 18, borderRadius: '50%', background: 'white', transition: '.2s' }} />
                </div>
                <span style={{ fontSize: 12, fontWeight: 600, color: useLogo ? '#16a34a' : 'var(--muted)' }}>
                  {useLogo ? 'Ja, verwenden' : 'Nein'}
                </span>
              </div>
            </div>
          )}
          {logoUrl === '__not_found__' && (
            <div style={{ fontSize: 12, color: 'var(--muted)', marginBottom: 8 }}>
              Kein Logo in der Datenbank gefunden.
            </div>
          )}

          <div className="field">
            <label style={{ color: 'var(--muted)' }}>Straße / Adresse</label>
            <input value={contact.street} onChange={e => setContact(p => ({ ...p, street: e.target.value }))} placeholder="Musterstraße 1" />
          </div>
          <div className="grid2">
            <div className="field">
              <label style={{ color: 'var(--muted)' }}>PLZ</label>
              <input value={contact.zip} onChange={e => setContact(p => ({ ...p, zip: e.target.value }))} placeholder="1010" />
            </div>
            <div className="field">
              <label style={{ color: 'var(--muted)' }}>Ort</label>
              <input value={contact.city} onChange={e => setContact(p => ({ ...p, city: e.target.value }))} placeholder="Wien" />
            </div>
          </div>

          {error && <p style={{ color: 'var(--red)', fontSize: 13, marginBottom: 12 }}>⚠ {error}</p>}

          <button className="btn btn-red btn-lg" onClick={goToOptions}>
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
                      {(() => {
                        const applyDisc = leasingSettings?.discount_enabled && discountPercent > 0 && o.discountable && !isOptional
                        const discounted = applyDisc ? Math.round(displayPrice * (1 - discountPercent / 100) * 100) / 100 : null
                        return applyDisc ? (
                          <span style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: 1 }}>
                            <span style={{ fontSize: 10, color: 'var(--muted)', textDecoration: 'line-through' }}>
                              {o.recurring ? money(displayPrice)+'/Mo.' : money(displayPrice)}
                            </span>
                            <b style={{ color: 'var(--red)' }}>
                              {o.recurring ? money(discounted)+'/Mo.' : money(discounted)}
                            </b>
                          </span>
                        ) : (
                          <b style={{ color: isOptional ? 'var(--muted)' : 'var(--red)',
                            textDecoration: isOptional ? 'line-through' : 'none' }}>
                            {displayPrice === 0 ? 'inkl.' : o.recurring ? money(displayPrice)+'/Mo.' : money(displayPrice)}
                          </b>
                        )
                      })()}
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

                  {/* Notiz-Textfeld für price_editable Artikel */}
                  {o.price_editable && (
                    <div style={{ marginTop: 6 }}>
                      <input
                        value={customNotes[o.id] || ''}
                        onChange={e => setCustomNotes(p => ({ ...p, [o.id]: e.target.value }))}
                        placeholder="Anmerkung / Beschreibung zum Preis …"
                        style={{
                          width: '100%', border: '1px solid var(--line)', borderRadius: 8,
                          padding: '6px 12px', fontSize: 12, color: 'var(--text)',
                          boxSizing: 'border-box',
                        }}
                      />
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

          {/* ── Zahlungsziel ── */}
          {(() => {
            const active = (leasingSettings?.payment_terms || []).filter(t => t.active)
            if (active.length === 0) return null
            return (
              <div className="card" style={{ marginBottom: 16 }}>
                <div className="card-title" style={{ marginBottom: 12 }}>💳 Zahlungsziel</div>
                {active.length === 1 ? (
                  <p style={{ fontSize: 13, color: 'var(--muted)', margin: 0 }}>
                    Wird automatisch übernommen:&nbsp;
                    <b style={{ color: 'var(--dark)' }}>{active[0].label}</b>
                  </p>
                ) : (
                  <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                    {active.map(term => (
                      <label key={term.id} style={{ display: 'flex', alignItems: 'center',
                        gap: 10, cursor: 'pointer', fontSize: 14 }}>
                        <input
                          type="radio"
                          name="payment_term"
                          value={term.label}
                          checked={selectedPaymentTerm === term.label}
                          onChange={() => setSelectedPaymentTerm(term.label)}
                          style={{ accentColor: 'var(--red)', width: 16, height: 16 }}
                        />
                        {term.label}
                      </label>
                    ))}
                    {!selectedPaymentTerm && (
                      <p style={{ fontSize: 11, color: 'var(--muted)', margin: 0 }}>
                        Kein Zahlungsziel ausgewählt – erscheint nicht im PDF.
                      </p>
                    )}
                  </div>
                )}
              </div>
            )
          })()}

          {/* ── Rabatt ── */}
          {leasingSettings?.discount_enabled && (() => {
            const discountableItems = selected.filter(o => o.discountable && !optionalIds.has(o.id))
            if (discountableItems.length === 0) return null
            const saved = discountPercent > 0
              ? discountableItems.reduce((s, o) => {
                  const base = customPrices[o.id] !== undefined ? Number(customPrices[o.id]) : (o.price || 0)
                  return s + base * (discountPercent / 100)
                }, 0)
              : 0
            return (
              <div className="card" style={{ marginBottom: 16 }}>
                <div className="card-title" style={{ marginBottom: 12 }}>🏷️ Rabattierung</div>
                <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 8 }}>
                  <label style={{ fontSize: 13, color: 'var(--muted)', whiteSpace: 'nowrap' }}>
                    Rabatt auf rabattfähige Positionen:
                  </label>
                  <div style={{ position: 'relative', display: 'flex', alignItems: 'center' }}>
                    <input
                      type="number" min="0" max="100" step="0.5"
                      value={discountPercent}
                      onChange={e => setDiscountPercent(Math.min(100, Math.max(0, Number(e.target.value))))}
                      style={{ border: '1px solid var(--red)', borderRadius: 8,
                        padding: '6px 28px 6px 10px', fontSize: 14, width: 80,
                        fontWeight: 700, color: 'var(--red)' }}
                    />
                    <span style={{ position: 'absolute', right: 8, fontSize: 13,
                      color: 'var(--muted)', pointerEvents: 'none' }}>%</span>
                  </div>
                </div>
                <p style={{ fontSize: 11, color: 'var(--muted)', margin: 0 }}>
                  {discountableItems.length} rabattfähige Position{discountableItems.length !== 1 ? 'en' : ''}
                  {saved > 0 && <> · Ersparnis: <b style={{ color: 'var(--red)' }}>{money(saved)}</b></>}
                </p>
              </div>
            )
          })()}

          {/* ── Lieferadresse ── */}
          <div className="card" style={{ marginBottom: 16 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 14, cursor: 'pointer', userSelect: 'none' }}
              onClick={() => { setDeliveryEnabled(v => !v); setDeliveryQuery(''); setDeliveryAddress(''); setDeliverySuggestions([]) }}>
              <div style={{ width: 44, height: 24, borderRadius: 12, flexShrink: 0, transition: '.2s',
                background: deliveryEnabled ? 'var(--red)' : '#ccc', position: 'relative' }}>
                <div style={{ position: 'absolute', top: 2, left: deliveryEnabled ? 22 : 2,
                  width: 20, height: 20, borderRadius: '50%', background: 'white',
                  boxShadow: '0 1px 4px rgba(0,0,0,.25)', transition: '.2s' }} />
              </div>
              <span style={{ fontWeight: 700, fontSize: 14 }}>📍 Lieferadresse angeben</span>
            </div>

            {deliveryEnabled && (
              <div style={{ marginTop: 16, position: 'relative' }}>
                <input
                  value={deliveryQuery}
                  onChange={e => onDeliveryInput(e.target.value)}
                  placeholder="Straße, PLZ oder Ort suchen …"
                  style={{ width: '100%', border: '1px solid var(--line)', borderRadius: 10,
                    padding: '10px 14px', fontSize: 13, boxSizing: 'border-box' }}
                />
                {deliveryLoading && (
                  <p style={{ fontSize: 11, color: 'var(--muted)', margin: '4px 0 0' }}>Suche …</p>
                )}
                {deliverySuggestions.length > 0 && (
                  <div style={{ position: 'absolute', top: '100%', left: 0, right: 0,
                    background: 'white', border: '1px solid var(--line)', borderRadius: 10,
                    boxShadow: '0 4px 16px rgba(0,0,0,.12)', zIndex: 100, overflow: 'hidden' }}>
                    {deliverySuggestions.map((f, i) => {
                      const p = f.properties
                      const line1 = [p.street, p.housenumber].filter(Boolean).join(' ') || p.name || ''
                      const line2 = [p.postcode, p.city || p.town || p.village].filter(Boolean).join(' ')
                      return (
                        <div key={i} onClick={() => selectDelivery(f)}
                          style={{ padding: '10px 14px', cursor: 'pointer',
                            borderBottom: '1px solid var(--line)', fontSize: 13 }}
                          onMouseEnter={e => e.currentTarget.style.background = '#f8f8f8'}
                          onMouseLeave={e => e.currentTarget.style.background = 'white'}>
                          <b>{line1}</b>
                          {line2 && <span style={{ color: 'var(--muted)', marginLeft: 6 }}>{line2}</span>}
                        </div>
                      )
                    })}
                  </div>
                )}
                {deliveryAddress && (
                  <p style={{ fontSize: 12, color: 'var(--muted)', marginTop: 6 }}>
                    ✓ Ausgewählt: <b style={{ color: 'var(--dark)' }}>{deliveryAddress}</b>
                  </p>
                )}
              </div>
            )}
          </div>

          {/* ── MwSt / Land ── */}
          {(() => {
            const vats = leasingSettings?.vat_countries || []
            if (vats.length === 0) return null
            return (
              <div className="card" style={{ marginBottom: 16 }}>
                <div className="card-title" style={{ marginBottom: 12 }}>🌍 MwSt / Land</div>
                <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                  <label style={{ display: 'flex', alignItems: 'center',
                    gap: 10, cursor: 'pointer', fontSize: 14 }}>
                    <input
                      type="radio"
                      name="vat_country"
                      checked={selectedVatCountry === null}
                      onChange={() => setSelectedVatCountry(null)}
                      style={{ accentColor: 'var(--red)', width: 16, height: 16 }}
                    />
                    <span style={{ color: 'var(--muted)' }}>Kein MwSt-Hinweis im PDF</span>
                  </label>
                  {vats.map(v => (
                    <label key={v.id} style={{ display: 'flex', alignItems: 'center',
                      gap: 10, cursor: 'pointer', fontSize: 14 }}>
                      <input
                        type="radio"
                        name="vat_country"
                        checked={selectedVatCountry?.id === v.id}
                        onChange={() => setSelectedVatCountry(v)}
                        style={{ accentColor: 'var(--red)', width: 16, height: 16 }}
                      />
                      {v.country}
                      <span style={{ fontSize: 12, color: 'var(--muted)' }}>{v.rate}% MwSt</span>
                    </label>
                  ))}
                </div>
              </div>
            )
          })()}

          <div className="card">

            <div className="field">
              <label>Projektbezeichnung (optional)</label>
              <input
                value={projectName}
                onChange={e => setProjectName(e.target.value)}
                placeholder="z.B. Standort Wien · Büro 3. OG – oder leer lassen"
                list="projekt-vorlagen"
              />
              <datalist id="projekt-vorlagen">
                {(leasingSettings?.project_templates || []).map(t => (
                  <option key={t.id} value={t.label} />
                ))}
              </datalist>
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
