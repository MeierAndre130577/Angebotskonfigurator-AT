import { OCRDropZone } from '../ocr/OCRDropZone';
import { CostDisplay } from '../ocr/CostDisplay';

export default function OCRTest() {
  return (
    <div style={{ maxWidth: 720, margin: '0 auto' }}>
      <h1 style={{ fontSize: 22, fontWeight: 700, marginBottom: 4 }}>OCR Test</h1>
      <p style={{ color: '#888', fontSize: 13, marginBottom: 24 }}>
        Bild hochladen oder hier ablegen — Claude Haiku extrahiert den Text per Vision-API.
      </p>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr', gap: 20 }}>
        {/* Kosten-Zähler */}
        <CostDisplay />

        {/* Drop-Zone + Ergebnis */}
        <OCRDropZone />
      </div>
    </div>
  );
}
