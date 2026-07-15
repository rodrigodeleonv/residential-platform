import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";

import { owner, renderApp, stubApi } from "./utils";

const UNAUTHENTICATED = { status: 401, json: { detail: "Not authenticated" } };

describe("login", () => {
  it("signs in with an email code", async () => {
    stubApi({
      "GET /api/v0/users/me": [UNAUTHENTICATED, { json: owner }],
      "GET /api/v0/units/mine": { json: [] },
      "POST /api/v0/auth/request-code": { status: 202, json: { detail: "sent" } },
      "POST /api/v0/auth/verify": { json: { detail: "Logged in" } },
    });
    renderApp("/login");
    const user = userEvent.setup();

    await user.type(await screen.findByLabelText("Email"), "owner@example.com");
    await user.click(screen.getByRole("button", { name: "Send code" }));

    await user.type(await screen.findByLabelText("Login code"), "123456");
    await user.click(screen.getByRole("button", { name: "Sign in" }));

    expect(await screen.findByText("Hello, Olga Owner")).toBeInTheDocument();
  });

  it("shows an error for an invalid code", async () => {
    stubApi({
      "GET /api/v0/users/me": UNAUTHENTICATED,
      "POST /api/v0/auth/request-code": { status: 202, json: { detail: "sent" } },
      "POST /api/v0/auth/verify": {
        status: 401,
        json: { detail: "Invalid or expired credentials" },
      },
    });
    renderApp("/login");
    const user = userEvent.setup();

    await user.type(await screen.findByLabelText("Email"), "owner@example.com");
    await user.click(screen.getByRole("button", { name: "Send code" }));
    await user.type(await screen.findByLabelText("Login code"), "000000");
    await user.click(screen.getByRole("button", { name: "Sign in" }));

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Invalid or expired code",
    );
  });

  it("redirects unauthenticated visitors to the login screen", async () => {
    stubApi({ "GET /api/v0/users/me": UNAUTHENTICATED });
    renderApp("/");

    expect(await screen.findByLabelText("Email")).toBeInTheDocument();
  });

  it("logs out", async () => {
    stubApi({
      "GET /api/v0/users/me": { json: owner },
      "GET /api/v0/units/mine": { json: [] },
      "POST /api/v0/auth/logout": { status: 204 },
    });
    renderApp("/");
    const user = userEvent.setup();

    await user.click(await screen.findByRole("button", { name: "Log out" }));

    expect(await screen.findByLabelText("Email")).toBeInTheDocument();
  });
});
