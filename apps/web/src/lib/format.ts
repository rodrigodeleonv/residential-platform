import i18n from "../i18n";

export function formatMoney(amount: string, currency: string): string {
  if (!currency) return amount;
  return new Intl.NumberFormat(i18n.language, {
    style: "currency",
    currency,
  }).format(Number(amount));
}

/** Date-only ISO strings (2026-07-14) parse as UTC midnight; format them as UTC. */
export function formatDate(iso: string): string {
  return new Intl.DateTimeFormat(i18n.language, {
    dateStyle: "medium",
    timeZone: "UTC",
  }).format(new Date(iso));
}

export function formatDateTime(iso: string): string {
  return new Intl.DateTimeFormat(i18n.language, {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(iso));
}

/** Weekday name for the API's 0 = Monday indexing. */
export function weekdayName(index: number): string {
  const monday = Date.UTC(2024, 0, 1); // 2024-01-01 was a Monday
  return new Intl.DateTimeFormat(i18n.language, {
    weekday: "long",
    timeZone: "UTC",
  }).format(new Date(monday + index * 86_400_000));
}
