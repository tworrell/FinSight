"use client";

import { useRef, useState } from "react";
import { api } from "@/lib/api";

export function UploadCard({ onUploaded }: { onUploaded: () => void }) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [uploading, setUploading] = useState(false);
  const [message, setMessage] = useState<string | null>(null);

  const handleFiles = async (files: FileList | null) => {
    if (!files || files.length === 0) return;
    setUploading(true);
    setMessage(null);
    try {
      const docs = await api.uploadDocuments(Array.from(files));
      const failed = docs.filter((d) => d.status === "error").length;
      setMessage(`Uploaded ${docs.length} file(s): ${docs.length - failed} processed, ${failed} failed.`);
      onUploaded();
    } catch (e) {
      setMessage(e instanceof Error ? e.message : "Upload failed.");
    } finally {
      setUploading(false);
      if (inputRef.current) inputRef.current.value = "";
    }
  };

  return (
    <div className="rounded-xl border border-neutral-800 bg-neutral-900/60 p-4">
      <h2 className="text-sm font-semibold text-neutral-200">Manual upload</h2>
      <p className="mt-1 text-sm text-neutral-400">
        Skip Drive entirely and drop files straight into the same pipeline — handy for a quick local test.
      </p>
      <div className="mt-3">
        <input
          ref={inputRef}
          type="file"
          multiple
          accept=".pdf,.csv,.html,.htm"
          onChange={(e) => handleFiles(e.target.files)}
          disabled={uploading}
          className="text-sm text-neutral-300 file:mr-3 file:rounded-lg file:border-0 file:bg-neutral-800 file:px-3 file:py-1.5 file:text-sm file:text-neutral-200 hover:file:bg-neutral-700"
        />
        {uploading && <p className="mt-2 text-xs text-neutral-500">Processing — extracting structured data…</p>}
        {message && <p className="mt-2 text-xs text-neutral-400">{message}</p>}
      </div>
    </div>
  );
}
