import { useState, useEffect } from 'react'
import { Routes, Route, NavLink, Navigate, useLocation } from 'react-router-dom'
import Messe         from './pages/Messe'
import Projekt       from './pages/Projekt'
import Konfiguration from './pages/Konfiguration'
import Bibliothek    from './pages/Bibliothek'
import Vorschau      from './pages/Vorschau'
import Angebote      from './pages/Angebote'

const NAV = [
  { group: 'Messe', items: [
    { to: '/messe',    icon: '🎯', label: 'Schnellerfassung' },
  ]},
  { group: 'Angebot', items: [
    { to: '/projekt',       icon: '👤', label: 'Kundendaten' },
    { to: '/konfiguration', icon: '🛠️', label: 'Konfiguration' },
    { to: '/vorschau',      icon: '👁️', label: 'PDF-Vorschau' },
  ]},
  { group: 'Stammdaten', items: [
    { to: '/angebote',   icon: '📋', label: 'Angebote' },
    { to: '/bibliothek', icon: '📚', label: 'Optionsbibliothek' },
  ]},
]

export default function App() {
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const location = useLocation()
  const [isMobile, setIsMobile] = useState(window.innerWidth < 768)

  useEffect(() => { setSidebarOpen(false) }, [location.pathname])

  useEffect(() => {
    const handler = () => setIsMobile(window.innerWidth < 768)
    window.addEventListener('resize', handler)
    return () => window.removeEventListener('resize', handler)
  }, [])

  const showSidebar = !isMobile || sidebarOpen

  return (
    <div className="layout">
      {isMobile && sidebarOpen && (
        <div onClick={() => setSidebarOpen(false)}
          style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,.4)', zIndex: 99 }} />
      )}

      {showSidebar && (
        <aside className="sidebar" style={isMobile ? {
          position: 'fixed', top: 0, left: 0, bottom: 0,
          width: 220, zIndex: 100, boxShadow: '4px 0 24px rgba(0,0,0,.15)',
        } : {}}>
          <div className="sidebar-logo">
            <div className="box">S</div>
            <span>Angebots­konfigurator</span>
            {isMobile && (
              <button onClick={() => setSidebarOpen(false)}
                style={{ marginLeft: 'auto', background: 'none', border: 'none', cursor: 'pointer', fontSize: 18, color: 'var(--muted)' }}>✕</button>
            )}
          </div>
          {NAV.map(group => (
            <div key={group.group}>
              <div className="nav-group-label">{group.group}</div>
              {group.items.map(item => (
                <NavLink key={item.to} to={item.to}
                  className={({ isActive }) => `nav-item${isActive ? ' active' : ''}`}>
                  <span className="icon">{item.icon}</span>
                  {item.label}
                </NavLink>
              ))}
            </div>
          ))}
        </aside>
      )}

      {isMobile && (
        <div style={{
          position: 'fixed', top: 0, left: 0, right: 0, height: 52,
          background: 'white', borderBottom: '1px solid var(--line)',
          display: 'flex', alignItems: 'center', padding: '0 16px', zIndex: 98, gap: 12,
        }}>
          <button onClick={() => setSidebarOpen(true)}
            style={{ background: 'none', border: 'none', cursor: 'pointer', fontSize: 22, color: 'var(--dark)', padding: '4px 8px', borderRadius: 8 }}>☰</button>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            <div style={{ width: 28, height: 28, background: 'var(--red)', borderRadius: 8, display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'white', fontWeight: 900, fontSize: 14 }}>S</div>
            <span style={{ fontSize: 13, fontWeight: 700 }}>Angebotskonfigurator</span>
          </div>
        </div>
      )}

      <main className="main" style={isMobile ? { marginLeft: 0, marginTop: 52, padding: '20px 16px' } : {}}>
        <Routes>
          <Route path="/"              element={<Navigate to="/messe" replace />} />
          <Route path="/messe"         element={<Messe />} />
          <Route path="/angebote"      element={<Angebote />} />
          <Route path="/projekt"       element={<Projekt />} />
          <Route path="/konfiguration" element={<Konfiguration />} />
          <Route path="/bibliothek"    element={<Bibliothek />} />
          <Route path="/vorschau"      element={<Vorschau />} />
        </Routes>
      </main>
    </div>
  )
}
