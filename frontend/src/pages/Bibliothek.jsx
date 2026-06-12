import { useState, useEffect, useRef } from 'react'
import { options as optionsApi, uploadImage } from '../lib/api'
import {
  DndContext, closestCenter, PointerSensor, TouchSensor, useSensor, useSensors
} from '@dnd-kit/core'
import {
  SortableContext, verticalListSortingStrategy, useSortable, arrayMove
} from '@dnd-kit/sortable'
import { CSS } from '@dnd-kit/utilities'

const CLUSTERS = ['Farmer Shop', 'Wein Shop', 'Maxibar', 'Erweiterungen', 'Zahlungssysteme', 'Zubehör', 'Service', 'Sonstiges']

function money(n) {
  return new Intl.NumberFormat('de-AT', { style: 'currency', currency: 'EUR' }).format(n || 0)
}

const EMPTY = {
  name: '', cluster: 'Farmer Shop', display_type: 'Großes Bild + Beschreibung',
  short_text: '', long_text: '', price: 0, recurring: false,
  image_path: '', sort_order: 0, documents: [], active: false,
  price_editable: false, price_hint: '',
}

async function uploadDocument(file) {
  const formData = new FormData()
  formData.append('file', file, file.name)
  const BASE = (import.meta.env.VITE_API_URL || '') + '/api'
  const res = await fetch(`${BASE}/upload/document`, { method: 'POST', body: formData })
  const data = await res.json().catch(() => ({}))
  if (!res.ok) throw new Error(data.error || 'Upload fehlgeschlagen')
  return data
}

