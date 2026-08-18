import { useId, useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { discoverConnections } from "../api/client";
import clsx from "clsx";

interface ConnectionsPanelProps {
  value: string;
  onChange: (v: string) => void;
  origin: string;
  destination: string;
}

export default function ConnectionsPanel({
  value,
  onChange,
  origin,
  destination,
}: ConnectionsPanelProps) {
  const inputId = useId();
  const [discoverError, setDiscoverError] = useState<string | null>(null);

  const discover = useMutation({
    mutationFn: () => discoverConnections(origin, destination),
    onSuccess(data) {
      onChange(data.connections.join(", "));
      setDiscoverError(null);
    },
    onError(err) {
      setDiscoverError(
        err instanceof Error ? err.message : "Discovery failed",
      );
    },
  });

  const canDiscover = /^[A-Z]{3}$/.test(origin) && /^[A-Z]{3}$/.test(destination);

  return (
    <div className="field">
      <label className="field-label" htmlFor={inputId}>
        Connection Airports
      </label>
      <div className="connections-row">
        <input
          id={inputId}
          type="text"
          className="field-input"
          value={value}
          placeholder="e.g. BGY, CRL, STN"
          onChange={(e) => onChange(e.target.value.toUpperCase())}
        />
        <button
          type="button"
          className={clsx("btn btn-secondary", discover.isPending && "btn--loading")}
          disabled={!canDiscover || discover.isPending}
          onClick={() => discover.mutate()}
        >
          {discover.isPending ? "Discovering..." : "Discover"}
        </button>
      </div>
      {discoverError && (
        <span className="field-error">{discoverError}</span>
      )}
    </div>
  );
}
