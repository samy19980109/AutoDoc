import { useMemo, useState } from "react";
import { api } from "../api/client";

export default function SettingsPage() {
  const [apiKey, setApiKey] = useState(localStorage.getItem("api_key") || "");
  const [username, setUsername] = useState(localStorage.getItem("dashboard_username") || "admin");
  const [password, setPassword] = useState("");
  const [banner, setBanner] = useState("");
  const [checking, setChecking] = useState(false);

  const hasToken = useMemo(() => Boolean(localStorage.getItem("auth_token")), [banner]);

  function saveApiKey(e) {
    e.preventDefault();
    localStorage.setItem("api_key", apiKey.trim());
    setBanner("API key saved to browser storage.");
  }

  async function login(e) {
    e.preventDefault();
    try {
      const resp = await api.login(username, password);
      localStorage.setItem("auth_token", resp.access_token);
      localStorage.setItem("dashboard_username", username);
      setPassword("");
      setBanner("Dashboard login succeeded. Bearer token stored.");
    } catch (err) {
      setBanner(`Login failed: ${err.message}`);
    }
  }

  function clearAuth() {
    localStorage.removeItem("auth_token");
    setBanner("Stored bearer token removed.");
  }

  async function checkConnection() {
    setChecking(true);
    try {
      const response = await fetch("/health");
      if (!response.ok) throw new Error(response.statusText);
      const data = await response.json();
      setBanner(`Gateway health: ${data.status}`);
    } catch (err) {
      setBanner(`Health check failed: ${err.message}`);
    } finally {
      setChecking(false);
    }
  }

  return (
    <div className="space-y-6 fade-in">
      {banner && <div className="panel p-3 text-sm">{banner}</div>}

      <section className="panel p-5 max-w-3xl">
        <h3 className="text-xl font-bold">Authentication</h3>
        <p className="soft-text text-sm mt-1">Use API key headers and/or dashboard JWT login. Either method works with the API gateway.</p>

        <div className="mt-4 grid md:grid-cols-2 gap-4">
          <form onSubmit={saveApiKey} className="rounded-xl border p-4" style={{ borderColor: "var(--border)" }}>
            <h4 className="font-semibold">API Key</h4>
            <label className="block mt-2">
              <span className="text-sm soft-text">X-API-Key value</span>
              <input
                type="password"
                value={apiKey}
                onChange={(e) => setApiKey(e.target.value)}
                className="mt-1 w-full rounded-xl border p-2.5"
                style={{ background: "var(--bg-elevated)", borderColor: "var(--border)" }}
                placeholder="test-key-1"
              />
            </label>
            <button type="submit" className="mt-3 px-4 py-2 rounded-xl text-sm font-semibold text-white" style={{ background: "var(--accent)" }}>
              Save API Key
            </button>
          </form>

          <form onSubmit={login} className="rounded-xl border p-4" style={{ borderColor: "var(--border)" }}>
            <h4 className="font-semibold">Dashboard Login</h4>
            <label className="block mt-2">
              <span className="text-sm soft-text">Username</span>
              <input
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                className="mt-1 w-full rounded-xl border p-2.5"
                style={{ background: "var(--bg-elevated)", borderColor: "var(--border)" }}
              />
            </label>
            <label className="block mt-2">
              <span className="text-sm soft-text">Password</span>
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="mt-1 w-full rounded-xl border p-2.5"
                style={{ background: "var(--bg-elevated)", borderColor: "var(--border)" }}
              />
            </label>
            <div className="mt-3 flex gap-2">
              <button type="submit" className="px-4 py-2 rounded-xl text-sm font-semibold text-white" style={{ background: "var(--accent)" }}>
                Log In
              </button>
              <button type="button" onClick={clearAuth} className="px-4 py-2 rounded-xl text-sm font-semibold" style={{ background: "var(--bg-muted)" }}>
                Clear Token
              </button>
            </div>
          </form>
        </div>

        <div className="mt-4 rounded-xl border p-4 flex flex-wrap items-center justify-between gap-3" style={{ borderColor: "var(--border)" }}>
          <div>
            <p className="text-sm font-semibold">Connection & Session</p>
            <p className="text-sm soft-text">Bearer token: {hasToken ? "Present" : "Not set"}</p>
          </div>
          <button onClick={checkConnection} disabled={checking} className="px-4 py-2 rounded-xl text-sm font-semibold" style={{ background: "var(--bg-muted)" }}>
            {checking ? "Checking..." : "Check API Health"}
          </button>
        </div>
      </section>

      <section className="panel p-5 max-w-3xl">
        <h3 className="text-xl font-bold">Theme</h3>
        <p className="soft-text text-sm mt-1">Use the toggle in the top bar to switch between dark and light mode at any time.</p>
        <p className="text-xs soft-text mt-2">Shortcut reference: dashboard navigation is optimized for pointer + keyboard flow.</p>
      </section>
    </div>
  );
}
