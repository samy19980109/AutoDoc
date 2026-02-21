import { useEffect, useMemo, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api } from "../api/client";

const statusStyles = {
  pending: { background: "rgba(245,158,11,.18)", color: "#b45309" },
  processing: { background: "rgba(59,130,246,.18)", color: "#2563eb" },
  completed: { background: "rgba(34,197,94,.18)", color: "#15803d" },
  failed: { background: "rgba(239,68,68,.18)", color: "#b91c1c" },
};

function repoName(url) {
  return (url || "").replace("https://github.com/", "").replace(/\.git$/, "");
}

export default function RepoDetailPage() {
  const { id } = useParams();
  const [repo, setRepo] = useState(null);
  const [mappings, setMappings] = useState([]);
  const [jobs, setJobs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [banner, setBanner] = useState("");
  const [saving, setSaving] = useState(false);

  const [form, setForm] = useState({
    default_branch: "main",
    destination_platform: "confluence",
  });
  const [spaceKey, setSpaceKey] = useState("");
  const [databaseId, setDatabaseId] = useState("");

  useEffect(() => {
    load();
  }, [id]);

  const mappingCount = useMemo(() => mappings.length, [mappings]);

  async function load() {
    setLoading(true);
    try {
      const [repoData, mappingsData, jobsData] = await Promise.all([
        api.getRepo(id),
        api.listMappings({ repo_id: id, limit: 100 }),
        api.listJobs({ repo_id: id, limit: 12 }),
      ]);

      setRepo(repoData);
      setMappings(mappingsData);
      setJobs(jobsData);

      setForm({
        default_branch: repoData.default_branch,
        destination_platform: repoData.destination_platform,
      });
      setSpaceKey(repoData.destination_config?.space_key || "");
      setDatabaseId(repoData.destination_config?.database_id || "");
    } catch (err) {
      setBanner(`Failed to load repository: ${err.message}`);
    } finally {
      setLoading(false);
    }
  }

  async function saveChanges(e) {
    e.preventDefault();
    if (!repo) return;

    try {
      setSaving(true);
      await api.updateRepo(repo.id, {
        ...form,
        destination_config:
          form.destination_platform === "confluence"
            ? { space_key: spaceKey.trim() }
            : { database_id: databaseId.trim() },
      });
      setBanner("Repository settings updated.");
      await load();
    } catch (err) {
      setBanner(`Update failed: ${err.message}`);
    } finally {
      setSaving(false);
    }
  }

  async function trigger(triggerType) {
    if (!repo) return;
    try {
      await api.triggerRepo(repo.id, triggerType);
      setBanner(`Job started with '${triggerType}' trigger.`);
      await load();
    } catch (err) {
      setBanner(`Trigger failed: ${err.message}`);
    }
  }

  async function deleteMapping(mappingId) {
    const ok = window.confirm("Delete this page mapping?");
    if (!ok) return;

    try {
      await api.deleteMapping(mappingId);
      setBanner("Mapping deleted.");
      await load();
    } catch (err) {
      setBanner(`Mapping delete failed: ${err.message}`);
    }
  }

  if (loading) return <div className="panel p-8 text-center soft-text">Loading repository...</div>;
  if (!repo) return <div className="panel p-8 text-center">Repository not found.</div>;

  return (
    <div className="space-y-6 fade-in">
      {banner && <div className="panel p-3 text-sm">{banner}</div>}

      <div className="flex flex-wrap gap-3 items-center justify-between">
        <div>
          <Link to="/" className="text-sm font-semibold" style={{ color: "var(--accent)" }}>
            ← Back to repositories
          </Link>
          <h3 className="text-2xl font-extrabold mt-1">{repoName(repo.github_url)}</h3>
          <p className="soft-text text-sm">Repository ID #{repo.id}</p>
        </div>
        <div className="flex gap-2">
          <button className="px-3 py-2 rounded-xl text-sm font-semibold" style={{ background: "var(--bg-muted)" }} onClick={() => trigger("manual")}>Run Now</button>
          <button className="px-3 py-2 rounded-xl text-sm font-semibold" style={{ background: "var(--bg-muted)" }} onClick={() => trigger("scheduled")}>Queue Scheduled</button>
          <button className="px-3 py-2 rounded-xl text-sm font-semibold" style={{ background: "var(--bg-muted)" }} onClick={() => trigger("webhook")}>Simulate Webhook</button>
        </div>
      </div>

      <section className="grid md:grid-cols-4 gap-4">
        <div className="panel p-4">
          <p className="text-xs uppercase soft-text">Branch</p>
          <p className="text-xl font-bold mt-1">{repo.default_branch}</p>
        </div>
        <div className="panel p-4">
          <p className="text-xs uppercase soft-text">Destination</p>
          <p className="text-xl font-bold mt-1 capitalize">{repo.destination_platform}</p>
        </div>
        <div className="panel p-4">
          <p className="text-xs uppercase soft-text">Mappings</p>
          <p className="text-xl font-bold mt-1">{mappingCount}</p>
        </div>
        <div className="panel p-4">
          <p className="text-xs uppercase soft-text">Recent Jobs</p>
          <p className="text-xl font-bold mt-1">{jobs.length}</p>
        </div>
      </section>

      <section className="panel p-5">
        <h4 className="text-lg font-bold">Repository Settings</h4>
        <form onSubmit={saveChanges} className="mt-4 grid md:grid-cols-2 gap-4">
          <label>
            <span className="text-sm soft-text">Default Branch</span>
            <input
              value={form.default_branch}
              onChange={(e) => setForm((v) => ({ ...v, default_branch: e.target.value }))}
              className="mt-1 w-full rounded-xl border p-2.5"
              style={{ background: "var(--bg-elevated)", borderColor: "var(--border)" }}
            />
          </label>

          <label>
            <span className="text-sm soft-text">Destination Platform</span>
            <select
              value={form.destination_platform}
              onChange={(e) => setForm((v) => ({ ...v, destination_platform: e.target.value }))}
              className="mt-1 w-full rounded-xl border p-2.5"
              style={{ background: "var(--bg-elevated)", borderColor: "var(--border)" }}
            >
              <option value="confluence">Confluence</option>
              <option value="notion">Notion</option>
            </select>
          </label>

          {form.destination_platform === "confluence" ? (
            <label>
              <span className="text-sm soft-text">Confluence Space Key</span>
              <input
                value={spaceKey}
                onChange={(e) => setSpaceKey(e.target.value)}
                className="mt-1 w-full rounded-xl border p-2.5"
                style={{ background: "var(--bg-elevated)", borderColor: "var(--border)" }}
                placeholder="DOCS"
              />
            </label>
          ) : (
            <label>
              <span className="text-sm soft-text">Notion Database ID</span>
              <input
                value={databaseId}
                onChange={(e) => setDatabaseId(e.target.value)}
                className="mt-1 w-full rounded-xl border p-2.5"
                style={{ background: "var(--bg-elevated)", borderColor: "var(--border)" }}
                placeholder="xxxxxxxxxxxxxxxx"
              />
            </label>
          )}

          <div className="md:col-span-2 flex justify-end">
            <button type="submit" disabled={saving} className="px-4 py-2 rounded-xl text-sm font-semibold text-white" style={{ background: "var(--accent)" }}>
              {saving ? "Saving..." : "Save Settings"}
            </button>
          </div>
        </form>
      </section>

      <section className="panel p-5">
        <div className="flex items-center justify-between mb-3">
          <h4 className="text-lg font-bold">Recent Jobs</h4>
          <Link to={`/jobs?repo_id=${repo.id}`} className="text-sm font-semibold" style={{ color: "var(--accent)" }}>View all jobs</Link>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b soft-text" style={{ borderColor: "var(--border)" }}>
                <th className="text-left py-2 pr-3">Job</th>
                <th className="text-left py-2 pr-3">Trigger</th>
                <th className="text-left py-2 pr-3">Status</th>
                <th className="text-left py-2">Started</th>
              </tr>
            </thead>
            <tbody>
              {jobs.map((job) => (
                <tr key={job.id} className="border-b" style={{ borderColor: "var(--border)" }}>
                  <td className="py-3 pr-3"><Link to={`/jobs/${job.id}`} style={{ color: "var(--accent)" }} className="font-semibold">#{job.id}</Link></td>
                  <td className="py-3 pr-3 capitalize">{job.trigger_type}</td>
                  <td className="py-3 pr-3"><span className="px-2 py-1 rounded-full text-xs font-semibold" style={statusStyles[job.status] || {}}>{job.status}</span></td>
                  <td className="py-3">{job.started_at ? new Date(job.started_at).toLocaleString() : "-"}</td>
                </tr>
              ))}
              {jobs.length === 0 && (
                <tr><td colSpan={4} className="py-6 text-center soft-text">No jobs yet.</td></tr>
              )}
            </tbody>
          </table>
        </div>
      </section>

      <section className="panel p-5">
        <div className="flex items-center justify-between mb-3">
          <h4 className="text-lg font-bold">Page Mappings</h4>
          <Link to={`/mappings?repo_id=${repo.id}`} className="text-sm font-semibold" style={{ color: "var(--accent)" }}>Open mappings explorer</Link>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b soft-text" style={{ borderColor: "var(--border)" }}>
                <th className="text-left py-2 pr-3">Code Path</th>
                <th className="text-left py-2 pr-3">Doc Type</th>
                <th className="text-left py-2 pr-3">Destination Page</th>
                <th className="text-left py-2 pr-3">Last Synced</th>
                <th className="text-right py-2">Actions</th>
              </tr>
            </thead>
            <tbody>
              {mappings.map((m) => (
                <tr key={m.id} className="border-b" style={{ borderColor: "var(--border)" }}>
                  <td className="py-3 pr-3 font-mono">{m.code_path}</td>
                  <td className="py-3 pr-3">{m.doc_type}</td>
                  <td className="py-3 pr-3 font-mono">{m.destination_page_id || "-"}</td>
                  <td className="py-3 pr-3">{m.last_synced_at ? new Date(m.last_synced_at).toLocaleString() : "Never"}</td>
                  <td className="py-3 text-right">
                    <button className="px-2.5 py-1.5 rounded-lg text-xs font-semibold" style={{ background: "rgba(239,68,68,.14)", color: "var(--danger)" }} onClick={() => deleteMapping(m.id)}>
                      Delete
                    </button>
                  </td>
                </tr>
              ))}
              {mappings.length === 0 && (
                <tr><td colSpan={5} className="py-6 text-center soft-text">No mappings yet.</td></tr>
              )}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}
