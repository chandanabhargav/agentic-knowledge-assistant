"use client";
import { useEffect, useState } from "react";
import Link from "next/link";

type Upload = {
  id: string;
  original_filename: string;
  stored_path: string;
  size_bytes?: number | null;
  chunk_count: number;
  ingested: boolean;
  created_at: string;
  error?: string | null;
  file_type?: string;
};
const API = process.env.NEXT_PUBLIC_API_BASE;
const TOKEN = process.env.NEXT_PUBLIC_BEARER_TOKEN || '';

export default function UploadsPage() {
  const [rows, setRows] = useState<Upload[]>([]);
  const [loading, setLoading] = useState(true);

  async function refresh() {
    setLoading(true);
    const res = await fetch(`${API}/uploads`, { 
        headers: {
          'Authorization': `Bearer ${TOKEN}`,
        },
        cache: "no-store" 
    });
    const data = await res.json();
    setRows(data);
    setLoading(false);
  }

  useEffect(() => { refresh(); }, []);

  async function onDelete(id: string) {
    if (!confirm("Delete this file and its vectors? This cannot be undone.")) return;
    const res = await fetch(`${API}/uploads/${id}`, { 
        method: "DELETE",
        headers: {
          'Authorization': `Bearer ${TOKEN}`,
        }, 
    });
    if (res.status === 204) {
      setRows(prev => prev.filter(r => r.id !== id));
    } else {
      alert("Delete failed");
    }
  }

  return (
    <div className="p-6">
      <Link href="/" className="inline-flex items-center mb-4 text-blue-600 hover:underline">
        ← Back to Home
      </Link>
      <h1 className="text-xl font-semibold mb-4">Uploaded Documents</h1>
      {loading ? <div>Loading…</div> : (
        <div className="overflow-x-auto">
          <table className="min-w-full text-sm">
            <thead>
              <tr className="text-left border-b">
                <th className="py-2 pr-4">Filename</th>
                {/* <th className="py-2 pr-4">Size</th> */}
                <th className="py-2 pr-4">Chunks</th>
                <th className="py-2 pr-4">Ingested</th>
                <th className="py-2 pr-4">Uploaded</th>
                <th className="py-2 pr-4">Actions</th>
              </tr>
            </thead>
            <tbody>
              {rows.map(r => (
                <tr key={r.id} className="border-b">
                  <td className="py-2 pr-4">{r.original_filename}</td>
                  {/* <td className="py-2 pr-4">{r.size_bytes ? (r.size_bytes/1024/1024).toFixed(2)+" MB" : "-"}</td> */}
                  <td className="py-2 pr-4">{r.chunk_count}</td>
                  <td className="py-2 pr-4">{r.ingested ? "✓" : (r.error ? "Error" : "…")}</td>
                  <td className="py-2 pr-4">{new Date(r.created_at).toLocaleString()}</td>
                  <td className="py-2 pr-4">
                    <button className="px-3 py-1 rounded bg-red-600 text-white" onClick={() => onDelete(r.id)}>Delete</button>
                  </td>
                </tr>
              ))}
              {rows.length === 0 && <tr><td className="py-6 text-gray-500" colSpan={6}>No uploads yet.</td></tr>}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
