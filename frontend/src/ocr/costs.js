// Preise in $ pro Token (Stand: claude-api skill, Juni 2026)
export const PRICING = {
  'claude-haiku-4-5':  { input: 1.00 / 1_000_000, output: 5.00  / 1_000_000 },
  'claude-sonnet-4-6': { input: 3.00 / 1_000_000, output: 15.00 / 1_000_000 },
  'claude-opus-4-8':   { input: 5.00 / 1_000_000, output: 25.00 / 1_000_000 },
};

export function calcCost(model, inputTokens, outputTokens) {
  const p = PRICING[model] ?? PRICING['claude-haiku-4-5'];
  return p.input * inputTokens + p.output * outputTokens;
}

export function formatUSD(amount) {
  if (amount < 0.01) return `$${(amount * 100).toFixed(3)} ¢`;
  return `$${amount.toFixed(4)}`;
}
