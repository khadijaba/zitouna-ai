// French date / number formatting without registering an Angular locale (keeps the bundle small).

const DAY = new Intl.DateTimeFormat('fr-FR', { weekday: 'short', day: 'numeric', month: 'short', timeZone: 'UTC' });
const SHORT = new Intl.DateTimeFormat('fr-FR', { day: 'numeric', month: 'short', timeZone: 'UTC' });
const MONTH = new Intl.DateTimeFormat('fr-FR', { month: 'short', year: 'numeric', timeZone: 'UTC' });

/** "2026-10-17" -> "ven. 17 oct." */
export function frDay(isoDate: string): string {
  return DAY.format(new Date(isoDate));
}

/** "2026-10-17" -> "17 oct." */
export function frShortDate(isoDate: string): string {
  return SHORT.format(new Date(isoDate));
}

/** "2026-07-15" -> "juil. 2026" */
export function frMonth(isoDate: string): string {
  return MONTH.format(new Date(isoDate));
}

/** 1234.5 -> "1 234,5" (fractionDigits decimals). */
export function frNumber(value: number, fractionDigits = 0): string {
  return value.toLocaleString('fr-FR', { minimumFractionDigits: fractionDigits, maximumFractionDigits: fractionDigits });
}
