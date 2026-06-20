from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.responses import StreamingResponse, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import sqlite3
import json
import uuid
import os
import io
import time
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(dotenv_path=Path(__file__).parent / ".env")

app = FastAPI(title="KI-Assistent")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Auf Render: /data (persistenter Disk), lokal: neben main.py
_data_dir = Path("/data") if Path("/data").exists() else Path(__file__).parent
DB_PATH = _data_dir / "assistant.db"

SYSTEM_PROMPT = """Du bist ein intelligenter KI-Assistent, spezialisiert auf Log-Analyse, Fehlerdiagnose und technischen Support.

Deine Kernfähigkeiten:
- Analysiere Logs, Stack Traces, Fehlermeldungen und Systemausgaben präzise
- Erkenne Muster in Logs und identifiziere die Wurzelursache (Root Cause) von Problemen
- Erkläre technische Probleme klar, strukturiert und lösungsorientiert
- Schlage konkrete, umsetzbare Lösungsschritte vor
- Merke dir alles, was der User dir sagt, beibringt oder als wichtig markiert

Formatierungsregeln:
- Nutze Markdown: Codeblöcke (```), Tabellen, Listen
- Bei Log-Analyse: Erst Zusammenfassung → dann kritische Fehler → dann Lösungsschritte
- Hebe kritische Fehler mit 🔴, Warnungen mit ⚠️, Erfolge mit ✅ hervor
- Nummeriere Lösungsschritte immer
- Wenn du dir nicht sicher bist, sage es explizit und erkläre warum

{memories}"""


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    c = conn.cursor()
    c.executescript("""
        CREATE TABLE IF NOT EXISTS sessions (
            id TEXT PRIMARY KEY,
            title TEXT,
            created_at TEXT,
            updated_at TEXT
        );
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT,
            role TEXT,
            content TEXT,
            timestamp TEXT
        );
        CREATE TABLE IF NOT EXISTS memories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            category TEXT DEFAULT 'general',
            content TEXT,
            created_at TEXT
        );
    """)
    conn.commit()
    conn.close()


init_db()


def build_memory_block():
    conn = get_db()
    rows = conn.execute("SELECT content FROM memories ORDER BY created_at").fetchall()
    conn.close()
    if not rows:
        return ""
    lines = "\n".join(f"- {r['content']}" for r in rows)
    return f"\n\nVom User gelerntes Wissen (immer beachten):\n{lines}"


DEMO_MODE = os.getenv("DEMO_MODE", "false").lower() == "true"

