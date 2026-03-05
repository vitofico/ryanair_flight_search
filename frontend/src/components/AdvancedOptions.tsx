import { useState } from "react";

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

  return (
    <div className="advanced-options">
      <button
        type="button"
        className="advanced-toggle"
        onClick={() => setOpen(!open)}
      >
        {open ? "Hide" : "Show"} Advanced Options
      </button>
      {open && (
        <div className="advanced-body">
          <div className="field-row">
            <div className="field">
              <label className="field-label">Currency</label>
              <input
                type="text"
                className="field-input"
                value={currency}
                maxLength={3}
                onChange={(e) => onCurrencyChange(e.target.value.toUpperCase())}
              />
            </div>
            <div className="field">
              <label className="field-label">Min Connection (min)</label>
              <input
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
              <label className="field-label">Max Connection (hrs)</label>
              <input
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
