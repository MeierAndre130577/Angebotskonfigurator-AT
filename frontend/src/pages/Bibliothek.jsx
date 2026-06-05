import { useState, useEffect, useRef } from 'react'
import { options as optionsApi, uploadImage } from '../lib/api'
import {
  DndContext, closestCenter, PointerSensor, TouchSensor,
  useSensor, useSensors, DragOverlay
} from '@dnd-kit/core'
import {
  SortableContext, verticalListSortingStrategy,
  useSortable, arrayMove
} from '@dnd-kit/sortable'
import { CSS } from '@dnd-kit/utilities'

const CLUSTERS = ['Farmer Shop', 'Wein Shop', 'Maxibar', 'Erweiterungen', 'Zahlungssysteme', 'Zubehör', 'Service', 'Sonstiges']

function money(n) {
  return new Intl.NumberFormat('de-AT', { style: 'currency', currency: 'EUR' }).format(n || 0)
}

const EMPTY = {
  name: '', cluster: 'Farmer Shop', display_type: 'Großes Bild + Beschreibung',
  short_text: '', long_text: '', price: 0, recurring: false, image_path: '', sort_order: 0
}

// ── Sortable Row ──────────────────────────────────────────────────────────────
function SortableRow({ o, index, onEdit, onDelete }) {
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } = useSortable({ id: o.id })

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
    opacity: isDragging ? 0.4 : 1,
    background: isDragging ? 'var(--red-light)' : 'white',
    borderBottom: '1px solid var(--line)',
  }

  return (
    <tr ref={setNodeRef} style={style}>
      {/* Drag Handle */}
      <td style={{ padding: '10px 12px', width: 40 }}>
        <div
          {...attributes}
          {...listeners}
          style={{
            cursor: 'grab', fontSize: 18, color: 'var(--muted)',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            width: 32, height: 32, borderRadius: 8,
            touchAction: 'none', userSelect: 'none',
          }}
          title="Halten und ziehen zum Sortieren"
        >
          ☰
        </div>
      </td>

      <td style={{ padding: '10px 12px', width: 60 }}>
        {o.image_path
          ? <img src={o.image_path} alt="" style={{ width: 48, height: 36, objectFit: 'cover', borderRadius: 6 }} />
          : <div style={{ width: 48, height: 36, background: 'var(--bg)', borderRadius: 6, border: '1px dashed var(--line)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 16 }}>📷</div>
        }
      </td>
      <td style={{ padding: '10px 12px' }}><b style={{ fontSize: 13 }}>{o.name}</b></td>
      <td style={{ padding: '10px 12px' }}><span className="pill">{o.cluster || '—'}</span></td>
      <td style={{ padding: '10px 12px', color: 'var(--muted)', maxWidth: 220, fontSize: 12 }}>
        <span style={{ display: '-webkit-box', WebkitLineClamp: 2, WebkitBoxOrient: 'vertical', overflow: 'hidden' }}>
          {o.short_text || '—'}
        </span>
      </td>
      <td style={{ padding: '10px 12px', textAlign: 'right', fontWeight: 700, fontSize: 13, whiteSpace: 'nowrap' }}>
        {o.price === 0
          ? <span style={{ color: 'var(--muted)' }}>inkl.</span>
          : o.recurring
            ? <span style={{ color: 'var(--red)' }}>{money(o.price)}/Mo.</span>
            : money(o.price)}
      </td>
      <td style={{ padding: '10px 12px', textAlign: 'right' }}>
        <div className="row" style={{ justifyContent: 'flex-end' }}>
          <button className="btn" style={{ padding: '6px 12px', fontSize: 12 }} onClick={() => onEdit(o)}>✏️</button>
          <button className="btn" style={{ padding: '6px 12px', fontSize: 12, color: 'var(--red)' }} onClick={() => onDelete(o.id)}>🗑️</button>
        </div>
      </td>
    </tr>
  )
}

// ── Main Component ────────────────────────────────────────────────────────────
export default function Bibliothek() {
  const [items, setItems]         = useState([])
  const [loading, setLoading]     = useState(true)
  const [search, setSearch]       = useState('')
  const [filterCluster, setFilter]= useState('')
  const [editing, setEditing]     = useState(null)
  const [form, setForm]           = useState(EMPTY)
  const [saving, setSaving]       = useState(false)
  const [uploading, setUploading] = useState(false)
  const [toast, setToast]         = useState('')
  const [activeId, setActiveId]   = useState(null)
  const fileRef                   = useRef()

  // Touch + Maus Support für Drag
  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 5 } }),
    useSensor(TouchSensor,   { activationConstraint: { delay: 200, tolerance: 5 } })
  )

  useEffect(() => { load() }, [])

  // Strg+V global abfangen wenn Modal offen
  useEffect(() => {
    if (!editing) return
    const handler = (e) => {
      const clipItems = e.clipboardData?.items
      if (!clipItems) return
      for (const item of clipItems) {
        if (item.type.startsWith('image/')) {
          e.preventDefault()
          const file = item.getAsFile()
          if (file) handleUploadFile(file)
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

  async function handleUploadFile(file) {
    setUploading(true)
    try {
      const url = await uploadImage(file)
      setForm(f => ({ ...f, image_path: url }))
      showToast('Bild hochgeladen ✓')
    } catch(e) {
      showToast('Bild-Upload fehlgeschlagen: ' + e.message)
    } finally {
      setUploading(false)
      if (fileRef.current) fileRef.current.value = ''
    }
  }

  function handleDrop(e) {
    e.preventDefault()
    const file = e.dataTransfer.files[0]
    if (file && file.type.startsWith('image/')) handleUploadFile(file)
  }

  // ── Drag End – neue Reihenfolge speichern ─────────────────────────────────
  async function handleDragEnd(event) {
    const { active, over } = event
    setActiveId(null)
    if (!over || active.id === over.id) return

    const oldIndex = filtered.findIndex(o => o.id === active.id)
    const newIndex = filtered.findIndex(o => o.id === over.id)
    const reordered = arrayMove(filtered, oldIndex, newIndex)

    // Optimistisch UI updaten
    const updatedItems = items.map(item => {
      const newPos = reordered.findIndex(r => r.id === item.id)
      return newPos >= 0 ? { ...item, sort_order: newPos } : item
    })
    setItems(updatedItems)

    // Im Backend speichern
    try {
      await Promise.all(
        reordered.map((o, idx) => optionsApi.upsert({ ...o, sort_order: idx }))
      )
      showToast('Reihenfolge gespeichert ✓')
    } catch(e) {
      showToast('Fehler beim Speichern der Reihenfolge')
      await load()
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
  const activeItem = activeId ? items.find(o => o.id === activeId) : null

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
          <p className="subtitle">{items.length} Optionen · ☰ Halten und ziehen zum Sortieren</p>
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

      {/* ── Edit Modal ──────────────────────────────────────────────────────── */}
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

            {/* Bild */}
            <div style={{ marginBottom: 20 }}>
              <label style={{ fontSize: 12, fontWeight: 700, color: 'var(--muted)', textTransform: 'uppercase', letterSpacing: '.05em', display: 'block', marginBottom: 8 }}>Bild</label>
              <div style={{ display: 'flex', gap: 16, alignItems: 'flex-start' }}>
                {form.image_path && (
                  <div style={{ position: 'relative', flex: 'none' }}>
                    <img src={form.image_path} alt="" style={{ width: 140, height: 100, objectFit: 'cover', borderRadius: 10, border: '1px solid var(--line)' }} />
                    <button onClick={() => setForm(f => ({ ...f, image_path: '' }))}
                      style={{ position: 'absolute', top: -8, right: -8, width: 22, height: 22, borderRadius: '50%', background: 'var(--red)', color: 'white', border: 'none', cursor: 'pointer', fontSize: 12, fontWeight: 900 }}>✕</button>
                  </div>
                )}
                <div
                  onDrop={handleDrop}
                  onDragOver={e => e.preventDefault()}
                  onClick={() => fileRef.current?.click()}
                  style={{
                    flex: 1, minHeight: 100, border: '2px dashed var(--line)', borderRadius: 12,
                    display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center',
                    cursor: 'pointer', background: 'var(--bg)', gap: 6, padding: 16,
                  }}
                  onMouseEnter={e => e.currentTarget.style.borderColor = 'var(--red)'}
                  onMouseLeave={e => e.currentTarget.style.borderColor = 'var(--line)'}
                >
                  {uploading
                    ? <p style={{ fontSize: 13, color: 'var(--muted)' }}>⏳ Lädt hoch …</p>
                    : <>
                        <span style={{ fontSize: 28 }}>📷</span>
                        <p style={{ fontSize: 13, fontWeight: 700 }}>Klicken oder Drag & Drop</p>
                        <p style={{ fontSize: 12, color: 'var(--muted)' }}>oder <b>Strg+V</b> aus Zwischenablage</p>
                      </>
                  }
                </div>
              </div>
              <input ref={fileRef} type="file" accept="image/*" onChange={e => { if(e.target.files[0]) handleUploadFile(e.target.files[0]) }} style={{ display: 'none' }} />
              <div style={{ marginTop: 8, padding: '8px 12px', background: 'var(--red-light)', borderRadius: 8, fontSize: 12, color: 'var(--red)', fontWeight: 600 }}>
                💡 Screenshot machen → <b>Strg+V</b> drücken → sofort hochgeladen
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

      {/* ── Tabelle mit Drag & Drop ──────────────────────────────────────────── */}
      {loading ? (
        <p className="muted">Lädt …</p>
      ) : (
        <div className="card" style={{ padding: 0, overflow: 'hidden' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
            <thead>
              <tr style={{ borderBottom: '1px solid var(--line)', background: 'var(--bg)' }}>
                <th style={{ padding: '12px 12px', width: 40 }}></th>
                <th style={{ padding: '12px 12px', width: 60, textAlign: 'left', fontWeight: 700, color: 'var(--muted)' }}>Bild</th>
                <th style={{ padding: '12px 12px', textAlign: 'left', fontWeight: 700, color: 'var(--muted)' }}>Option</th>
                <th style={{ padding: '12px 12px', textAlign: 'left', fontWeight: 700, color: 'var(--muted)' }}>Cluster</th>
                <th style={{ padding: '12px 12px', textAlign: 'left', fontWeight: 700, color: 'var(--muted)' }}>Kurzbeschreibung</th>
                <th style={{ padding: '12px 12px', textAlign: 'right', fontWeight: 700, color: 'var(--muted)' }}>Preis</th>
                <th style={{ padding: '12px 12px', textAlign: 'right', fontWeight: 700, color: 'var(--muted)' }}></th>
              </tr>
            </thead>
            <DndContext
              sensors={sensors}
              collisionDetection={closestCenter}
              onDragStart={({ active }) => setActiveId(active.id)}
              onDragEnd={handleDragEnd}
            >
              <SortableContext items={filtered.map(o => o.id)} strategy={verticalListSortingStrategy}>
                <tbody>
                  {filtered.map((o, index) => (
                    <SortableRow key={o.id} o={o} index={index} onEdit={startEdit} onDelete={handleDelete} />
                  ))}
                </tbody>
              </SortableContext>
            </DndContext>
          </table>
          {filtered.length === 0 && (
            <p className="muted small" style={{ padding: 24 }}>Keine Optionen gefunden.</p>
          )}
        </div>
      )}
    </div>
  )
}
