import { Routes, Route, Link, useLocation } from "react-router-dom";
import ReposPage from "./pages/ReposPage";
import RepoDetailPage from "./pages/RepoDetailPage";
import JobsPage from "./pages/JobsPage";
import JobDetailPage from "./pages/JobDetailPage";
import SettingsPage from "./pages/SettingsPage";

const navItems = [
  { path: "/", label: "Repositories" },
  { path: "/jobs", label: "Jobs" },
  { path: "/settings", label: "Settings" },
];

export default function App() {
  const location = useLocation();

  return (
    <div className="min-h-screen">
      <nav className="bg-white border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between h-16">
            <div className="flex">
              <div className="flex-shrink-0 flex items-center">
                <h1 className="text-xl font-bold text-indigo-600">AutoDoc</h1>
              </div>
              <div className="ml-10 flex space-x-8">
                {navItems.map((item) => {
                  const isActive =
                    item.path === "/"
                      ? location.pathname === "/" || location.pathname.startsWith("/repos")
                      : location.pathname.startsWith(item.path);
                  return (
                    <Link
                      key={item.path}
                      to={item.path}
                      className={`inline-flex items-center px-1 pt-1 border-b-2 text-sm font-medium ${
                        isActive
                          ? "border-indigo-500 text-gray-900"
                          : "border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300"
                      }`}
                    >
                      {item.label}
                    </Link>
                  );
                })}
              </div>
            </div>
          </div>
        </div>
      </nav>

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <Routes>
          <Route path="/" element={<ReposPage />} />
          <Route path="/repos/:id" element={<RepoDetailPage />} />
          <Route path="/jobs" element={<JobsPage />} />
          <Route path="/jobs/:id" element={<JobDetailPage />} />
          <Route path="/settings" element={<SettingsPage />} />
        </Routes>
      </main>
    </div>
  );
}
