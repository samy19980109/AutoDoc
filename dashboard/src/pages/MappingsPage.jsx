import { useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { api } from "../api/client";

export default function MappingsPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const [mappings, setMappings] = useState([]);
  const [loading, setLoading] = useState(true);
  const [banner, setBanner] = useState("");

  const [repoId, setRepoId] = useState(searchParams.get("repo_id") || "");
  const [selectedMapping, setSelectedMapping] = useState(null);

  useEffect(() => {
    loadMappings();
  }, []);

  async function loadMappings() {
    setLoading(true);
    try {
      const params = { limit: 300 };
      if (repoId.trim()) params.repo_id = repoId.trim();

      const next = new URLSearchParams();
      if (params.repo_id) next.set("repo_id", params.repo_id);
      setSearchParams(next);

      const data = await api.listMappings(params);
      setMappings(data);
      setBanner("");
    } catch (err) {
      setBanner(`Failed to load mappings: ${err.message}`);
    } finally {
      setLoading(false);
    }
  }

  async function openMapping(mappingId) {
    try {
      const data = await api.getMapping(mappingId);
      setSelectedMapping(data);
    } catch (err) {
      setBanner(`Failed to fetch mapping: ${err.message}`);
    }
  }

  async function deleteMapping(mappingId) {
    const ok = window.confirm("Delete this mapping?");
    if (!ok) return;

    try {
      await api.deleteMapping(mappingId);
      setBanner("Mapping deleted.");
      if (selectedMapping?.id === mappingId) setSelectedMapping(null);
      await loadMappings();
    } catch (err) {
      setBanner(`Delete failed: ${err.message}`);
    }
  }

  function clearFilters() {
    setRepoId("");
    setSearchParams(new URLSearchParams());
    setTimeout(() => loadMappings(), 0);
  }

  return (
    <div className="space-y-6 fade-in">
      {banner && <div className="panel p-3 text-sm">{banner}</div>}

      <section className="panel p-5">
        <div className="flex flex-wrap items-end gap-3">
          <label className="block">
            <span className="text-sm soft-text">Filter by Repository ID</span>
            <input
              value={repoId}
              onChange={(e) => setRepoId(e.target.value)}
              placeholder="e.g. 4"
              className="mt-1 rounded-xl border p-2.5"
              style={{ background: "var(--bg-elevated)", borderColor: "var(--border)" }}
            />
          </label>
          <button onClick={loadMappings} className="px-4 py-2.5 rounded-xl text-sm font-semibold text-white" style={{ background: "var(--accent)" }}>
            Apply Filter
          </button>
          <button onClick={clearFilters} className="px-4 py-2.5 rounded-xl text-sm font-semibold" style={{ background: "var(--bg-muted)" }}>
            Clear
          </button>
        </div>
      </section>

      <section className="panel p-5 overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b soft-text" style={{ borderColor: "var(--border)" }}>
              <th className="text-left py-2 pr-3">ID</th>
              <th className="text-left py-2 pr-3">Repo</th>
              <th className="text-left py-2 pr-3">Code Path</th>
              <th className="text-left py-2 pr-3">Doc Type</th>
              <th className="text-left py-2 pr-3">Destination Page</th>
              <th className="text-left py-2 pr-3">Last Synced</th>
              <th className="text-right py-2">Actions</th>
            </tr>
          </thead>
          <tbody>
            {!loading && mappings.map((m) => (
              <tr key={m.id} className="border-b" style={{ borderColor: "var(--border)" }}>
                <td className="py-3 pr-3 font-semibold">#{m.id}</td>
                <td className="py-3 pr-3"><Link to={`/repos/${m.repo_id}`} style={{ color: "var(--accent)" }}>Repo #{m.repo_id}</Link></td>
                <td className="py-3 pr-3 font-mono">{m.code_path}</td>
                <td className="py-3 pr-3">{m.doc_type}</td>
                <td className="py-3 pr-3 font-mono">{m.destination_page_id || "-"}</td>
                <td className="py-3 pr-3">{m.last_synced_at ? new Date(m.last_synced_at).toLocaleString() : "Never"}</td>
                <td className="py-3 text-right">
                  <div className="flex justify-end gap-2">
                    <button onClick={() => openMapping(m.id)} className="px-2.5 py-1.5 rounded-lg text-xs font-semibold" style={{ background: "var(--bg-muted)" }}>Inspect</button>
                    <button onClick={() => deleteMapping(m.id)} className="px-2.5 py-1.5 rounded-lg text-xs font-semibold" style={{ background: "rgba(239,68,68,.14)", color: "var(--danger)" }}>Delete</button>
                  </div>
                </td>
              </tr>
            ))}

            {loading && <tr><td colSpan={7} className="py-8 text-center soft-text">Loading mappings...</td></tr>}
            {!loading && mappings.length === 0 && <tr><td colSpan={7} className="py-8 text-center soft-text">No mappings found.</td></tr>}
          </tbody>
        </table>
      </section>

      {selectedMapping && (
        <section className="panel p-5">
          <div className="flex items-center justify-between">
            <h4 className="text-lg font-bold">Mapping #{selectedMapping.id}</h4>
            <button onClick={() => setSelectedMapping(null)} className="px-3 py-2 rounded-lg text-xs font-semibold" style={{ background: "var(--bg-muted)" }}>Close</button>
          </div>
          <pre className="mt-3 rounded-xl p-4 overflow-auto text-xs" style={{ background: "var(--bg-muted)", border: "1px solid var(--border)" }}>
{JSON.stringify(selectedMapping, null, 2)}
          </pre>
        </section>
      )}
    </div>
  );
}
