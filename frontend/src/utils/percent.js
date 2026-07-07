export function toNumber(value) {
  const numberValue = Number(value);
  return Number.isFinite(numberValue) ? numberValue : null;
}

export function normalizePercent(value, { inputScale = 'percent' } = {}) {
  const numberValue = toNumber(value);
  if (numberValue === null) return null;

  if (inputScale === 'fraction') return numberValue * 100;
  if (inputScale === 'auto' && Math.abs(numberValue) <= 1 && numberValue !== 0) {
    return numberValue * 100;
  }

  return numberValue;
}

export function clampPercent(value, options = {}) {
  const percent = normalizePercent(value, options);
  if (percent === null) return 0;
  return Math.max(0, Math.min(100, percent));
}

export function formatPercent(value, digits = 1, options = {}) {
  const percent = normalizePercent(value, options);
  return percent === null ? 'N/A' : `${percent.toFixed(digits)}%`;
}
