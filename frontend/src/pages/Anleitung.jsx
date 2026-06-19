import { useState, useEffect } from 'react'

export default function Anleitung() {
  const [manual, setManual]   = useState([])
  const [open, setOpen]       = useState({})

  useEffect(() => {
    fetch('/manual.json').then(r => r.json()).then(data => {
      setManual(data)
      // Ersten Eintrag standardmäßig öffnen
      if (data.length > 0) setOpen({ [data[0].id]: true })
    }).catch(() => {})
  }, [])

  function toggle(id) {
    setOpen(o => ({ ...o, [id]: !o[id] }))
  }

  return (
    <div style={{ maxWidth: 760 }}>
      <div className="page-header">
        <div>
          <h1>📖 Anleitung</h1>
          <p className="subtitle">Alle Funktionen erklärt – wird mit neuen Features aktualisiert</p>
        </div>
      </div>

      {manual.map(section => (
        <div key={section.id} className="card" style={{ marginBottom: 16, padding: 0, overflow: 'hidden' }}>

          {/* Header */}
          <div
            onClick={() => toggle(section.id)}
            style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between',
              padding: '16px 20px', cursor: 'pointer', userSelect: 'none',
              background: open[section.id] ? '#fff1f2' : 'white',
              borderBottom: open[section.id] ? '1px solid var(--line)' : 'none',
              transition: 'background .15s' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
              <span style={{ fontSize: 22 }}>{section.icon}</span>
              <span style={{ fontWeight: 800, fontSize: 16, color: 'var(--dark)' }}>{section.title}</span>
            </div>
            <span style={{ fontSize: 12, color: 'var(--muted)' }}>{open[section.id] ? '▲' : '▼'}</span>
          </div>

          {open[section.id] && (
            <div style={{ padding: '20px 24px' }}>

              {/* Intro */}
              {section.intro && (
                <p style={{ fontSize: 14, color: 'var(--text)', lineHeight: 1.7,
                  marginBottom: 20, paddingBottom: 16, borderBottom: '1px solid var(--line)' }}>
                  {section.intro}
                </p>
              )}

              {/* Steps */}
              {(section.steps || []).map((step, i) => (
                <div key={i} style={{ marginBottom: 20, display: 'flex', gap: 16 }}>
                  <div style={{ flexShrink: 0, width: 28, height: 28, borderRadius: '50%',
                    background: 'var(--red)', color: 'white', display: 'flex',
                    alignItems: 'center', justifyContent: 'center',
                    fontSize: 12, fontWeight: 800, marginTop: 1 }}>
                    {i + 1}
                  </div>
                  <div style={{ flex: 1 }}>
                    <div style={{ fontWeight: 700, fontSize: 14, color: 'var(--dark)', marginBottom: 6 }}>
                      {step.title}
                    </div>
                    <div style={{ fontSize: 13, color: 'var(--text)', lineHeight: 1.7, whiteSpace: 'pre-line' }}>
                      {step.text}
                    </div>
                  </div>
                </div>
              ))}

              {/* Tips */}
              {(section.tips || []).length > 0 && (
                <div style={{ background: '#fffbeb', border: '1px solid #fde68a',
                  borderRadius: 12, padding: '14px 18px', marginTop: 4 }}>
                  <div style={{ fontSize: 12, fontWeight: 800, color: '#92400e',
                    marginBottom: 8, textTransform: 'uppercase', letterSpacing: '.05em' }}>
                    💡 Tipps
                  </div>
                  {section.tips.map((tip, i) => (
                    <div key={i} style={{ display: 'flex', gap: 8, fontSize: 13,
                      color: '#78350f', lineHeight: 1.6, marginBottom: i < section.tips.length - 1 ? 6 : 0 }}>
                      <span style={{ flexShrink: 0, color: '#f59e0b', fontWeight: 700 }}>·</span>
                      {tip}
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>
      ))}

      {manual.length === 0 && (
        <p className="muted">Anleitung wird geladen …</p>
      )}
    </div>
  )
}