DEMO_RESPONSES = {
    "log": """## 🔍 Log-Analyse

**Zusammenfassung:** Ich habe deinen Log analysiert und folgende Auffälligkeiten gefunden:

---

### 🔴 Kritische Fehler (2)

```
ERROR 2024-01-15 14:32:11 - Connection timeout after 30s
java.net.SocketTimeoutException: Read timed out
    at sun.net.www.protocol.http.HttpClient.parseHTTPHeader(HttpClient.java:851)
    at com.myapp.service.ApiClient.call(ApiClient.java:112)
```

**Ursache:** Der API-Endpunkt antwortet nicht innerhalb des Timeouts. Klassisches Netzwerk- oder Last-Problem.

---

### ⚠️ Warnungen (3)

- Verbindungspool läuft voll (`pool size: 98/100`)
- Retry-Mechanismus wurde 5x ausgelöst
- Heap-Auslastung bei 87% kurz vor dem Timeout

---

### 🛠️ Lösungsschritte

1. **Timeout erhöhen** – aktuell 30s, empfohlen 60s für diesen Endpunkt
2. **Connection-Pool vergrößern** – `max-pool-size` von 100 auf 200 setzen
3. **Retry mit Backoff** – statt sofortigem Retry, 2-5s warten
4. **Gegenseite prüfen** – API-Endpunkt auf Last und Antwortzeiten monitoren

---

### ✅ Fazit

Das Problem liegt **nicht** in deinem Code, sondern an der Gegenstelle oder am Netzwerk. Erhöhe zuerst den Timeout und beobachte ob die Fehler abnehmen.""",

    "error": """## 🔴 Fehleranalyse

Ich habe den Fehler analysiert. Hier ist was ich gefunden habe:

**Root Cause:** `NullPointerException` – Ein Objekt wurde verwendet, bevor es initialisiert wurde.

### Betroffene Stelle

```java
// Zeile 247 in UserService.java
String email = user.getProfile().getEmail();  // ← user.getProfile() ist null!
```

### Warum passiert das?

Der User-Datensatz wurde aus der Datenbank geladen, aber das `Profile`-Objekt wird **lazy geladen** und war zum Zeitpunkt des Zugriffs noch nicht initialisiert.

### Lösung

```java
// Option 1: Null-Check
if (user.getProfile() != null) {
    String email = user.getProfile().getEmail();
}

// Option 2: Optional (empfohlen)
String email = Optional.ofNullable(user.getProfile())
    .map(Profile::getEmail)
    .orElse("keine E-Mail");

// Option 3: Eager Loading in der Query
@Query("SELECT u FROM User u JOIN FETCH u.profile WHERE u.id = :id")
User findByIdWithProfile(@Param("id") Long id);
```

**Empfehlung:** Option 3 ist am saubersten – lädt das Profil direkt mit.""",

    "default": """## 👋 Demo-Modus aktiv

Ich bin der **KI Log-Analyse Assistent** im Demo-Modus.

Im echten Betrieb (mit Anthropic API-Key) kann ich:

- 📋 **Beliebige Logs analysieren** – Apache, Nginx, Java, Python, Docker, K8s, ...
- 🔍 **Root Cause finden** – Nicht nur den Fehler, sondern die echte Ursache
- 🛠️ **Konkrete Fixes vorschlagen** – Mit Codebeispielen
- 💾 **Wissen merken** – Wenn du mir sagst wie dein System aufgebaut ist, behalte ich das
- 📎 **Log-Dateien analysieren** – Einfach anhängen, ich parse alles

### Teste die Demo-Funktionen:

Schreibe eine der folgenden Nachrichten um eine Beispiel-Analyse zu sehen:
- `"Analysiere diesen Log"` oder füge einen Log ein
- `"Fehler in meinem Code"` für eine Fehleranalyse
- `"Merke dir: ..."` um das Gedächtnis zu testen

---
*Um den echten Modus zu aktivieren: `ANTHROPIC_API_KEY` in `.env` eintragen und `DEMO_MODE=false` setzen.*"""
}


def get_demo_response(message: str) -> str:
    lower = message.lower()
    if any(w in lower for w in ["log", "analysier", "stack trace", "exception", "traceback", "```"]):
        return DEMO_RESPONSES["log"]
    elif any(w in lower for w in ["fehler", "error", "bug", "problem", "crash", "null"]):
        return DEMO_RESPONSES["error"]
    else:
        return DEMO_RESPONSES["default"]


MEMORY_TRIGGER_WORDS = [
    "merke dir", "remember", "merke:", "wichtig:", "beachte:", "wisse dass",
    "immer wenn", "nie wieder", "von nun an", "ab jetzt", "denke daran",
    "vergiss nicht", "notiere dir"
]


def auto_detect_memory(message: str) -> bool:
    lower = message.lower()
    return any(kw in lower for kw in MEMORY_TRIGGER_WORDS)


# ─── Models ────────────────────────────────────────────────────────────────────

class ChatRequest(BaseModel):
    session_id: str
    message: str


class MemoryRequest(BaseModel):
    content: str
    category: str = "general"


class SessionTitleRequest(BaseModel):
    title: str


# ─── Routes ────────────────────────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
async def root():
    html_path = Path(__file__).parent / "index.html"
    return HTMLResponse(html_path.read_text(encoding="utf-8"))


# Sessions

@app.post("/ai/sessions")
async def create_session():
    session_id = str(uuid.uuid4())
    now = datetime.now().isoformat()
    conn = get_db()
    conn.execute("INSERT INTO sessions VALUES (?,?,?,?)", (session_id, "Neue Unterhaltung", now, now))
    conn.commit()
    conn.close()
    return {"id": session_id, "title": "Neue Unterhaltung", "created_at": now}


@app.get("/ai/sessions")
async def list_sessions():
    conn = get_db()
    rows = conn.execute("SELECT * FROM sessions ORDER BY updated_at DESC").fetchall()
    conn.close()
    return [dict(r) for r in rows]


@app.delete("/ai/sessions/{session_id}")
async def delete_session(session_id: str):
    conn = get_db()
    conn.execute("DELETE FROM messages WHERE session_id=?", (session_id,))
    conn.execute("DELETE FROM sessions WHERE id=?", (session_id,))
    conn.commit()
    conn.close()
    return {"ok": True}


