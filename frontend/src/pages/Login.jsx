import { useState } from 'react'

const BASE = (import.meta.env.VITE_API_URL || '') + '/api'

export default function Login({ onLogin }) {
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError]       = useState('')
  const [busy, setBusy]         = useState(false)

  async function submit(e) {
    e.preventDefault()
    setError('')
    setBusy(true)
    try {
      const res = await fetch(`${BASE}/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username, password }),
      })
      if (res.ok) {
        localStorage.setItem('sielaff_auth', '1')
        onLogin()
      } else {
        setError('Falscher Benutzername oder Passwort.')
      }
    } catch {
      setError('Verbindungsfehler – bitte erneut versuchen.')
    } finally {
      setBusy(false)
    }
  }

  return (
    <div style={{
      minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center',
      background: 'var(--bg)', padding: 24,
    }}>
      <div style={{
        background: 'white', borderRadius: 20, padding: '40px 36px', width: '100%', maxWidth: 380,
        boxShadow: '0 8px 40px rgba(0,0,0,.10)', border: '1px solid var(--line)',
      }}>
        {/* Logo */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 32 }}>
          <div style={{
            width: 44, height: 44, background: 'var(--red)', borderRadius: 12,
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            color: 'white', fontWeight: 900, fontSize: 22, flexShrink: 0,
          }}>S</div>
          <div>
            <div style={{ fontWeight: 800, fontSize: 16, color: 'var(--dark)' }}>Angebotskonfigurator</div>
            <div style={{ fontSize: 12, color: 'var(--muted)' }}>Sielaff Austria GmbH</div>
          </div>
        </div>

        <form onSubmit={submit} style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
          <div className="field">
            <label>Benutzername</label>
            <input
              autoFocus
              autoComplete="username"
              value={username}
              onChange={e => setUsername(e.target.value)}
              placeholder="Benutzername"
              disabled={busy}
            />
          </div>

          <div className="field">
            <label>Passwort</label>
            <input
              type="password"
              autoComplete="current-password"
              value={password}
              onChange={e => setPassword(e.target.value)}
              placeholder="Passwort"
              disabled={busy}
            />
          </div>

          {error && (
            <div style={{
              background: '#fff1f2', border: '1px solid #fecaca', color: 'var(--red)',
              borderRadius: 8, padding: '8px 12px', fontSize: 13,
            }}>
              {error}
            </div>
          )}

          <button
            type="submit"
            className="btn btn-red"
            disabled={busy || !username || !password}
            style={{ marginTop: 4, width: '100%', justifyContent: 'center' }}
          >
            {busy ? 'Anmelden …' : 'Anmelden'}
          </button>
        </form>
      </div>
    </div>
  )
}
