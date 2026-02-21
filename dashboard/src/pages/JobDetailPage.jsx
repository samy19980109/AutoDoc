import { useEffect, useMemo, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api } from "../api/client";

const statusStyles = {
  pending: { background: "rgba(245,158,11,.18)", color: "#b45309" },
  processing: { background: "rgba(59,130,246,.18)", color: "#2563eb" },
  completed: { background: "rgba(34,197,94,.18)", color: "#15803d" },
  failed: { background: "rgba(239,68,68,.18)", color: "#b91c1c" },
};

export default function JobDetailPage() {
  const { id } = useParams();
  const [job, setJob] = useState(null);
  const [logs, setLogs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [autoRefresh, setAutoRefresh] = useState(true);
  const [banner, setBanner] = useState("");

  useEffect(() => {
    loadData();
  }, [id]);

  useEffect(() => {
    if (!autoRefresh) return undefined;
    if (!job || ["completed", "failed"].includes(job.status)) return undefined;

    const timer = setInterval(loadData, 5000);
    return () => clearInterval(timer);
  }, [autoRefresh, job?.status, id]);

  const logCount = useMemo(() => logs.length, [logs]);

  async function loadData() {
    try {
      const [jobData, logsData] = await Promise.all([api.getJob(id), api.getJobLogs(id)]);
      setJob(jobData);
      setLogs(logsData);
      setBanner("");
    } catch (err) {
      setBanner(`Failed to load job: ${err.message}`);
    } finally {
      setLoading(false);
    }
  }

  if (loading) return <div className="panel p-8 text-center soft-text">Loading job details...</div>;
  if (!job) return <div className="panel p-8 text-center">Job not found.</div>;

  return (
    <div className="space-y-6 fade-in">
      {banner && <div className="panel p-3 text-sm">{banner}</div>}

      <div className="flex flex-wrap gap-3 items-center justify-between">
        <div>
          <Link to="/jobs" className="text-sm font-semibold" style={{ color: "var(--accent)" }}>← Back to jobs</Link>
          <div className="flex items-center gap-3 mt-1">
            <h3 className="text-2xl font-extrabold">Job #{job.id}</h3>
            <span className="px-3 py-1 rounded-full text-sm font-semibold" style={statusStyles[job.status] || {}}>{job.status}</span>
          </div>
        </div>
        <div className="flex gap-2">
          <button onClick={loadData} className="px-3 py-2 rounded-xl text-sm font-semibold" style={{ background: "var(--bg-muted)" }}>Refresh</button>
          <button onClick={() => setAutoRefresh((v) => !v)} className="px-3 py-2 rounded-xl text-sm font-semibold" style={{ background: autoRefresh ? "var(--accent)" : "var(--bg-muted)", color: autoRefresh ? "white" : "var(--text)" }}>
            {autoRefresh ? "Auto-refresh On" : "Auto-refresh Off"}
          </button>
        </div>
      </div>

      <section className="grid md:grid-cols-4 gap-4">
        <div className="panel p-4"><p className="text-xs uppercase soft-text">Repository</p><p className="text-lg font-bold mt-1"><Link to={`/repos/${job.repo_id}`} style={{ color: "var(--accent)" }}>#{job.repo_id}</Link></p></div>
        <div className="panel p-4"><p className="text-xs uppercase soft-text">Trigger</p><p className="text-lg font-bold mt-1 capitalize">{job.trigger_type}</p></div>
        <div className="panel p-4"><p className="text-xs uppercase soft-text">Started</p><p className="text-sm font-semibold mt-1">{job.started_at ? new Date(job.started_at).toLocaleString() : "-"}</p></div>
        <div className="panel p-4"><p className="text-xs uppercase soft-text">Logs</p><p className="text-lg font-bold mt-1">{logCount}</p></div>
      </section>

      {job.error && (
        <section className="panel p-4" style={{ borderColor: "rgba(239,68,68,.45)", background: "rgba(239,68,68,.08)" }}>
          <p className="text-sm font-semibold" style={{ color: "var(--danger)" }}>Error</p>
          <p className="mt-1 text-sm font-mono whitespace-pre-wrap">{job.error}</p>
        </section>
      )}

      <section className="panel p-5">
        <h4 className="text-lg font-bold mb-3">Processing Logs</h4>
        <div className="space-y-3 max-h-[520px] overflow-auto pr-1">
          {logs.map((log, idx) => (
            <div key={log.id} className="rounded-xl border p-3" style={{ borderColor: "var(--border)", animationDelay: `${idx * 25}ms` }}>
              <div className="flex items-center justify-between gap-2">
                <span className="text-xs font-semibold px-2 py-1 rounded-lg" style={{ background: "var(--bg-muted)" }}>{log.step}</span>
                <span className="text-xs soft-text">{new Date(log.created_at).toLocaleString()}</span>
              </div>
              <p className="text-sm mt-2">{log.message}</p>
            </div>
          ))}
          {logs.length === 0 && <div className="soft-text text-sm">No logs yet.</div>}
        </div>
      </section>
    </div>
  );
}
