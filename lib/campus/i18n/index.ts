import { campusNames } from './names.ts';
import { englishMessages } from './messages.ts';
export type Locale = 'zh' | 'en';
export type Message =
  | string
  | { text: string; values?: Record<string, string | number> };
export const LOCALE_STORAGE_KEY = 'gxu-campus.locale.v1';
export function isLocale(value: unknown): value is Locale {
  return value === 'zh' || value === 'en';
}
/** Source names may use a middle dot as a separator; the UI never shows it. */
function withoutMiddleDot(name: string, locale: Locale): string {
  return name.replace(/\s*·\s*/g, locale === 'en' ? ', ' : ' ');
}
export function placeName(source: string, locale: Locale): string {
  return withoutMiddleDot(
    campusNames[source]?.[locale === 'en' ? 1 : 0] ?? source,
    locale,
  );
}
export function translate(
  locale: Locale,
  source: string,
  values: Record<string, string | number> = {},
): string {
  const singular =
    values.count === 1
      ? source === '{count} 个结果'
        ? '{count} result'
        : source === '{count} 处' || source === '{count} 个地点'
          ? '{count} place'
          : undefined
      : undefined;
  const text =
    locale === 'en' ? (singular ?? englishMessages[source] ?? source) : source;
  return text.replace(/\{(\w+)\}/g, (token, key: string) =>
    String(values[key] ?? token),
  );
}
/** Load progress carries data, not a pre-translated string, so switching language is immediate. */
export function statusText(locale: Locale, message: Message): string {
  if (typeof message === 'string') return translate(locale, message);
  const values = { ...message.values };
  if (typeof values.name === 'string')
    values.name = translate(locale, placeName(values.name, locale));
  if (typeof values.label === 'string')
    values.label = translate(locale, values.label);
  return translate(locale, message.text, values);
}
