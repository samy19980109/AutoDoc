import { useState, useEffect } from "react";
import { useParams, Link } from "react-router-dom";
import { api } from "../api/client";

const statusColor = {
  pending: "bg-yellow-100 text-yellow-800",
  processing: "bg-blue-100 text-blue-800",
  completed: "bg-green-100 text-green-800",
  failed: "bg-red-100 text-red-800",
};

export default function JobDetailPage() {
  const { id } = useParams();
  const [job, setJob] = useState(null);
  const [logs, setLogs] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadData();
  }, [id]);

  async function loadData() {
    try {
      const [jobData, logsData] = await Promise.all([api.getJob(id), api.getJobLogs(id)]);
      setJob(jobData);
      setLogs(logsData);
    } catch (err) {
      console.error("Failed to load job:", err);
    } finally {
      setLoading(false);
    }
  }

  if (loading) return <div className="text-center py-12 text-gray-500">Loading...</div>;
  if (!job) return <div className="text-center py-12 text-red-500">Job not found</div>;

  return (
    <div>
      <Link to="/jobs" className="text-sm text-indigo-600 hover:text-indigo-900">&larr; Back to Jobs</Link>
      <div className="flex items-center gap-4 mt-2 mb-6">
        <h2 className="text-2xl font-bold text-gray-900">Job #{job.id}</h2>
        <span className={`px-3 py-1 rounded-full text-sm font-medium ${statusColor[job.status] || ""}`}>
          {job.status}
        </span>
      </div>

      <div className="grid grid-cols-4 gap-4 mb-8">
        <div className="bg-white p-4 rounded-lg shadow">
          <div className="text-sm text-gray-500">Repository</div>
          <Link to={`/repos/${job.repo_id}`} className="text-lg font-medium text-indigo-600">
            #{job.repo_id}
          </Link>
        </div>
        <div className="bg-white p-4 rounded-lg shadow">
          <div className="text-sm text-gray-500">Trigger</div>
          <div className="text-lg font-medium">{job.trigger_type}</div>
        </div>
        <div className="bg-white p-4 rounded-lg shadow">
          <div className="text-sm text-gray-500">Started</div>
          <div className="text-lg font-medium">{job.started_at ? new Date(job.started_at).toLocaleString() : "—"}</div>
        </div>
        <div className="bg-white p-4 rounded-lg shadow">
          <div className="text-sm text-gray-500">Completed</div>
          <div className="text-lg font-medium">{job.completed_at ? new Date(job.completed_at).toLocaleString() : "—"}</div>
        </div>
      </div>

      {job.error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4 mb-8">
          <h3 className="text-sm font-medium text-red-800">Error</h3>
          <p className="text-sm text-red-700 mt-1 font-mono">{job.error}</p>
        </div>
      )}

      <h3 className="text-lg font-semibold text-gray-900 mb-3">Processing Logs</h3>
      <div className="bg-white shadow rounded-lg overflow-hidden">
        <div className="divide-y divide-gray-200">
          {logs.map((log) => (
            <div key={log.id} className="px-6 py-4">
              <div className="flex items-center gap-3">
                <span className="text-xs font-medium bg-gray-100 text-gray-600 px-2 py-1 rounded">{log.step}</span>
                <span className="text-xs text-gray-400">{new Date(log.created_at).toLocaleTimeString()}</span>
              </div>
              <p className="text-sm text-gray-700 mt-1">{log.message}</p>
            </div>
          ))}
          {logs.length === 0 && (
            <div className="px-6 py-8 text-center text-gray-500">No logs yet</div>
          )}
        </div>
      </div>
    </div>
  );
}
