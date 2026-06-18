import { useState, useCallback, useEffect } from 'react';

const STORAGE_KEY = 'ocr_cost_tracker';
const DEFAULT_BUDGET = 1.00; // $

function load() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    return raw ? JSON.parse(raw) : null;
  } catch {
    return null;
  }
}

function save(data) {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(data));
}

/**
 * useCostTracker — verwaltet OCR-Kosten persistent im localStorage.
 *
 * Gibt zurück:
 *   spent      — bisher verbraucht ($)
 *   budget     — eingestelltes Budget ($)
 *   remaining  — verbleibendes Budget ($)
 *   callCount  — Anzahl der API-Aufrufe
 *   lastCost   — Kosten des letzten Aufrufs ($)
 *   addCost    — addCost(usd) → nach jedem OCR-Aufruf aufrufen
 *   setBudget  — setBudget(usd) → Budget anpassen
 *   reset      — Zähler zurücksetzen (Budget bleibt)
 */
export function useCostTracker() {
  const [state, setState] = useState(() => {
    const stored = load();
    return stored ?? { spent: 0, budget: DEFAULT_BUDGET, callCount: 0, lastCost: 0 };
  });

  useEffect(() => {
    save(state);
  }, [state]);

  const addCost = useCallback((usd) => {
    setState(prev => ({
      ...prev,
      spent: prev.spent + usd,
      callCount: prev.callCount + 1,
      lastCost: usd,
    }));
  }, []);

  const setBudget = useCallback((usd) => {
    setState(prev => ({ ...prev, budget: usd }));
  }, []);

  const reset = useCallback(() => {
    setState(prev => ({ ...prev, spent: 0, callCount: 0, lastCost: 0 }));
  }, []);

  return {
    spent: state.spent,
    budget: state.budget,
    remaining: Math.max(0, state.budget - state.spent),
    callCount: state.callCount,
    lastCost: state.lastCost,
    addCost,
    setBudget,
    reset,
  };
}
