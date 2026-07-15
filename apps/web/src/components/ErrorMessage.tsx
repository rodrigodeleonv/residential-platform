import { useTranslation } from "react-i18next";

import { ApiError } from "../api/client";

/** Friendly rendering for an API failure (null renders nothing). */
export function ErrorMessage({ error }: { error: ApiError | null }) {
  const { t } = useTranslation();
  if (error === null) return null;
  const text =
    error.status === 401 || error.status === 403
      ? t("common.noAccess")
      : error.message || t("common.error");
  return (
    <p role="alert" className="error">
      {text}
    </p>
  );
}
