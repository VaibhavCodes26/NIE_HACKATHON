import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react';
import { T } from './data/translations';

const Ctx = createContext(null);
const KEY = 'np_lang';

export function I18nProvider({ children }) {
  const [lang, setLang] = useState(() => {
    try { const s = localStorage.getItem(KEY); if (T[s]) return s; } catch { /* storage unavailable */ }
    return 'en';
  });
  useEffect(() => {
    document.documentElement.lang = lang;
    try { localStorage.setItem(KEY, lang); } catch { /* ignore */ }
  }, [lang]);
  const t = useCallback((k) => T[lang]?.[k] ?? T.en[k] ?? k, [lang]);
  const value = useMemo(() => ({ lang, setLang, t }), [lang, t]);
  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}
export const useI18n = () => useContext(Ctx);
