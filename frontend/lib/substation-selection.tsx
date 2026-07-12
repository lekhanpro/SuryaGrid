"use client";
// Shared substation selection.
//
// One substation_id is the active context for the whole app. The catalog is the
// real parquet-backed /substations/catalog (344 OSM rows). Selection persists in
// localStorage so it survives navigation and reloads. No fabrication: while the
// catalog is loading the selection is empty and consumers must disable themselves.

import {
  createContext,
  useContext,
  useEffect,
  useState,
  type ReactNode,
} from "react";
import { getSubstationCatalog } from "@/lib/api";

export type CatalogRow = {
  substation_id: string;
  display_label: string;
  voltage_kv: number | null;
  latitude: number | null;
  longitude: number | null;
  reliability_score: number | null;
};

const STORAGE_KEY = "suryagrid.selected_substation_id";

type SelectionState = {
  catalog: CatalogRow[];
  selectedId: string;
  setSelectedId: (id: string) => void;
  loading: boolean;
  error: string;
};

const Ctx = createContext<SelectionState>({
  catalog: [],
  selectedId: "",
  setSelectedId: () => {},
  loading: true,
  error: "",
});

export function SubstationSelectionProvider({ children }: { children: ReactNode }) {
  const [catalog, setCatalog] = useState<CatalogRow[]>([]);
  const [selectedId, setSelectedIdState] = useState<string>("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const c = await getSubstationCatalog(1000);
        if (cancelled) return;
        const rows: CatalogRow[] = c.substations || [];
        setCatalog(rows);
        const saved =
          typeof window !== "undefined" ? window.localStorage.getItem(STORAGE_KEY) : null;
        if (saved && rows.some((r) => r.substation_id === saved)) {
          setSelectedIdState(saved);
        } else if (rows.length) {
          setSelectedIdState(rows[0].substation_id);
        }
      } catch (e: any) {
        if (!cancelled) setError(e?.message || "Failed to load substation catalog");
      }
      if (!cancelled) setLoading(false);
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  const setSelectedId = (id: string) => {
    setSelectedIdState(id);
    try {
      window.localStorage.setItem(STORAGE_KEY, id);
    } catch {
      // storage unavailable (private mode) — selection still works in-memory
    }
  };

  return (
    <Ctx.Provider value={{ catalog, selectedId, setSelectedId, loading, error }}>
      {children}
    </Ctx.Provider>
  );
}

export function useSubstationSelection() {
  return useContext(Ctx);
}
