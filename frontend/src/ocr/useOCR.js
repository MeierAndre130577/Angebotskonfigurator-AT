import { useState, useCallback } from 'react';
import { calcCost } from './costs';

const PROMPT = 'Extrahiere den gesamten lesbaren Text aus diesem Bild. Gib nur den reinen Text zurück, behalte sinnvolle Zeilenumbrüche und Struktur bei. Ohne Kommentare oder Erklärungen.';

function fileToBase64(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(reader.result.split(',')[1]);
    reader.onerror = reject;
    reader.readAsDataURL(file);
  });
}

/**
 * useOCR — extrahiert Text aus Bildern via Claude Vision.
 *
 * Config-Optionen (mind. eine angeben):
 *   apiKey  — Anthropic API-Key (alternativ: VITE_ANTHROPIC_API_KEY in .env)
 *   apiUrl  — URL eines eigenen Backend-Proxys (empfohlen für Produktion)
 *   model   — Claude-Modell (Standard: claude-haiku-4-5)
 */
export function useOCR({ apiKey, apiUrl, model = 'claude-haiku-4-5' } = {}) {
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [lastUsage, setLastUsage] = useState(null); // { inputTokens, outputTokens, cost }

  const extract = useCallback(async (file) => {
    if (!file) return;
    setLoading(true);
    setError(null);

    try {
      const base64 = await fileToBase64(file);
      const mediaType = file.type; // image/jpeg | image/png

      let text;
      let inputTokens = 0;
      let outputTokens = 0;

      if (apiUrl) {
        // Backend-Proxy (API-Key bleibt serverseitig)
        const res = await fetch(apiUrl, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ image: base64, mediaType }),
        });
        if (!res.ok) throw new Error(`Proxy-Fehler: ${res.status}`);
        const data = await res.json();
        text = data.text;
        // Proxy sollte usage mitliefern: { text, inputTokens, outputTokens }
        inputTokens = data.inputTokens ?? 0;
        outputTokens = data.outputTokens ?? 0;
      } else {
        // Direkter Browser-Aufruf (nur für interne Tools / Entwicklung)
        const key = apiKey || import.meta.env.VITE_ANTHROPIC_API_KEY;
        if (!key) throw new Error('Kein API-Key gefunden. apiKey-Prop oder VITE_ANTHROPIC_API_KEY setzen.');

        const res = await fetch('https://api.anthropic.com/v1/messages', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'x-api-key': key,
            'anthropic-version': '2023-06-01',
            'anthropic-dangerous-direct-browser-access': 'true',
          },
          body: JSON.stringify({
            model,
            max_tokens: 4096,
            messages: [{
              role: 'user',
              content: [
                { type: 'image', source: { type: 'base64', media_type: mediaType, data: base64 } },
                { type: 'text', text: PROMPT },
              ],
            }],
          }),
        });
        if (!res.ok) {
          const err = await res.json();
          throw new Error(err.error?.message || `API-Fehler: ${res.status}`);
        }
        const data = await res.json();
        text = data.content?.[0]?.text ?? '';
        inputTokens = data.usage?.input_tokens ?? 0;
        outputTokens = data.usage?.output_tokens ?? 0;
      }

      const cost = calcCost(model, inputTokens, outputTokens);
      const usage = { inputTokens, outputTokens, cost };
      setLastUsage(usage);
      setResult(text);
      return { text, usage };
    } catch (err) {
      setError(err.message);
      throw err;
    } finally {
      setLoading(false);
    }
  }, [apiKey, apiUrl, model]);

  const reset = useCallback(() => {
    setResult(null);
    setError(null);
    setLastUsage(null);
  }, []);

  return { extract, result, loading, error, lastUsage, reset };
}
