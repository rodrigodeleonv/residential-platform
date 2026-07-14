import { useState, type FormEvent } from "react";
import { useTranslation } from "react-i18next";
import { Navigate, useNavigate } from "react-router";

import { api, ApiError } from "../api/client";
import { useAuth } from "../auth/context";
import { LanguageToggle } from "../components/LanguageToggle";

export function LoginPage() {
  const { t } = useTranslation();
  const { user, refresh } = useAuth();
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [code, setCode] = useState("");
  const [codeSent, setCodeSent] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  if (user !== null) return <Navigate to="/" replace />;

  function messageFor(error: unknown): string {
    if (error instanceof ApiError && error.status === 401) {
      return t("login.invalidCode");
    }
    if (error instanceof ApiError && error.status === 429) {
      return t("login.tooManyAttempts");
    }
    return t("common.error");
  }

  async function requestCode(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await api("/auth/request-code", {
        method: "POST",
        body: JSON.stringify({ email }),
      });
      setCodeSent(true);
    } catch (error) {
      setError(messageFor(error));
    } finally {
      setBusy(false);
    }
  }

  async function verify(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await api("/auth/verify", {
        method: "POST",
        body: JSON.stringify({ email, code }),
      });
      await refresh();
      void navigate("/", { replace: true });
    } catch (error) {
      setError(messageFor(error));
      setBusy(false);
    }
  }

  return (
    <div className="login">
      <header className="login-header">
        <span className="brand">{t("app.title")}</span>
        <LanguageToggle />
      </header>
      <h1>{t("login.title")}</h1>
      {codeSent ? (
        <form onSubmit={verify}>
          <p className="hint">{t("login.codeSent")}</p>
          <label htmlFor="code">{t("login.codeLabel")}</label>
          <input
            id="code"
            autoComplete="one-time-code"
            required
            value={code}
            onChange={(event) => setCode(event.target.value)}
          />
          <button type="submit" disabled={busy}>
            {t("login.verify")}
          </button>
          <button
            type="button"
            className="ghost"
            onClick={() => {
              setCodeSent(false);
              setCode("");
              setError(null);
            }}
          >
            {t("login.changeEmail")}
          </button>
        </form>
      ) : (
        <form onSubmit={requestCode}>
          <label htmlFor="email">{t("login.emailLabel")}</label>
          <input
            id="email"
            type="email"
            autoComplete="email"
            required
            value={email}
            onChange={(event) => setEmail(event.target.value)}
          />
          <button type="submit" disabled={busy}>
            {t("login.sendCode")}
          </button>
        </form>
      )}
      {error !== null && (
        <p role="alert" className="error">
          {error}
        </p>
      )}
    </div>
  );
}
