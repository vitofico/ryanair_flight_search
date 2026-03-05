const BASE = "/api/v1";

export interface DiscoverResponse {
  origin: string;
  destination: string;
  connections: string[];
}

export interface SearchParams {
  origin: string;
  destination: string;
  connections: string[];
  start: string;
  end: string;
  currency: string;
  min_connection_minutes: number;
  max_connection_hours: number;
  allow_overnight: boolean;
  no_cache: boolean;
}

export interface JobCreated {
  job_id: string;
}

export interface ProgressInfo {
  connection: string;
  current: number;
  total: number;
  message: string;
}

export interface JobStatus {
  job_id: string;
  status: "queued" | "running" | "completed" | "failed";
  progress: ProgressInfo | null;
  error: string | null;
}

export interface FlightLeg {
  origin: string;
  destination: string;
  flight_number: string;
  departure_datetime: string;
  arrival_datetime: string;
  price: string;
  currency: string;
}

export interface Itinerary {
  first_leg: FlightLeg;
  second_leg: FlightLeg;
  connection_airport: string;
  connection_minutes: number;
  total_price: string;
  total_duration_minutes: number;
}

export interface SearchResult {
  count: number;
  itineraries: Itinerary[];
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, init);
  if (!res.ok) {
    const body = await res.text().catch(() => "");
    throw new Error(`API error ${res.status}: ${body || res.statusText}`);
  }
  return res.json() as Promise<T>;
}

export interface Airport {
  code: string;
  name: string;
  city: string;
  country: string;
}

export function getAirports(): Promise<Airport[]> {
  return request<Airport[]>("/airports");
}

export function discoverConnections(
  origin: string,
  destination: string,
  noCache = false,
): Promise<DiscoverResponse> {
  return request<DiscoverResponse>("/discover", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ origin, destination, no_cache: noCache }),
  });
}

export function createSearchJob(params: SearchParams): Promise<JobCreated> {
  return request<JobCreated>("/search", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(params),
  });
}

export function getJobStatus(jobId: string): Promise<JobStatus> {
  return request<JobStatus>(`/search/${encodeURIComponent(jobId)}`);
}

export function getSearchResult(jobId: string): Promise<SearchResult> {
  return request<SearchResult>(
    `/search/${encodeURIComponent(jobId)}/result`,
  );
}

export function cancelJob(
  jobId: string,
): Promise<{ job_id: string; status: string }> {
  return request(`/search/${encodeURIComponent(jobId)}`, {
    method: "DELETE",
  });
}

export interface JobEventHandlers {
  onProgress: (p: ProgressInfo) => void;
  onCompleted: (jobId: string) => void;
  onFailed: (jobId: string, error: string) => void;
  onError: (err: Event) => void;
}

export function subscribeToJobEvents(
  jobId: string,
  handlers: JobEventHandlers,
): () => void {
  const url = `${BASE}/search/${encodeURIComponent(jobId)}/events`;
  let es: EventSource | null = new EventSource(url);
  let pollTimer: ReturnType<typeof setInterval> | null = null;
  let closed = false;

  function startPolling() {
    if (pollTimer || closed) return;
    pollTimer = setInterval(async () => {
      try {
        const status = await getJobStatus(jobId);
        if (status.progress) handlers.onProgress(status.progress);
        if (status.status === "completed") {
          handlers.onCompleted(jobId);
          cleanup();
        } else if (status.status === "failed") {
          handlers.onFailed(jobId, status.error ?? "Unknown error");
          cleanup();
        }
      } catch {
        // keep polling
      }
    }, 2000);
  }

  es.addEventListener("progress", (e) => {
    handlers.onProgress(JSON.parse(e.data) as ProgressInfo);
  });

  es.addEventListener("completed", (e) => {
    const data = JSON.parse(e.data) as { job_id: string };
    handlers.onCompleted(data.job_id);
    cleanup();
  });

  es.addEventListener("failed", (e) => {
    const data = JSON.parse(e.data) as { job_id: string; error: string };
    handlers.onFailed(data.job_id, data.error);
    cleanup();
  });

  es.onerror = (e) => {
    es?.close();
    es = null;
    handlers.onError(e);
    startPolling();
  };

  function cleanup() {
    closed = true;
    es?.close();
    es = null;
    if (pollTimer) {
      clearInterval(pollTimer);
      pollTimer = null;
    }
  }

  return cleanup;
}
