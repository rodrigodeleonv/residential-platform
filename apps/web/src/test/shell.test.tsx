import { screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { admin, owner, renderApp, stubApi } from "./utils";

describe("role-aware shell", () => {
  it("shows the Users section to admins", async () => {
    stubApi({ "GET /api/v0/users/me": { json: admin } });
    renderApp("/");

    expect(await screen.findByRole("link", { name: "Users" })).toBeInTheDocument();
  });

  it("hides the Users section from residents", async () => {
    stubApi({ "GET /api/v0/users/me": { json: owner } });
    renderApp("/");

    expect(await screen.findByText("Hello, Olga Owner")).toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "Users" })).not.toBeInTheDocument();
  });

  it("sends a resident visiting /users back home", async () => {
    stubApi({ "GET /api/v0/users/me": { json: owner } });
    renderApp("/users");

    expect(await screen.findByText("Hello, Olga Owner")).toBeInTheDocument();
    expect(screen.queryByRole("table")).not.toBeInTheDocument();
  });
});
