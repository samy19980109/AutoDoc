import { useEffect, useMemo, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { api } from "../api/client";

const statusStyles = {
  pending: { background: "rgba(245,158,11,.18)", color: "#b45309" },
  processing: { background: "rgba(59,130,246,.18)", color: "#2563eb" },
  completed: { background: "rgba(34,197,94,.18)", color: "#15803d" },
  failed: { background: "rgba(239,68,68,.18)", color: "#b91c1c" },
};

export default function JobsPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const [jobs, setJobs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [banner, setBanner] = useState("");

  const initialRepoId = searchParams.get("repo_id") || "";
  const initialStatus = searchParams.get("status") || "";

  const [repoId, setRepoId] = useState(initialRepoId);
  const [statusFilter, setStatusFilter] = useState(initialStatus);

  useEffect(() => {
    loadJobs();
  }, []);

  const stats = useMemo(() => {
    return {
      total: jobs.length,
      running: jobs.filter((j) => j.status === "processing").length,
      failed: jobs.filter((j) => j.status === "failed").length,
    };
  }, [jobs]);

  async function loadJobs() {
    setLoading(true);
    try {
      const params = { limit: 100 };
      if (repoId.trim()) params.repo_id = repoId.trim();
      if (statusFilter) params.status = statusFilter;

      const nextSearch = new URLSearchParams();
      if (params.repo_id) nextSearch.set("repo_id", params.repo_id);
      if (params.status) nextSearch.set("status", params.status);
      setSearchParams(nextSearch);

      const data = await api.listJobs(params);
      setJobs(data);
      setBanner("");
    } catch (err) {
      setBanner(`Failed to load jobs: ${err.message}`);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="space-y-6 fade-in">
      {banner && <div className="panel p-3 text-sm">{banner}</div>}

      <section className="grid md:grid-cols-3 gap-4">
        <div className="panel p-4"><p className="text-xs uppercase soft-text">Loaded Jobs</p><p className="text-3xl font-extrabold mt-1">{stats.total}</p></div>
        <div className="panel p-4"><p className="text-xs uppercase soft-text">Currently Processing</p><p className="text-3xl font-extrabold mt-1">{stats.running}</p></div>
        <div className="panel p-4"><p className="text-xs uppercase soft-text">Failed</p><p className="text-3xl font-extrabold mt-1">{stats.failed}</p></div>
      </section>

      <section className="panel p-5">
        <div className="flex flex-wrap items-end gap-3">
          <label className="block">
            <span className="text-sm soft-text">Repository ID</span>
            <input
              value={repoId}
              onChange={(e) => setRepoId(e.target.value)}
              placeholder="e.g. 7"
              className="mt-1 rounded-xl border p-2.5"
              style={{ background: "var(--bg-elevated)", borderColor: "var(--border)" }}
            />
          </label>
          <label className="block">
            <span className="text-sm soft-text">Status</span>
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="mt-1 rounded-xl border p-2.5"
              style={{ background: "var(--bg-elevated)", borderColor: "var(--border)" }}
            >
              <option value="">All</option>
              <option value="pending">Pending</option>
              <option value="processing">Processing</option>
              <option value="completed">Completed</option>
              <option value="failed">Failed</option>
            </select>
          </label>
          <button className="px-4 py-2.5 rounded-xl text-sm font-semibold text-white" style={{ background: "var(--accent)" }} onClick={loadJobs}>
            Apply Filters
          </button>
        </div>
      </section>

      <section className="panel p-5 overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b soft-text" style={{ borderColor: "var(--border)" }}>
              <th className="text-left py-2 pr-3">Job</th>
              <th className="text-left py-2 pr-3">Repository</th>
              <th className="text-left py-2 pr-3">Trigger</th>
              <th className="text-left py-2 pr-3">Status</th>
              <th className="text-left py-2 pr-3">Started</th>
              <th className="text-left py-2">Completed</th>
            </tr>
          </thead>
          <tbody>
            {!loading && jobs.map((job) => (
              <tr key={job.id} className="border-b" style={{ borderColor: "var(--border)" }}>
                <td className="py-3 pr-3"><Link to={`/jobs/${job.id}`} className="font-semibold" style={{ color: "var(--accent)" }}>#{job.id}</Link></td>
                <td className="py-3 pr-3"><Link to={`/repos/${job.repo_id}`} style={{ color: "var(--accent)" }}>Repo #{job.repo_id}</Link></td>
                <td className="py-3 pr-3 capitalize">{job.trigger_type}</td>
                <td className="py-3 pr-3"><span className="px-2 py-1 rounded-full text-xs font-semibold" style={statusStyles[job.status] || {}}>{job.status}</span></td>
                <td className="py-3 pr-3">{job.started_at ? new Date(job.started_at).toLocaleString() : "-"}</td>
                <td className="py-3">{job.completed_at ? new Date(job.completed_at).toLocaleString() : "-"}</td>
              </tr>
            ))}

            {loading && <tr><td colSpan={6} className="py-8 text-center soft-text">Loading jobs...</td></tr>}
            {!loading && jobs.length === 0 && <tr><td colSpan={6} className="py-8 text-center soft-text">No jobs found for selected filters.</td></tr>}
          </tbody>
        </table>
      </section>
    </div>
  );
}
