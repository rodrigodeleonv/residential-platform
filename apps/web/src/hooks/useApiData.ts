import { useCallback, useEffect, useState } from "react";

import { api, ApiError } from "../api/client";

/**
 * Fetch `path` and re-fetch on `reload()`. Pass null to fetch nothing yet.
 * `data` stays null until the first success; `error` reflects the last attempt.
 */
export function useApiData<T>(path: string | null) {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<ApiError | null>(null);
  const [version, setVersion] = useState(0);

  useEffect(() => {
    if (path === null) return;
    let cancelled = false;
    api<T>(path)
      .then((result) => {
        if (!cancelled) {
          setData(result);
          setError(null);
        }
      })
      .catch((failure: unknown) => {
        if (!cancelled) {
          setError(
            failure instanceof ApiError ? failure : new ApiError(0, String(failure)),
          );
        }
      });
    return () => {
      cancelled = true;
    };
  }, [path, version]);

  const reload = useCallback(() => setVersion((v) => v + 1), []);
  return { data, error, reload };
}
