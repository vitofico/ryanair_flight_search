import { createContext, useContext, useState, useCallback, type ReactNode } from "react";
import type { Itinerary } from "../api/client";

function itineraryKey(it: Itinerary): string {
  return `${it.first_leg.flight_number}-${it.first_leg.departure_datetime}|${it.second_leg.flight_number}-${it.second_leg.departure_datetime}`;
}

interface CompareContextValue {
  items: Itinerary[];
  add: (it: Itinerary) => void;
  remove: (it: Itinerary) => void;
  has: (it: Itinerary) => boolean;
  toggle: (it: Itinerary) => void;
  clear: () => void;
}

const CompareContext = createContext<CompareContextValue | null>(null);

export function CompareProvider({ children }: { children: ReactNode }) {
  const [items, setItems] = useState<Itinerary[]>([]);

  const has = useCallback(
    (it: Itinerary) => items.some((x) => itineraryKey(x) === itineraryKey(it)),
    [items],
  );

  const add = useCallback((it: Itinerary) => {
    setItems((prev) => {
      const key = itineraryKey(it);
      if (prev.some((x) => itineraryKey(x) === key)) return prev;
      return [...prev, it];
    });
  }, []);

  const remove = useCallback((it: Itinerary) => {
    setItems((prev) => prev.filter((x) => itineraryKey(x) !== itineraryKey(it)));
  }, []);

  const toggle = useCallback((it: Itinerary) => {
    setItems((prev) => {
      const key = itineraryKey(it);
      if (prev.some((x) => itineraryKey(x) === key)) {
        return prev.filter((x) => itineraryKey(x) !== key);
      }
      return [...prev, it];
    });
  }, []);

  const clear = useCallback(() => setItems([]), []);

  return (
    <CompareContext.Provider value={{ items, add, remove, has, toggle, clear }}>
      {children}
    </CompareContext.Provider>
  );
}

export function useCompare(): CompareContextValue {
  const ctx = useContext(CompareContext);
  if (!ctx) throw new Error("useCompare must be used within CompareProvider");
  return ctx;
}
