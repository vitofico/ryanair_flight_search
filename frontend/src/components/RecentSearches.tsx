import type { SearchParams } from "../api/client";

interface RecentSearchesProps {
  searches: SearchParams[];
  onSelect: (params: SearchParams) => void;
}

function formatDate(iso: string): string {
  const d = new Date(iso + "T00:00:00");
  return d.toLocaleDateString(undefined, { month: "short", day: "numeric" });
}

export default function RecentSearches({ searches, onSelect }: RecentSearchesProps) {
  return (
    <div className="recent-searches">
      <h3 className="recent-title">Recent Searches</h3>
      <div className="recent-cards">
        {searches.map((s, i) => (
          <button
            key={`${s.origin}-${s.destination}-${s.start}-${i}`}
            className="recent-card"
            onClick={() => onSelect(s)}
          >
            <span className="recent-route">
              {s.origin} → {s.destination}
            </span>
            <span className="recent-dates">
              {formatDate(s.start)} – {formatDate(s.end)}
            </span>
            <span className="recent-via">
              via {s.connections.join(", ")}
            </span>
          </button>
        ))}
      </div>
    </div>
  );
}
