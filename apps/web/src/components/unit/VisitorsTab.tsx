import { useState, type FormEvent } from "react";
import { useTranslation } from "react-i18next";

import { api, ApiError } from "../../api/client";
import type { PreRegistration, PreRegKind } from "../../api/types";
import { useApiData } from "../../hooks/useApiData";
import { formatDate, formatDateTime, weekdayName } from "../../lib/format";
import { ErrorMessage } from "../ErrorMessage";

// Must match the deployment's APP_VISIT_EXPIRATION_HOURS_OPTIONS.
const EXPIRATION_OPTIONS = [1, 2, 4];

function describeWindow(prereg: PreRegistration, recurringLabel: string): string {
  if (prereg.kind === "one_off" && prereg.starts_at !== null) {
    return formatDateTime(prereg.starts_at);
  }
  const time = prereg.time_of_day?.slice(0, 5) ?? "";
  const range =
    prereg.valid_from !== null && prereg.valid_until !== null
      ? `${formatDate(prereg.valid_from)} – ${formatDate(prereg.valid_until)}`
      : "";
  return `${recurringLabel}: ${weekdayName(prereg.weekday ?? 0)} ${time} (${range})`;
}

export function VisitorsTab({ unitId }: { unitId: number }) {
  const { t } = useTranslation();
  const preregs = useApiData<PreRegistration[]>(`/units/${unitId}/preregistrations`);
  const [kind, setKind] = useState<PreRegKind>("one_off");
  const [name, setName] = useState("");
  const [plate, setPlate] = useState("");
  const [expiration, setExpiration] = useState(EXPIRATION_OPTIONS[0]);
  const [startsAt, setStartsAt] = useState("");
  const [weekday, setWeekday] = useState(0);
  const [timeOfDay, setTimeOfDay] = useState("");
  const [validFrom, setValidFrom] = useState("");
  const [validUntil, setValidUntil] = useState("");
  const [actionError, setActionError] = useState<ApiError | null>(null);

  if (preregs.error) return <ErrorMessage error={preregs.error} />;
  if (preregs.data === null) return <p className="status">{t("common.loading")}</p>;

  async function create(event: FormEvent) {
    event.preventDefault();
    setActionError(null);
    const payload =
      kind === "one_off"
        ? { starts_at: new Date(startsAt).toISOString() }
        : {
            weekday,
            time_of_day: timeOfDay,
            valid_from: validFrom,
            valid_until: validUntil,
          };
    try {
      await api(`/units/${unitId}/preregistrations`, {
        method: "POST",
        body: JSON.stringify({
          visitor_name: name,
          visitor_plate: plate || null,
          kind,
          expiration_hours: expiration,
          ...payload,
        }),
      });
      setName("");
      setPlate("");
      preregs.reload();
    } catch (error) {
      if (error instanceof ApiError) setActionError(error);
    }
  }

  async function cancel(preregId: number) {
    setActionError(null);
    try {
      await api(`/units/${unitId}/preregistrations/${preregId}`, {
        method: "DELETE",
      });
      preregs.reload();
    } catch (error) {
      if (error instanceof ApiError) setActionError(error);
    }
  }

  return (
    <div>
      {preregs.data.length === 0 ? (
        <p className="hint">{t("visitors.noPreregs")}</p>
      ) : (
        <table>
          <thead>
            <tr>
              <th>{t("visitors.visitorName")}</th>
              <th>{t("vehicles.plate")}</th>
              <th>{t("visitors.startsAt")}</th>
              <th>{t("visitors.expiration")}</th>
              <th>{t("common.actions")}</th>
            </tr>
          </thead>
          <tbody>
            {preregs.data.map((prereg) => (
              <tr key={prereg.id}>
                <td>{prereg.visitor_name}</td>
                <td>{prereg.visitor_plate ?? "—"}</td>
                <td>{describeWindow(prereg, t("visitors.recurring"))}</td>
                <td>{prereg.expiration_hours} h</td>
                <td>
                  <button
                    type="button"
                    className="ghost"
                    onClick={() => void cancel(prereg.id)}
                  >
                    {t("common.cancel")}
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}

      <form onSubmit={create} className="stack-form">
        <h4>{t("visitors.add")}</h4>
        <label htmlFor="prereg-name">{t("visitors.visitorName")}</label>
        <input
          id="prereg-name"
          required
          value={name}
          onChange={(event) => setName(event.target.value)}
        />
        <label htmlFor="prereg-plate">{t("visitors.visitorPlate")}</label>
        <input
          id="prereg-plate"
          value={plate}
          onChange={(event) => setPlate(event.target.value)}
        />
        <label htmlFor="prereg-kind">{t("visitors.kind")}</label>
        <select
          id="prereg-kind"
          value={kind}
          onChange={(event) => setKind(event.target.value as PreRegKind)}
        >
          <option value="one_off">{t("visitors.oneOff")}</option>
          <option value="recurring">{t("visitors.recurring")}</option>
        </select>
        <label htmlFor="prereg-expiration">{t("visitors.expiration")}</label>
        <select
          id="prereg-expiration"
          value={expiration}
          onChange={(event) => setExpiration(Number(event.target.value))}
        >
          {EXPIRATION_OPTIONS.map((hours) => (
            <option key={hours} value={hours}>
              {hours} h
            </option>
          ))}
        </select>
        {kind === "one_off" ? (
          <>
            <label htmlFor="prereg-starts">{t("visitors.startsAt")}</label>
            <input
              id="prereg-starts"
              type="datetime-local"
              required
              value={startsAt}
              onChange={(event) => setStartsAt(event.target.value)}
            />
          </>
        ) : (
          <>
            <label htmlFor="prereg-weekday">{t("visitors.weekday")}</label>
            <select
              id="prereg-weekday"
              value={weekday}
              onChange={(event) => setWeekday(Number(event.target.value))}
            >
              {[0, 1, 2, 3, 4, 5, 6].map((day) => (
                <option key={day} value={day}>
                  {weekdayName(day)}
                </option>
              ))}
            </select>
            <label htmlFor="prereg-time">{t("visitors.timeOfDay")}</label>
            <input
              id="prereg-time"
              type="time"
              required
              value={timeOfDay}
              onChange={(event) => setTimeOfDay(event.target.value)}
            />
            <label htmlFor="prereg-from">{t("visitors.validFrom")}</label>
            <input
              id="prereg-from"
              type="date"
              required
              value={validFrom}
              onChange={(event) => setValidFrom(event.target.value)}
            />
            <label htmlFor="prereg-until">{t("visitors.validUntil")}</label>
            <input
              id="prereg-until"
              type="date"
              required
              value={validUntil}
              onChange={(event) => setValidUntil(event.target.value)}
            />
          </>
        )}
        <button type="submit">{t("visitors.add")}</button>
      </form>
      <ErrorMessage error={actionError} />
    </div>
  );
}
