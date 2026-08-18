import { useMemo, useState } from "react";
import { format } from "date-fns";
import { useCompare } from "../context/CompareContext";
import type { Itinerary } from "../api/client";
import ItineraryCard from "../components/ItineraryCard";

type SortKey = "price" | "duration" | "layover" | "departure";

function sortItems(items: Itinerary[], key: SortKey): Itinerary[] {
  const sorted = [...items];
  sorted.sort((a, b) => {
    switch (key) {
      case "price":
        return parseFloat(a.total_price) - parseFloat(b.total_price);
      case "duration":
        return a.total_duration_minutes - b.total_duration_minutes;
      case "layover":
        return a.connection_minutes - b.connection_minutes;
      case "departure":
        return a.first_leg.departure_datetime.localeCompare(b.first_leg.departure_datetime);
    }
  });
  return sorted;
}

function formatDuration(minutes: number): string {
  const h = Math.floor(minutes / 60);
  const m = minutes % 60;
  return `${h}h ${m}m`;
}

function downloadFile(content: string, filename: string, mime: string) {
  const blob = new Blob([content], { type: mime });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

function exportJson(items: Itinerary[]) {
  downloadFile(
    JSON.stringify({ count: items.length, itineraries: items }, null, 2),
    "comparison.json",
    "application/json",
  );
}

function exportCsv(items: Itinerary[]) {
  const header = [
    "Origin",
    "Connection",
    "Destination",
    "Leg 1 Flight",
    "Leg 1 Departure",
    "Leg 1 Arrival",
    "Leg 1 Price",
    "Layover",
    "Leg 2 Flight",
    "Leg 2 Departure",
    "Leg 2 Arrival",
    "Leg 2 Price",
    "Total Price",
    "Total Duration",
    "Currency",
  ];
  const rows = items.map((it) => [
    it.first_leg.origin,
    it.connection_airport,
    it.second_leg.destination,
    it.first_leg.flight_number,
    it.first_leg.departure_datetime,
    it.first_leg.arrival_datetime,
    it.first_leg.price,
    formatDuration(it.connection_minutes),
    it.second_leg.flight_number,
    it.second_leg.departure_datetime,
    it.second_leg.arrival_datetime,
    it.second_leg.price,
    it.total_price,
    formatDuration(it.total_duration_minutes),
    it.first_leg.currency,
  ]);
  const csv = [header, ...rows].map((r) => r.map((c) => `"${c}"`).join(",")).join("\n");
  downloadFile(csv, "comparison.csv", "text/csv");
}

export default function ComparePage() {
  const { items, clear } = useCompare();
  const [sortKey, setSortKey] = useState<SortKey>("price");

  const sorted = useMemo(() => sortItems(items, sortKey), [items, sortKey]);

  const cheapest = useMemo(() => {
    if (items.length === 0) return null;
    return items.reduce((a, b) =>
      parseFloat(a.total_price) <= parseFloat(b.total_price) ? a : b,
    );
  }, [items]);

  const fastest = useMemo(() => {
    if (items.length === 0) return null;
    return items.reduce((a, b) =>
      a.total_duration_minutes <= b.total_duration_minutes ? a : b,
    );
  }, [items]);

  const routes = useMemo(() => {
    const set = new Set(items.map((it) => `${it.first_leg.origin} → ${it.connection_airport} → ${it.second_leg.destination}`));
    return [...set];
  }, [items]);

  return (
    <div className="page page--wide">
      <header className="page-header">
        <div className="page-header-inner">
          <h1>Compare Flights</h1>
          <p>
            {items.length === 0
              ? "No flights selected"
              : `${items.length} flight${items.length === 1 ? "" : "s"} selected`}
          </p>
        </div>
      </header>

      <main className="page-main">
        <div className="compare-nav">
          <a href="#/" className="btn btn-secondary">Back to Search</a>
        </div>

        {items.length === 0 ? (
          <div className="compare-empty">
            <p>No flights added to comparison yet.</p>
            <p>Search for flights and click "Compare" to add them here.</p>
          </div>
        ) : (
          <>
            {/* Summary strip */}
            <div className="compare-summary">
              <div className="compare-summary-item">
                <span className="compare-summary-label">Routes</span>
                <span className="compare-summary-value">{routes.join(" / ")}</span>
              </div>
              {cheapest && (
                <div className="compare-summary-item">
                  <span className="compare-summary-label">Cheapest</span>
                  <span className="compare-summary-value compare-summary-value--highlight">
                    {cheapest.first_leg.currency} {cheapest.total_price}
                    <span className="compare-summary-detail">
                      {" "}via {cheapest.connection_airport} ({format(new Date(cheapest.first_leg.departure_datetime), "dd MMM")})
                    </span>
                  </span>
                </div>
              )}
              {fastest && (
                <div className="compare-summary-item">
                  <span className="compare-summary-label">Fastest</span>
                  <span className="compare-summary-value compare-summary-value--highlight">
                    {formatDuration(fastest.total_duration_minutes)}
                    <span className="compare-summary-detail">
                      {" "}via {fastest.connection_airport} ({format(new Date(fastest.first_leg.departure_datetime), "dd MMM")})
                    </span>
                  </span>
                </div>
              )}
            </div>

            {/* Toolbar */}
            <div className="results-toolbar">
              <label className="sort-label">
                Sort by:
                <span className="select-wrap">
                  <select value={sortKey} onChange={(e) => setSortKey(e.target.value as SortKey)}>
                    <option value="price">Price</option>
                    <option value="duration">Duration</option>
                    <option value="layover">Layover</option>
                    <option value="departure">Departure</option>
                  </select>
                </span>
              </label>
              <div className="results-actions">
                <button className="btn btn-secondary" onClick={() => exportJson(items)}>
                  Export JSON
                </button>
                <button className="btn btn-secondary" onClick={() => exportCsv(items)}>
                  Export CSV
                </button>
                <button className="btn btn-danger" onClick={clear}>
                  Clear All
                </button>
              </div>
            </div>

            {/* Cards */}
            <div className="itinerary-cards">
              {sorted.map((it, i) => (
                <ItineraryCard key={i} itinerary={it} showCompare={false} showRemove />
              ))}
            </div>
          </>
        )}
      </main>
    </div>
  );
}
