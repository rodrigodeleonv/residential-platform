import { useTranslation } from "react-i18next";

import { useAuth } from "../auth/context";

export function HomePage() {
  const { t } = useTranslation();
  const { user } = useAuth();
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
    </section>
  );
}
