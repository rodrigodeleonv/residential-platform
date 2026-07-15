import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";

import { admin, house, renderApp, stubApi } from "./utils";

const ME = {
  "GET /api/v0/users/me": { json: admin },
  "GET /api/v0/units/mine": { json: [] },
};

describe("admin pages", () => {
  it("creates a house from the units admin page", async () => {
    const fetchMock = stubApi({
      ...ME,
      "GET /api/v0/buildings": { json: [] },
      "GET /api/v0/units": [{ json: [] }, { json: [house] }],
      "GET /api/v0/visitor-parking-spots": { json: [] },
      "POST /api/v0/units": { status: 201, json: house },
    });
    renderApp("/admin/units");
    const user = userEvent.setup();

    await user.type(await screen.findByLabelText("Number"), "H-1{Enter}");

    expect(await screen.findByText("H-1")).toBeInTheDocument();
    const post = fetchMock.mock.calls.find(([, init]) => init?.method === "POST");
    expect(post?.[1]?.body).toContain('"kind":"house"');
  });

  it("marks a pending charge as paid", async () => {
    const charge = {
      id: 3,
      unit_id: 1,
      kind: "fine",
      description: "Noise",
      amount: "100.00",
      reservation_id: null,
      infraction_type_id: 1,
      paid_at: null,
      voided_at: null,
      created_at: "2026-07-10T00:00:00Z",
      currency: "GTQ",
    };
    stubApi({
      ...ME,
      "GET /api/v0/infractions": { json: [] },
      "GET /api/v0/units": { json: [house] },
      "GET /api/v0/charges?status=pending": [{ json: [charge] }, { json: [] }],
      "POST /api/v0/charges/3/pay": {
        json: { ...charge, paid_at: "2026-07-14T00:00:00Z" },
      },
    });
    renderApp("/admin/billing");
    const user = userEvent.setup();

    await user.click(await screen.findByRole("button", { name: "Mark paid" }));

    expect(await screen.findByText("No records")).toBeInTheDocument();
  });
});
