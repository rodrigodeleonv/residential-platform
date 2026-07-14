import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";

import { api } from "../api/client";
import type { User } from "../api/types";

export function UsersPage() {
  const { t } = useTranslation();
  const [users, setUsers] = useState<User[] | null>(null);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    let cancelled = false;
    api<User[]>("/users")
      .then((list) => {
        if (!cancelled) setUsers(list);
      })
      .catch(() => {
        if (!cancelled) setFailed(true);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  if (failed) {
    return (
      <p role="alert" className="error">
        {t("common.error")}
      </p>
    );
  }
  if (users === null) return <p className="status">{t("common.loading")}</p>;

  return (
    <section>
      <h2>{t("users.title")}</h2>
      <table>
        <thead>
          <tr>
            <th>{t("users.name")}</th>
            <th>{t("users.email")}</th>
            <th>{t("users.phone")}</th>
            <th>{t("users.roles")}</th>
            <th>{t("users.status")}</th>
          </tr>
        </thead>
        <tbody>
          {users.map((user) => (
            <tr key={user.id}>
              <td>{user.full_name}</td>
              <td>{user.email}</td>
              <td>{user.phone ?? "—"}</td>
              <td>{user.roles.map((role) => t(`roles.${role}`)).join(", ")}</td>
              <td>{user.is_active ? t("users.active") : t("users.inactive")}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  );
}