// ── Sortierbare Tabellenzeile ─────────────────────────────────────────────────
function SortableRow({ o, onEdit, onDelete, onToggleActive }) {
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } = useSortable({ id: o.id })

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
    opacity: isDragging ? 0.4 : 1,
    background: isDragging ? 'var(--red-light)' : 'white',
    borderBottom: '1px solid var(--line)',
  }

  return (
    <tr ref={setNodeRef} style={style}
      onMouseEnter={e => { if (!isDragging) e.currentTarget.style.background = 'var(--bg)' }}
      onMouseLeave={e => { if (!isDragging) e.currentTarget.style.background = o.active !== false ? 'white' : '#fafafa' }}
      style={{ ...style, opacity: o.active !== false ? 1 : 0.5 }}>

      {/* Drag Handle – 3 waagrechte Striche */}
      <td style={{ padding: '10px 8px', width: 36 }}>
        <div
          {...attributes}
          {...listeners}
          title="Halten und ziehen zum Sortieren"
          style={{
            cursor: 'grab',
            display: 'flex', flexDirection: 'column', gap: 3,
            alignItems: 'center', justifyContent: 'center',
            width: 28, height: 28, borderRadius: 6,
            padding: '4px 6px',
            touchAction: 'none', userSelect: 'none',
            color: 'var(--muted)',
          }}
        >
          {/* 3 echte waagrechte Striche */}
          {[0,1,2].map(i => (
            <div key={i} style={{ width: 16, height: 2, background: 'currentColor', borderRadius: 1 }} />
          ))}
        </div>
      </td>

      <td style={{ padding: '10px 8px', width: 60 }}>
        {o.image_path
          ? <img src={o.image_path} alt="" style={{ width: 48, height: 36, objectFit: 'cover', borderRadius: 6 }} />
          : <div style={{ width: 48, height: 36, background: 'var(--bg)', borderRadius: 6, border: '1px dashed var(--line)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 14, color: 'var(--muted)' }}>📷</div>
        }
      </td>

      <td style={{ padding: '10px 8px' }}>
        <b style={{ fontSize: 13 }}>{o.name}</b>
        {(o.documents || []).length > 0 && (
          <span style={{ marginLeft: 8, fontSize: 11, color: 'var(--muted)' }}>
            📎 {o.documents.length} Dok.
          </span>
        )}
      </td>

      <td style={{ padding: '10px 8px' }}>
        <span className="pill">{o.cluster || '—'}</span>
      </td>

      <td style={{ padding: '10px 8px', color: 'var(--muted)', maxWidth: 220, fontSize: 12 }}>
        <span style={{ display: '-webkit-box', WebkitLineClamp: 2, WebkitBoxOrient: 'vertical', overflow: 'hidden' }}>
          {o.short_text || '—'}
        </span>
      </td>

      <td style={{ padding: '10px 8px', textAlign: 'right', fontWeight: 700, fontSize: 13, whiteSpace: 'nowrap' }}>
        {o.price === 0
          ? <span style={{ color: 'var(--muted)' }}>inkl.</span>
          : o.recurring
            ? <span style={{ color: 'var(--red)' }}>{money(o.price)}/Mo.</span>
            : money(o.price)}
      </td>

      {/* Aktiv Toggle */}
      <td style={{ padding: '10px 8px', textAlign: 'center' }}>
        <button
          onClick={() => onToggleActive(o)}
          style={{
            width: 44, height: 24, borderRadius: 12, border: 'none', cursor: 'pointer',
            background: o.active !== false ? 'var(--red)' : 'var(--line)',
            position: 'relative', transition: '.2s',
          }}
        >
          <div style={{
            width: 18, height: 18, borderRadius: '50%', background: 'white',
            position: 'absolute', top: 3,
            left: o.active !== false ? 23 : 3,
            transition: '.2s',
          }} />
        </button>
      </td>
      <td style={{ padding: '10px 8px', textAlign: 'right' }}>
        <div className="row" style={{ justifyContent: 'flex-end' }}>
          <button className="btn" style={{ padding: '6px 12px', fontSize: 12 }} onClick={() => onEdit(o)}>✏️</button>
          <button className="btn" style={{ padding: '6px 12px', fontSize: 12, color: 'var(--red)' }} onClick={() => onDelete(o.id)}>🗑️</button>
        </div>
      </td>
    </tr>
  )
}

// ── Dokument-Item ─────────────────────────────────────────────────────────────
function DocItem({ doc, onRemove, onTitleChange }) {
  return (
    <div style={{ marginBottom: 8 }}>
      <div style={{
        display: 'flex', alignItems: 'center', gap: 10,
        padding: '8px 12px', background: 'var(--bg)', borderRadius: 10,
        border: '1px solid var(--line)', marginBottom: 4
      }}>
        <span style={{ fontSize: 18 }}>📄</span>
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ fontSize: 12, color: 'var(--muted)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{doc.file_name}</div>
        </div>
        {doc.file_url && (
          <a href={doc.file_url} target="_blank" rel="noopener noreferrer"
            className="btn" style={{ padding: '3px 8px', fontSize: 11, textDecoration: 'none', flex: 'none' }}>👁️</a>
        )}
        <button onClick={onRemove}
          style={{ border: 'none', background: 'none', cursor: 'pointer', color: 'var(--red)', fontSize: 16, flex: 'none' }}>✕</button>
      </div>
      <input
        value={doc.title}
        onChange={e => onTitleChange(doc.id, e.target.value)}
        placeholder="Titel (erscheint in Anlagen)"
        style={{ width: '100%', border: '1px solid var(--line)', borderRadius: 8, padding: '6px 12px', fontSize: 12 }}
      />
    </div>
  )
}

// ── Hauptkomponente ───────────────────────────────────────────────────────────
export default function Bibliothek() {
  const [items, setItems]           = useState([])
  const [loading, setLoading]       = useState(true)
  const [search, setSearch]         = useState('')
  const [filterCluster, setFilter]  = useState('')
  const [editing, setEditing]       = useState(null)
  const [form, setForm]             = useState(EMPTY)
  const [saving, setSaving]         = useState(false)
  const [uploading, setUploading]   = useState(false)
  const [uploadingDoc, setUploadingDoc] = useState(false)
  const [toast, setToast]           = useState('')
  const [templates, setTemplates]   = useState([])
  const [showTemplates, setShowTemplates] = useState(false)
  const [editingTemplate, setEditingTemplate] = useState(null)
  const [newTplName, setNewTplName]           = useState('')
  const [defaultTemplateId, setDefaultTemplateId] = useState(
    () => localStorage.getItem('bibliothek_default_template') || null
  )
  const fileRef                     = useRef()
  const docRef                      = useRef()
  const BASE = (import.meta.env.VITE_API_URL || '') + '/api'

  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 5 } }),
    useSensor(TouchSensor,   { activationConstraint: { delay: 200, tolerance: 5 } })
  )

  useEffect(() => { load(); loadTemplates() }, [])

  useEffect(() => {
    if (!editing) return
    const handler = (e) => {
      const clipItems = e.clipboardData?.items
      if (!clipItems) return
      for (const item of clipItems) {
        if (item.type.startsWith('image/')) {
          e.preventDefault()
          handleUploadImage(item.getAsFile())
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
    catch(e) { showToast('Fehler: ' + e.message) }
    finally { setLoading(false) }
  }

  async function loadTemplates() {
    try {
      const res  = await fetch(`${BASE}/templates`)
      const tpls = await res.json()
      setTemplates(tpls)

      // Standard-Vorlage anwenden: Optionen aktivieren/deaktivieren
      const defId = localStorage.getItem('bibliothek_default_template')
      if (defId) {
        const defTpl = tpls.find(t => t.id === defId)
        if (defTpl) applyTemplate(defTpl)
      }
    } catch(e) { console.warn(e) }
  }

  async function applyTemplate(tpl) {
    // Alle Optionen: aktiv wenn in Vorlage, inaktiv sonst
    const ids = new Set((tpl.option_ids || []).map(String))
    const all  = await optionsApi.list()
    const toUpdate = all.filter(o => {
      const inTpl    = ids.has(String(o.id))
      const isActive = o.active !== false
      return inTpl !== isActive  // nur ändern wenn nötig
    })
    if (toUpdate.length === 0) return
    await Promise.all(toUpdate.map(o => optionsApi.upsert({ ...o, active: ids.has(String(o.id)) })))
    await load()
    showToast(`Vorlage "${tpl.name}" angewendet ✓`)
  }

  function setAsDefault(tpl) {
    if (defaultTemplateId === tpl.id) {
      // Abwählen
      localStorage.removeItem('bibliothek_default_template')
      setDefaultTemplateId(null)
      showToast('Standard-Vorlage entfernt')
    } else {
      localStorage.setItem('bibliothek_default_template', tpl.id)
      setDefaultTemplateId(tpl.id)
      showToast(`"${tpl.name}" als Standard gesetzt ✓`)
    }
  }

  async function saveTemplate(tpl) {
    await fetch(`${BASE}/templates`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(tpl)
    })
    await loadTemplates()
    showToast('Vorlage gespeichert ✓')
  }

  async function deleteTemplate(id) {
    if (!confirm('Vorlage löschen?')) return
    await fetch(`${BASE}/templates/${id}`, { method: 'DELETE' })
    await loadTemplates()
    showToast('Vorlage gelöscht')
  }

  async function toggleActive(item) {
    try {
      await optionsApi.upsert({ ...item, active: !item.active })
      await load()
    } catch(e) { showToast('Fehler: ' + e.message) }
  }

  function showToast(msg) { setToast(msg); setTimeout(() => setToast(''), 2500) }
  function startNew()  { setForm({ ...EMPTY, sort_order: items.length + 1, documents: [] }); setEditing('new') }
  function startEdit(item) { setForm({ ...item, documents: item.documents || [] }); setEditing(item) }
  function cancelEdit() { setEditing(null); setForm(EMPTY) }

  async function handleSave() {
    if (!form.name.trim()) { showToast('Name ist erforderlich'); return }
    setSaving(true)
    try {
      await optionsApi.upsert({
        ...form,
        id: editing === 'new' ? crypto.randomUUID() : editing.id,
        price: Number(form.price) || 0,
        sort_order: Number(form.sort_order) || 0,
        documents: form.documents || [],
      })
      await load(); cancelEdit()
      showToast(editing === 'new' ? 'Option angelegt ✓' : 'Gespeichert ✓')
    } catch(e) { showToast('Fehler: ' + e.message) }
    finally { setSaving(false) }
  }

  async function handleDelete(id) {
    if (!confirm('Option wirklich löschen?')) return
    try { await optionsApi.delete(id); await load(); showToast('Gelöscht') }
    catch(e) { showToast('Fehler: ' + e.message) }
  }

  async function handleUploadImage(file) {
    if (!file) return
    setUploading(true)
    try {
      const url = await uploadImage(file)
      setForm(f => ({ ...f, image_path: url }))
      showToast('Bild hochgeladen ✓')
    } catch(e) { showToast('Fehler: ' + e.message) }
    finally { setUploading(false); if (fileRef.current) fileRef.current.value = '' }
  }

  async function handleDocumentUpload(e) {
    const file = e.target.files[0]
    if (!file) return
    setUploadingDoc(true)
    try {
      const result = await uploadDocument(file)
      setForm(f => ({ ...f, documents: [...(f.documents || []), {
        id: crypto.randomUUID(),
        title: file.name.replace(/\.[^.]+$/, ''),
        file_name: file.name,
        file_url: result.url || '',
      }]}))
      showToast('Dokument hochgeladen ✓')
    } catch(e) { showToast('Fehler: ' + e.message) }
    finally { setUploadingDoc(false); if (docRef.current) docRef.current.value = '' }
  }

  function removeDocument(docId) {
    setForm(f => ({ ...f, documents: (f.documents || []).filter(d => d.id !== docId) }))
  }

  function updateDocTitle(docId, title) {
    setForm(f => ({ ...f, documents: (f.documents || []).map(d => d.id === docId ? { ...d, title } : d) }))
  }

  async function handleDragEnd(event) {
    const { active, over } = event
    if (!over || active.id === over.id) return
    const oldIndex = filtered.findIndex(o => o.id === active.id)
    const newIndex = filtered.findIndex(o => o.id === over.id)
    const reordered = arrayMove(filtered, oldIndex, newIndex)
    // Optimistisch updaten
    const updated = items.map(item => {
      const newPos = reordered.findIndex(r => r.id === item.id)
      return newPos >= 0 ? { ...item, sort_order: newPos } : item
    })
    setItems(updated)
    try {
      await Promise.all(reordered.map((o, idx) => optionsApi.upsert({ ...o, sort_order: idx })))
      showToast('Reihenfolge gespeichert ✓')
    } catch { showToast('Fehler beim Speichern'); await load() }
  }

  const filtered = items
    .filter(o => {
      const ms = o.name.toLowerCase().includes(search.toLowerCase()) ||
        (o.short_text || '').toLowerCase().includes(search.toLowerCase())
      return ms && (!filterCluster || o.cluster === filterCluster)
    })
    .sort((a, b) => (a.sort_order ?? 0) - (b.sort_order ?? 0))

  const clusters = [...new Set(items.map(o => o.cluster || 'Sonstiges'))]

  return (
    <div>
      {toast && (
        <div style={{
          position: 'fixed', bottom: 24, right: 24, background: 'var(--dark)',
          color: 'white', padding: '12px 20px', borderRadius: 12,
          fontSize: 13, fontWeight: 600, zIndex: 9999
        }}>{toast}</div>
      )}

      <div className="page-header">
        <div>
          <h1>📚 Optionsbibliothek</h1>
          <p className="subtitle">
            {items.filter(i => i.active !== false).length} aktiv · {items.filter(i => i.active === false).length} inaktiv
          </p>
        </div>
        <div className="row" style={{ gap: 8 }}>
          <button className="btn" onClick={() => setShowTemplates(v => !v)}
            style={{ background: showTemplates ? 'var(--dark)' : 'white', color: showTemplates ? 'white' : 'var(--dark)' }}>
            📋 Vorlagen {templates.length > 0 ? `(${templates.length})` : ''}
          </button>
          <button className="btn btn-red" onClick={startNew}>＋ Neue Option</button>
        </div>
      </div>

      {/* ── Vorlagen Panel ───────────────────────────────────────────────── */}
      {showTemplates && (
        <div className="card" style={{ marginBottom: 16 }}>
          <div className="card-title">📋 Vorlagen</div>
          <p style={{ fontSize: 12, color: 'var(--muted)', marginBottom: 12 }}>
            Eine Vorlage ist eine benannte Auswahl von Optionen – z.B. „Weinmesse" oder „Bauernmarkt".
            In der Schnellerfassung kannst du eine Vorlage auswählen um nur relevante Optionen zu sehen.
          </p>

          {/* Neue Vorlage – aktuell aktive Optionen speichern */}
          <div style={{ marginBottom: 16 }}>
            <p style={{ fontSize: 12, color: 'var(--muted)', marginBottom: 10 }}>
              Aktiviere/deaktiviere Optionen in der Liste unten, dann gib einen Namen ein und speichere die Vorlage.
              Beim Laden werden die Optionen wieder so gesetzt.
            </p>
            <div className="row" style={{ gap: 8 }}>
              <input
                value={newTplName}
                onChange={e => setNewTplName(e.target.value)}
                placeholder="Vorlagenname z.B. Weinmesse"
                style={{ flex: 1, border: '1px solid var(--line)', borderRadius: 10, padding: '8px 12px', fontSize: 13 }}
              />
              <button className="btn btn-red" style={{ flex: 'none' }}
                onClick={() => {
                  if (!newTplName.trim()) { showToast('Bitte Namen eingeben'); return }
                  const activeIds = items.filter(o => o.active !== false).map(o => o.id)
                  if (activeIds.length === 0) { showToast('Keine aktiven Optionen vorhanden'); return }
                  saveTemplate({ id: crypto.randomUUID(), name: newTplName.trim(), option_ids: activeIds })
                  setNewTplName('')
                }}>
                ＋ Aktuellen Stand speichern
              </button>
            </div>
            <p style={{ fontSize: 11, color: 'var(--muted)', marginTop: 6 }}>
              Aktuell aktiv: <b>{items.filter(o => o.active !== false).length}</b> von {items.length} Optionen
            </p>
          </div>

          {/* Vorlagen Liste */}
          {templates.length === 0 ? (
            <p style={{ fontSize: 12, color: 'var(--muted)', fontStyle: 'italic' }}>Noch keine Vorlagen</p>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
              {templates.map(tpl => (
                <div key={tpl.id} style={{
                  display: 'flex', alignItems: 'center', gap: 10,
                  padding: '10px 14px', background: 'var(--bg)',
                  borderRadius: 10, border: '1px solid var(--line)'
                }}>
                  <span style={{ fontSize: 14 }}>📋</span>
                  {editingTemplate?.id === tpl.id ? (
                    <input
                      value={editingTemplate.name}
                      onChange={e => setEditingTemplate(t => ({...t, name: e.target.value}))}
                      style={{ flex: 1, border: '1px solid var(--line)', borderRadius: 8, padding: '4px 8px', fontSize: 13 }}
                      autoFocus
                    />
                  ) : (
                    <span style={{ flex: 1, fontWeight: 700, fontSize: 13 }}>{tpl.name}</span>
                  )}
                  <span style={{ fontSize: 11, color: 'var(--muted)' }}>
                    {(tpl.option_ids || []).length} Opt.
                    {defaultTemplateId === tpl.id && (
                      <span style={{ marginLeft: 6, color: 'var(--dark)', fontWeight: 700 }}>★</span>
                    )}
                  </span>
                  {editingTemplate?.id === tpl.id ? (
                    <>
                      <button className="btn" style={{ padding: '4px 10px', fontSize: 11 }}
                        onClick={() => { saveTemplate(editingTemplate); setEditingTemplate(null) }}>
                        💾
                      </button>
                      <button className="btn" style={{ padding: '4px 10px', fontSize: 11 }}
                        onClick={() => setEditingTemplate(null)}>✕</button>
                    </>
                  ) : (
                    <>
                      {/* Anwenden */}
                      <button className="btn" style={{ padding: '4px 10px', fontSize: 11,
                        background: 'var(--red)', color: 'white', border: 'none' }}
                        onClick={() => applyTemplate(tpl)}
                        title="Toggle-Status aller Optionen nach dieser Vorlage setzen">
                        ▶ Laden
                      </button>
                      {/* Als Standard */}
                      <button className="btn" style={{ padding: '4px 10px', fontSize: 11,
                        background: defaultTemplateId === tpl.id ? 'var(--dark)' : 'white',
                        color: defaultTemplateId === tpl.id ? 'white' : 'var(--muted)' }}
                        onClick={() => setAsDefault(tpl)}
                        title={defaultTemplateId === tpl.id ? 'Standard entfernen' : 'Beim Öffnen automatisch laden'}>
                        {defaultTemplateId === tpl.id ? '★ Standard' : '☆ Standard'}
                      </button>
                      <button className="btn" style={{ padding: '4px 10px', fontSize: 11 }}
                        onClick={() => setEditingTemplate(tpl)} title="Umbenennen">✏️</button>
                      <button className="btn" style={{ padding: '4px 10px', fontSize: 11 }}
                        onClick={() => {
                          const ids = items.filter(o => o.active !== false).map(o => o.id)
                          if (ids.length === 0) { showToast('Keine aktiven Optionen'); return }
                          saveTemplate({...tpl, option_ids: ids})
                        }} title="Mit aktuellem Aktiv-Stand überschreiben">🔄</button>
                      <button className="btn" style={{ padding: '4px 10px', fontSize: 11, color: 'var(--red)' }}
                        onClick={() => deleteTemplate(tpl.id)}>🗑️</button>
                    </>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      <div className="row" style={{ marginBottom: 12, gap: 12 }}>
        <input placeholder="🔍 Suchen …" value={search} onChange={e => setSearch(e.target.value)}
          style={{ border: '1px solid var(--line)', borderRadius: 10, padding: '9px 14px', fontSize: 13, flex: 1 }} />
        <select value={filterCluster} onChange={e => setFilter(e.target.value)}
          style={{ border: '1px solid var(--line)', borderRadius: 10, padding: '9px 14px', fontSize: 13 }}>
          <option value="">Alle Cluster</option>
          {clusters.map(c => <option key={c}>{c}</option>)}
        </select>
      </div>

      {/* Alle aktiv / inaktiv */}
      <div className="row" style={{ marginBottom: 16, gap: 8 }}>
        <span style={{ fontSize: 12, color: 'var(--muted)' }}>Sichtbare Optionen:</span>
        <button className="btn" style={{ fontSize: 11, padding: '5px 12px' }}
          onClick={async () => {
            await Promise.all(filtered.filter(o => o.active === false).map(o => optionsApi.upsert({...o, active: true})))
            await load()
            showToast('Alle aktiviert ✓')
          }}>
          ✅ Alle aktivieren
        </button>
        <button className="btn" style={{ fontSize: 11, padding: '5px 12px' }}
          onClick={async () => {
            await Promise.all(filtered.filter(o => o.active !== false).map(o => optionsApi.upsert({...o, active: false})))
            await load()
            showToast('Alle deaktiviert ✓')
          }}>
          ⬜ Alle deaktivieren
        </button>
      </div>

      {/* ── Edit Modal ──────────────────────────────────────────────────────── */}
      {editing && (
        <div style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,.5)', zIndex: 1000, display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 20 }}>
          <div style={{ background: 'white', borderRadius: 20, padding: 28, width: '100%', maxWidth: 700, maxHeight: '92vh', overflowY: 'auto', boxShadow: '0 24px 60px rgba(0,0,0,.2)' }}>
            <div className="between" style={{ marginBottom: 20 }}>
              <h2 style={{ fontSize: 20, fontWeight: 800 }}>{editing === 'new' ? '＋ Neue Option' : `✏️ ${editing.name}`}</h2>
              <button className="btn" onClick={cancelEdit}>✕</button>
            </div>

            {/* Bild */}
            <div style={{ marginBottom: 16 }}>
              <label style={{ fontSize: 12, fontWeight: 700, color: 'var(--muted)', textTransform: 'uppercase', letterSpacing: '.05em', display: 'block', marginBottom: 8 }}>Bild</label>
              <div style={{ display: 'flex', gap: 16, alignItems: 'flex-start' }}>
                {form.image_path && (
                  <div style={{ position: 'relative', flex: 'none' }}>
                    <img src={form.image_path} alt="" style={{ width: 120, height: 90, objectFit: 'cover', borderRadius: 10, border: '1px solid var(--line)' }} />
                    <button onClick={() => setForm(f => ({ ...f, image_path: '' }))}
                      style={{ position: 'absolute', top: -8, right: -8, width: 22, height: 22, borderRadius: '50%', background: 'var(--red)', color: 'white', border: 'none', cursor: 'pointer', fontSize: 12, fontWeight: 900 }}>✕</button>
                  </div>
                )}
                <div onClick={() => fileRef.current?.click()}
                  onDrop={e => { e.preventDefault(); handleUploadImage(e.dataTransfer.files[0]) }}
                  onDragOver={e => e.preventDefault()}
                  style={{ flex: 1, minHeight: 90, border: '2px dashed var(--line)', borderRadius: 12, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', cursor: 'pointer', background: 'var(--bg)', gap: 4, padding: 12 }}
                  onMouseEnter={e => e.currentTarget.style.borderColor = 'var(--red)'}
                  onMouseLeave={e => e.currentTarget.style.borderColor = 'var(--line)'}>
                  {uploading
                    ? <p style={{ fontSize: 12, color: 'var(--muted)' }}>⏳ Lädt …</p>
                    : <><span style={{ fontSize: 22 }}>📷</span><p style={{ fontSize: 12, fontWeight: 700 }}>Klicken, Drag & Drop oder Strg+V</p></>}
                </div>
              </div>
              <input ref={fileRef} type="file" accept="image/*" onChange={e => handleUploadImage(e.target.files[0])} style={{ display: 'none' }} />
            </div>

            {/* Felder */}
            <div className="grid2">
              <div className="field"><label>Name *</label><input value={form.name} onChange={e => setForm(f => ({ ...f, name: e.target.value }))} autoFocus /></div>
              <div className="field"><label>Cluster</label>
                <select value={form.cluster} onChange={e => setForm(f => ({ ...f, cluster: e.target.value }))}>
                  {CLUSTERS.map(c => <option key={c}>{c}</option>)}
                </select>
              </div>
              <div className="field"><label>Preis (€)</label><input type="number" value={form.price} onChange={e => setForm(f => ({ ...f, price: e.target.value }))} /></div>
              <div className="field"><label>Preisart</label>
                <select value={form.recurring ? 'monthly' : 'once'} onChange={e => setForm(f => ({ ...f, recurring: e.target.value === 'monthly' }))}>
                  <option value="once">Einmalig</option>
                  <option value="monthly">Monatlich</option>
                </select>
              </div>

              {/* Preis veränderbar */}
              <div className="field" style={{ gridColumn: 'span 2' }}>
                <label>Preis in Schnellerfassung veränderbar?</label>
                <div
                  onClick={() => setForm(f => ({ ...f, price_editable: !f.price_editable }))}
                  style={{ display: 'flex', alignItems: 'center', gap: 12, marginTop: 6, cursor: 'pointer', userSelect: 'none', width: 'fit-content' }}>
                  {/* Toggle-Schiene */}
                  <div style={{
                    width: 44, height: 24, borderRadius: 12, flexShrink: 0, transition: '.2s',
                    background: form.price_editable ? 'var(--red)' : '#ccc',
                    position: 'relative',
                  }}>
                    {/* Knopf */}
                    <div style={{
                      position: 'absolute', top: 2,
                      left: form.price_editable ? 22 : 2,
                      width: 20, height: 20, borderRadius: '50%',
                      background: 'white', boxShadow: '0 1px 4px rgba(0,0,0,.25)',
                      transition: '.2s',
                    }} />
                  </div>
                  <span style={{ fontSize: 13, fontWeight: 600, color: form.price_editable ? 'var(--red)' : 'var(--muted)' }}>
                    {form.price_editable ? '✏️ Ja – Preis ist anpassbar' : 'Nein – Preis ist fest'}
                  </span>
                </div>
              </div>

              {/* Hinweis bei editierbarem Preis */}
              {form.price_editable && (
                <div className="field" style={{ gridColumn: 'span 2' }}>
                  <label>Hinweistext (erscheint beim Preiseingabefeld)</label>
                  <input
                    value={form.price_hint || ''}
                    onChange={e => setForm(f => ({ ...f, price_hint: e.target.value }))}
                    placeholder="z. B. Preis abhängig von Standort und Ausstattung"
                    style={{ border: '1px solid var(--line)', borderRadius: 10, padding: '10px 14px', fontSize: 13 }}
                  />
                </div>
              )}
              <div className="field"><label>Darstellung</label>
                <select value={form.display_type} onChange={e => setForm(f => ({ ...f, display_type: e.target.value }))}>
                  <option>Großes Bild + Beschreibung</option>
                  <option>Kleines Bild + Langtext</option>
                  <option>Kein Bild, Langtext + Kurztext</option>
                  <option>Kein Bild, Kurztext</option>
                </select>
              </div>
            </div>
            <div className="field"><label>Kurzbeschreibung</label><textarea value={form.short_text || ''} onChange={e => setForm(f => ({ ...f, short_text: e.target.value }))} style={{ minHeight: 60 }} /></div>
            <div className="field"><label>Langtext</label><textarea value={form.long_text || ''} onChange={e => setForm(f => ({ ...f, long_text: e.target.value }))} style={{ minHeight: 90 }} /></div>

            {/* Dokumente */}
            <div style={{ marginBottom: 16 }}>
              <div className="between" style={{ marginBottom: 10 }}>
                <label style={{ fontSize: 12, fontWeight: 700, color: 'var(--muted)', textTransform: 'uppercase', letterSpacing: '.05em' }}>Dokumente (Anlagen)</label>
                <button className="btn" style={{ padding: '5px 12px', fontSize: 12 }} onClick={() => docRef.current?.click()} disabled={uploadingDoc}>
                  {uploadingDoc ? '⏳ Lädt …' : '📎 PDF hinzufügen'}
                </button>
              </div>
              <input ref={docRef} type="file" accept=".pdf,.doc,.docx,.xls,.xlsx" onChange={handleDocumentUpload} style={{ display: 'none' }} />
              {(form.documents || []).length === 0 && (
                <p style={{ fontSize: 12, color: 'var(--muted)', fontStyle: 'italic' }}>Noch keine Dokumente – PDFs werden automatisch als Anlagen ins Angebot aufgenommen.</p>
              )}
              {(form.documents || []).map(doc => (
                <DocItem key={doc.id} doc={doc} onRemove={() => removeDocument(doc.id)} onTitleChange={updateDocTitle} />
              ))}
            </div>

            <div className="row">
              <button className="btn btn-red" onClick={handleSave} disabled={saving} style={{ flex: 1, justifyContent: 'center' }}>
                {saving ? '⏳ Speichert …' : '💾 Speichern'}
              </button>
              <button className="btn" onClick={cancelEdit}>Abbrechen</button>
            </div>
          </div>
        </div>
      )}

      {/* ── Tabelle mit Drag & Drop ─────────────────────────────────────────── */}
      {loading ? <p className="muted">Lädt …</p> : (
        <div className="card" style={{ padding: 0, overflow: 'hidden' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
            <thead>
              <tr style={{ borderBottom: '1px solid var(--line)', background: 'var(--bg)' }}>
                <th style={{ width: 36, padding: '12px 8px' }}></th>
                <th style={{ padding: '12px 8px', width: 60, textAlign: 'left', fontWeight: 700, color: 'var(--muted)' }}>Bild</th>
                <th style={{ padding: '12px 8px', textAlign: 'left', fontWeight: 700, color: 'var(--muted)' }}>Option</th>
                <th style={{ padding: '12px 8px', textAlign: 'left', fontWeight: 700, color: 'var(--muted)' }}>Cluster</th>
                <th style={{ padding: '12px 8px', textAlign: 'left', fontWeight: 700, color: 'var(--muted)' }}>Beschreibung</th>
                <th style={{ padding: '12px 8px', textAlign: 'right', fontWeight: 700, color: 'var(--muted)' }}>Preis</th>
                <th style={{ padding: '12px 8px', textAlign: 'center', fontWeight: 700, color: 'var(--muted)' }}>Aktiv</th>
                <th style={{ padding: '12px 8px', textAlign: 'right', fontWeight: 700, color: 'var(--muted)' }}></th>
              </tr>
            </thead>
            <DndContext sensors={sensors} collisionDetection={closestCenter} onDragEnd={handleDragEnd}>
              <SortableContext items={filtered.map(o => o.id)} strategy={verticalListSortingStrategy}>
                <tbody>
                  {filtered.map(o => (
                    <SortableRow key={o.id} o={o} onEdit={startEdit} onDelete={handleDelete} onToggleActive={toggleActive} />
                  ))}
                </tbody>
              </SortableContext>
            </DndContext>
          </table>
          {filtered.length === 0 && <p className="muted small" style={{ padding: 24 }}>Keine Optionen gefunden.</p>}
        </div>
      )}
    </div>
  )
}
