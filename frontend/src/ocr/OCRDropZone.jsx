import { useRef, useState, useCallback } from 'react';
import { useOCR } from './useOCR';
import { useCostTracker } from './useCostTracker';

const ACCEPTED = ['image/jpeg', 'image/png'];

/**
 * OCRDropZone — Drag-&-Drop-Bereich + Bildvorschau + OCR-Ergebnis.
 *
 * Props:
 *   apiKey      — Anthropic API-Key (oder VITE_ANTHROPIC_API_KEY in .env)
 *   apiUrl      — URL eines Backend-Proxys (empfohlen für Produktion)
 *   model       — Claude-Modell (Standard: claude-haiku-4-5)
 *   onResult    — Callback(text) wenn Extraktion fertig
 *   placeholder — Text im Drop-Bereich (optional)
 */
export function OCRDropZone({ apiKey, apiUrl, model, onResult, placeholder }) {
  const { extract, result, loading, error, reset } = useOCR({ apiKey, apiUrl, model });
  const { addCost } = useCostTracker();
  const [preview, setPreview] = useState(null);
  const [dragging, setDragging] = useState(false);
  const inputRef = useRef(null);

  const handleFile = useCallback(async (file) => {
    if (!file || !ACCEPTED.includes(file.type)) return;
    setPreview(URL.createObjectURL(file));
    try {
      const { text, usage } = await extract(file);
      addCost(usage.cost);
      onResult?.(text);
    } catch (_) {
      // Fehler wird über error-State angezeigt
    }
  }, [extract, onResult]);

  const onDrop = useCallback((e) => {
    e.preventDefault();
    setDragging(false);
    const file = e.dataTransfer.files?.[0];
    handleFile(file);
  }, [handleFile]);

  const onInputChange = useCallback((e) => {
    handleFile(e.target.files?.[0]);
  }, [handleFile]);

  const handleReset = useCallback(() => {
    setPreview(null);
    reset();
    if (inputRef.current) inputRef.current.value = '';
  }, [reset]);

  const copyToClipboard = useCallback(() => {
    if (result) navigator.clipboard.writeText(result);
  }, [result]);

  return (
    <div style={styles.wrapper}>
      {/* Drop-Zone */}
      <div
        style={{ ...styles.dropZone, ...(dragging ? styles.dropZoneActive : {}) }}
        onClick={() => inputRef.current?.click()}
        onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
        onDragLeave={() => setDragging(false)}
        onDrop={onDrop}
      >
        <input
          ref={inputRef}
          type="file"
          accept="image/jpeg,image/png"
          style={{ display: 'none' }}
          onChange={onInputChange}
        />
        {preview ? (
          <img src={preview} alt="Vorschau" style={styles.preview} />
        ) : (
          <div style={styles.hint}>
            <span style={styles.icon}>🖼️</span>
            <span>{placeholder ?? 'Bild hierher ziehen oder klicken (JPG / PNG)'}</span>
          </div>
        )}
      </div>

      {/* Status */}
      {loading && <p style={styles.status}>⏳ Text wird erkannt…</p>}
      {error && <p style={styles.error}>⚠️ {error}</p>}

      {/* Ergebnis */}
      {result && (
        <div style={styles.resultBox}>
          <div style={styles.resultHeader}>
            <strong>Erkannter Text</strong>
            <div style={styles.actions}>
              <button style={styles.btn} onClick={copyToClipboard}>📋 Kopieren</button>
              <button style={{ ...styles.btn, ...styles.btnSecondary }} onClick={handleReset}>✖ Neu</button>
            </div>
          </div>
          <pre style={styles.resultText}>{result}</pre>
        </div>
      )}
    </div>
  );
}

const styles = {
  wrapper: { display: 'flex', flexDirection: 'column', gap: '12px' },
  dropZone: {
    border: '2px dashed #ccc',
    borderRadius: '8px',
    minHeight: '140px',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    cursor: 'pointer',
    padding: '16px',
    transition: 'border-color 0.2s, background 0.2s',
    background: '#fafafa',
    overflow: 'hidden',
  },
  dropZoneActive: { borderColor: '#4f8ef7', background: '#eef4ff' },
  hint: { display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '8px', color: '#888', fontSize: '14px' },
  icon: { fontSize: '32px' },
  preview: { maxWidth: '100%', maxHeight: '300px', borderRadius: '6px', objectFit: 'contain' },
  status: { margin: 0, color: '#555', fontSize: '14px' },
  error: { margin: 0, color: '#c0392b', fontSize: '14px' },
  resultBox: { border: '1px solid #e0e0e0', borderRadius: '8px', overflow: 'hidden' },
  resultHeader: { display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '8px 12px', background: '#f5f5f5', borderBottom: '1px solid #e0e0e0' },
  actions: { display: 'flex', gap: '8px' },
  btn: { padding: '4px 10px', fontSize: '13px', borderRadius: '4px', border: '1px solid #ccc', cursor: 'pointer', background: '#fff' },
  btnSecondary: { color: '#888' },
  resultText: { margin: 0, padding: '12px', whiteSpace: 'pre-wrap', fontSize: '14px', fontFamily: 'inherit', lineHeight: '1.5', maxHeight: '300px', overflowY: 'auto' },
};
