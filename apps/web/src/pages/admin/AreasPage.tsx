import { useState, type FormEvent } from "react";
import { useTranslation } from "react-i18next";

import { api, ApiError } from "../../api/client";
import type { Area, Reservation, Unit } from "../../api/types";
import { ErrorMessage } from "../../components/ErrorMessage";
import { useApiData } from "../../hooks/useApiData";
import { formatDate, formatMoney } from "../../lib/format";

export function AreasPage() {
  const { t } = useTranslation();
  const areas = useApiData<Area[]>("/areas");
  const units = useApiData<Unit[]>("/units");
  const [name, setName] = useState("");
  const [capacity, setCapacity] = useState("1");
  const [fee, setFee] = useState("0");
  const [dayFilter, setDayFilter] = useState("");
  const [areaFilter, setAreaFilter] = useState("");
  const reservationsPath = `/reservations?${new URLSearchParams({
    ...(dayFilter && { day: dayFilter }),
    ...(areaFilter && { area_id: areaFilter }),
  }).toString()}`;
  const reservations = useApiData<Reservation[]>(reservationsPath);
  const [actionError, setActionError] = useState<ApiError | null>(null);

  const areaName = (id: number) =>
    areas.data?.find((area) => area.id === id)?.name ?? `#${id}`;
  const unitNumber = (id: number) =>
    units.data?.find((unit) => unit.id === id)?.number ?? `#${id}`;

  async function run(action: () => Promise<unknown>, after: () => void) {
    setActionError(null);
    try {
      await action();
      after();
    } catch (error) {
      if (error instanceof ApiError) setActionError(error);
    }
  }

  function createArea(event: FormEvent) {
    event.preventDefault();
    void run(
      () =>
        api("/areas", {
          method: "POST",
          body: JSON.stringify({ name, capacity: Number(capacity), fee }),
        }),
      () => {
        setName("");
        areas.reload();
      },
    );
  }

  return (
    <section>
      <h2>{t("nav.areas")}</h2>

      <h3>{t("areas.catalog")}</h3>
      {areas.data !== null && (
        <table>
          <thead>
            <tr>
              <th>{t("users.name")}</th>
              <th>{t("areas.capacity")}</th>
              <th>{t("areas.fee")}</th>
              <th>{t("billing.status")}</th>
              <th>{t("common.actions")}</th>
            </tr>
          </thead>
          <tbody>
            {areas.data.map((area) => (
              <tr key={area.id}>
                <td>{area.name}</td>
                <td>{area.capacity}</td>
                <td>{formatMoney(area.fee, area.currency)}</td>
                <td>{area.is_active ? t("areas.active") : t("areas.inactive")}</td>
                <td>
                  <button
                    type="button"
                    className="ghost"
                    onClick={() =>
                      void run(
                        () =>
                          api(`/areas/${area.id}`, {
                            method: "PATCH",
                            body: JSON.stringify({ is_active: !area.is_active }),
                          }),
                        areas.reload,
                      )
                    }
                  >
                    {area.is_active ? t("areas.deactivate") : t("areas.activate")}
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
      <form onSubmit={createArea} className="inline-form">
        <label htmlFor="area-name">{t("areas.newArea")}</label>
        <input
          id="area-name"
          required
          value={name}
          onChange={(event) => setName(event.target.value)}
        />
        <label htmlFor="area-capacity">{t("areas.capacity")}</label>
        <input
          id="area-capacity"
          type="number"
          min="1"
          required
          value={capacity}
          onChange={(event) => setCapacity(event.target.value)}
        />
        <label htmlFor="area-fee">{t("areas.fee")}</label>
        <input
          id="area-fee"
          type="number"
          min="0"
          step="0.01"
          required
          value={fee}
          onChange={(event) => setFee(event.target.value)}
        />
        <button type="submit">{t("common.create")}</button>
      </form>

      <h3>{t("areas.overview")}</h3>
      <div className="inline-form">
        <label htmlFor="filter-day">{t("reservations.day")}</label>
        <input
          id="filter-day"
          type="date"
          value={dayFilter}
          onChange={(event) => setDayFilter(event.target.value)}
        />
        <label htmlFor="filter-area">{t("reservations.area")}</label>
        <select
          id="filter-area"
          value={areaFilter}
          onChange={(event) => setAreaFilter(event.target.value)}
        >
          <option value="">{t("areas.anyArea")}</option>
          {areas.data?.map((area) => (
            <option key={area.id} value={area.id}>
              {area.name}
            </option>
          ))}
        </select>
      </div>
      {reservations.data !== null &&
        (reservations.data.length === 0 ? (
          <p className="hint">{t("common.empty")}</p>
        ) : (
          <table>
            <thead>
              <tr>
                <th>{t("reservations.area")}</th>
                <th>{t("billing.unit")}</th>
                <th>{t("reservations.day")}</th>
                <th>{t("reservations.slot")}</th>
                <th>{t("reservations.fee")}</th>
                <th>{t("common.actions")}</th>
              </tr>
            </thead>
            <tbody>
              {reservations.data.map((reservation) => (
                <tr key={reservation.id}>
                  <td>{areaName(reservation.area_id)}</td>
                  <td>{unitNumber(reservation.unit_id)}</td>
                  <td>{formatDate(reservation.day)}</td>
                  <td>{t(`reservations.slots.${reservation.slot}`)}</td>
                  <td>{formatMoney(reservation.fee, reservation.currency)}</td>
                  <td>
                    {reservation.canceled_at !== null ? (
                      <span className="hint">{t("reservations.canceled")}</span>
                    ) : (
                      <button
                        type="button"
                        className="ghost"
                        onClick={() =>
                          void run(
                            () =>
                              api(
                                `/units/${reservation.unit_id}/reservations/${reservation.id}`,
                                { method: "DELETE" },
                              ),
                            reservations.reload,
                          )
                        }
                      >
                        {t("common.cancel")}
                      </button>
                    )}
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
