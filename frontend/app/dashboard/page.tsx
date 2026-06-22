"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { api } from "@/lib/api";
import { useRequireAuth } from "@/lib/useRequireAuth";
import type { SupplyChain } from "@/lib/types";
import Navbar from "@/components/Navbar";

export default function DashboardPage() {
  const ready = useRequireAuth();

  const [supplyChains, setSupplyChains] = useState<SupplyChain[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [showCreate, setShowCreate] = useState(false);
  const [newName, setNewName] = useState("");
  const [newDescription, setNewDescription] = useState("");
  const [creating, setCreating] = useState(false);

  useEffect(() => {
    if (!ready) return;
    fetchSupplyChains();
  }, [ready]);

  async function fetchSupplyChains() {
    setLoading(true);
    setError(null);
    try {
      const res = await api.get<SupplyChain[]>("/api/supply-chains");
      setSupplyChains(res.data);
    } catch {
      setError("Could not load supply chains.");
    } finally {
      setLoading(false);
    }
  }

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault();
    setCreating(true);
    try {
      await api.post("/api/supply-chains", {
        name: newName,
        description: newDescription || null,
      });
      setNewName("");
      setNewDescription("");
      setShowCreate(false);
      await fetchSupplyChains();
    } catch {
      setError("Could not create supply chain.");
    } finally {
      setCreating(false);
    }
  }

  if (!ready) return null;

  return (
    <main className="min-h-screen bg-background">
      <Navbar />

      <div className="mx-auto max-w-4xl px-6 py-10">
        <div className="mb-6 flex items-center justify-between">
          <h1 className="text-lg font-semibold text-white">Your supply chains</h1>
          <button
            onClick={() => setShowCreate((v) => !v)}
            className="rounded-md bg-primary px-4 py-2 text-sm font-medium text-white hover:opacity-90"
          >
            {showCreate ? "Cancel" : "+ New supply chain"}
          </button>
        </div>

        {showCreate && (
          <form
            onSubmit={handleCreate}
            className="mb-8 space-y-3 rounded-lg border border-border bg-surface p-5"
          >
            <div>
              <label className="mb-1 block text-sm text-gray-300">Name</label>
              <input
                required
                value={newName}
                onChange={(e) => setNewName(e.target.value)}
                className="w-full rounded-md border border-border bg-background px-3 py-2 text-sm text-white outline-none focus:border-primary"
                placeholder="e.g. Global Electronics Network"
              />
            </div>
            <div>
              <label className="mb-1 block text-sm text-gray-300">Description (optional)</label>
              <textarea
                value={newDescription}
                onChange={(e) => setNewDescription(e.target.value)}
                className="w-full rounded-md border border-border bg-background px-3 py-2 text-sm text-white outline-none focus:border-primary"
                rows={2}
              />
            </div>
            <button
              type="submit"
              disabled={creating}
              className="rounded-md bg-primary px-4 py-2 text-sm font-medium text-white hover:opacity-90 disabled:opacity-50"
            >
              {creating ? "Creating..." : "Create"}
            </button>
          </form>
        )}

        {error && <p className="mb-4 text-sm text-critical">{error}</p>}

        {loading ? (
          <p className="text-sm text-gray-400">Loading...</p>
        ) : supplyChains.length === 0 ? (
          <p className="text-sm text-gray-400">
            No supply chains yet. Create one to get started.
          </p>
        ) : (
          <div className="grid gap-3">
            {supplyChains.map((sc) => (
              <Link
                key={sc.id}
                href={`/supply-chains/${sc.id}`}
                className="rounded-lg border border-border bg-surface p-4 transition hover:border-primary"
              >
                <h2 className="font-medium text-white">{sc.name}</h2>
                {sc.description && (
                  <p className="mt-1 text-sm text-gray-400">{sc.description}</p>
                )}
              </Link>
            ))}
          </div>
        )}
      </div>
    </main>
  );
}
