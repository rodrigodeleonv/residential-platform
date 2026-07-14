import "@testing-library/jest-dom/vitest";
import { cleanup } from "@testing-library/react";
import { afterEach, vi } from "vitest";

import i18n from "../i18n";

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
  localStorage.clear();
  void i18n.changeLanguage("en"); // jsdom reports en-US; keep tests deterministic
});
