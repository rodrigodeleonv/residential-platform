import { useState, type FormEvent } from "react";
import { useTranslation } from "react-i18next";

import { api, ApiError } from "../../api/client";
import type { Area, Reservation, SlotAvailability, TimeSlot } from "../../api/types";
import { useApiData } from "../../hooks/useApiData";
import { formatDate, formatMoney } from "../../lib/format";
import { ErrorMessage } from "../ErrorMessage";

export function ReservationsTab({ unitId }: { unitId: number }) {
  const { t } = useTranslation();
  const reservations = useApiData<Reservation[]>(`/units/${unitId}/reservations`);
  const areas = useApiData<Area[]>("/areas");
  const [areaId, setAreaId] = useState("");
  const [day, setDay] = useState("");
  const [slot, setSlot] = useState<TimeSlot | "">("");
  const availability = useApiData<SlotAvailability[]>(
    areaId && day ? `/areas/${areaId}/availability?day=${day}` : null,
  );
  const [actionError, setActionError] = useState<ApiError | null>(null);

  if (reservations.error) return <ErrorMessage error={reservations.error} />;
  if (reservations.data === null) {
    return <p className="status">{t("common.loading")}</p>;
  }

  const areaName = (id: number) =>
    areas.data?.find((area) => area.id === id)?.name ?? `#${id}`;
  const selectedArea = areas.data?.find((area) => area.id === Number(areaId));

  async function book(event: FormEvent) {
    event.preventDefault();
    if (slot === "") return;
    setActionError(null);
    try {
      await api(`/units/${unitId}/reservations`, {
        method: "POST",
        body: JSON.stringify({ area_id: Number(areaId), day, slot }),
      });
      setSlot("");
      reservations.reload();
      availability.reload();
    } catch (error) {
      if (error instanceof ApiError) setActionError(error);
    }
  }

  async function cancel(reservationId: number) {
    setActionError(null);
    try {
      await api(`/units/${unitId}/reservations/${reservationId}`, {
        method: "DELETE",
      });
      reservations.reload();
    } catch (error) {
      if (error instanceof ApiError) setActionError(error);
    }
  }

  return (
    <div>
      {reservations.data.length === 0 ? (
        <p className="hint">{t("reservations.noReservations")}</p>
      ) : (
        <table>
          <thead>
            <tr>
              <th>{t("reservations.area")}</th>
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
                      onClick={() => void cancel(reservation.id)}
                    >
                      {t("common.cancel")}
                    </button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}

      <form onSubmit={book} className="stack-form">
        <h4>{t("reservations.book")}</h4>
        <label htmlFor="reservation-area">{t("reservations.area")}</label>
        <select
          id="reservation-area"
          required
          value={areaId}
          onChange={(event) => {
            setAreaId(event.target.value);
            setSlot("");
          }}
        >
          <option value="" />
          {areas.data
            ?.filter((area) => area.is_active)
            .map((area) => (
              <option key={area.id} value={area.id}>
                {area.name} · {formatMoney(area.fee, area.currency)}
              </option>
            ))}
        </select>
        <label htmlFor="reservation-day">{t("reservations.day")}</label>
        <input
          id="reservation-day"
          type="date"
          required
          value={day}
          onChange={(event) => {
            setDay(event.target.value);
            setSlot("");
          }}
        />
        {availability.data !== null && (
          <div className="slot-picker" role="radiogroup">
            {availability.data.map((entry) => (
              <button
                key={entry.slot}
                type="button"
                role="radio"
                aria-checked={slot === entry.slot}
                disabled={entry.available <= 0}
                className={slot === entry.slot ? "tab active" : "tab"}
                onClick={() => setSlot(entry.slot)}
              >
                {t(`reservations.slots.${entry.slot}`)} ·{" "}
                {t("reservations.available", { count: entry.available })}
              </button>
            ))}
          </div>
        )}
        <button type="submit" disabled={slot === ""}>
          {t("reservations.book")}
          {selectedArea && ` (${formatMoney(selectedArea.fee, selectedArea.currency)})`}
        </button>
      </form>
      <ErrorMessage error={actionError} />
    </div>
  );
}
