/**
 * HistoryContext — persists search history in localStorage (7-day expiry).
 * Also owns the sidebar open/close state so any component can toggle it.
 *
 * Full search results are cached in a separate localStorage key
 * (shopbuddy_result_cache) so that clicking a history entry restores
 * results instantly without re-running the search pipeline.
 */
import {
  createContext,
  useContext,
  useState,
  useCallback,
  useMemo,
  useEffect,
} from "react";

const STORAGE_KEY = "shopbuddy_search_history";
const CACHE_KEY = "shopbuddy_result_cache";
const EXPIRY_MS = 7 * 24 * 60 * 60 * 1000; // 7 days
const MAX_ENTRIES = 50;
const MAX_CACHE_BYTES = 4 * 1024 * 1024; // 4 MB safety limit

// ---------------------------------------------------------------------------
// localStorage helpers (history metadata)
// ---------------------------------------------------------------------------
function loadFromStorage() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw);
    if (!Array.isArray(parsed)) return [];
    const now = Date.now();
    return parsed.filter((e) => now - e.timestamp < EXPIRY_MS);
  } catch {
    return [];
  }
}

// ---------------------------------------------------------------------------
// Result-cache helpers (lazy read/write — never held in React state)
// ---------------------------------------------------------------------------
function readCache() {
  try {
    const raw = localStorage.getItem(CACHE_KEY);
    return raw ? JSON.parse(raw) : {};
  } catch {
    return {};
  }
}

function writeCache(cache) {
  try {
    let serialized = JSON.stringify(cache);
    // If over budget, evict oldest entries until under 3 MB
    if (serialized.length > MAX_CACHE_BYTES) {
      const sorted = Object.entries(cache).sort(
        (a, b) => a[1].timestamp - b[1].timestamp,
      );
      while (serialized.length > 3 * 1024 * 1024 && sorted.length > 0) {
        const [oldId] = sorted.shift();
        delete cache[oldId];
        serialized = JSON.stringify(cache);
      }
    }
    localStorage.setItem(CACHE_KEY, serialized);
  } catch {
    // localStorage full — silently skip
  }
}

function removeCacheEntry(id) {
  const cache = readCache();
  if (id in cache) {
    delete cache[id];
    writeCache(cache);
  }
}

// ---------------------------------------------------------------------------
// Context
// ---------------------------------------------------------------------------
const HistoryContext = createContext(null);

export function HistoryProvider({ children }) {
  const [history, setHistory] = useState(loadFromStorage);
  const [sidebarOpen, setSidebarOpen] = useState(false);

  // Sync history metadata to localStorage & prune orphaned cache entries
  useEffect(() => {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(history));

    // Prune cache entries whose IDs no longer appear in history
    const validIds = new Set(history.map((e) => e.id));
    const cache = readCache();
    let changed = false;
    for (const key of Object.keys(cache)) {
      if (!validIds.has(key)) {
        delete cache[key];
        changed = true;
      }
    }
    if (changed) writeCache(cache);
  }, [history]);

  // Add a history entry and return its generated ID so the caller can
  // write the result cache under the same key.
  const addToHistory = useCallback((entry) => {
    const id = crypto.randomUUID();
    setHistory((prev) => {
      // Remove old cache for deduplicated entry
      const dup = prev.find(
        (e) => e.query.toLowerCase() === entry.query.toLowerCase(),
      );
      if (dup) removeCacheEntry(dup.id);

      const deduped = prev.filter(
        (e) => e.query.toLowerCase() !== entry.query.toLowerCase(),
      );
      return [{ ...entry, id, timestamp: Date.now() }, ...deduped].slice(
        0,
        MAX_ENTRIES,
      );
    });
    return id;
  }, []);

  // Cache the full SSE "complete" payload for a history entry
  const cacheResults = useCallback((id, data) => {
    const cache = readCache();
    cache[id] = { data, timestamp: Date.now() };
    writeCache(cache);
  }, []);

  // Retrieve cached results (or null on miss)
  const getCachedResults = useCallback((id) => {
    const cache = readCache();
    return cache[id] ?? null;
  }, []);

  const deleteEntry = useCallback((id) => {
    removeCacheEntry(id);
    setHistory((prev) => prev.filter((e) => e.id !== id));
  }, []);

  const clearHistory = useCallback(() => {
    setHistory([]);
    try {
      localStorage.removeItem(CACHE_KEY);
    } catch {
      // ignore
    }
  }, []);

  const value = useMemo(
    () => ({
      history,
      sidebarOpen,
      setSidebarOpen,
      addToHistory,
      deleteEntry,
      clearHistory,
      cacheResults,
      getCachedResults,
    }),
    [
      history,
      sidebarOpen,
      addToHistory,
      deleteEntry,
      clearHistory,
      cacheResults,
      getCachedResults,
    ],
  );

  return (
    <HistoryContext.Provider value={value}>{children}</HistoryContext.Provider>
  );
}

export function useHistory() {
  const ctx = useContext(HistoryContext);
  if (!ctx) throw new Error("useHistory must be used inside HistoryProvider");
  return ctx;
}
