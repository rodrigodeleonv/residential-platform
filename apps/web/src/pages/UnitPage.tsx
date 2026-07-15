import { useState } from "react";
import { useTranslation } from "react-i18next";
import { useParams } from "react-router";

import type { Unit } from "../api/types";
import { useAuth } from "../auth/context";
import { PeopleTab } from "../components/unit/PeopleTab";
import { ReservationsTab } from "../components/unit/ReservationsTab";
import { StatementTab } from "../components/unit/StatementTab";
import { VehiclesTab } from "../components/unit/VehiclesTab";
import { VisitorsTab } from "../components/unit/VisitorsTab";
import { useApiData } from "../hooks/useApiData";

const TABS = ["vehicles", "visitors", "reservations", "statement", "people"] as const;
type Tab = (typeof TABS)[number];

export function UnitPage() {
  const { t } = useTranslation();
  const { unitId = "" } = useParams();
  const { user } = useAuth();
  const isAdmin = user?.roles.includes("admin") ?? false;
  const [tab, setTab] = useState<Tab>("vehicles");

  // There is no per-unit GET: members find the unit in their own list,
  // admins in the full list.
  const mine = useApiData<Unit[]>("/units/mine");
  const all = useApiData<Unit[]>(isAdmin ? "/units" : null);
  const id = Number(unitId);
  const unit =
    mine.data?.find((u) => u.id === id) ?? all.data?.find((u) => u.id === id);

  if (mine.data === null && mine.error === null) {
    return <p className="status">{t("common.loading")}</p>;
  }
  if (unit === undefined) {
    return (
      <p role="alert" className="error">
        {t("common.noAccess")}
      </p>
    );
  }

  return (
    <section>
      <h2>{t("unit.title", { number: unit.number })}</h2>
      <p className="hint">
        {t(`unit.kinds.${unit.kind}`)}
        {unit.floor !== null && ` · ${t("unit.floor")} ${unit.floor}`}
      </p>
      <div className="tabs" role="tablist">
        {TABS.map((name) => (
          <button
            key={name}
            type="button"
            role="tab"
            aria-selected={tab === name}
            className={tab === name ? "tab active" : "tab"}
            onClick={() => setTab(name)}
          >
            {t(`unit.tabs.${name}`)}
          </button>
        ))}
      </div>
      {tab === "vehicles" && <VehiclesTab unitId={unit.id} />}
      {tab === "visitors" && <VisitorsTab unitId={unit.id} />}
      {tab === "reservations" && <ReservationsTab unitId={unit.id} />}
      {tab === "statement" && <StatementTab unitId={unit.id} />}
      {tab === "people" && <PeopleTab unitId={unit.id} isAdmin={isAdmin} />}
    </section>
  );
}
