import { Routes, Route, Link, useLocation } from "react-router-dom";
import { useEffect, useMemo, useState } from "react";
import ReposPage from "./pages/ReposPage";
import RepoDetailPage from "./pages/RepoDetailPage";
import JobsPage from "./pages/JobsPage";
import JobDetailPage from "./pages/JobDetailPage";
import SettingsPage from "./pages/SettingsPage";
import MappingsPage from "./pages/MappingsPage";

const navItems = [
  { path: "/", label: "Repositories" },
  { path: "/jobs", label: "Jobs" },
  { path: "/mappings", label: "Mappings" },
  { path: "/settings", label: "Settings" },
];

const themeKey = "dashboard_theme";

export default function App() {
  const location = useLocation();
  const [theme, setTheme] = useState(localStorage.getItem(themeKey) || "dark");

  useEffect(() => {
    const root = document.documentElement;
    root.classList.toggle("dark", theme === "dark");
    localStorage.setItem(themeKey, theme);
  }, [theme]);

  const title = useMemo(() => {
    if (location.pathname.startsWith("/jobs")) return "Pipeline Jobs";
    if (location.pathname.startsWith("/mappings")) return "Destination Mappings";
    if (location.pathname.startsWith("/settings")) return "Workspace Settings";
    return "Repository Control Center";
  }, [location.pathname]);

  const subtitle = useMemo(() => {
    if (location.pathname.startsWith("/jobs")) return "Monitor generation runs, status, and logs in real time.";
    if (location.pathname.startsWith("/mappings")) return "Inspect and clean page bindings across destinations.";
    if (location.pathname.startsWith("/settings")) return "Configure authentication and dashboard defaults.";
    return "Manage repositories, destinations, and docs generation without terminal commands.";
  }, [location.pathname]);

  return (
    <div className="min-h-screen">
      <header className="sticky top-0 z-20 backdrop-blur-md border-b" style={{ borderColor: "var(--border)", background: "color-mix(in srgb, var(--bg) 80%, transparent)" }}>
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
          <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
            <div>
              <p className="text-xs uppercase tracking-[0.22em] soft-text">Enterprise Auto Documentation</p>
              <h1 className="text-2xl font-extrabold">AutoDoc Console</h1>
            </div>
            <div className="flex items-center gap-2">
              <button
                onClick={() => setTheme((v) => (v === "dark" ? "light" : "dark"))}
                className="px-3 py-2 rounded-xl text-sm font-semibold panel"
                title="Toggle theme"
              >
                {theme === "dark" ? "Light Mode" : "Dark Mode"}
              </button>
              <Link to="/settings" className="px-3 py-2 rounded-xl text-sm font-semibold panel">
                Auth
              </Link>
            </div>
          </div>
          <div className="mt-4 flex flex-wrap items-center gap-2">
            {navItems.map((item) => {
              const isActive = item.path === "/"
                ? location.pathname === "/" || location.pathname.startsWith("/repos")
                : location.pathname.startsWith(item.path);
              return (
                <Link
                  key={item.path}
                  to={item.path}
                  className="px-4 py-2 rounded-xl text-sm font-semibold transition"
                  style={isActive ? { background: "var(--accent)", color: "white" } : { background: "var(--bg-muted)", color: "var(--text)" }}
                >
                  {item.label}
                </Link>
              );
            })}
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <section className="mb-6 fade-in">
          <h2 className="text-2xl md:text-3xl font-bold">{title}</h2>
          <p className="soft-text mt-1">{subtitle}</p>
        </section>

        <Routes>
          <Route path="/" element={<ReposPage />} />
          <Route path="/repos/:id" element={<RepoDetailPage />} />
          <Route path="/jobs" element={<JobsPage />} />
          <Route path="/jobs/:id" element={<JobDetailPage />} />
          <Route path="/mappings" element={<MappingsPage />} />
          <Route path="/settings" element={<SettingsPage />} />
        </Routes>
      </main>
    </div>
  );
}
