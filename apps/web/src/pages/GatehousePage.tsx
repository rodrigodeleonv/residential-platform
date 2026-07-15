import { useState, type FormEvent } from "react";
import { useTranslation } from "react-i18next";

import { api, ApiError } from "../api/client";
import type {
  GatehouseUnitCard,
  GatehouseUnitSummary,
  PreRegistration,
  Visit,
  VisitorParkingSpot,
} from "../api/types";
import { ErrorMessage } from "../components/ErrorMessage";
import { useApiData } from "../hooks/useApiData";
import { formatDateTime } from "../lib/format";

function unitLabel(unit: GatehouseUnitSummary): string {
  return unit.building_name !== null
    ? `${unit.building_name} · ${unit.number}`
    : unit.number;
}

export function GatehousePage() {
  const { t } = useTranslation();
  const units = useApiData<GatehouseUnitSummary[]>("/gatehouse/units");
  const spots = useApiData<VisitorParkingSpot[]>("/visitor-parking-spots");
  const openVisits = useApiData<Visit[]>("/gatehouse/visits?open_only=true");
  const [query, setQuery] = useState("");
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const card = useApiData<GatehouseUnitCard>(
    selectedId !== null ? `/gatehouse/units/${selectedId}` : null,
  );
  const preregs = useApiData<PreRegistration[]>(
    selectedId !== null
      ? `/gatehouse/units/${selectedId}/active-preregistrations`
      : null,
  );

  const [visitorName, setVisitorName] = useState("");
  const [visitorPlate, setVisitorPlate] = useState("");
  const [spotId, setSpotId] = useState("");
  const [flow, setFlow] = useState<"A" | "B">("A");
  const [residentId, setResidentId] = useState("");
  const [preregId, setPreregId] = useState("");
  const [actionError, setActionError] = useState<ApiError | null>(null);

  const matches =
    query.trim() === ""
      ? []
      : (units.data ?? []).filter((unit) =>
          unitLabel(unit).toLowerCase().includes(query.trim().toLowerCase()),
        );
  const busySpotIds = new Set(
    (openVisits.data ?? [])
      .map((visit) => visit.visitor_spot_id)
      .filter((id) => id !== null),
  );
  const unitName = (id: number) => {
    const unit = units.data?.find((u) => u.unit_id === id);
    return unit !== undefined ? unitLabel(unit) : `#${id}`;
  };

  async function registerEntry(event: FormEvent) {
    event.preventDefault();
    setActionError(null);
    try {
      await api("/gatehouse/visits", {
        method: "POST",
        body: JSON.stringify({
          unit_id: selectedId,
          visitor_name: visitorName,
          visitor_plate: visitorPlate || null,
          visitor_spot_id: spotId ? Number(spotId) : null,
          authorized_by_user_id: flow === "A" ? Number(residentId) : null,
          preregistration_id: flow === "B" ? Number(preregId) : null,
        }),
      });
      setVisitorName("");
      setVisitorPlate("");
      setSpotId("");
      openVisits.reload();
    } catch (error) {
      if (error instanceof ApiError) setActionError(error);
    }
  }

  async function registerExit(visitId: number) {
    setActionError(null);
    try {
      await api(`/gatehouse/visits/${visitId}/exit`, { method: "POST" });
      openVisits.reload();
    } catch (error) {
      if (error instanceof ApiError) setActionError(error);
    }
  }

  return (
    <section>
      <h2>{t("nav.gatehouse")}</h2>
      <ErrorMessage error={units.error} />

      <label htmlFor="gatehouse-search">{t("gatehouse.findUnit")}</label>{" "}
      <input
        id="gatehouse-search"
        placeholder={t("gatehouse.searchPlaceholder")}
        value={query}
        onChange={(event) => setQuery(event.target.value)}
      />
      {matches.length > 0 && (
        <ul className="chips">
          {matches.slice(0, 10).map((unit) => (
            <li key={unit.unit_id}>
              <button
                type="button"
                className="ghost"
                onClick={() => {
                  setSelectedId(unit.unit_id);
                  setQuery("");
                }}
              >
                {unitLabel(unit)}
              </button>
            </li>
          ))}
        </ul>
      )}

      {card.data !== null && selectedId !== null && (
        <div className="card-panel">
          <h3>{t("unit.title", { number: card.data.number })}</h3>
          <p>
            <strong>{t("gatehouse.residents")}:</strong>{" "}
            {card.data.residents
              .map((r) => `${r.full_name} (${r.phone ?? "—"})`)
              .join(", ") || "—"}
          </p>
          <p>
            <strong>{t("gatehouse.plates")}:</strong>{" "}
            {card.data.plates.join(", ") || "—"}
          </p>
          <p>
            <strong>{t("gatehouse.spots")}:</strong>{" "}
            {card.data.parking_spot_numbers.join(", ") || "—"}
          </p>

          <h4>{t("gatehouse.activePreregs")}</h4>
          {preregs.data !== null &&
            (preregs.data.length === 0 ? (
              <p className="hint">{t("gatehouse.noActivePreregs")}</p>
            ) : (
              <ul>
                {preregs.data.map((prereg) => (
                  <li key={prereg.id}>
                    {prereg.visitor_name}
                    {prereg.visitor_plate !== null && ` · ${prereg.visitor_plate}`}
                  </li>
                ))}
              </ul>
            ))}

          <form onSubmit={registerEntry} className="stack-form">
            <h4>{t("gatehouse.registerEntry")}</h4>
            <label htmlFor="visit-name">{t("visitors.visitorName")}</label>
            <input
              id="visit-name"
              required
              value={visitorName}
              onChange={(event) => setVisitorName(event.target.value)}
            />
            <label htmlFor="visit-plate">{t("visitors.visitorPlate")}</label>
            <input
              id="visit-plate"
              value={visitorPlate}
              onChange={(event) => setVisitorPlate(event.target.value)}
            />
            <label htmlFor="visit-spot">{t("gatehouse.visitorSpot")}</label>
            <select
              id="visit-spot"
              value={spotId}
              onChange={(event) => setSpotId(event.target.value)}
            >
              <option value="">{t("gatehouse.noSpot")}</option>
              {spots.data
                ?.filter((spot) => !busySpotIds.has(spot.id))
                .map((spot) => (
                  <option key={spot.id} value={spot.id}>
                    {spot.number}
                  </option>
                ))}
            </select>
            <label htmlFor="visit-flow">{t("gatehouse.authorization")}</label>
            <select
              id="visit-flow"
              value={flow}
              onChange={(event) => setFlow(event.target.value as "A" | "B")}
            >
              <option value="A">{t("gatehouse.flowA")}</option>
              <option value="B">{t("gatehouse.flowB")}</option>
            </select>
            {flow === "A" ? (
              <>
                <label htmlFor="visit-resident">{t("gatehouse.authorizedBy")}</label>
                <select
                  id="visit-resident"
                  required
                  value={residentId}
                  onChange={(event) => setResidentId(event.target.value)}
                >
                  <option value="" />
                  {card.data.residents.map((resident) => (
                    <option key={resident.user_id} value={resident.user_id}>
                      {resident.full_name}
                    </option>
                  ))}
                </select>
              </>
            ) : (
              <>
                <label htmlFor="visit-prereg">{t("gatehouse.prereg")}</label>
                <select
                  id="visit-prereg"
                  required
                  value={preregId}
                  onChange={(event) => setPreregId(event.target.value)}
                >
                  <option value="" />
                  {preregs.data?.map((prereg) => (
                    <option key={prereg.id} value={prereg.id}>
                      {prereg.visitor_name}
                    </option>
                  ))}
                </select>
              </>
            )}
            <button type="submit">{t("gatehouse.enter")}</button>
          </form>
        </div>
      )}

      <h3>{t("gatehouse.openVisits")}</h3>
      {openVisits.data !== null &&
        (openVisits.data.length === 0 ? (
          <p className="hint">{t("gatehouse.noOpenVisits")}</p>
        ) : (
          <table>
            <thead>
              <tr>
                <th>{t("visitors.visitorName")}</th>
                <th>{t("billing.unit")}</th>
                <th>{t("gatehouse.visitorSpot")}</th>
                <th>{t("gatehouse.enteredAt")}</th>
                <th>{t("common.actions")}</th>
              </tr>
            </thead>
            <tbody>
              {openVisits.data.map((visit) => (
                <tr key={visit.id}>
                  <td>
                    {visit.visitor_name}
                    {visit.visitor_plate !== null && ` · ${visit.visitor_plate}`}
                  </td>
                  <td>{unitName(visit.unit_id)}</td>
                  <td>
                    {spots.data?.find((s) => s.id === visit.visitor_spot_id)?.number ??
                      "—"}
                  </td>
                  <td>{formatDateTime(visit.entered_at)}</td>
                  <td>
                    <button
                      type="button"
                      className="ghost"
                      onClick={() => void registerExit(visit.id)}
                    >
                      {t("gatehouse.exit")}
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        ))}
      <ErrorMessage error={actionError} />
    </section>
  );
}
