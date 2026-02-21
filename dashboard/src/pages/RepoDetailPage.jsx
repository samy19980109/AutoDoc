import { useState, useEffect } from "react";
import { useParams, Link } from "react-router-dom";
import { api } from "../api/client";

const PLATFORM_LABELS = { confluence: "Confluence", notion: "Notion" };

export default function RepoDetailPage() {
  const { id } = useParams();
  const [repo, setRepo] = useState(null);
  const [mappings, setMappings] = useState([]);
  const [jobs, setJobs] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadData();
  }, [id]);

  async function loadData() {
    try {
      const [repoData, mappingsData, jobsData] = await Promise.all([
        api.getRepo(id),
        api.listMappings(id),
        api.listJobs({ repo_id: id, limit: 10 }),
      ]);
      setRepo(repoData);
      setMappings(mappingsData);
      setJobs(jobsData);
    } catch (err) {
      console.error("Failed to load repo:", err);
    } finally {
      setLoading(false);
    }
  }

  async function handleTrigger() {
    try {
      await api.triggerRepo(id);
      alert("Documentation generation triggered!");
      loadData();
    } catch (err) {
      alert("Trigger failed: " + err.message);
    }
  }

  if (loading) return <div className="text-center py-12 text-gray-500">Loading...</div>;
  if (!repo) return <div className="text-center py-12 text-red-500">Repository not found</div>;

  const statusColor = {
    pending: "bg-yellow-100 text-yellow-800",
    processing: "bg-blue-100 text-blue-800",
    completed: "bg-green-100 text-green-800",
    failed: "bg-red-100 text-red-800",
  };

  const platformLabel = PLATFORM_LABELS[repo.destination_platform] || repo.destination_platform;
  const configSummary =
    repo.destination_platform === "confluence"
      ? repo.destination_config?.space_key || "Not set"
      : repo.destination_config?.database_id
        ? repo.destination_config.database_id.slice(0, 12) + "..."
        : "Not set";

  return (
    <div>
      <div className="flex justify-between items-center mb-6">
        <div>
          <Link to="/" className="text-sm text-indigo-600 hover:text-indigo-900">&larr; Back to Repositories</Link>
          <h2 className="text-2xl font-bold text-gray-900 mt-1">
            {repo.github_url.replace("https://github.com/", "")}
          </h2>
        </div>
        <button
          onClick={handleTrigger}
          className="bg-indigo-600 text-white px-4 py-2 rounded-md hover:bg-indigo-700 text-sm font-medium"
        >
          Generate Docs
        </button>
      </div>

      <div className="grid grid-cols-4 gap-4 mb-8">
        <div className="bg-white p-4 rounded-lg shadow">
          <div className="text-sm text-gray-500">Branch</div>
          <div className="text-lg font-medium">{repo.default_branch}</div>
        </div>
        <div className="bg-white p-4 rounded-lg shadow">
          <div className="text-sm text-gray-500">Destination</div>
          <div className="text-lg font-medium">
            <span className={`px-2 py-1 rounded-full text-xs font-medium ${
              repo.destination_platform === "notion"
                ? "bg-gray-100 text-gray-800"
                : "bg-blue-100 text-blue-800"
            }`}>
              {platformLabel}
            </span>
          </div>
        </div>
        <div className="bg-white p-4 rounded-lg shadow">
          <div className="text-sm text-gray-500">
            {repo.destination_platform === "confluence" ? "Space Key" : "Database ID"}
          </div>
          <div className="text-lg font-medium">{configSummary}</div>
        </div>
        <div className="bg-white p-4 rounded-lg shadow">
          <div className="text-sm text-gray-500">Page Mappings</div>
          <div className="text-lg font-medium">{mappings.length}</div>
        </div>
      </div>

      <h3 className="text-lg font-semibold text-gray-900 mb-3">Recent Jobs</h3>
      <div className="bg-white shadow rounded-lg overflow-hidden mb-8">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">ID</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Trigger</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Status</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Started</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-200">
            {jobs.map((job) => (
              <tr key={job.id} className="hover:bg-gray-50">
                <td className="px-6 py-4">
                  <Link to={`/jobs/${job.id}`} className="text-indigo-600 hover:text-indigo-900">#{job.id}</Link>
                </td>
                <td className="px-6 py-4 text-sm text-gray-500">{job.trigger_type}</td>
                <td className="px-6 py-4">
                  <span className={`px-2 py-1 rounded-full text-xs font-medium ${statusColor[job.status] || ""}`}>
                    {job.status}
                  </span>
                </td>
                <td className="px-6 py-4 text-sm text-gray-500">
                  {job.started_at ? new Date(job.started_at).toLocaleString() : "\u2014"}
                </td>
              </tr>
            ))}
            {jobs.length === 0 && (
              <tr>
                <td colSpan="4" className="px-6 py-8 text-center text-gray-500">No jobs yet</td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      <h3 className="text-lg font-semibold text-gray-900 mb-3">Page Mappings</h3>
      <div className="bg-white shadow rounded-lg overflow-hidden">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Code Path</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Doc Type</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Page ID</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Last Synced</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-200">
            {mappings.map((m) => (
              <tr key={m.id} className="hover:bg-gray-50">
                <td className="px-6 py-4 text-sm font-mono">{m.code_path}</td>
                <td className="px-6 py-4 text-sm text-gray-500">{m.doc_type}</td>
                <td className="px-6 py-4 text-sm text-gray-500">{m.destination_page_id || "\u2014"}</td>
                <td className="px-6 py-4 text-sm text-gray-500">
                  {m.last_synced_at ? new Date(m.last_synced_at).toLocaleString() : "Never"}
                </td>
              </tr>
            ))}
            {mappings.length === 0 && (
              <tr>
                <td colSpan="4" className="px-6 py-8 text-center text-gray-500">No page mappings yet</td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
