# Angebotskonfigurator v3 – Prototyp

**Stack:** FastAPI (Backend) · React + Vite (Frontend) · SQLite lokal → Supabase Produktion

---

## Lokaler Start (Entwicklung)

### 1. Backend

```bash
cd backend
pip install -r requirements.txt
python run.py
# läuft auf http://localhost:8000
```

### 2. Frontend

```bash
cd frontend
npm install
npm run dev
# läuft auf http://localhost:5173
```

Beide Fenster offen lassen – Vite leitet `/api`-Requests automatisch ans Backend weiter.

---

## Umgebungsvariablen

```bash
# backend/.env  (Datei erstellen, .env.example als Vorlage)
# Leer lassen für lokale SQLite-Entwicklung
# Supabase-Keys eintragen wenn Produktion:
# SUPABASE_URL=https://DEIN-PROJEKT.supabase.co
# SUPABASE_SERVICE_KEY=eyJ...
```

---

## Projektstruktur

```
angebotskonfigurator/
├── backend/
│   ├── main.py          ← FastAPI Routen
│   ├── db.py            ← Datenbank (SQLite lokal / Supabase Prod)
│   ├── pdf.py           ← PDF-Generierung
│   ├── run.py           ← Starten
│   ├── .env.example
│   └── requirements.txt
│
└── frontend/
    ├── src/
    │   ├── pages/
    │   │   ├── Messe.jsx          ✅ fertig
    │   │   ├── Bibliothek.jsx     ✅ fertig
    │   │   ├── Projekt.jsx        🚧 Platzhalter
    │   │   ├── Konfiguration.jsx  🚧 Platzhalter
    │   │   └── Vorschau.jsx       🚧 Platzhalter
    │   ├── lib/
    │   │   └── api.js             ← alle API-Calls zentral
    │   ├── App.jsx
    │   ├── main.jsx
    │   └── index.css
    ├── index.html
    ├── vite.config.js
    └── package.json
```

---

## Nächste Schritte

1. ✅ Backend + Frontend lokal testen
2. 🚧 Screens: Projekt, Konfiguration, Vorschau ausbauen
3. 🔜 Supabase anbinden (`.env` befüllen)
4. 🔜 GitHub Repo erstellen, pushen
5. 🔜 Render Deploy
