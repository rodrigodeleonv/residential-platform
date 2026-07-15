import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";

import { guard, renderApp, stubApi } from "./utils";

describe("gatehouse", () => {
  it("finds a unit and registers an entry from a pre-registration", async () => {
    const prereg = {
      id: 4,
      unit_id: 1,
      created_by_id: 2,
      visitor_name: "Vicky Visitor",
      visitor_plate: "V111AAA",
      kind: "one_off",
      expiration_hours: 2,
      starts_at: "2026-07-14T20:00:00Z",
      weekday: null,
      time_of_day: null,
      valid_from: null,
      valid_until: null,
    };
    const visit = {
      id: 7,
      unit_id: 1,
      visitor_name: "Vicky Visitor",
      visitor_plate: "V111AAA",
      visitor_spot_id: 1,
      guard_id: 3,
      authorized_by_id: null,
      preregistration_id: 4,
      entered_at: "2026-07-14T20:05:00Z",
      exited_at: null,
    };
    const fetchMock = stubApi({
      "GET /api/v0/users/me": { json: guard },
      "GET /api/v0/units/mine": { json: [] },
      "GET /api/v0/gatehouse/units": {
        json: [{ unit_id: 1, kind: "house", number: "H-1", building_name: null }],
      },
      "GET /api/v0/visitor-parking-spots": { json: [{ id: 1, number: "V-1" }] },
      "GET /api/v0/gatehouse/visits?open_only=true": [
        { json: [] },
        { json: [visit] },
        { json: [] },
      ],
      "GET /api/v0/gatehouse/units/1": {
        json: {
          unit_id: 1,
          kind: "house",
          number: "H-1",
          building_name: null,
          residents: [{ user_id: 2, full_name: "Olga Owner", phone: "555-0100" }],
          plates: ["P123ABC"],
          parking_spot_numbers: ["P-1"],
        },
      },
      "GET /api/v0/gatehouse/units/1/active-preregistrations": { json: [prereg] },
      "POST /api/v0/gatehouse/visits": { status: 201, json: visit },
      "POST /api/v0/gatehouse/visits/7/exit": {
        json: { ...visit, exited_at: "2026-07-14T21:00:00Z" },
      },
    });
    renderApp("/gatehouse");
    const user = userEvent.setup();

    // find the unit and open its card
    await user.type(await screen.findByLabelText("Find unit"), "H-1");
    await user.click(screen.getByRole("button", { name: "H-1" }));
    expect(await screen.findByText(/Olga Owner \(555-0100\)/)).toBeInTheDocument();
    expect(screen.getByText(/P123ABC/)).toBeInTheDocument();

    // register the entry via flow B (valid pre-registration)
    await user.type(screen.getByLabelText("Visitor name"), "Vicky Visitor");
    await user.selectOptions(screen.getByLabelText("Visitor parking spot"), "1");
    await user.selectOptions(
      screen.getByLabelText("Authorization"),
      "Valid pre-registration",
    );
    await user.selectOptions(screen.getByLabelText("Pre-registration"), "4");
    await user.click(screen.getByRole("button", { name: "Enter" }));

    // the visitor now appears inside, and can be checked out
    const exitButton = await screen.findByRole("button", { name: "Register exit" });
    const post = fetchMock.mock.calls.find(
      ([url, init]) => init?.method === "POST" && String(url).endsWith("/visits"),
    );
    expect(post?.[1]?.body).toContain('"preregistration_id":4');
    expect(post?.[1]?.body).toContain('"authorized_by_user_id":null');

    await user.click(exitButton);
    expect(await screen.findByText("No visitors inside.")).toBeInTheDocument();
  });

  it("shows the gatehouse nav entry to guards only", async () => {
    stubApi({
      "GET /api/v0/users/me": { json: guard },
      "GET /api/v0/units/mine": { json: [] },
    });
    renderApp("/");

    expect(await screen.findByRole("link", { name: "Gatehouse" })).toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "Users" })).not.toBeInTheDocument();
  });
});
