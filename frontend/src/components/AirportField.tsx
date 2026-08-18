import { useState, useRef, useEffect, useMemo, useId } from "react";
import { useQuery } from "@tanstack/react-query";
import clsx from "clsx";
import { getAirports, type Airport } from "../api/client";

interface AirportFieldProps {
  label: string;
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
}

const IATA_RE = /^[A-Z]{3}$/;

function matchAirport(airport: Airport, query: string): boolean {
  const q = query.toLowerCase();
  return (
    airport.code.toLowerCase().includes(q) ||
    airport.name.toLowerCase().includes(q) ||
    airport.city.toLowerCase().includes(q) ||
    airport.country.toLowerCase().includes(q)
  );
}

export default function AirportField({
  label,
  value,
  onChange,
  placeholder = "Search city or IATA code",
}: AirportFieldProps) {
  const inputId = useId();
  const [inputValue, setInputValue] = useState(value);
  const [open, setOpen] = useState(false);
  const [touched, setTouched] = useState(false);
  const [highlightIndex, setHighlightIndex] = useState(-1);
  const wrapperRef = useRef<HTMLDivElement>(null);
  const listRef = useRef<HTMLUListElement>(null);

  const { data: airports = [] } = useQuery({
    queryKey: ["airports"],
    queryFn: getAirports,
    staleTime: 1000 * 60 * 60,
  });

  const isValid = IATA_RE.test(value);
  const showError = touched && value.length > 0 && !isValid;

  const selectedAirport = useMemo(
    () => airports.find((a) => a.code === value),
    [airports, value],
  );

  const suggestions = useMemo(() => {
    if (inputValue.length === 0) return [];
    if (selectedAirport && inputValue === formatDisplay(selectedAirport))
      return [];
    return airports.filter((a) => matchAirport(a, inputValue)).slice(0, 8);
  }, [airports, inputValue, selectedAirport]);

  useEffect(() => {
    if (value && !inputValue && selectedAirport) {
      setInputValue(formatDisplay(selectedAirport));
    }
  }, [value, selectedAirport, inputValue]);

  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (
        wrapperRef.current &&
        !wrapperRef.current.contains(e.target as Node)
      ) {
        setOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  useEffect(() => {
    setHighlightIndex(-1);
  }, [suggestions.length]);

  useEffect(() => {
    if (highlightIndex >= 0 && listRef.current) {
      const item = listRef.current.children[highlightIndex] as HTMLElement;
      item?.scrollIntoView({ block: "nearest" });
    }
  }, [highlightIndex]);

  function handleInputChange(raw: string) {
    setInputValue(raw);
    setOpen(true);

    const upper = raw.toUpperCase().trim();
    if (IATA_RE.test(upper)) {
      onChange(upper);
    } else {
      if (value !== "") onChange("");
    }
  }

  function selectAirport(airport: Airport) {
    onChange(airport.code);
    setInputValue(formatDisplay(airport));
    setOpen(false);
  }

  function handleKeyDown(e: React.KeyboardEvent) {
    if (!open || suggestions.length === 0) return;

    if (e.key === "ArrowDown") {
      e.preventDefault();
      setHighlightIndex((i) =>
        i < suggestions.length - 1 ? i + 1 : 0,
      );
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setHighlightIndex((i) =>
        i > 0 ? i - 1 : suggestions.length - 1,
      );
    } else if (e.key === "Enter" && highlightIndex >= 0 && suggestions[highlightIndex]) {
      e.preventDefault();
      selectAirport(suggestions[highlightIndex]);
    } else if (e.key === "Escape") {
      setOpen(false);
    }
  }

  function handleFocus() {
    if (inputValue.length > 0 && suggestions.length > 0) {
      setOpen(true);
    }
  }

  function handleBlur() {
    setTouched(true);
    setTimeout(() => setOpen(false), 150);
  }

  return (
    <div className="field airport-field" ref={wrapperRef}>
      <label className="field-label" htmlFor={inputId}>
        {label}
      </label>
      <input
        id={inputId}
        type="text"
        className={clsx("field-input", showError && "field-input--error")}
        value={inputValue}
        placeholder={placeholder}
        onChange={(e) => handleInputChange(e.target.value)}
        onFocus={handleFocus}
        onBlur={handleBlur}
        onKeyDown={handleKeyDown}
        role="combobox"
        aria-expanded={open && suggestions.length > 0}
        aria-autocomplete="list"
        autoComplete="off"
      />
      {open && suggestions.length > 0 && (
        <ul className="airport-dropdown" ref={listRef} role="listbox">
          {suggestions.map((a, i) => (
            <li
              key={a.code}
              className={clsx(
                "airport-option",
                i === highlightIndex && "airport-option--active",
              )}
              role="option"
              aria-selected={i === highlightIndex}
              onMouseDown={() => selectAirport(a)}
              onMouseEnter={() => setHighlightIndex(i)}
            >
              <span className="airport-option-code">{a.code}</span>
              <span className="airport-option-name">
                {a.city || a.name}
                {a.country ? `, ${a.country}` : ""}
              </span>
            </li>
          ))}
        </ul>
      )}
      {showError && (
        <span className="field-error">Select an airport or enter 3-letter IATA code</span>
      )}
    </div>
  );
}

function formatDisplay(airport: Airport): string {
  const city = airport.city || airport.name;
  return city ? `${airport.code} - ${city}` : airport.code;
}
