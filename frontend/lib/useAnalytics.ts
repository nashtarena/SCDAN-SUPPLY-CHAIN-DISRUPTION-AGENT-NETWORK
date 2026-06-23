"use client";

import { useEffect, useState } from "react";
import { api } from "./api";
import type {
  ChainAnalytics,
  ExecutiveSummary,
  GlobalAnalytics,
} from "./types";

// ── global analytics ───────────────────────────────────────────────────────

export function useGlobalAnalytics() {
  const [data, setData] = useState<GlobalAnalytics | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api
      .get<GlobalAnalytics>("/api/analytics/summary")
      .then((r) => setData(r.data))
      .catch(() => setError("Could not load analytics."))
      .finally(() => setLoading(false));
  }, []);

  return { data, loading, error };
}

export function useGlobalSummary(refresh = false) {
  const [data, setData] = useState<ExecutiveSummary | null>(null);
  const [loading, setLoading] = useState(true);

  async function load(forceRefresh = false) {
    setLoading(true);
    try {
      const r = await api.get<ExecutiveSummary>(
        `/api/analytics/summary/executive${forceRefresh ? "?refresh=true" : ""}`
      );
      setData(r.data);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { load(refresh); }, []);

  return { data, loading, refresh: () => load(true) };
}

// ── per-chain analytics ────────────────────────────────────────────────────

export function useChainAnalytics(supplyChainId: string) {
  const [data, setData] = useState<ChainAnalytics | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!supplyChainId) return;
    api
      .get<ChainAnalytics>(`/api/analytics/${supplyChainId}`)
      .then((r) => setData(r.data))
      .catch(() => setError("Could not load chain analytics."))
      .finally(() => setLoading(false));
  }, [supplyChainId]);

  return { data, loading, error };
}

export function useChainSummary(supplyChainId: string) {
  const [data, setData] = useState<ExecutiveSummary | null>(null);
  const [loading, setLoading] = useState(true);

  async function load(forceRefresh = false) {
    if (!supplyChainId) return;
    setLoading(true);
    try {
      const r = await api.get<ExecutiveSummary>(
        `/api/analytics/${supplyChainId}/executive${forceRefresh ? "?refresh=true" : ""}`
      );
      setData(r.data);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { load(); }, [supplyChainId]);

  return { data, loading, refresh: () => load(true) };
}