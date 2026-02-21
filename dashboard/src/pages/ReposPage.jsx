import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api/client";

const EMPTY_FORM = {
  github_url: "",
  default_branch: "main",
  destination_platform: "confluence",
  destination_config: {},
  config_json: {},
};

function formatRepoName(url) {
  return (url || "").replace("https://github.com/", "").replace(/\.git$/, "");
}

function destinationBadge(platform) {
  if (platform === "notion") {
    return { text: "Notion", style: { background: "rgba(99,102,241,.14)", color: "#4f46e5" } };
  }
  return { text: "Confluence", style: { background: "rgba(14,116,144,.14)", color: "#0e7490" } };
}

export default function ReposPage() {
  const [repos, setRepos] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showCreate, setShowCreate] = useState(false);
  const [createForm, setCreateForm] = useState(EMPTY_FORM);
  const [spaceKey, setSpaceKey] = useState("");
  const [databaseId, setDatabaseId] = useState("");
  const [editingId, setEditingId] = useState(null);
  const [editForm, setEditForm] = useState(null);
  const [editSpaceKey, setEditSpaceKey] = useState("");
  const [editDatabaseId, setEditDatabaseId] = useState("");
  const [busyId, setBusyId] = useState(null);
  const [banner, setBanner] = useState("");

  useEffect(() => {
    loadRepos();
  }, []);

  const stats = useMemo(() => {
    return {
      total: repos.length,
      confluence: repos.filter((r) => r.destination_platform === "confluence").length,
      notion: repos.filter((r) => r.destination_platform === "notion").length,
    };
  }, [repos]);

  async function loadRepos() {
    setLoading(true);
    try {
      const data = await api.listRepos(0, 100);
      setRepos(data);
    } catch (err) {
      setBanner(`Failed to load repositories: ${err.message}`);
    } finally {
      setLoading(false);
    }
  }

  function withConfig(form, confluenceValue, notionValue) {
    return {
      ...form,
      destination_config:
        form.destination_platform === "confluence"
          ? { space_key: confluenceValue.trim() }
          : { database_id: notionValue.trim() },
    };
  }

  async function createRepo(e) {
    e.preventDefault();
    try {
      await api.createRepo(withConfig(createForm, spaceKey, databaseId));
      setShowCreate(false);
      setCreateForm(EMPTY_FORM);
      setSpaceKey("");
      setDatabaseId("");
      setBanner("Repository added.");
      await loadRepos();
    } catch (err) {
      setBanner(`Create failed: ${err.message}`);
    }
  }

  function startEdit(repo) {
    setEditingId(repo.id);
    setEditForm({
      github_url: repo.github_url,
      default_branch: repo.default_branch,
      destination_platform: repo.destination_platform,
      destination_config: repo.destination_config || {},
      config_json: repo.config_json || {},
    });
    setEditSpaceKey(repo.destination_config?.space_key || "");
    setEditDatabaseId(repo.destination_config?.database_id || "");
  }

  async function saveEdit(e) {
    e.preventDefault();
    if (!editingId || !editForm) return;

    try {
      setBusyId(editingId);
      await api.updateRepo(editingId, withConfig(editForm, editSpaceKey, editDatabaseId));
      setEditingId(null);
      setEditForm(null);
      setBanner("Repository updated.");
      await loadRepos();
    } catch (err) {
      setBanner(`Update failed: ${err.message}`);
    } finally {
      setBusyId(null);
    }
  }

  async function deleteRepo(repo) {
    const ok = window.confirm(`Delete ${formatRepoName(repo.github_url)} and all linked jobs/mappings?`);
    if (!ok) return;

    try {
      setBusyId(repo.id);
      await api.deleteRepo(repo.id);
      setBanner("Repository deleted.");
      await loadRepos();
    } catch (err) {
      setBanner(`Delete failed: ${err.message}`);
    } finally {
      setBusyId(null);
    }
  }

  async function trigger(repoId, triggerType) {
    try {
      setBusyId(repoId);
      await api.triggerRepo(repoId, triggerType);
      setBanner(`Job queued with trigger '${triggerType}'.`);
    } catch (err) {
      setBanner(`Trigger failed: ${err.message}`);
    } finally {
      setBusyId(null);
    }
  }

  return (
    <div className="space-y-6 fade-in">
      {banner && (
        <div className="panel p-3 text-sm" style={{ color: "var(--text)" }}>
          {banner}
        </div>
      )}

      <section className="grid md:grid-cols-3 gap-4">
        <div className="panel p-4">
          <p className="text-xs uppercase soft-text">Total Repositories</p>
          <p className="text-3xl font-extrabold mt-1">{stats.total}</p>
        </div>
        <div className="panel p-4">
          <p className="text-xs uppercase soft-text">Confluence Destinations</p>
          <p className="text-3xl font-extrabold mt-1">{stats.confluence}</p>
        </div>
        <div className="panel p-4">
          <p className="text-xs uppercase soft-text">Notion Destinations</p>
          <p className="text-3xl font-extrabold mt-1">{stats.notion}</p>
        </div>
      </section>

      <section className="panel p-4 md:p-6">
        <div className="flex flex-wrap justify-between gap-3 items-center">
          <div>
            <h3 className="text-xl font-bold">Repository Registry</h3>
            <p className="soft-text text-sm">Full CRUD + trigger controls for every repo.</p>
          </div>
          <div className="flex gap-2">
            <button className="px-3 py-2 rounded-xl text-sm font-semibold" style={{ background: "var(--bg-muted)" }} onClick={loadRepos}>Refresh</button>
            <button className="px-3 py-2 rounded-xl text-sm font-semibold text-white" style={{ background: "var(--accent)" }} onClick={() => setShowCreate((v) => !v)}>
              {showCreate ? "Close" : "Add Repository"}
            </button>
          </div>
        </div>

        {showCreate && (
          <form onSubmit={createRepo} className="mt-5 grid md:grid-cols-2 gap-4">
            <label className="block">
              <span className="text-sm soft-text">GitHub URL</span>
              <input
                type="url"
                required
                value={createForm.github_url}
                onChange={(e) => setCreateForm((v) => ({ ...v, github_url: e.target.value }))}
                className="mt-1 w-full rounded-xl border p-2.5"
                style={{ background: "var(--bg-elevated)", borderColor: "var(--border)" }}
                placeholder="https://github.com/org/repo"
              />
            </label>
            <label className="block">
              <span className="text-sm soft-text">Default Branch</span>
              <input
                value={createForm.default_branch}
                onChange={(e) => setCreateForm((v) => ({ ...v, default_branch: e.target.value }))}
                className="mt-1 w-full rounded-xl border p-2.5"
                style={{ background: "var(--bg-elevated)", borderColor: "var(--border)" }}
              />
            </label>
            <label className="block">
              <span className="text-sm soft-text">Destination Platform</span>
              <select
                value={createForm.destination_platform}
                onChange={(e) => setCreateForm((v) => ({ ...v, destination_platform: e.target.value }))}
                className="mt-1 w-full rounded-xl border p-2.5"
                style={{ background: "var(--bg-elevated)", borderColor: "var(--border)" }}
              >
                <option value="confluence">Confluence</option>
                <option value="notion">Notion</option>
              </select>
            </label>

            {createForm.destination_platform === "confluence" ? (
              <label className="block">
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
              <label className="block">
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
              <button className="px-4 py-2 rounded-xl text-sm font-semibold text-white" style={{ background: "var(--accent)" }} type="submit">
                Create Repository
              </button>
            </div>
          </form>
        )}

        <div className="mt-6 overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left soft-text border-b" style={{ borderColor: "var(--border)" }}>
                <th className="py-3 pr-3">Repository</th>
                <th className="py-3 pr-3">Branch</th>
                <th className="py-3 pr-3">Destination</th>
                <th className="py-3 pr-3">Created</th>
                <th className="py-3 text-right">Actions</th>
              </tr>
            </thead>
            <tbody>
              {!loading && repos.map((repo) => {
                const badge = destinationBadge(repo.destination_platform);
                const rowBusy = busyId === repo.id;
                const isEditing = editingId === repo.id;
                return [
                    <tr key={`repo-${repo.id}`} className="border-b align-top" style={{ borderColor: "var(--border)" }}>
                      <td className="py-4 pr-3">
                        <Link to={`/repos/${repo.id}`} className="font-semibold" style={{ color: "var(--accent)" }}>
                          {formatRepoName(repo.github_url)}
                        </Link>
                        <p className="text-xs soft-text mt-1">#{repo.id}</p>
                      </td>
                      <td className="py-4 pr-3">{repo.default_branch}</td>
                      <td className="py-4 pr-3">
                        <span className="px-2 py-1 rounded-full text-xs font-semibold" style={badge.style}>{badge.text}</span>
                      </td>
                      <td className="py-4 pr-3">{new Date(repo.created_at).toLocaleString()}</td>
                      <td className="py-4 text-right">
                        <div className="flex flex-wrap justify-end gap-2">
                          <button className="px-2.5 py-1.5 rounded-lg text-xs font-semibold" style={{ background: "var(--bg-muted)" }} onClick={() => trigger(repo.id, "manual")} disabled={rowBusy}>Run</button>
                          <button className="px-2.5 py-1.5 rounded-lg text-xs font-semibold" style={{ background: "var(--bg-muted)" }} onClick={() => trigger(repo.id, "scheduled")} disabled={rowBusy}>Queue</button>
                          <button className="px-2.5 py-1.5 rounded-lg text-xs font-semibold" style={{ background: "var(--bg-muted)" }} onClick={() => startEdit(repo)} disabled={rowBusy}>Edit</button>
                          <button className="px-2.5 py-1.5 rounded-lg text-xs font-semibold" style={{ background: "rgba(239,68,68,0.14)", color: "var(--danger)" }} onClick={() => deleteRepo(repo)} disabled={rowBusy}>Delete</button>
                        </div>
                      </td>
                    </tr>,
                    isEditing && editForm ? (
                      <tr key={`repo-edit-${repo.id}`} className="border-b" style={{ borderColor: "var(--border)" }}>
                        <td className="py-4" colSpan={5}>
                          <form onSubmit={saveEdit} className="panel p-4 mt-1 grid md:grid-cols-2 gap-3">
                            <label>
                              <span className="text-xs soft-text">GitHub URL</span>
                              <input
                                type="url"
                                value={editForm.github_url}
                                onChange={(e) => setEditForm((v) => ({ ...v, github_url: e.target.value }))}
                                className="mt-1 w-full rounded-xl border p-2"
                                style={{ background: "var(--bg-elevated)", borderColor: "var(--border)" }}
                              />
                            </label>
                            <label>
                              <span className="text-xs soft-text">Default Branch</span>
                              <input
                                value={editForm.default_branch}
                                onChange={(e) => setEditForm((v) => ({ ...v, default_branch: e.target.value }))}
                                className="mt-1 w-full rounded-xl border p-2"
                                style={{ background: "var(--bg-elevated)", borderColor: "var(--border)" }}
                              />
                            </label>
                            <label>
                              <span className="text-xs soft-text">Destination Platform</span>
                              <select
                                value={editForm.destination_platform}
                                onChange={(e) => setEditForm((v) => ({ ...v, destination_platform: e.target.value }))}
                                className="mt-1 w-full rounded-xl border p-2"
                                style={{ background: "var(--bg-elevated)", borderColor: "var(--border)" }}
                              >
                                <option value="confluence">Confluence</option>
                                <option value="notion">Notion</option>
                              </select>
                            </label>
                            {editForm.destination_platform === "confluence" ? (
                              <label>
                                <span className="text-xs soft-text">Confluence Space Key</span>
                                <input
                                  value={editSpaceKey}
                                  onChange={(e) => setEditSpaceKey(e.target.value)}
                                  className="mt-1 w-full rounded-xl border p-2"
                                  style={{ background: "var(--bg-elevated)", borderColor: "var(--border)" }}
                                />
                              </label>
                            ) : (
                              <label>
                                <span className="text-xs soft-text">Notion Database ID</span>
                                <input
                                  value={editDatabaseId}
                                  onChange={(e) => setEditDatabaseId(e.target.value)}
                                  className="mt-1 w-full rounded-xl border p-2"
                                  style={{ background: "var(--bg-elevated)", borderColor: "var(--border)" }}
                                />
                              </label>
                            )}
                            <div className="md:col-span-2 flex justify-end gap-2">
                              <button type="button" onClick={() => { setEditingId(null); setEditForm(null); }} className="px-3 py-2 rounded-xl text-xs font-semibold" style={{ background: "var(--bg-muted)" }}>Cancel</button>
                              <button type="submit" className="px-3 py-2 rounded-xl text-xs font-semibold text-white" style={{ background: "var(--accent)" }}>Save Changes</button>
                            </div>
                          </form>
                        </td>
                      </tr>
                    ) : null,
                  ];
              })}

              {!loading && repos.length === 0 && (
                <tr>
                  <td colSpan={5} className="py-10 text-center soft-text">No repositories configured yet.</td>
                </tr>
              )}

              {loading && (
                <tr>
                  <td colSpan={5} className="py-10 text-center soft-text">Loading repositories...</td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}
