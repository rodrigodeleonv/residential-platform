import { fireEvent, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";

import { house, owner, renderApp, stubApi } from "./utils";

const ME = { "GET /api/v0/users/me": { json: owner } };
const MY_UNITS = { "GET /api/v0/units/mine": { json: [house] } };

describe("unit page", () => {
  it("lists vehicles and registers a new one", async () => {
    const vehicle = { id: 1, unit_id: 1, plate: "P123ABC", description: null };
    const added = { id: 2, unit_id: 1, plate: "P456DEF", description: "Red car" };
    const fetchMock = stubApi({
      ...ME,
      ...MY_UNITS,
      "GET /api/v0/units/1/parking-spots": {
        json: [{ id: 1, unit_id: 1, number: "P-1" }],
      },
      "GET /api/v0/units/1/vehicles": [
        { json: [vehicle] },
        { json: [vehicle, added] },
      ],
      "POST /api/v0/units/1/vehicles": { status: 201, json: added },
    });
    renderApp("/units/1");
    const user = userEvent.setup();

    expect(await screen.findByText("P123ABC")).toBeInTheDocument();
    expect(screen.getByText("P-1")).toBeInTheDocument();

    await user.type(screen.getByLabelText("Plate"), "P456DEF");
    await user.click(screen.getByRole("button", { name: "Register vehicle" }));

    expect(await screen.findByText("P456DEF")).toBeInTheDocument();
    const post = fetchMock.mock.calls.find(([, init]) => init?.method === "POST");
    expect(post?.[1]?.body).toContain("P456DEF");
  });

  it("shows the unit statement with the pending total", async () => {
    stubApi({
      ...ME,
      ...MY_UNITS,
      "GET /api/v0/units/1/parking-spots": { json: [] },
      "GET /api/v0/units/1/vehicles": { json: [] },
      "GET /api/v0/units/1/statement": {
        json: {
          currency: "GTQ",
          pending: [
            {
              id: 1,
              unit_id: 1,
              kind: "maintenance",
              description: "July fee",
              amount: "350.00",
              reservation_id: null,
              infraction_type_id: null,
              paid_at: null,
              voided_at: null,
              created_at: "2026-07-01T00:00:00Z",
              currency: "GTQ",
            },
          ],
          pending_total: "350.00",
          paid: [],
        },
      },
    });
    renderApp("/units/1");
    const user = userEvent.setup();

    await user.click(await screen.findByRole("tab", { name: "Statement" }));

    expect(await screen.findByText("July fee")).toBeInTheDocument();
    expect(screen.getByText(/Pending total/)).toHaveTextContent("350");
  });

  it("books an area slot", async () => {
    const area = {
      id: 5,
      name: "Pool",
      description: null,
      capacity: 2,
      fee: "50.00",
      is_active: true,
      currency: "GTQ",
    };
    const fetchMock = stubApi({
      ...ME,
      ...MY_UNITS,
      "GET /api/v0/units/1/parking-spots": { json: [] },
      "GET /api/v0/units/1/vehicles": { json: [] },
      "GET /api/v0/areas": { json: [area] },
      "GET /api/v0/units/1/reservations": [
        { json: [] },
        {
          json: [
            {
              id: 9,
              area_id: 5,
              unit_id: 1,
              user_id: 2,
              day: "2026-07-20",
              slot: "morning",
              fee: "50.00",
              canceled_at: null,
              currency: "GTQ",
            },
          ],
        },
      ],
      "GET /api/v0/areas/5/availability?day=2026-07-20": {
        json: [
          { slot: "morning", capacity: 2, booked: 0, available: 2 },
          { slot: "afternoon", capacity: 2, booked: 2, available: 0 },
          { slot: "evening", capacity: 2, booked: 0, available: 2 },
        ],
      },
      "POST /api/v0/units/1/reservations": { status: 201, json: {} },
    });
    renderApp("/units/1");
    const user = userEvent.setup();

    await user.click(await screen.findByRole("tab", { name: "Reservations" }));
    await user.selectOptions(await screen.findByLabelText("Area"), "5");
    fireEvent.change(screen.getByLabelText("Day"), {
      target: { value: "2026-07-20" },
    });

    const morning = await screen.findByRole("radio", { name: /Morning/ });
    expect(screen.getByRole("radio", { name: /Afternoon/ })).toBeDisabled();
    await user.click(morning);
    await user.click(screen.getByRole("button", { name: /Book/ }));

    expect(await screen.findByText(/Morning/, { selector: "td" })).toBeInTheDocument();
    const post = fetchMock.mock.calls.find(([, init]) => init?.method === "POST");
    expect(post?.[1]?.body).toContain('"slot":"morning"');
  });
});
