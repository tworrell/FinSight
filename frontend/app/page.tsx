"use client";

import { useCallback, useState } from "react";
import { DriveConnectCard } from "@/components/DriveConnectCard";
import { UploadCard } from "@/components/UploadCard";
import { DocumentsTable } from "@/components/DocumentsTable";
import { QueryPanel } from "@/components/QueryPanel";

export default function Home() {
  const [refreshKey, setRefreshKey] = useState(0);
  const bump = useCallback(() => setRefreshKey((k) => k + 1), []);

  return (
    <main className="mx-auto max-w-6xl w-full px-6 py-8 flex-1">
      <header className="mb-6">
        <h1 className="text-lg font-semibold text-neutral-100">Document Intelligence</h1>
        <p className="text-sm text-neutral-500">
          Connect Drive, sync fund documents, and ask questions across everything that&apos;s been ingested.
        </p>
      </header>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 mb-6">
        <DriveConnectCard onSynced={bump} />
        <UploadCard onUploaded={bump} />
      </div>

      <div className="mb-4">
        <DocumentsTable refreshKey={refreshKey} />
      </div>

      <QueryPanel />
    </main>
  );
}