@app.get("/ai/sessions/{session_id}/messages")
async def get_messages(session_id: str):
    conn = get_db()
    rows = conn.execute(
        "SELECT role, content, timestamp FROM messages WHERE session_id=? ORDER BY id",
        (session_id,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# Chat

@app.get("/ai/mode")
async def get_mode():
    api_key = os.getenv("ANTHROPIC_API_KEY")
    demo = DEMO_MODE or not api_key
    return {"demo": demo, "has_key": bool(api_key)}


@app.post("/ai/chat")
async def chat(req: ChatRequest):
    api_key = os.getenv("ANTHROPIC_API_KEY")
    use_demo = DEMO_MODE or not api_key

    now = datetime.now().isoformat()
    conn = get_db()

    conn.execute(
        "INSERT INTO messages (session_id, role, content, timestamp) VALUES (?,?,?,?)",
        (req.session_id, "user", req.message, now)
    )

    if auto_detect_memory(req.message):
        conn.execute(
            "INSERT INTO memories (category, content, created_at) VALUES (?,?,?)",
            ("auto", req.message, now)
        )

    history = [
        {"role": r["role"], "content": r["content"]}
        for r in conn.execute(
            "SELECT role, content FROM messages WHERE session_id=? ORDER BY id",
            (req.session_id,)
        ).fetchall()
    ]

    msg_count = conn.execute(
        "SELECT COUNT(*) as c FROM messages WHERE session_id=?", (req.session_id,)
    ).fetchone()["c"]
    if msg_count == 1:
        title = req.message[:55] + ("…" if len(req.message) > 55 else "")
        conn.execute("UPDATE sessions SET title=?, updated_at=? WHERE id=?", (title, now, req.session_id))
    else:
        conn.execute("UPDATE sessions SET updated_at=? WHERE id=?", (now, req.session_id))

    conn.commit()
    conn.close()

    # ── DEMO MODE: stream fake response word-by-word ──────────────────────────
    if use_demo:
        response_text = get_demo_response(req.message)

        def generate_demo():
            words = response_text.split(" ")
            for i, word in enumerate(words):
                chunk = word + (" " if i < len(words) - 1 else "")
                yield f"data: {json.dumps({'text': chunk})}\n\n"
                time.sleep(0.018)

            conn2 = get_db()
            conn2.execute(
                "INSERT INTO messages (session_id, role, content, timestamp) VALUES (?,?,?,?)",
                (req.session_id, "assistant", response_text, datetime.now().isoformat())
            )
            conn2.commit()
            conn2.close()
            yield f"data: {json.dumps({'done': True})}\n\n"

        return StreamingResponse(generate_demo(), media_type="text/event-stream",
                                 headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})

    # ── REAL MODE: Claude API ─────────────────────────────────────────────────
    import anthropic
    memories = build_memory_block()
    system = SYSTEM_PROMPT.format(memories=memories)
    client = anthropic.Anthropic(api_key=api_key)

    def generate():
        full_response = ""
        try:
            with client.messages.stream(
                model="claude-haiku-4-5-20251001",
                max_tokens=8192,
                system=system,
                messages=history,
            ) as stream:
                for text in stream.text_stream:
                    full_response += text
                    yield f"data: {json.dumps({'text': text})}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)})}\n\n"
            return

        conn2 = get_db()
        conn2.execute(
            "INSERT INTO messages (session_id, role, content, timestamp) VALUES (?,?,?,?)",
            (req.session_id, "assistant", full_response, datetime.now().isoformat())
        )
        conn2.commit()
        conn2.close()
        yield f"data: {json.dumps({'done': True})}\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


# Memory

@app.get("/ai/memory")
async def get_memory():
    conn = get_db()
    rows = conn.execute("SELECT * FROM memories ORDER BY created_at DESC").fetchall()
    conn.close()
    return [dict(r) for r in rows]


@app.post("/ai/memory")
async def add_memory(req: MemoryRequest):
    conn = get_db()
    cur = conn.execute(
        "INSERT INTO memories (category, content, created_at) VALUES (?,?,?)",
        (req.category, req.content, datetime.now().isoformat())
    )
    conn.commit()
    mem_id = cur.lastrowid
    conn.close()
    return {"id": mem_id, "content": req.content, "category": req.category}


@app.delete("/ai/memory/{mem_id}")
async def delete_memory(mem_id: int):
    conn = get_db()
    conn.execute("DELETE FROM memories WHERE id=?", (mem_id,))
    conn.commit()
    conn.close()
    return {"ok": True}


# ── Document Upload & Knowledge Extraction ────────────────────────────────────

EXTRACT_PROMPT = """Analysiere das folgende Dokument und extrahiere ALLE relevanten Informationen daraus.

Regeln:
- Extrahiere jeden einzelnen Fakt, jede Konfiguration, jede Regel, jeden Wert, jedes Muster
- Schreibe jeden Fakt als eigenständigen, vollständigen Satz (kein Kontext nötig um ihn zu verstehen)
- Ignoriere Formatierung, Überschriften, Seitenzahlen
- Redundanz ist OK – lieber zu viel als zu wenig
- Keine Zusammenfassungen – konkrete Fakten

Antworte NUR mit einer JSON-Liste in diesem Format:
[
  "Fakt 1 als vollständiger Satz",
  "Fakt 2 als vollständiger Satz",
  ...
]

Dokument:
---
{text}
---"""


def extract_text_from_file(filename: str, content: bytes) -> str:
    ext = Path(filename).suffix.lower()

    if ext == ".pdf":
        try:
            import pypdf
            reader = pypdf.PdfReader(io.BytesIO(content))
            return "\n".join(page.extract_text() or "" for page in reader.pages)
        except ImportError:
            return content.decode("utf-8", errors="ignore")

    if ext in (".docx",):
        try:
            import docx
            doc = docx.Document(io.BytesIO(content))
            return "\n".join(p.text for p in doc.paragraphs)
        except ImportError:
            return content.decode("utf-8", errors="ignore")

    # txt, log, csv, json, xml, md, yaml, ...
    for enc in ("utf-8", "latin-1", "cp1252"):
        try:
            return content.decode(enc)
        except UnicodeDecodeError:
            continue
    return content.decode("utf-8", errors="ignore")


@app.post("/ai/upload")
async def upload_document(file: UploadFile = File(...)):
    api_key = os.getenv("ANTHROPIC_API_KEY")

    content = await file.read()
    text = extract_text_from_file(file.filename, content)

    if not text.strip():
        raise HTTPException(400, "Dokument ist leer oder konnte nicht gelesen werden.")

    # Truncate to ~60k chars to stay within context limits
    if len(text) > 60000:
        text = text[:60000] + "\n\n[... Dokument gekürzt ...]"

    # Demo mode: return fake extracted facts
    if DEMO_MODE or not api_key:
        demo_facts = [
            f"Datei '{file.filename}' wurde analysiert (Demo-Modus).",
            "Demo: Im echten Modus extrahiert Claude alle Fakten aus dem Dokument.",
            "Demo: Konfigurationen, Regeln und Werte werden als Memories gespeichert.",
            "Demo: Das Originaldokument wird nach der Extraktion verworfen.",
        ]
        conn = get_db()
        now = datetime.now().isoformat()
        for fact in demo_facts:
            conn.execute(
                "INSERT INTO memories (category, content, created_at) VALUES (?,?,?)",
                ("dokument", fact, now)
            )
        conn.commit()
        conn.close()
        return {"facts": demo_facts, "count": len(demo_facts), "demo": True}

    import anthropic
    client = anthropic.Anthropic(api_key=api_key)

    response = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=4096,
        messages=[{"role": "user", "content": EXTRACT_PROMPT.format(text=text)}],
    )

    raw = response.content[0].text.strip()

    # Parse JSON list of facts
    try:
        # Strip markdown code fences if present
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        facts = json.loads(raw)
        if not isinstance(facts, list):
            facts = [raw]
    except Exception:
        # Fallback: split by newlines
        facts = [line.strip("- •*").strip() for line in raw.split("\n") if line.strip()]

    # Save all facts as memories
    conn = get_db()
    now = datetime.now().isoformat()
    source_note = f"[Aus: {file.filename}] "
    for fact in facts:
        if fact.strip():
            conn.execute(
                "INSERT INTO memories (category, content, created_at) VALUES (?,?,?)",
                ("dokument", source_note + fact, now)
            )
    conn.commit()
    conn.close()

    return {"facts": facts, "count": len(facts), "filename": file.filename}
