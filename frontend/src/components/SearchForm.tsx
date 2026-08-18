import { useState, useEffect, type FormEvent } from "react";
import type { SearchParams } from "../api/client";
import AirportField from "./AirportField";
import DateRangeField from "./DateRangeField";
import ConnectionsPanel from "./ConnectionsPanel";
import AdvancedOptions from "./AdvancedOptions";

interface SearchFormProps {
  onSearch: (params: SearchParams) => void;
  initialParams?: SearchParams | null;
}

const IATA_RE = /^[A-Z]{3}$/;

function parseConnections(raw: string): string[] {
  return raw
    .split(",")
    .map((s) => s.trim())
    .filter((s) => IATA_RE.test(s));
}

export default function SearchForm({ onSearch, initialParams }: SearchFormProps) {
  const [origin, setOrigin] = useState("");
  const [destination, setDestination] = useState("");
  const [start, setStart] = useState("");
  const [end, setEnd] = useState("");
  const [connectionsRaw, setConnectionsRaw] = useState("");
  const [currency, setCurrency] = useState("EUR");
  const [minConnectionMinutes, setMinConnectionMinutes] = useState(60);
  const [maxConnectionHours, setMaxConnectionHours] = useState(8);
  const [allowOvernight, setAllowOvernight] = useState(false);
  const [noCache, setNoCache] = useState(false);

  useEffect(() => {
    if (initialParams) {
      setOrigin(initialParams.origin);
      setDestination(initialParams.destination);
      setStart(initialParams.start);
      setEnd(initialParams.end);
      setConnectionsRaw(initialParams.connections.join(", "));
      setCurrency(initialParams.currency);
      setMinConnectionMinutes(initialParams.min_connection_minutes);
      setMaxConnectionHours(initialParams.max_connection_hours);
      setAllowOvernight(initialParams.allow_overnight);
      setNoCache(false);
    }
  }, [initialParams]);

  const connections = parseConnections(connectionsRaw);
  const validDates = start !== "" && end !== "" && start <= end;
  const canSubmit =
    IATA_RE.test(origin) &&
    IATA_RE.test(destination) &&
    connections.length > 0 &&
    validDates;

  function handleSubmit(e: FormEvent) {
    e.preventDefault();
    if (!canSubmit) return;
    onSearch({
      origin,
      destination,
      connections,
      start,
      end,
      currency,
      min_connection_minutes: minConnectionMinutes,
      max_connection_hours: maxConnectionHours,
      allow_overnight: allowOvernight,
      no_cache: noCache,
    });
  }

  return (
    <form className="search-form" onSubmit={handleSubmit}>
      <div className="search-form-body">
        <div className="field-row field-row--route">
          <AirportField
            label="Origin"
            value={origin}
            onChange={setOrigin}
            placeholder="e.g. CRV"
          />
          <span className="route-arrow" aria-hidden="true">
            &rarr;
          </span>
          <AirportField
            label="Destination"
            value={destination}
            onChange={setDestination}
            placeholder="e.g. SVQ"
          />
        </div>

        <DateRangeField
          start={start}
          end={end}
          onStartChange={setStart}
          onEndChange={setEnd}
        />

        <ConnectionsPanel
          value={connectionsRaw}
          onChange={setConnectionsRaw}
          origin={origin}
          destination={destination}
        />

        <AdvancedOptions
          currency={currency}
          onCurrencyChange={setCurrency}
          minConnectionMinutes={minConnectionMinutes}
          onMinConnectionMinutesChange={setMinConnectionMinutes}
          maxConnectionHours={maxConnectionHours}
          onMaxConnectionHoursChange={setMaxConnectionHours}
          allowOvernight={allowOvernight}
          onAllowOvernightChange={setAllowOvernight}
        />
      </div>

      <div className="search-form-footer">
        <label className="checkbox-label">
          <input
            type="checkbox"
            checked={noCache}
            onChange={(e) => setNoCache(e.target.checked)}
          />
          Skip cache (force fresh results)
        </label>
        <button type="submit" className="btn btn-primary btn-search" disabled={!canSubmit}>
          Search Flights
        </button>
      </div>
    </form>
  );
}
