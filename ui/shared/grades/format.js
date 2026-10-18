export const formatPercent = (value) => new Intl.NumberFormat(undefined, { maximumFractionDigits: 1 }).format(value);
export const requiredPercent = (value) => formatPercent(Math.ceil((value - 1e-9) * 10) / 10);
