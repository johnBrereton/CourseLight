export const text = (value, max = 240) => typeof value === "string" && value.length > 0 && value.length <= max;
export const array = (value, max) => Array.isArray(value) && value.length <= max;
export const integer = (value, min, max) => Number.isSafeInteger(value) && value >= min && value <= max;
export const isoDate = value => typeof value === "string" && /^\d{4}-\d{2}-\d{2}$/.test(value) &&
  Number.isFinite(Date.parse(value)) && new Date(value).toISOString().slice(0, 10) === value;
export const mapConfig = value => value?.provider === "apple" && ["ready", "missing_token", "invalid_token"].includes(value.status);
export const place = value => value && text(value.id, 60) && /^[a-z0-9-]+$/.test(value.id) && text(value.name) && text(value.query, 400) &&
  (value.coordinate === null || value.coordinate && Number.isFinite(value.coordinate.latitude) && Math.abs(value.coordinate.latitude) <= 90 &&
    Number.isFinite(value.coordinate.longitude) && Math.abs(value.coordinate.longitude) <= 180);
