import { useId, useState } from "react";
import clsx from "clsx";

interface AdvancedOptionsProps {
  currency: string;
  onCurrencyChange: (v: string) => void;
  minConnectionMinutes: number;
  onMinConnectionMinutesChange: (v: number) => void;
  maxConnectionHours: number;
  onMaxConnectionHoursChange: (v: number) => void;
  allowOvernight: boolean;
  onAllowOvernightChange: (v: boolean) => void;
}

export default function AdvancedOptions({
  currency,
  onCurrencyChange,
  minConnectionMinutes,
  onMinConnectionMinutesChange,
  maxConnectionHours,
  onMaxConnectionHoursChange,
  allowOvernight,
  onAllowOvernightChange,
}: AdvancedOptionsProps) {
  const [open, setOpen] = useState(false);
  const bodyId = useId();
  const currencyId = useId();
  const minId = useId();
  const maxId = useId();

  return (
    <div className="advanced-options">
      <button
        type="button"
        className="advanced-toggle"
        onClick={() => setOpen(!open)}
        aria-expanded={open}
        aria-controls={bodyId}
      >
        {open ? "Hide" : "Show"} Advanced Options
        <span
          className={clsx("advanced-chevron", open && "advanced-chevron--open")}
          aria-hidden="true"
        />
      </button>
      {open && (
        <div className="advanced-body" id={bodyId}>
          <div className="field-row field-row--triple">
            <div className="field">
              <label className="field-label" htmlFor={currencyId}>
                Currency
              </label>
              <input
                id={currencyId}
                type="text"
                className="field-input"
                value={currency}
                maxLength={3}
                onChange={(e) => onCurrencyChange(e.target.value.toUpperCase())}
              />
            </div>
            <div className="field">
              <label className="field-label" htmlFor={minId}>
                Min Connection (min)
              </label>
              <input
                id={minId}
                type="number"
                className="field-input"
                value={minConnectionMinutes}
                min={0}
                onChange={(e) =>
                  onMinConnectionMinutesChange(Number(e.target.value))
                }
              />
            </div>
            <div className="field">
              <label className="field-label" htmlFor={maxId}>
                Max Connection (hrs)
              </label>
              <input
                id={maxId}
                type="number"
                className="field-input"
                value={maxConnectionHours}
                min={1}
                onChange={(e) =>
                  onMaxConnectionHoursChange(Number(e.target.value))
                }
              />
            </div>
          </div>
          <label className="checkbox-label">
            <input
              type="checkbox"
              checked={allowOvernight}
              onChange={(e) => onAllowOvernightChange(e.target.checked)}
            />
            Allow overnight connections
          </label>
        </div>
      )}
    </div>
  );
}
