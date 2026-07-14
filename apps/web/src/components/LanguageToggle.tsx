import { useTranslation } from "react-i18next";

import { setLanguage, type Language } from "../i18n";

export function LanguageToggle() {
  const { i18n } = useTranslation();
  const next: Language = i18n.language.startsWith("es") ? "en" : "es";
  return (
    <button type="button" className="ghost" onClick={() => setLanguage(next)}>
      {next.toUpperCase()}
    </button>
  );
}
