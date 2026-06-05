import { Routes, Route, NavLink, Navigate } from 'react-router-dom'
import Messe       from './pages/Messe'
import Projekt     from './pages/Projekt'
import Konfiguration from './pages/Konfiguration'
import Bibliothek  from './pages/Bibliothek'
import Vorschau    from './pages/Vorschau'

const NAV = [
  { group: 'Messe', items: [
    { to: '/messe',         icon: '🎯', label: 'Schnellerfassung' },
  ]},
  { group: 'Angebot', items: [
    { to: '/projekt',       icon: '👤', label: 'Kundendaten' },
    { to: '/konfiguration', icon: '🛠️', label: 'Konfiguration' },
    { to: '/vorschau',      icon: '👁️', label: 'PDF-Vorschau' },
  ]},
  { group: 'Stammdaten', items: [
    { to: '/bibliothek',    icon: '📚', label: 'Optionsbibliothek' },
  ]},
]

export default function App() {
  return (
    <div className="layout">
      {/* ── Sidebar ── */}
      <aside className="sidebar">
        <div className="sidebar-logo">
          <div className="box">S</div>
          <span>Angebots­konfigurator</span>
        </div>

        {NAV.map(group => (
          <div key={group.group}>
            <div className="nav-group-label">{group.group}</div>
            {group.items.map(item => (
              <NavLink
                key={item.to}
                to={item.to}
                className={({ isActive }) => `nav-item${isActive ? ' active' : ''}`}
              >
                <span className="icon">{item.icon}</span>
                {item.label}
              </NavLink>
            ))}
          </div>
        ))}
      </aside>

      {/* ── Main Content ── */}
      <main className="main">
        <Routes>
          <Route path="/"              element={<Navigate to="/messe" replace />} />
          <Route path="/messe"         element={<Messe />} />
          <Route path="/projekt"       element={<Projekt />} />
          <Route path="/konfiguration" element={<Konfiguration />} />
          <Route path="/bibliothek"    element={<Bibliothek />} />
          <Route path="/vorschau"      element={<Vorschau />} />
        </Routes>
      </main>
    </div>
  )
}
