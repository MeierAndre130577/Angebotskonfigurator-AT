import { useState, useEffect, useRef, useCallback } from 'react'
import { options as optionsApi, uploadImage } from '../lib/api'

const CLUSTERS = ['Farmer Shop', 'Wein Shop', 'Maxibar', 'Erweiterungen', 'Zahlungssysteme', 'Zubehör', 'Service', 'Sonstiges']

function money(n) {
  return new Intl.NumberFormat('de-AT', { style: 'currency', currency: 'EUR' }).format(n || 0)
}

const EMPTY = {
  name: '', cluster: 'Farmer Shop', display_type: 'Großes Bild + Beschreibung',
  short_text: '', long_text: '', price: 0, recurring: false, image_path: '', sort_order: 0
}

export default function Bibliothek() {
  const [items, setItems]         = useState([])
  const [loading, setLoading]     = useState(true)
  const [search, setSearch]       = useState('')
  const [filterCluster, setFilter]= useState('')
  const [editing, setEditing]     = useState(null)
  const [form, setForm]           = useState(EMPTY)
  const [saving, setSaving]       = useState(false)
  const [uploading, setUploading] = useState(false)
  const [pasteHint, setPasteHint] = useState(false)
  const [toast, setToast]         = useState('')
  const fileRef                   = useRef()
  const pasteZoneRef              = useRef()

  useEffect(() => { load() }, [])

  // Strg+V global abfangen wenn Modal offen
  useEffect(() => {
    if (!editing) return
    const handler = (e) => {
      const items = e.clipboardData?.items
      if (!items) return
      for (const item of items) {
        if (item.type.startsWith('image/')) {
          e.preventDefault()
          const file = item.getAsFile()
          if (file) uploadFile(file)
          return
        }
      }
    }
    window.addEventListener('paste', handler)
    return () => window.removeEventListener('paste', handler)
  }, [editing])

  async function load() {
    setLoading(true)
    try { setItems(await optionsApi.list()) }
    catch(e) { showToast('Fehler beim Laden: ' + e.message) }
    finally { setLoading(false) }
  }

  function showToast(msg) {
    setToast(msg)
    setTimeout(() => setToast(''), 2500)
  }

  function startNew() {
    setForm({ ...EMPTY, sort_order: items.length + 1 })
    setEditing('new')
  }

  function startEdit(item) {
    setForm({ ...item })
    setEditing(item)
  }

  function cancelEdit() {
    setEditing(null)
    setForm(EMPTY)
    setPasteHint(false)
  }

  async function handleSave() {
    if (!form.name.trim()) { showToast('Name ist erforderlich'); return }
    setSaving(true)
    try {
      await optionsApi.upsert({
        ...form,
        id: editing === 'new' ? crypto.randomUUID() : editing.id,
        price: Number(form.price) || 0,
        sort_order: Number(form.sort_order) || 0,
      })
      await load()
      cancelEdit()
      showToast(editing === 'new' ? 'Option angelegt ✓' : 'Option gespeichert ✓')
    } catch(e) {
      showToast('Fehler: ' + e.message)
    } finally {
      setSaving(false)
    }
  }

  async function handleDelete(id) {
    if (!confirm('Option wirklich löschen?')) return
    try {
      await optionsApi.delete(id)
      await load()
      showToast('Option gelöscht')
    } catch(e) {
      showToast('Fehler: ' + e.message)
    }
  }

  async function uploadFile(file) {
    setUploading(true)
    try {
      const url = await uploadImage(file)
      setForm(f => ({ ...f, image_path: url }))
      showToast('Bild hochgeladen ✓')
      setPasteHint(false)
    } catch(e) {
      showToast('Bild-Upload fehlgeschlagen: ' + e.message)
    } finally {
      setUploading(false)
      if (fileRef.current) fileRef.current.value = ''
    }
  }

  async function handleImageUpload(e) {
    const file = e.target.files[0]
    if (file) uploadFile(file)
  }

  // Drag & Drop
  function handleDrop(e) {
    e.preventDefault()
    const file = e.dataTransfer.files[0]
    if (file && file.type.startsWith('image/')) uploadFile(file)
  }

  // Reihenfolge tauschen
  async function moveItem(index, dir) {
    const newItems = [...items]
    const targetIndex = index + dir
    if (targetIndex < 0 || targetIndex >= newItems.length) return
    // sort_order tauschen
    const a = { ...newItems[index], sort_order: newItems[targetIndex].sort_order }
    const b = { ...newItems[targetIndex], sort_order: newItems[index].sort_order }
    try {
      await Promise.all([optionsApi.upsert(a), optionsApi.upsert(b)])
      await load()
    } catch(e) {
      showToast('Fehler beim Verschieben')
    }
  }

  const filtered = items
    .filter(o => {
      const matchSearch = o.name.toLowerCase().includes(search.toLowerCase()) ||
        (o.short_text || '').toLowerCase().includes(search.toLowerCase())
      const matchCluster = !filterCluster || o.cluster === filterCluster
      return matchSearch && matchCluster
    })
    .sort((a, b) => (a.sort_order ?? 0) - (b.sort_order ?? 0))

  const clusters = [...new Set(items.map(o => o.cluster || 'Sonstiges'))]

  return (
    <div>
      {/* Toast */}
      {toast && (
        <div style={{
          position: 'fixed', bottom: 24, right: 24, background: 'var(--dark)',
          color: 'white', padding: '12px 20px', borderRadius: 12,
          fontSize: 13, fontWeight: 600, zIndex: 9999, boxShadow: '0 8px 24px rgba(0,0,0,.2)'
        }}>{toast}</div>
      )}

      {/* Header */}
      <div className="page-header">
        <div>
          <h1>📚 Optionsbibliothek</h1>
          <p className="subtitle">{items.length} Optionen in {clusters.length} Clustern</p>
        </div>
        <button className="btn btn-red" onClick={startNew}>＋ Neue Option</button>
      </div>

      {/* Filter */}
      <div className="row" style={{ marginBottom: 20, gap: 12 }}>
        <input
          placeholder="🔍 Suchen …"
          value={search}
          onChange={e => setSearch(e.target.value)}
          style={{ border: '1px solid var(--line)', borderRadius: 10, padding: '9px 14px', fontSize: 13, flex: 1 }}
        />
        <select
          value={filterCluster}
          onChange={e => setFilter(e.target.value)}
          style={{ border: '1px solid var(--line)', borderRadius: 10, padding: '9px 14px', fontSize: 13 }}
        >
          <option value="">Alle Cluster</option>
          {clusters.map(c => <option key={c}>{c}</option>)}
        </select>
      </div>

      {/* ── Edit Modal ─────────────────────────────────────────────────────── */}
      {editing && (
        <div style={{
          position: 'fixed', inset: 0, background: 'rgba(0,0,0,.5)',
          zIndex: 1000, display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 20
        }}>
          <div style={{
            background: 'white', borderRadius: 20, padding: 28,
            width: '100%', maxWidth: 680, maxHeight: '90vh', overflowY: 'auto',
            boxShadow: '0 24px 60px rgba(0,0,0,.2)'
          }}>
            <div className="between" style={{ marginBottom: 20 }}>
              <h2 style={{ fontSize: 20, fontWeight: 800 }}>
                {editing === 'new' ? '＋ Neue Option' : `✏️ ${editing.name}`}
              </h2>
              <button className="btn" onClick={cancelEdit}>✕</button>
            </div>

            {/* Bild-Upload Zone */}
            <div style={{ marginBottom: 20 }}>
              <label style={{ fontSize: 12, fontWeight: 700, color: 'var(--muted)', textTransform: 'uppercase', letterSpacing: '.05em', display: 'block', marginBottom: 8 }}>
                Bild
              </label>
              <div style={{ display: 'flex', gap: 16, alignItems: 'flex-start' }}>
                {/* Vorschau */}
                {form.image_path ? (
                  <div style={{ position: 'relative', flex: 'none' }}>
                    <img src={form.image_path} alt="" style={{ width: 140, height: 100, objectFit: 'cover', borderRadius: 10, border: '1px solid var(--line)' }} />
                    <button onClick={() => setForm(f => ({ ...f, image_path: '' }))}
                      style={{ position: 'absolute', top: -8, right: -8, width: 22, height: 22, borderRadius: '50%', background: 'var(--red)', color: 'white', border: 'none', cursor: 'pointer', fontSize: 12, fontWeight: 900 }}>✕</button>
                  </div>
                ) : null}

                {/* Drop/Paste Zone */}
                <div
                  ref={pasteZoneRef}
                  onDrop={handleDrop}
                  onDragOver={e => e.preventDefault()}
                  onClick={() => fileRef.current?.click()}
                  style={{
                    flex: 1, minHeight: 100, border: '2px dashed var(--line)', borderRadius: 12,
                    display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center',
                    cursor: 'pointer', background: 'var(--bg)', gap: 6, padding: 16,
                    transition: 'border-color .15s',
                  }}
                  onMouseEnter={e => e.currentTarget.style.borderColor = 'var(--red)'}
                  onMouseLeave={e => e.currentTarget.style.borderColor = 'var(--line)'}
                >
                  {uploading ? (
                    <p style={{ fontSize: 13, color: 'var(--muted)' }}>⏳ Lädt hoch …</p>
                  ) : (
                    <>
                      <span style={{ fontSize: 28 }}>📷</span>
                      <p style={{ fontSize: 13, fontWeight: 700, color: 'var(--dark)' }}>Klicken, Drag & Drop</p>
                      <p style={{ fontSize: 12, color: 'var(--muted)' }}>oder <b>Strg+V</b> zum Einfügen aus Zwischenablage</p>
                    </>
                  )}
                </div>
              </div>
              <input ref={fileRef} type="file" accept="image/*" onChange={handleImageUpload} style={{ display: 'none' }} />

              {/* Strg+V Hinweis */}
              <div style={{ marginTop: 8, padding: '8px 12px', background: 'var(--red-light)', borderRadius: 8, fontSize: 12, color: 'var(--red)', fontWeight: 600 }}>
                💡 Tipp: Screenshot machen → direkt hier im Fenster <b>Strg+V</b> drücken → Bild wird sofort hochgeladen
              </div>
            </div>

            {/* Felder */}
            <div className="grid2">
              <div className="field">
                <label>Name *</label>
                <input value={form.name} onChange={e => setForm(f => ({ ...f, name: e.target.value }))} placeholder="z.B. Farmer Shop 2.0 Standard" autoFocus />
              </div>
              <div className="field">
                <label>Cluster</label>
                <select value={form.cluster} onChange={e => setForm(f => ({ ...f, cluster: e.target.value }))}>
                  {CLUSTERS.map(c => <option key={c}>{c}</option>)}
                </select>
              </div>
              <div className="field">
                <label>Preis (€)</label>
                <input type="number" value={form.price} onChange={e => setForm(f => ({ ...f, price: e.target.value }))} />
              </div>
              <div className="field">
                <label>Preisart</label>
                <select value={form.recurring ? 'monthly' : 'once'} onChange={e => setForm(f => ({ ...f, recurring: e.target.value === 'monthly' }))}>
                  <option value="once">Einmalig</option>
                  <option value="monthly">Monatlich</option>
                </select>
              </div>
            </div>

            <div className="field">
              <label>Kurzbeschreibung</label>
              <textarea value={form.short_text || ''} onChange={e => setForm(f => ({ ...f, short_text: e.target.value }))} placeholder="Kurzer Text für Übersichten und Karten …" style={{ minHeight: 70 }} />
            </div>

            <div className="field">
              <label>Langtext</label>
              <textarea value={form.long_text || ''} onChange={e => setForm(f => ({ ...f, long_text: e.target.value }))} placeholder="Ausführliche Beschreibung für Detailseiten …" style={{ minHeight: 100 }} />
            </div>

            <div className="row" style={{ marginTop: 8 }}>
              <button className="btn btn-red" onClick={handleSave} disabled={saving} style={{ flex: 1, justifyContent: 'center' }}>
                {saving ? '⏳ Speichert …' : '💾 Speichern'}
              </button>
              <button className="btn" onClick={cancelEdit}>Abbrechen</button>
            </div>
          </div>
        </div>
      )}

      {/* ── Tabelle ───────────────────────────────────────────────────────── */}
      {loading ? (
        <p className="muted">Lädt …</p>
      ) : (
        <div className="card" style={{ padding: 0, overflow: 'hidden' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
            <thead>
              <tr style={{ borderBottom: '1px solid var(--line)', background: 'var(--bg)' }}>
                <th style={{ padding: '12px 16px', textAlign: 'left', fontWeight: 700, color: 'var(--muted)', width: 50 }}>#</th>
                <th style={{ padding: '12px 16px', textAlign: 'left', fontWeight: 700, color: 'var(--muted)', width: 60 }}>Bild</th>
                <th style={{ padding: '12px 16px', textAlign: 'left', fontWeight: 700, color: 'var(--muted)' }}>Option</th>
                <th style={{ padding: '12px 16px', textAlign: 'left', fontWeight: 700, color: 'var(--muted)' }}>Cluster</th>
                <th style={{ padding: '12px 16px', textAlign: 'left', fontWeight: 700, color: 'var(--muted)' }}>Kurzbeschreibung</th>
                <th style={{ padding: '12px 16px', textAlign: 'right', fontWeight: 700, color: 'var(--muted)' }}>Preis</th>
                <th style={{ padding: '12px 16px', textAlign: 'right', fontWeight: 700, color: 'var(--muted)' }}></th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((o, index) => (
                <tr key={o.id} style={{ borderBottom: '1px solid var(--line)' }}
                  onMouseEnter={e => e.currentTarget.style.background = 'var(--bg)'}
                  onMouseLeave={e => e.currentTarget.style.background = 'white'}>

                  {/* Reihenfolge Buttons */}
                  <td style={{ padding: '10px 16px' }}>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
                      <button onClick={() => moveItem(index, -1)} disabled={index === 0}
                        style={{ border: 'none', background: 'none', cursor: index === 0 ? 'default' : 'pointer', fontSize: 14, color: index === 0 ? 'var(--line)' : 'var(--muted)', padding: '2px 4px', borderRadius: 4 }}>▲</button>
                      <button onClick={() => moveItem(index, 1)} disabled={index === filtered.length - 1}
                        style={{ border: 'none', background: 'none', cursor: index === filtered.length - 1 ? 'default' : 'pointer', fontSize: 14, color: index === filtered.length - 1 ? 'var(--line)' : 'var(--muted)', padding: '2px 4px', borderRadius: 4 }}>▼</button>
                    </div>
                  </td>

                  <td style={{ padding: '10px 16px' }}>
                    {o.image_path
                      ? <img src={o.image_path} alt="" style={{ width: 48, height: 36, objectFit: 'cover', borderRadius: 6 }} />
                      : <div style={{ width: 48, height: 36, background: 'var(--bg)', borderRadius: 6, border: '1px dashed var(--line)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 16 }}>📷</div>
                    }
                  </td>
                  <td style={{ padding: '10px 16px' }}><b>{o.name}</b></td>
                  <td style={{ padding: '10px 16px' }}><span className="pill">{o.cluster || '—'}</span></td>
                  <td style={{ padding: '10px 16px', color: 'var(--muted)', maxWidth: 240 }}>
                    <span style={{ display: '-webkit-box', WebkitLineClamp: 2, WebkitBoxOrient: 'vertical', overflow: 'hidden' }}>
                      {o.short_text || '—'}
                    </span>
                  </td>
                  <td style={{ padding: '10px 16px', textAlign: 'right', fontWeight: 700, whiteSpace: 'nowrap' }}>
                    {o.price === 0
                      ? <span style={{ color: 'var(--muted)' }}>inkl.</span>
                      : o.recurring
                        ? <span style={{ color: 'var(--red)' }}>{money(o.price)}/Mo.</span>
                        : money(o.price)}
                  </td>
                  <td style={{ padding: '10px 16px', textAlign: 'right' }}>
                    <div className="row" style={{ justifyContent: 'flex-end' }}>
                      <button className="btn" style={{ padding: '6px 12px', fontSize: 12 }} onClick={() => startEdit(o)}>✏️</button>
                      <button className="btn" style={{ padding: '6px 12px', fontSize: 12, color: 'var(--red)' }} onClick={() => handleDelete(o.id)}>🗑️</button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          {filtered.length === 0 && (
            <p className="muted small" style={{ padding: 24 }}>Keine Optionen gefunden.</p>
          )}
        </div>
      )}
    </div>
  )
}
