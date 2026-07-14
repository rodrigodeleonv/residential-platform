import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";

import { renderApp, stubApi } from "./utils";

describe("i18n", () => {
  it("switches between English and Spanish and remembers the choice", async () => {
    stubApi({
      "GET /api/v0/users/me": { status: 401, json: { detail: "Not authenticated" } },
    });
    renderApp("/login");
    const user = userEvent.setup();

    expect(await screen.findByLabelText("Email")).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "ES" }));

    expect(await screen.findByLabelText("Correo electrónico")).toBeInTheDocument();
    expect(localStorage.getItem("language")).toBe("es");
  });
});
