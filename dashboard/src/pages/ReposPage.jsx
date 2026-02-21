import { useState, useEffect } from "react";
import { Link } from "react-router-dom";
import { api } from "../api/client";

const PLATFORM_LABELS = { confluence: "Confluence", notion: "Notion" };

export default function ReposPage() {
  const [repos, setRepos] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({
    github_url: "",
    default_branch: "main",
    destination_platform: "confluence",
    destination_config: {},
  });

  // Derived config fields
  const [spaceKey, setSpaceKey] = useState("");
  const [databaseId, setDatabaseId] = useState("");

  useEffect(() => {
    loadRepos();
  }, []);

  async function loadRepos() {
    try {
      const data = await api.listRepos();
      setRepos(data);
    } catch (err) {
      console.error("Failed to load repos:", err);
    } finally {
      setLoading(false);
    }
  }

  async function handleCreate(e) {
    e.preventDefault();
    const config =
      form.destination_platform === "confluence"
        ? { space_key: spaceKey }
        : { database_id: databaseId };
    const payload = { ...form, destination_config: config };
    try {
      await api.createRepo(payload);
      setForm({ github_url: "", default_branch: "main", destination_platform: "confluence", destination_config: {} });
      setSpaceKey("");
      setDatabaseId("");
      setShowForm(false);
      loadRepos();
    } catch (err) {
      alert("Failed to create repo: " + err.message);
    }
  }

  async function handleTrigger(repoId) {
    try {
      await api.triggerRepo(repoId);
      alert("Documentation generation triggered!");
    } catch (err) {
      alert("Failed to trigger: " + err.message);
    }
  }

  if (loading) return <div className="text-center py-12 text-gray-500">Loading...</div>;

  return (
    <div>
      <div className="flex justify-between items-center mb-6">
        <h2 className="text-2xl font-bold text-gray-900">Repositories</h2>
        <button
          onClick={() => setShowForm(!showForm)}
          className="bg-indigo-600 text-white px-4 py-2 rounded-md hover:bg-indigo-700 text-sm font-medium"
        >
          Add Repository
        </button>
      </div>

      {showForm && (
        <form onSubmit={handleCreate} className="bg-white p-6 rounded-lg shadow mb-6 space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700">GitHub URL</label>
            <input
              type="url"
              required
              value={form.github_url}
              onChange={(e) => setForm({ ...form, github_url: e.target.value })}
              placeholder="https://github.com/org/repo"
              className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 border p-2"
            />
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700">Default Branch</label>
              <input
                type="text"
                value={form.default_branch}
                onChange={(e) => setForm({ ...form, default_branch: e.target.value })}
                className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 border p-2"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700">Documentation Destination</label>
              <select
                value={form.destination_platform}
                onChange={(e) => setForm({ ...form, destination_platform: e.target.value })}
                className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 border p-2"
              >
                <option value="confluence">Confluence</option>
                <option value="notion">Notion</option>
              </select>
            </div>
          </div>

          {form.destination_platform === "confluence" && (
            <div>
              <label className="block text-sm font-medium text-gray-700">Confluence Space Key</label>
              <input
                type="text"
                value={spaceKey}
                onChange={(e) => setSpaceKey(e.target.value)}
                placeholder="DOCS"
                className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 border p-2"
              />
            </div>
          )}

          {form.destination_platform === "notion" && (
            <div>
              <label className="block text-sm font-medium text-gray-700">Notion Database ID</label>
              <input
                type="text"
                value={databaseId}
                onChange={(e) => setDatabaseId(e.target.value)}
                placeholder="abc123def456..."
                className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 border p-2"
              />
            </div>
          )}

          <div className="flex gap-2">
            <button type="submit" className="bg-indigo-600 text-white px-4 py-2 rounded-md hover:bg-indigo-700 text-sm">
              Create
            </button>
            <button type="button" onClick={() => setShowForm(false)} className="bg-gray-200 text-gray-700 px-4 py-2 rounded-md text-sm">
              Cancel
            </button>
          </div>
        </form>
      )}

      <div className="bg-white shadow rounded-lg overflow-hidden">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Repository</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Branch</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Destination</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Created</th>
              <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase">Actions</th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {repos.map((repo) => (
              <tr key={repo.id} className="hover:bg-gray-50">
                <td className="px-6 py-4">
                  <Link to={`/repos/${repo.id}`} className="text-indigo-600 hover:text-indigo-900 font-medium">
                    {repo.github_url.replace("https://github.com/", "")}
                  </Link>
                </td>
                <td className="px-6 py-4 text-sm text-gray-500">{repo.default_branch}</td>
                <td className="px-6 py-4 text-sm text-gray-500">
                  <span className={`px-2 py-1 rounded-full text-xs font-medium ${
                    repo.destination_platform === "notion"
                      ? "bg-gray-100 text-gray-800"
                      : "bg-blue-100 text-blue-800"
                  }`}>
                    {PLATFORM_LABELS[repo.destination_platform] || repo.destination_platform}
                  </span>
                </td>
                <td className="px-6 py-4 text-sm text-gray-500">{new Date(repo.created_at).toLocaleDateString()}</td>
                <td className="px-6 py-4 text-right">
                  <button
                    onClick={() => handleTrigger(repo.id)}
                    className="text-sm text-indigo-600 hover:text-indigo-900 font-medium"
                  >
                    Generate Docs
                  </button>
                </td>
              </tr>
            ))}
            {repos.length === 0 && (
              <tr>
                <td colSpan="5" className="px-6 py-12 text-center text-gray-500">
                  No repositories configured. Add one to get started.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
