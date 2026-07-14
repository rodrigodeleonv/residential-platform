import { screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { admin, owner, renderApp, stubApi } from "./utils";

describe("users page", () => {
  it("lists all users for an admin", async () => {
    stubApi({
      "GET /api/v0/users/me": { json: admin },
      "GET /api/v0/users": { json: [admin, owner] },
    });
    renderApp("/users");

    const table = await screen.findByRole("table");
    expect(within(table).getByText("owner@example.com")).toBeInTheDocument();
    expect(within(table).getByText("Alice Admin")).toBeInTheDocument();
    expect(within(table).getByText("Owner")).toBeInTheDocument();
  });
});
