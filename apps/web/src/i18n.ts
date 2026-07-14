import i18n from "i18next";
import { initReactI18next } from "react-i18next";

import en from "./locales/en.json";
import es from "./locales/es.json";

export type Language = "es" | "en";

const stored = localStorage.getItem("language");
const browserDefault: Language = navigator.language.toLowerCase().startsWith("es")
  ? "es"
  : "en";

void i18n.use(initReactI18next).init({
  resources: { es: { translation: es }, en: { translation: en } },
  lng: stored ?? browserDefault,
  fallbackLng: "es",
  interpolation: { escapeValue: false }, // react already escapes
});

export function setLanguage(language: Language): void {
  localStorage.setItem("language", language);
  void i18n.changeLanguage(language);
}

export default i18n;
