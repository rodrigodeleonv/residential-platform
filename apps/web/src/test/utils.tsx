import { render, type RenderResult } from "@testing-library/react";
import { MemoryRouter } from "react-router";
import { vi } from "vitest";

import type { User } from "../api/types";
import { App } from "../App";

export const admin: User = {
  id: 1,
  email: "admin@example.com",
  full_name: "Alice Admin",
  phone: null,
  is_active: true,
  roles: ["admin"],
};

export const owner: User = {
  id: 2,
  email: "owner@example.com",
  full_name: "Olga Owner",
  phone: "555-0100",
  is_active: true,
  roles: ["owner"],
};

export function renderApp(path = "/"): RenderResult {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <App />
    </MemoryRouter>,
  );
}

interface MockResponse {
  status?: number;
  json?: unknown;
}

/**
 * Stub global fetch with canned responses keyed by "METHOD url".
 * An array is consumed in order (the last entry repeats).
 */
export function stubApi(routes: Record<string, MockResponse | MockResponse[]>) {
  const fetchMock = vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
    const url =
      typeof input === "string"
        ? input
        : input instanceof URL
          ? input.href
          : input.url;
    const key = `${init?.method ?? "GET"} ${url}`;
    const route = routes[key];
    if (route === undefined) {
      return Promise.reject(new Error(`unexpected request: ${key}`));
    }
    const next = Array.isArray(route)
      ? route.length > 1
        ? (route.shift() as MockResponse)
        : route[0]
      : route;
    const status = next.status ?? 200;
    return Promise.resolve({
      ok: status >= 200 && status < 300,
      status,
      statusText: `${status}`,
      json: () =>
        next.json !== undefined
          ? Promise.resolve(next.json)
          : Promise.reject(new Error("no body")),
    } as Response);
  });
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}
