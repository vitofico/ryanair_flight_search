import { format } from "date-fns";
import clsx from "clsx";
import type { Itinerary } from "../api/client";
import { useCompare } from "../context/CompareContext";

interface ItineraryCardProps {
  itinerary: Itinerary;
  showCompare?: boolean;
  showRemove?: boolean;
}

function formatDuration(minutes: number): string {
  const h = Math.floor(minutes / 60);
  const m = minutes % 60;
  return `${h}h ${m}m`;
}

function formatTime(iso: string): string {
  return format(new Date(iso), "HH:mm");
}

function formatDate(iso: string): string {
  return format(new Date(iso), "dd MMM");
}

export default function ItineraryCard({
  itinerary,
  showCompare = true,
  showRemove = false,
}: ItineraryCardProps) {
  const { first_leg, second_leg, connection_airport, connection_minutes, total_price, total_duration_minutes } = itinerary;
  const { has, toggle, remove } = useCompare();
  const selected = has(itinerary);

  return (
    <div className={clsx("itinerary-card", selected && "itinerary-card--selected")}>
      <div className="itinerary-legs">
        <div className="leg">
          <div className="leg-route">
            <span className="leg-airport">{first_leg.origin}</span>
            <span className="leg-arrow">&rarr;</span>
            <span className="leg-airport">{first_leg.destination}</span>
          </div>
          <div className="leg-times">
            <span>{formatTime(first_leg.departure_datetime)}</span>
            <span className="leg-date">{formatDate(first_leg.departure_datetime)}</span>
            <span className="leg-sep">-</span>
            <span>{formatTime(first_leg.arrival_datetime)}</span>
          </div>
          <div className="leg-meta">
            <span className="leg-flight">{first_leg.flight_number}</span>
            <span className="leg-price">{first_leg.currency} {first_leg.price}</span>
          </div>
        </div>

        <div className="connection-badge">
          <span className="connection-code">{connection_airport}</span>
          <span className="connection-time">{formatDuration(connection_minutes)}</span>
        </div>

        <div className="leg">
          <div className="leg-route">
            <span className="leg-airport">{second_leg.origin}</span>
            <span className="leg-arrow">&rarr;</span>
            <span className="leg-airport">{second_leg.destination}</span>
          </div>
          <div className="leg-times">
            <span>{formatTime(second_leg.departure_datetime)}</span>
            <span className="leg-date">{formatDate(second_leg.departure_datetime)}</span>
            <span className="leg-sep">-</span>
            <span>{formatTime(second_leg.arrival_datetime)}</span>
          </div>
          <div className="leg-meta">
            <span className="leg-flight">{second_leg.flight_number}</span>
            <span className="leg-price">{second_leg.currency} {second_leg.price}</span>
          </div>
        </div>
      </div>

      <div className="itinerary-summary">
        <span className="itinerary-total-price">
          {first_leg.currency} {total_price}
        </span>
        <span className="itinerary-duration">
          {formatDuration(total_duration_minutes)}
        </span>
        {showCompare && (
          <button
            className={clsx("btn-compare", selected && "btn-compare--active")}
            onClick={() => toggle(itinerary)}
            title={selected ? "Remove from comparison" : "Add to comparison"}
          >
            {selected ? "Added" : "Compare"}
          </button>
        )}
        {showRemove && (
          <button
            className="btn-compare btn-compare--remove"
            onClick={() => remove(itinerary)}
            title="Remove from comparison"
          >
            Remove
          </button>
        )}
      </div>
    </div>
  );
}
