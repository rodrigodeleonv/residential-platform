import { useTranslation } from "react-i18next";
import { Link } from "react-router";

import type { Unit } from "../api/types";
import { useAuth } from "../auth/context";
import { ErrorMessage } from "../components/ErrorMessage";
import { useApiData } from "../hooks/useApiData";

export function HomePage() {
  const { t } = useTranslation();
  const { user } = useAuth();
  const { data: units, error } = useApiData<Unit[]>("/units/mine");
  if (user === null) return null;

  return (
    <section>
      <h2>{t("home.greeting", { name: user.full_name })}</h2>
      <h3>{t("home.rolesTitle")}</h3>
      <ul className="chips">
        {user.roles.map((role) => (
          <li key={role}>{t(`roles.${role}`)}</li>
        ))}
      </ul>

      <h3>{t("home.myUnits")}</h3>
      <ErrorMessage error={error} />
      {units !== null &&
        (units.length === 0 ? (
          <p className="hint">{t("home.noUnits")}</p>
        ) : (
          <ul className="cards">
            {units.map((unit) => (
              <li key={unit.id}>
                <Link to={`/units/${unit.id}`} className="card">
                  <strong>{t("unit.title", { number: unit.number })}</strong>
                  <span className="hint">{t(`unit.kinds.${unit.kind}`)}</span>
                </Link>
              </li>
            ))}
          </ul>
        ))}
    </section>
  );
}
