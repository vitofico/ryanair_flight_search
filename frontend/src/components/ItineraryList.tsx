import { useMemo, useState } from "react";
import type { SearchResult, Itinerary } from "../api/client";
import ItineraryCard from "./ItineraryCard";

interface ItineraryListProps {
  result: SearchResult;
}

type SortKey = "price" | "duration" | "layover";

function sortItineraries(items: Itinerary[], key: SortKey): Itinerary[] {
  const sorted = [...items];
  sorted.sort((a, b) => {
    switch (key) {
      case "price":
        return parseFloat(a.total_price) - parseFloat(b.total_price);
      case "duration":
        return a.total_duration_minutes - b.total_duration_minutes;
      case "layover":
        return a.connection_minutes - b.connection_minutes;
    }
  });
  return sorted;
}

function downloadJson(result: SearchResult) {
  const blob = new Blob([JSON.stringify(result, null, 2)], {
    type: "application/json",
  });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = "flight-results.json";
  a.click();
  URL.revokeObjectURL(url);
}

export default function ItineraryList({ result }: ItineraryListProps) {
  const [sortKey, setSortKey] = useState<SortKey>("price");
  const sorted = useMemo(
    () => sortItineraries(result.itineraries, sortKey),
    [result.itineraries, sortKey],
  );

  return (
    <div className="itinerary-list">
      <div className="results-toolbar">
        <span className="results-count">
          Found {result.count} itinerar{result.count === 1 ? "y" : "ies"}
        </span>
        <div className="results-actions">
          <label className="sort-label">
            Sort by:
            <span className="select-wrap">
              <select
                value={sortKey}
                onChange={(e) => setSortKey(e.target.value as SortKey)}
              >
                <option value="price">Price</option>
                <option value="duration">Duration</option>
                <option value="layover">Layover</option>
              </select>
            </span>
          </label>
          <button
            className="btn btn-secondary"
            onClick={() => downloadJson(result)}
          >
            Export JSON
          </button>
        </div>
      </div>
      <div className="itinerary-cards">
        {sorted.map((it, i) => (
          <ItineraryCard key={i} itinerary={it} />
        ))}
      </div>
    </div>
  );
}
