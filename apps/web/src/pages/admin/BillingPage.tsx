import { useState, type FormEvent } from "react";
import { useTranslation } from "react-i18next";

import { api, ApiError } from "../../api/client";
import type { Charge, Infraction, Unit } from "../../api/types";
import { ErrorMessage } from "../../components/ErrorMessage";
import { useApiData } from "../../hooks/useApiData";
import { formatDate, formatMoney } from "../../lib/format";

export function BillingPage() {
  const { t } = useTranslation();
  const infractions = useApiData<Infraction[]>("/infractions");
  const units = useApiData<Unit[]>("/units");
  const [status, setStatus] = useState("pending");
  const [unitFilter, setUnitFilter] = useState("");
  const chargesPath = `/charges?${new URLSearchParams({
    ...(status !== "all" && { status }),
    ...(unitFilter && { unit_id: unitFilter }),
  }).toString()}`;
  const charges = useApiData<Charge[]>(chargesPath);

  const [infractionName, setInfractionName] = useState("");
  const [fineAmount, setFineAmount] = useState("");
  const [chargeUnit, setChargeUnit] = useState("");
  const [chargeDescription, setChargeDescription] = useState("");
  const [chargeAmount, setChargeAmount] = useState("");
  const [fineUnit, setFineUnit] = useState("");
  const [fineInfraction, setFineInfraction] = useState("");
  const [actionError, setActionError] = useState<ApiError | null>(null);

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

  function createInfraction(event: FormEvent) {
    event.preventDefault();
    void run(
      () =>
        api("/infractions", {
          method: "POST",
          body: JSON.stringify({ name: infractionName, fine_amount: fineAmount }),
        }),
      () => {
        setInfractionName("");
        setFineAmount("");
        infractions.reload();
      },
    );
  }

  function createCharge(event: FormEvent) {
    event.preventDefault();
    void run(
      () =>
        api(`/units/${chargeUnit}/charges`, {
          method: "POST",
          body: JSON.stringify({
            description: chargeDescription,
            amount: chargeAmount,
          }),
        }),
      () => {
        setChargeDescription("");
        setChargeAmount("");
        charges.reload();
      },
    );
  }

  function issueFine(event: FormEvent) {
    event.preventDefault();
    void run(
      () =>
        api(`/units/${fineUnit}/fines`, {
          method: "POST",
          body: JSON.stringify({ infraction_type_id: Number(fineInfraction) }),
        }),
      charges.reload,
    );
  }

  return (
    <section>
      <h2>{t("nav.billing")}</h2>

      <h3>{t("billing.infractions")}</h3>
      {infractions.data !== null && (
        <table>
          <thead>
            <tr>
              <th>{t("users.name")}</th>
              <th>{t("billing.fineAmount")}</th>
              <th>{t("billing.status")}</th>
              <th>{t("common.actions")}</th>
            </tr>
          </thead>
          <tbody>
            {infractions.data.map((infraction) => (
              <tr key={infraction.id}>
                <td>{infraction.name}</td>
                <td>{formatMoney(infraction.fine_amount, infraction.currency)}</td>
                <td>
                  {infraction.is_active ? t("billing.active") : t("billing.inactive")}
                </td>
                <td>
                  <button
                    type="button"
                    className="ghost"
                    onClick={() =>
                      void run(
                        () =>
                          api(`/infractions/${infraction.id}`, {
                            method: "PATCH",
                            body: JSON.stringify({
                              is_active: !infraction.is_active,
                            }),
                          }),
                        infractions.reload,
                      )
                    }
                  >
                    {infraction.is_active
                      ? t("areas.deactivate")
                      : t("areas.activate")}
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
      <form onSubmit={createInfraction} className="inline-form">
        <label htmlFor="infraction-name">{t("billing.newInfraction")}</label>
        <input
          id="infraction-name"
          required
          value={infractionName}
          onChange={(event) => setInfractionName(event.target.value)}
        />
        <label htmlFor="infraction-amount">{t("billing.fineAmount")}</label>
        <input
          id="infraction-amount"
          type="number"
          min="0.01"
          step="0.01"
          required
          value={fineAmount}
          onChange={(event) => setFineAmount(event.target.value)}
        />
        <button type="submit">{t("common.create")}</button>
      </form>

      <h3>{t("billing.charges")}</h3>
      <div className="inline-form">
        <label htmlFor="charge-status">{t("billing.status")}</label>
        <select
          id="charge-status"
          value={status}
          onChange={(event) => setStatus(event.target.value)}
        >
          <option value="all">{t("billing.statusAll")}</option>
          <option value="pending">{t("billing.statusPending")}</option>
          <option value="paid">{t("billing.statusPaid")}</option>
          <option value="voided">{t("billing.statusVoided")}</option>
        </select>
        <label htmlFor="charge-unit-filter">{t("billing.unit")}</label>
        <select
          id="charge-unit-filter"
          value={unitFilter}
          onChange={(event) => setUnitFilter(event.target.value)}
        >
          <option value="">{t("billing.allUnits")}</option>
          {units.data?.map((unit) => (
            <option key={unit.id} value={unit.id}>
              {unit.number}
            </option>
          ))}
        </select>
      </div>
      {charges.data !== null &&
        (charges.data.length === 0 ? (
          <p className="hint">{t("common.empty")}</p>
        ) : (
          <table>
            <thead>
              <tr>
                <th>{t("billing.unit")}</th>
                <th>{t("statement.kind")}</th>
                <th>{t("statement.description")}</th>
                <th>{t("statement.date")}</th>
                <th>{t("statement.amount")}</th>
                <th>{t("common.actions")}</th>
              </tr>
            </thead>
            <tbody>
              {charges.data.map((charge) => (
                <tr key={charge.id}>
                  <td>{unitNumber(charge.unit_id)}</td>
                  <td>{t(`statement.kinds.${charge.kind}`)}</td>
                  <td>{charge.description}</td>
                  <td>{formatDate(charge.created_at)}</td>
                  <td>{formatMoney(charge.amount, charge.currency)}</td>
                  <td>
                    {charge.paid_at !== null ? (
                      t("billing.statusPaid")
                    ) : charge.voided_at !== null ? (
                      t("billing.statusVoided")
                    ) : (
                      <button
                        type="button"
                        className="ghost"
                        onClick={() =>
                          void run(
                            () =>
                              api(`/charges/${charge.id}/pay`, { method: "POST" }),
                            charges.reload,
                          )
                        }
                      >
                        {t("billing.markPaid")}
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        ))}

      <form onSubmit={createCharge} className="stack-form">
        <h4>{t("billing.newCharge")}</h4>
        <label htmlFor="charge-unit">{t("billing.unit")}</label>
        <select
          id="charge-unit"
          required
          value={chargeUnit}
          onChange={(event) => setChargeUnit(event.target.value)}
        >
          <option value="" />
          {units.data?.map((unit) => (
            <option key={unit.id} value={unit.id}>
              {unit.number}
            </option>
          ))}
        </select>
        <label htmlFor="charge-description">{t("statement.description")}</label>
        <input
          id="charge-description"
          required
          value={chargeDescription}
          onChange={(event) => setChargeDescription(event.target.value)}
        />
        <label htmlFor="charge-amount">{t("statement.amount")}</label>
        <input
          id="charge-amount"
          type="number"
          min="0.01"
          step="0.01"
          required
          value={chargeAmount}
          onChange={(event) => setChargeAmount(event.target.value)}
        />
        <button type="submit">{t("common.create")}</button>
      </form>

      <form onSubmit={issueFine} className="stack-form">
        <h4>{t("billing.issueFine")}</h4>
        <label htmlFor="fine-unit">{t("billing.unit")}</label>
        <select
          id="fine-unit"
          required
          value={fineUnit}
          onChange={(event) => setFineUnit(event.target.value)}
        >
          <option value="" />
          {units.data?.map((unit) => (
            <option key={unit.id} value={unit.id}>
              {unit.number}
            </option>
          ))}
        </select>
        <label htmlFor="fine-infraction">{t("billing.infractions")}</label>
        <select
          id="fine-infraction"
          required
          value={fineInfraction}
          onChange={(event) => setFineInfraction(event.target.value)}
        >
          <option value="" />
          {infractions.data
            ?.filter((infraction) => infraction.is_active)
            .map((infraction) => (
              <option key={infraction.id} value={infraction.id}>
                {infraction.name} ·{" "}
                {formatMoney(infraction.fine_amount, infraction.currency)}
              </option>
            ))}
        </select>
        <button type="submit">{t("billing.issueFine")}</button>
      </form>
      <ErrorMessage error={actionError} />
    </section>
  );
}
