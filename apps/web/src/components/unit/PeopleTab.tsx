import { useState, type FormEvent } from "react";
import { useTranslation } from "react-i18next";

import { api, ApiError } from "../../api/client";
import type { Tenancy, User } from "../../api/types";
import { useApiData } from "../../hooks/useApiData";
import { formatDate } from "../../lib/format";
import { ErrorMessage } from "../ErrorMessage";

export function PeopleTab({ unitId, isAdmin }: { unitId: number; isAdmin: boolean }) {
  const { t } = useTranslation();
  const owners = useApiData<User[]>(`/units/${unitId}/owners`);
  const tenants = useApiData<Tenancy[]>(`/units/${unitId}/tenants`);
  const users = useApiData<User[]>(isAdmin ? "/users" : null);
  const [ownerId, setOwnerId] = useState("");
  const [email, setEmail] = useState("");
  const [fullName, setFullName] = useState("");
  const [startsOn, setStartsOn] = useState("");
  const [endsOn, setEndsOn] = useState("");
  const [actionError, setActionError] = useState<ApiError | null>(null);

  if (owners.error) return <ErrorMessage error={owners.error} />;
  if (owners.data === null) return <p className="status">{t("common.loading")}</p>;

  async function run(action: () => Promise<unknown>, after: () => void) {
    setActionError(null);
    try {
      await action();
      after();
    } catch (error) {
      if (error instanceof ApiError) setActionError(error);
    }
  }

  function assignOwner(event: FormEvent) {
    event.preventDefault();
    void run(
      () =>
        api(`/units/${unitId}/owners`, {
          method: "POST",
          body: JSON.stringify({ user_id: Number(ownerId) }),
        }),
      () => {
        setOwnerId("");
        owners.reload();
      },
    );
  }

  function registerTenant(event: FormEvent) {
    event.preventDefault();
    void run(
      () =>
        api(`/units/${unitId}/tenants`, {
          method: "POST",
          body: JSON.stringify({
            email,
            full_name: fullName,
            starts_on: startsOn,
            ends_on: endsOn,
          }),
        }),
      () => {
        setEmail("");
        setFullName("");
        tenants.reload();
      },
    );
  }

  return (
    <div>
      <h4>{t("people.owners")}</h4>
      {owners.data.length === 0 ? (
        <p className="hint">{t("people.noOwners")}</p>
      ) : (
        <ul>
          {owners.data.map((owner) => (
            <li key={owner.id}>
              {owner.full_name} · {owner.email}
              {isAdmin && (
                <button
                  type="button"
                  className="ghost"
                  onClick={() =>
                    void run(
                      () =>
                        api(`/units/${unitId}/owners/${owner.id}`, {
                          method: "DELETE",
                        }),
                      owners.reload,
                    )
                  }
                >
                  {t("common.delete")}
                </button>
              )}
            </li>
          ))}
        </ul>
      )}
      {isAdmin && users.data !== null && (
        <form onSubmit={assignOwner} className="inline-form">
          <label htmlFor="owner-user">{t("people.user")}</label>
          <select
            id="owner-user"
            required
            value={ownerId}
            onChange={(event) => setOwnerId(event.target.value)}
          >
            <option value="" />
            {users.data.map((user) => (
              <option key={user.id} value={user.id}>
                {user.full_name} ({user.email})
              </option>
            ))}
          </select>
          <button type="submit">{t("people.assignOwner")}</button>
        </form>
      )}

      <h4>{t("people.tenants")}</h4>
      {tenants.data !== null &&
        (tenants.data.length === 0 ? (
          <p className="hint">{t("people.noTenants")}</p>
        ) : (
          <table>
            <thead>
              <tr>
                <th>{t("users.name")}</th>
                <th>{t("people.startsOn")}</th>
                <th>{t("people.endsOn")}</th>
                <th>{t("common.actions")}</th>
              </tr>
            </thead>
            <tbody>
              {tenants.data.map((tenancy) => (
                <tr key={tenancy.id}>
                  <td>
                    {tenancy.user.full_name} · {tenancy.user.email}
                  </td>
                  <td>{formatDate(tenancy.starts_on)}</td>
                  <td>{formatDate(tenancy.ends_on)}</td>
                  <td>
                    <button
                      type="button"
                      className="ghost"
                      onClick={() =>
                        void run(
                          () =>
                            api(`/units/${unitId}/tenants/${tenancy.id}`, {
                              method: "DELETE",
                            }),
                          tenants.reload,
                        )
                      }
                    >
                      {t("people.revoke")}
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        ))}

      <form onSubmit={registerTenant} className="stack-form">
        <h4>{t("people.registerTenant")}</h4>
        <label htmlFor="tenant-email">{t("users.email")}</label>
        <input
          id="tenant-email"
          type="email"
          required
          value={email}
          onChange={(event) => setEmail(event.target.value)}
        />
        <label htmlFor="tenant-name">{t("users.name")}</label>
        <input
          id="tenant-name"
          required
          value={fullName}
          onChange={(event) => setFullName(event.target.value)}
        />
        <label htmlFor="tenant-starts">{t("people.startsOn")}</label>
        <input
          id="tenant-starts"
          type="date"
          required
          value={startsOn}
          onChange={(event) => setStartsOn(event.target.value)}
        />
        <label htmlFor="tenant-ends">{t("people.endsOn")}</label>
        <input
          id="tenant-ends"
          type="date"
          required
          value={endsOn}
          onChange={(event) => setEndsOn(event.target.value)}
        />
        <button type="submit">{t("people.registerTenant")}</button>
      </form>
      <ErrorMessage error={actionError} />
    </div>
  );
}
