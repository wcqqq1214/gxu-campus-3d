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
function readInitialLocale(): Locale {
  const requested = new URLSearchParams(location.search).get('lang');
  if (isLocale(requested)) return requested;
  try {
    const saved = localStorage.getItem(LOCALE_STORAGE_KEY);
    if (isLocale(saved)) return saved;
  } catch {
    /* Storage may be disabled. */
  }
  return 'zh';
}
export function CampusLocaleProvider({ children }: { children: ReactNode }) {
  const [locale, setLocale] = useState<Locale>(readInitialLocale);
  useEffect(() => {
    document.documentElement.lang = locale === 'zh' ? 'zh-CN' : 'en';
    document.title = translate(locale, '广西大学 校园地图');
    document
      .querySelector('meta[name="description"]')
      ?.setAttribute(
        'content',
        translate(
          locale,
          '广西大学主校区三维地图，支持地点与建筑搜索、多视角浏览、校园游览与昼夜切换。使用 Three.js 和 Blender 制作。',
        ),
      );
    try {
      localStorage.setItem(LOCALE_STORAGE_KEY, locale);
    } catch {
      /* The in-memory switch still works. */
    }
  }, [locale]);
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
