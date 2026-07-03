"use client";

import { useCallback, useEffect, useState } from "react";
import { api, DriveFolder, DriveStatus } from "@/lib/api";
import { timeAgo } from "@/lib/timeAgo";

const AUTO_SYNC_INTERVAL_MS = 30_000;

export function DriveConnectCard({ onSynced }: { onSynced: () => void }) {
  const [status, setStatus] = useState<DriveStatus | null>(null);
  const [folders, setFolders] = useState<DriveFolder[] | null>(null);
  const [syncing, setSyncing] = useState(false);
  const [syncMessage, setSyncMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [, forceTick] = useState(0);

  const refreshStatus = useCallback(async () => {
    try {
      const s = await api.driveStatus();
      setStatus(s);
      setError(null);
    } catch {
      setError("Could not reach the backend API. Is it running on :8000?");
    }
  }, []);

  useEffect(() => {
    refreshStatus();
    if (typeof window !== "undefined" && window.location.search.includes("drive_connected=1")) {
      window.history.replaceState({}, "", window.location.pathname);
    }
  }, [refreshStatus]);

  // re-render every 15s so "Last synced: X min ago" stays fresh without re-fetching
  useEffect(() => {
    const id = setInterval(() => forceTick((t) => t + 1), 15_000);
    return () => clearInterval(id);
  }, []);

  const runSync = useCallback(async () => {
    setSyncing(true);
    setSyncMessage(null);
    try {
      const result = await api.driveSync();
      setSyncMessage(
        result.new_files === 0
          ? "No new or changed files since last sync."
          : `Synced ${result.new_files} file(s): ${result.processed} processed, ${result.failed} failed.`
      );
      await refreshStatus();
      onSynced();
    } catch (e) {
      setSyncMessage(e instanceof Error ? e.message : "Sync failed.");
    } finally {
      setSyncing(false);
    }
  }, [onSynced, refreshStatus]);

  // light polling once a folder is selected — no webhooks, just "poll on load + every 30s"
  useEffect(() => {
    if (!status?.connected || !status.folder_id) return;
    const id = setInterval(runSync, AUTO_SYNC_INTERVAL_MS);
    return () => clearInterval(id);
  }, [status?.connected, status?.folder_id, runSync]);

  const connect = async () => {
    try {
      const { url } = await api.driveAuthUrl();
      window.location.href = url;
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not start Google OAuth flow.");
    }
  };

  const loadFolders = async () => {
    try {
      const f = await api.driveFolders();
      setFolders(f);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not list Drive folders.");
    }
  };

  const selectFolder = async (folder: DriveFolder) => {
    const s = await api.driveSelectFolder(folder.id, folder.name);
    setStatus(s);
    setFolders(null);
    runSync();
  };

  if (!status) {
    return <Card>{error ?? "Loading Drive connection status…"}</Card>;
  }

  return (
    <Card>
      <div className="flex items-center justify-between">
        <h2 className="text-sm font-semibold text-neutral-200">Google Drive</h2>
        <span
          className={`text-xs rounded-full px-2 py-0.5 ${
            status.connected ? "bg-emerald-900/40 text-emerald-300" : "bg-neutral-800 text-neutral-400"
          }`}
        >
          {status.connected ? "Connected" : "Not connected"}
        </span>
      </div>

      {error && <p className="mt-2 text-xs text-red-400">{error}</p>}

      {!status.connected && (
        <div className="mt-3">
          <p className="text-sm text-neutral-400 mb-3">
            Connect a Google account to watch a folder for fund factsheets, statements, and performance reports.
          </p>
          <button onClick={connect} className="btn-primary">
            Connect Google Drive
          </button>
        </div>
      )}

      {status.connected && !status.folder_id && (
        <div className="mt-3">
          {folders === null ? (
            <button onClick={loadFolders} className="btn-secondary">
              Choose a folder to watch
            </button>
          ) : (
            <ul className="mt-1 max-h-48 overflow-y-auto divide-y divide-neutral-800 border border-neutral-800 rounded-lg">
              {folders.length === 0 && <li className="px-3 py-2 text-sm text-neutral-500">No folders found.</li>}
              {folders.map((f) => (
                <li key={f.id}>
                  <button
                    onClick={() => selectFolder(f)}
                    className="w-full text-left px-3 py-2 text-sm hover:bg-neutral-800/60 transition"
                  >
                    {f.name}
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>
      )}

      {status.connected && status.folder_id && (
        <div className="mt-3 space-y-2">
          <p className="text-sm text-neutral-300">
            Watching folder: <span className="font-medium text-neutral-100">{status.folder_name}</span>
          </p>
          <div className="flex items-center gap-3">
            <button onClick={runSync} disabled={syncing} className="btn-primary">
              {syncing ? "Syncing…" : "Sync Now"}
            </button>
            <span className="text-xs text-neutral-500">Last synced: {timeAgo(status.last_synced_at)}</span>
          </div>
          {syncMessage && <p className="text-xs text-neutral-400">{syncMessage}</p>}
        </div>
      )}
    </Card>
  );
}

function Card({ children }: { children: React.ReactNode }) {
  return <div className="rounded-xl border border-neutral-800 bg-neutral-900/60 p-4">{children}</div>;
}
