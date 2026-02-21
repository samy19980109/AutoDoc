import { useState } from "react";

export default function SettingsPage() {
  const [apiKey, setApiKey] = useState(localStorage.getItem("api_key") || "");
  const [saved, setSaved] = useState(false);

  function handleSave(e) {
    e.preventDefault();
    localStorage.setItem("api_key", apiKey);
    setSaved(true);
    setTimeout(() => setSaved(false), 2000);
  }

  return (
    <div>
      <h2 className="text-2xl font-bold text-gray-900 mb-6">Settings</h2>

      <div className="bg-white shadow rounded-lg p-6 max-w-2xl">
        <h3 className="text-lg font-medium text-gray-900 mb-4">API Configuration</h3>
        <form onSubmit={handleSave} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700">API Key</label>
            <input
              type="password"
              value={apiKey}
              onChange={(e) => setApiKey(e.target.value)}
              placeholder="Enter your API key"
              className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 border p-2"
            />
            <p className="mt-1 text-sm text-gray-500">Used to authenticate requests to the API Gateway.</p>
          </div>
          <div className="flex items-center gap-3">
            <button
              type="submit"
              className="bg-indigo-600 text-white px-4 py-2 rounded-md hover:bg-indigo-700 text-sm font-medium"
            >
              Save
            </button>
            {saved && <span className="text-sm text-green-600">Saved!</span>}
          </div>
        </form>
      </div>
    </div>
  );
}
