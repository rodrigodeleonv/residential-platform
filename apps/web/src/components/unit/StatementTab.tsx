import { useTranslation } from "react-i18next";

import type { Charge, Statement } from "../../api/types";
import { useApiData } from "../../hooks/useApiData";
import { formatDate, formatMoney } from "../../lib/format";
import { ErrorMessage } from "../ErrorMessage";

function ChargesTable({ charges, dateOf }: { charges: Charge[]; dateOf: keyof Charge }) {
  const { t } = useTranslation();
  return (
    <table>
      <thead>
        <tr>
          <th>{t("statement.kind")}</th>
          <th>{t("statement.description")}</th>
          <th>{t("statement.date")}</th>
          <th>{t("statement.amount")}</th>
        </tr>
      </thead>
      <tbody>
        {charges.map((charge) => (
          <tr key={charge.id}>
            <td>{t(`statement.kinds.${charge.kind}`)}</td>
            <td>{charge.description}</td>
            <td>{formatDate((charge[dateOf] as string | null) ?? charge.created_at)}</td>
            <td>{formatMoney(charge.amount, charge.currency)}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

export function StatementTab({ unitId }: { unitId: number }) {
  const { t } = useTranslation();
  const statement = useApiData<Statement>(`/units/${unitId}/statement`);

  if (statement.error) return <ErrorMessage error={statement.error} />;
  if (statement.data === null) return <p className="status">{t("common.loading")}</p>;

  const { pending, pending_total, paid, currency } = statement.data;
  return (
    <div>
      <h4>{t("statement.pending")}</h4>
      {pending.length === 0 ? (
        <p className="hint">{t("common.empty")}</p>
      ) : (
        <ChargesTable charges={pending} dateOf="created_at" />
      )}
      <p>
        <strong>
          {t("statement.pendingTotal")}: {formatMoney(pending_total, currency)}
        </strong>
      </p>

      <h4>{t("statement.paid")}</h4>
      {paid.length === 0 ? (
        <p className="hint">{t("common.empty")}</p>
      ) : (
        <ChargesTable charges={paid} dateOf="paid_at" />
      )}
    </div>
  );
}
