'use client';
import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from 'react';
import {
  isLocale,
  LOCALE_STORAGE_KEY,
  placeName,
  translate,
  type Locale,
} from '@/lib/campus/i18n';

const LocaleContext = createContext({
  locale: 'zh' as Locale,
  setLocale: (_locale: Locale) => {},
  t: (source: string, values?: Record<string, string | number>) =>
    translate('zh', source, values),
  name: (source: string) => placeName(source, 'zh'),
});
export function CampusLocaleProvider({ children }: { children: ReactNode }) {
  // Match the static Chinese document for hydration; restore preference after mount.
  const [locale, setLocale] = useState<Locale>('zh');
  const [restored, setRestored] = useState(false);
  useEffect(() => {
    const requested = new URLSearchParams(location.search).get('lang');
    let saved: string | null = null;
    try {
      saved = localStorage.getItem(LOCALE_STORAGE_KEY);
    } catch {
      /* Storage may be disabled. */
    }
    let active = true;
    queueMicrotask(() => {
      if (!active) return;
      setLocale(
        isLocale(requested) ? requested : isLocale(saved) ? saved : 'zh',
      );
      setRestored(true);
    });
    return () => {
      active = false;
    };
  }, []);
  useEffect(() => {
    if (!restored) return;
    document.documentElement.lang = locale === 'zh' ? 'zh-CN' : 'en';
    document.title = translate(locale, '广西大学 校园地图');
    document
      .querySelector('meta[name="description"]')
      ?.setAttribute(
        'content',
        translate(
          locale,
          '广西大学主校区三维地图，支持地标搜索、游览和昼夜切换。使用 Three.js 和 Blender 制作。',
        ),
      );
    try {
      localStorage.setItem(LOCALE_STORAGE_KEY, locale);
    } catch {
      /* The in-memory switch still works. */
    }
  }, [locale, restored]);
  const changeLocale = useCallback((next: Locale) => {
    setLocale(next);
    const url = new URL(location.href);
    url.searchParams.set('lang', next);
    history.replaceState(history.state, '', url);
  }, []);
  const value = useMemo(
    () => ({
      locale,
      setLocale: changeLocale,
      t: (source: string, values?: Record<string, string | number>) =>
        translate(locale, source, values),
      name: (source: string) => placeName(source, locale),
    }),
    [locale, changeLocale],
  );
  return (
    <LocaleContext.Provider value={value}>{children}</LocaleContext.Provider>
  );
}
export function useCampusLocale() {
  return useContext(LocaleContext);
}
