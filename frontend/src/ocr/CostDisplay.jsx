import { useState } from 'react';
import { useCostTracker } from './useCostTracker';
import { formatUSD } from './costs';

/**
 * CostDisplay — zeigt Kosten-Zähler mit Budget-Einstellung.
 * Kann unabhängig vom OCRDropZone irgendwo in der App platziert werden.
 * Liest denselben localStorage-Schlüssel wie useCostTracker.
 */
export function CostDisplay() {
  const { spent, budget, remaining, callCount, lastCost, setBudget, reset } = useCostTracker();
  const [editingBudget, setEditingBudget] = useState(false);
  const [budgetInput, setBudgetInput] = useState('');

  const pct = budget > 0 ? Math.min(100, (spent / budget) * 100) : 0;
  const isWarning = pct >= 80;
  const isDanger = pct >= 100;

  const barColor = isDanger ? '#e74c3c' : isWarning ? '#f39c12' : '#27ae60';

  function confirmBudget() {
    const val = parseFloat(budgetInput.replace(',', '.'));
    if (!isNaN(val) && val > 0) setBudget(val);
    setEditingBudget(false);
  }

  return (
    <div style={styles.card}>
      <div style={styles.header}>
        <span style={styles.title}>💰 OCR-Kosten</span>
        <span style={styles.calls}>{callCount} Aufruf{callCount !== 1 ? 'e' : ''}</span>
      </div>

      {/* Fortschrittsbalken */}
      <div style={styles.barTrack}>
        <div style={{ ...styles.barFill, width: `${pct}%`, background: barColor }} />
      </div>

      {/* Zahlen */}
      <div style={styles.row}>
        <div style={styles.stat}>
          <span style={styles.label}>Verbraucht</span>
          <span style={{ ...styles.value, color: isDanger ? '#e74c3c' : '#333' }}>{formatUSD(spent)}</span>
        </div>
        <div style={styles.stat}>
          <span style={styles.label}>Verbleibend</span>
          <span style={{ ...styles.value, color: barColor }}>{formatUSD(remaining)}</span>
        </div>
        <div style={styles.stat}>
          <span style={styles.label}>Budget</span>
          {editingBudget ? (
            <div style={styles.budgetEdit}>
              <input
                autoFocus
                type="text"
                value={budgetInput}
                onChange={e => setBudgetInput(e.target.value)}
                onKeyDown={e => { if (e.key === 'Enter') confirmBudget(); if (e.key === 'Escape') setEditingBudget(false); }}
                style={styles.budgetInput}
                placeholder="z.B. 2.50"
              />
              <button style={styles.smallBtn} onClick={confirmBudget}>✓</button>
            </div>
          ) : (
            <span
              style={{ ...styles.value, cursor: 'pointer', textDecoration: 'underline dotted' }}
              title="Klicken um Budget zu ändern"
              onClick={() => { setBudgetInput(budget.toFixed(2)); setEditingBudget(true); }}
            >
              ${budget.toFixed(2)}
            </span>
          )}
        </div>
      </div>

      {/* Letzter Aufruf + Reset */}
      <div style={styles.footer}>
        {lastCost > 0 && <span style={styles.lastCost}>Letzter Aufruf: {formatUSD(lastCost)}</span>}
        <button style={styles.resetBtn} onClick={reset}>Zähler zurücksetzen</button>
      </div>

      {isDanger && (
        <div style={styles.warning}>⚠️ Budget überschritten</div>
      )}
    </div>
  );
}

const styles = {
  card: { background: '#fff', border: '1px solid #e0e0e0', borderRadius: '10px', padding: '14px 16px', display: 'flex', flexDirection: 'column', gap: '10px', minWidth: '260px' },
  header: { display: 'flex', justifyContent: 'space-between', alignItems: 'center' },
  title: { fontWeight: '600', fontSize: '14px' },
  calls: { fontSize: '12px', color: '#888' },
  barTrack: { height: '6px', background: '#eee', borderRadius: '3px', overflow: 'hidden' },
  barFill: { height: '100%', borderRadius: '3px', transition: 'width 0.4s ease, background 0.3s' },
  row: { display: 'flex', justifyContent: 'space-between' },
  stat: { display: 'flex', flexDirection: 'column', gap: '2px' },
  label: { fontSize: '11px', color: '#999', textTransform: 'uppercase', letterSpacing: '0.5px' },
  value: { fontSize: '15px', fontWeight: '600' },
  budgetEdit: { display: 'flex', gap: '4px', alignItems: 'center' },
  budgetInput: { width: '64px', fontSize: '13px', padding: '2px 4px', border: '1px solid #ccc', borderRadius: '4px' },
  smallBtn: { padding: '2px 6px', fontSize: '12px', cursor: 'pointer', borderRadius: '4px', border: '1px solid #ccc', background: '#fff' },
  footer: { display: 'flex', justifyContent: 'space-between', alignItems: 'center' },
  lastCost: { fontSize: '12px', color: '#888' },
  resetBtn: { fontSize: '12px', color: '#888', background: 'none', border: 'none', cursor: 'pointer', textDecoration: 'underline', padding: 0 },
  warning: { background: '#fff3cd', color: '#856404', fontSize: '12px', padding: '6px 10px', borderRadius: '6px' },
};
