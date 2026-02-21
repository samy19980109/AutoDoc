import { useState, useEffect } from "react";
import { Link } from "react-router-dom";
import { api } from "../api/client";

const statusColor = {
  pending: "bg-yellow-100 text-yellow-800",
  processing: "bg-blue-100 text-blue-800",
  completed: "bg-green-100 text-green-800",
  failed: "bg-red-100 text-red-800",
};

export default function JobsPage() {
  const [jobs, setJobs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [statusFilter, setStatusFilter] = useState("");

  useEffect(() => {
    loadJobs();
  }, [statusFilter]);

  async function loadJobs() {
    try {
      const params = { limit: 50 };
      if (statusFilter) params.status = statusFilter;
      const data = await api.listJobs(params);
      setJobs(data);
    } catch (err) {
      console.error("Failed to load jobs:", err);
    } finally {
      setLoading(false);
    }
  }

  if (loading) return <div className="text-center py-12 text-gray-500">Loading...</div>;

  return (
    <div>
      <div className="flex justify-between items-center mb-6">
        <h2 className="text-2xl font-bold text-gray-900">Jobs</h2>
        <select
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
          className="rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 border p-2 text-sm"
        >
          <option value="">All Statuses</option>
          <option value="pending">Pending</option>
          <option value="processing">Processing</option>
          <option value="completed">Completed</option>
          <option value="failed">Failed</option>
        </select>
      </div>

      <div className="bg-white shadow rounded-lg overflow-hidden">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">ID</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Repository</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Trigger</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Status</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Started</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Completed</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-200">
            {jobs.map((job) => (
              <tr key={job.id} className="hover:bg-gray-50">
                <td className="px-6 py-4">
                  <Link to={`/jobs/${job.id}`} className="text-indigo-600 hover:text-indigo-900 font-medium">
                    #{job.id}
                  </Link>
                </td>
                <td className="px-6 py-4 text-sm text-gray-500">
                  <Link to={`/repos/${job.repo_id}`} className="text-indigo-600 hover:text-indigo-900">
                    Repo #{job.repo_id}
                  </Link>
                </td>
                <td className="px-6 py-4 text-sm text-gray-500">{job.trigger_type}</td>
                <td className="px-6 py-4">
                  <span className={`px-2 py-1 rounded-full text-xs font-medium ${statusColor[job.status] || ""}`}>
                    {job.status}
                  </span>
                </td>
                <td className="px-6 py-4 text-sm text-gray-500">
                  {job.started_at ? new Date(job.started_at).toLocaleString() : "—"}
                </td>
                <td className="px-6 py-4 text-sm text-gray-500">
                  {job.completed_at ? new Date(job.completed_at).toLocaleString() : "—"}
                </td>
              </tr>
            ))}
            {jobs.length === 0 && (
              <tr>
                <td colSpan="6" className="px-6 py-12 text-center text-gray-500">No jobs found</td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
