import { useState, useCallback, useRef, useEffect } from "react";
import {
  createSearchJob,
  getSearchResult,
  subscribeToJobEvents,
  type SearchParams,
  type ProgressInfo,
  type SearchResult,
  cancelJob,
} from "../api/client";
import SearchForm from "../components/SearchForm";
import ProgressPanel from "../components/ProgressPanel";
import ItineraryList from "../components/ItineraryList";
import RecentSearches from "../components/RecentSearches";
import { useCompare } from "../context/CompareContext";

const RECENT_KEY = "ryanair-recent-searches";
const MAX_RECENT = 3;

function loadRecent(): SearchParams[] {
  try {
    const raw = localStorage.getItem(RECENT_KEY);
    if (!raw) return [];
    const arr = JSON.parse(raw) as SearchParams[];
    return Array.isArray(arr) ? arr.slice(0, MAX_RECENT) : [];
  } catch {
    return [];
  }
}

function saveRecent(params: SearchParams): void {
  const existing = loadRecent();
  const key = `${params.origin}-${params.destination}-${params.start}-${params.end}`;
  const filtered = existing.filter(
    (p) => `${p.origin}-${p.destination}-${p.start}-${p.end}` !== key,
  );
  const updated = [params, ...filtered].slice(0, MAX_RECENT);
  localStorage.setItem(RECENT_KEY, JSON.stringify(updated));
}

type PageState = "idle" | "searching" | "results" | "error";

export default function SearchPage() {
  const { items: compareItems } = useCompare();
  const [state, setState] = useState<PageState>("idle");
  const [progress, setProgress] = useState<ProgressInfo | null>(null);
  const [result, setResult] = useState<SearchResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [jobId, setJobId] = useState<string | null>(null);
  const [recentSearches, setRecentSearches] = useState<SearchParams[]>(loadRecent);
  const [prefill, setPrefill] = useState<SearchParams | null>(null);
  const cleanupRef = useRef<(() => void) | null>(null);

  useEffect(() => {
    return () => cleanupRef.current?.();
  }, []);

  const handleSearch = useCallback(async (params: SearchParams) => {
    cleanupRef.current?.();
    setState("searching");
    setProgress(null);
    setResult(null);
    setError(null);

    saveRecent(params);
    setRecentSearches(loadRecent());

    try {
      const { job_id } = await createSearchJob(params);
      setJobId(job_id);

      cleanupRef.current = subscribeToJobEvents(job_id, {
        onProgress(p) {
          setProgress(p);
        },
        async onCompleted(id) {
          try {
            const res = await getSearchResult(id);
            setResult(res);
            setState("results");
          } catch (err) {
            setError(
              err instanceof Error ? err.message : "Failed to fetch results",
            );
            setState("error");
          }
        },
        onFailed(_id, errMsg) {
          setError(errMsg);
          setState("error");
        },
        onError() {
          // SSE disconnected, fallback polling started automatically
        },
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to start search");
      setState("error");
    }
  }, []);

  const handleCancel = useCallback(async () => {
    cleanupRef.current?.();
    cleanupRef.current = null;
    if (jobId) {
      try {
        await cancelJob(jobId);
      } catch {
        // best effort
      }
    }
    setState("idle");
    setJobId(null);
  }, [jobId]);

  const handleReset = useCallback(() => {
    setState("idle");
    setResult(null);
    setError(null);
    setJobId(null);
    setPrefill(null);
  }, []);

  const handleSelectRecent = useCallback((params: SearchParams) => {
    setPrefill({ ...params });
  }, []);

  return (
    <div className="page">
      <header className="page-header">
        <div className="page-header-inner">
          <h1>Ryanair Flight Search</h1>
          <p>Find connecting flights at the best prices</p>
        </div>
      </header>

      <main className="page-main">
        {state === "idle" && (
          <>
            <SearchForm onSearch={handleSearch} initialParams={prefill} />
            {recentSearches.length > 0 && (
              <RecentSearches
                searches={recentSearches}
                onSelect={handleSelectRecent}
              />
            )}
          </>
        )}

        {state === "searching" && (
          <ProgressPanel progress={progress} onCancel={handleCancel} />
        )}

        {state === "results" && result && (
          <>
            <button className="btn btn-secondary" onClick={handleReset}>
              New Search
            </button>
            <ItineraryList result={result} />
          </>
        )}

        {state === "error" && (
          <div className="error-panel">
            <h2>Something went wrong</h2>
            <p className="error-message">{error}</p>
            <button className="btn btn-primary" onClick={handleReset}>
              Try Again
            </button>
          </div>
        )}
      </main>

      {compareItems.length > 0 && (
        <a href="#/compare" className="compare-fab">
          Compare ({compareItems.length})
        </a>
      )}
    </div>
  );
}
